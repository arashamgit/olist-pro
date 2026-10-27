"""Business metrics: every number reported in the notebooks and the report.

Design rules that this module enforces:

* **No metric is computed across grains.**  ``order_*`` frames are one row per
  order, ``item_*`` frames one row per item line; anything that mixes them
  states its grain in the function name and its denominator explicitly.
* **Every percentage reports its denominator.**  Group tables carry an ``n``
  column next to the ``pct`` column so a reader can always audit the base.
* **Small groups are surfaced, not hidden.**  Functions accept a minimum sample
  size and return the sample column even when a group is filtered out.
* **Averages of scores use distinct orders**, never item rows, so no customer
  opinion is counted twice.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import (
    CURRENCY,
    MIN_ORDERS_PER_STATE,
    MIN_REVIEWS_PER_GROUP,
)
from .features import Dataset

WEEKDAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
MONTH_ORDER = list(range(1, 13))
DELAY_BUCKET_ORDER = ["on_time_or_early", "1_3_days", "4_7_days", "more_than_7_days"]


def pct(part: float, whole: float) -> float:
    """Percentage with an explicit denominator, safe against a zero base.

    Always returns a plain ``float`` so every metric value can be serialised to
    JSON without a NumPy type leaking out of the analysis layer.
    """
    if not whole:
        return 0.0
    return float(round(100.0 * float(part) / float(whole), 4))


def _round(frame: pd.DataFrame, digits: int = 2) -> pd.DataFrame:
    """Round numeric columns for presentation, but never the share columns.

    Percentages keep their full four-decimal precision so that a group of
    percentages still sums to exactly 100 and the reconciliation tests in
    ``tests/test_metrics.py`` stay meaningful. Rounding 73 category shares to
    two decimals, for example, would make the column add up to 99.97.
    """
    numeric = frame.select_dtypes(include=["number", "Int64", "Float64"]).columns
    pct_like = [
        column
        for column in numeric
        if column.startswith("pct")
        or column.startswith("cum")
        or column.endswith("_pct")
    ]
    to_round = [column for column in numeric if column not in pct_like]
    frame[to_round] = frame[to_round].round(digits)
    return frame


# =========================================================================== #
# 5. Orders and business trend
# =========================================================================== #
def order_status_summary(ds: Dataset) -> pd.DataFrame:
    """Question 5.1 - order count and share per ``order_status``."""
    orders = ds.orders
    counts = orders["order_status"].value_counts()
    out = pd.DataFrame({"order_status": counts.index, "n_orders": counts.to_numpy()})
    out["pct_orders"] = out["n_orders"].map(lambda n: pct(n, len(orders)))
    out["is_delivered"] = out["order_status"].eq("delivered")
    return out.reset_index(drop=True)


def monthly_orders(ds: Dataset) -> pd.DataFrame:
    """Question 5.2 - orders per calendar month with a 3-month rolling mean."""
    orders = ds.orders
    grouped = orders.groupby("purchase_ym", as_index=False).agg(
        n_orders=("order_id", "size"),
        n_delivered=("is_delivered", "sum"),
        in_core_window=("in_core_window", "first"),
    )
    grouped = grouped.sort_values("purchase_ym").reset_index(drop=True)
    grouped["order_month"] = pd.PeriodIndex(grouped["purchase_ym"], freq="M").to_timestamp()
    grouped["n_orders_rolling3"] = grouped["n_orders"].rolling(3, min_periods=1).mean().round(2)
    grouped["pct_of_total"] = grouped["n_orders"].map(lambda n: pct(n, len(orders)))
    return grouped


def year_month_matrix(ds: Dataset) -> pd.DataFrame:
    """Question 5.2 - orders by year x month, with a total column."""
    orders = ds.orders
    matrix = (
        orders.pivot_table(
            index="purchase_year", columns="purchase_month", values="order_id",
            aggfunc="size", fill_value=0,
        )
        .reindex(columns=MONTH_ORDER, fill_value=0)
        .sort_index()
    )
    matrix.columns = [f"month_{m:02d}" for m in matrix.columns]
    matrix["total"] = matrix.sum(axis=1)
    matrix["avg_per_active_month"] = (
        matrix.iloc[:, :-1].replace(0, np.nan).mean(axis=1).round(1)
    )
    return matrix.reset_index()


def weekday_orders(ds: Dataset) -> pd.DataFrame:
    """Question 5.3 - orders per weekday (calendar order, not alphabetical)."""
    orders = ds.orders
    counts = orders["purchase_weekday"].value_counts().reindex(WEEKDAY_ORDER, fill_value=0)
    out = pd.DataFrame({"weekday": counts.index, "n_orders": counts.to_numpy()})
    out["pct_orders"] = out["n_orders"].map(lambda n: pct(n, len(orders)))
    out["avg_orders_per_day"] = [
        round(n / orders.loc[orders["purchase_weekday"] == day, "purchase_date"].nunique(), 1)
        if orders.loc[orders["purchase_weekday"] == day, "purchase_date"].nunique()
        else 0.0
        for day, n in zip(out["weekday"], out["n_orders"])
    ]
    return out


def top_months(ds: Dataset, k: int = 5) -> pd.DataFrame:
    """Question 5.4 - the k busiest calendar months."""
    monthly = monthly_orders(ds).sort_values("n_orders", ascending=False).head(k)
    return monthly[["purchase_ym", "n_orders", "pct_of_total"]].reset_index(drop=True)


def growth_evidence(ds: Dataset) -> dict:
    """Questions 5.2/5.4 - numeric evidence on growth vs seasonality."""
    monthly = monthly_orders(ds)
    core = monthly[monthly["in_core_window"]].reset_index(drop=True)
    first, last = core.iloc[0], core.iloc[-1]

    orders = ds.orders
    jan_aug_2017 = int(((orders["purchase_ym"] >= "2017-01") & (orders["purchase_ym"] <= "2017-08")).sum())
    jan_aug_2018 = int(((orders["purchase_ym"] >= "2018-01") & (orders["purchase_ym"] <= "2018-08")).sum())

    first_six = core.head(6)["n_orders"].mean()
    last_six = core.tail(6)["n_orders"].mean()

    peak = core.sort_values("n_orders", ascending=False).iloc[0]
    trough = core.sort_values("n_orders").iloc[0]
    return {
        "total_orders": int(len(orders)),
        "core_orders": int(orders["in_core_window"].sum()),
        "core_months": int(len(core)),
        "first_core_month": first["purchase_ym"],
        "first_core_month_orders": int(first["n_orders"]),
        "last_core_month": last["purchase_ym"],
        "last_core_month_orders": int(last["n_orders"]),
        "peak_month": peak["purchase_ym"],
        "peak_month_orders": int(peak["n_orders"]),
        "trough_month": trough["purchase_ym"],
        "trough_month_orders": int(trough["n_orders"]),
        "jan_aug_2017_orders": jan_aug_2017,
        "jan_aug_2018_orders": jan_aug_2018,
        "yoy_jan_aug_pct_change": pct(jan_aug_2018 - jan_aug_2017, jan_aug_2017),
        "mean_orders_first_6_core_months": round(float(first_six), 1),
        "mean_orders_last_6_core_months": round(float(last_six), 1),
        "first6_to_last6_pct_change": pct(last_six - first_six, first_six),
        "peak_over_median_ratio": round(
            float(peak["n_orders"]) / float(core["n_orders"].median()), 3
        ),
    }


# =========================================================================== #
# 6. Customers and geography
# =========================================================================== #
def customer_overview(ds: Dataset) -> dict:
    """Question 6.1 - rows vs unique buyers vs unique people."""
    customers = ds.customers
    orders = ds.orders
    repeat = customers.groupby("customer_unique_id").size()
    return {
        "customer_rows": int(len(customers)),
        "unique_customer_id": int(customers["customer_id"].nunique()),
        "unique_people": int(customers["customer_unique_id"].nunique()),
        "repeat_people": int((repeat > 1).sum()),
        "repeat_share_pct": pct(int((repeat > 1).sum()), len(repeat)),
        "max_orders_one_person": int(repeat.max()),
        "orders": int(len(orders)),
        "orders_per_person": round(len(orders) / customers["customer_unique_id"].nunique(), 4),
    }


def customers_by_state(ds: Dataset, top: int | None = None, by: str = "people") -> pd.DataFrame:
    """Question 6.2 - customers per state.

    ``by="people"`` counts distinct buyers (``customer_unique_id``), which is the
    correct base for "how many customers are there in this state".  ``by="rows"``
    counts customer records, i.e. orders, and is provided only for comparison.
    """
    customers = ds.customers
    if by == "people":
        grouped = customers.groupby("customer_state", as_index=False).agg(
            n_customers=("customer_unique_id", "nunique"),
            n_customer_rows=("customer_id", "size"),
        )
    else:
        grouped = customers.groupby("customer_state", as_index=False).agg(
            n_customers=("customer_id", "size"),
            n_customer_rows=("customer_id", "size"),
        )
    grouped = grouped.sort_values("n_customers", ascending=False).reset_index(drop=True)
    grouped["pct_customers"] = grouped["n_customers"].map(
        lambda n: pct(n, grouped["n_customers"].sum())
    )
    grouped["cum_pct"] = grouped["pct_customers"].cumsum().round(4)
    grouped["rank"] = grouped.index + 1
    return grouped.head(top) if top else grouped


def top_n_state_share(ds: Dataset, n: int = 5) -> dict:
    """Question 6.2 - share of the n largest states."""
    by_state = customers_by_state(ds)
    top = by_state.head(n)
    orders_by_state = (
        ds.orders.groupby("customer_state", as_index=False)
        .agg(n_orders=("order_id", "size"))
        .sort_values("n_orders", ascending=False)
    )
    return {
        "n": n,
        "states": ", ".join(top["customer_state"]),
        "customers_top_n": int(top["n_customers"].sum()),
        "customers_total": int(by_state["n_customers"].sum()),
        "top_n_customer_share_pct": pct(
            top["n_customers"].sum(), by_state["n_customers"].sum()
        ),
        "top_n_order_share_pct": pct(
            orders_by_state.head(n)["n_orders"].sum(), orders_by_state["n_orders"].sum()
        ),
        "n_states": int(len(by_state)),
    }


def customers_by_city(ds: Dataset, top: int = 10) -> pd.DataFrame:
    """Question 6.3 - busiest cities by distinct buyers."""
    cities = (
        ds.customers.groupby(["customer_city", "customer_state"], as_index=False)
        .agg(n_customers=("customer_unique_id", "nunique"))
        .sort_values("n_customers", ascending=False)
        .head(top)
        .reset_index(drop=True)
    )
    cities["pct_customers"] = cities["n_customers"].map(
        lambda n: pct(n, ds.customers["customer_unique_id"].nunique())
    )
    cities["rank"] = cities.index + 1
    return cities


def state_customers_vs_orders(ds: Dataset) -> pd.DataFrame:
    """Question 6.4 - customer share vs order share per state."""
    by_state = customers_by_state(ds)
    orders_by_state = ds.orders.groupby("customer_state", as_index=False).agg(
        n_orders=("order_id", "size"),
        total_order_value=("order_total_value", "sum"),
    )
    merged = by_state.merge(orders_by_state, on="customer_state", how="left", validate="one_to_one")
    merged["pct_orders"] = merged["n_orders"].map(lambda n: pct(n, merged["n_orders"].sum()))
    merged["diff_orders_minus_customers_pp"] = (
        merged["pct_orders"] - merged["pct_customers"]
    ).round(4)
    merged["orders_per_customer"] = (
        merged["n_orders"] / merged["n_customers"]
    ).round(4)
    return merged.sort_values("n_customers", ascending=False).reset_index(drop=True)


# =========================================================================== #
# 7. Products and sales performance
# =========================================================================== #
def category_performance(ds: Dataset, exclude_unknown: bool = False) -> pd.DataFrame:
    """Questions 7.1-7.6 - one row per product category with both rankings."""
    items = ds.items
    if exclude_unknown:
        items = items[items["category_label"] != "unknown"]
    grouped = items.groupby("category_label", as_index=False).agg(
        n_items=("order_item_id", "size"),
        n_orders=("order_id", "nunique"),
        revenue=("price", "sum"),
        mean_item_price=("price", "mean"),
        median_item_price=("price", "median"),
        mean_freight=("freight_value", "mean"),
    )
    grouped["pct_items"] = grouped["n_items"].map(lambda n: pct(n, grouped["n_items"].sum()))
    grouped["pct_revenue"] = grouped["revenue"].map(lambda r: pct(r, grouped["revenue"].sum()))
    grouped["revenue_per_item"] = (grouped["revenue"] / grouped["n_items"]).round(2)
    grouped["rank_items"] = grouped["n_items"].rank(ascending=False, method="min").astype(int)
    grouped["rank_revenue"] = grouped["revenue"].rank(ascending=False, method="min").astype(int)
    grouped["rank_gap_revenue_minus_items"] = grouped["rank_revenue"] - grouped["rank_items"]
    grouped["cum_revenue_pct"] = (
        grouped.sort_values("revenue", ascending=False)["pct_revenue"].cumsum().to_numpy()
    )
    grouped = _round(grouped).sort_values("revenue", ascending=False).reset_index(drop=True)
    return grouped


def top_categories(ds: Dataset, by: str = "revenue", k: int = 10) -> pd.DataFrame:
    """Questions 7.1/7.2/7.4 - top k categories by revenue or by items sold."""
    table = category_performance(ds)
    table = table[table["category_label"] != "unknown"]
    if by == "revenue":
        table = table.sort_values("revenue", ascending=False)
    elif by == "items":
        table = table.sort_values("n_items", ascending=False)
    elif by == "mean_price":
        # Only categories with a meaningful volume, so a single expensive item
        # cannot top the chart.
        table = table[table["n_items"] >= MIN_REVIEWS_PER_GROUP].sort_values(
            "mean_item_price", ascending=False
        )
    return table.head(k).reset_index(drop=True)


def top_n_revenue_share(ds: Dataset, n: int = 5) -> dict:
    """Question 7.5 - revenue concentration among the n largest categories."""
    table = category_performance(ds, exclude_unknown=True).sort_values("revenue", ascending=False)
    return {
        "n": n,
        "total_revenue": round(float(table["revenue"].sum()), 2),
        "top_n_revenue": round(float(table.head(n)["revenue"].sum()), 2),
        "top_n_revenue_share_pct": pct(table.head(n)["revenue"].sum(), table["revenue"].sum()),
        "n_categories": int(len(table)),
    }


def category_rank_comparison(ds: Dataset, k: int = 20, min_gap: int = 10) -> pd.DataFrame:
    """Question 7.3 - categories whose volume rank and revenue rank diverge."""
    table = category_performance(ds, exclude_unknown=True)
    table = table[(table["rank_items"] <= k) | (table["rank_revenue"] <= k)]
    return (
        table.assign(abs_rank_gap=table["rank_gap_revenue_minus_items"].abs())
        .query("abs_rank_gap >= @min_gap")
        .sort_values("abs_rank_gap", ascending=False)[
            ["category_label", "n_items", "revenue", "mean_item_price", "rank_items",
             "rank_revenue", "rank_gap_revenue_minus_items"]
        ]
        .reset_index(drop=True)
    )


# =========================================================================== #
# 8. Payment behaviour
# =========================================================================== #
def payment_reconciliation(ds: Dataset) -> pd.DataFrame:
    """Question 8 note - the three different population sizes in the payment table."""
    rows = [
        ("payment rows (transactions)", len(ds.payments)),
        ("unique orders in payments", ds.payments["order_id"].nunique()),
        ("orders in orders table", len(ds.orders)),
        ("orders with no payment row", len(ds.orders) - ds.payments["order_id"].nunique()),
        ("customer rows, i.e. orders", len(ds.customers)),
        ("unique buyers (people)", ds.customers["customer_unique_id"].nunique()),
    ]
    out = pd.DataFrame(rows, columns=["population", "n"])
    out["note"] = [
        "one row per payment transaction",
        "an order may pay with several transactions",
        "the analysis base for order metrics",
        "created / canceled orders",
        "customer_id is one row per order",
        "customer_unique_id is the physical person",
    ]
    return out.reset_index(drop=True)


def payment_type_summary(ds: Dataset) -> pd.DataFrame:
    """Questions 8.1-8.3 - transactions, value and average value per method."""
    payments = ds.payments
    total_rows = len(payments)
    grouped = payments.groupby("payment_type", as_index=False).agg(
        n_transactions=("payment_sequential", "size"),
        total_payment_value=("payment_value", "sum"),
        mean_payment_value=("payment_value", "mean"),
        median_payment_value=("payment_value", "median"),
        n_orders=("order_id", "nunique"),
        mean_installments=("payment_installments", "mean"),
        pct_transactions_with_installment_gt1=(
            "payment_installments", lambda s: pct((s > 1).sum(), len(s))
        ),
    )
    grouped["pct_transactions"] = grouped["n_transactions"].map(lambda n: pct(n, total_rows))
    grouped["pct_payment_value"] = grouped["total_payment_value"].map(
        lambda v: pct(v, grouped["total_payment_value"].sum())
    )
    grouped["pct_orders"] = grouped["n_orders"].map(
        lambda n: pct(n, ds.payments["order_id"].nunique())
    )
    return _round(
        grouped.sort_values("n_transactions", ascending=False).reset_index(drop=True)
    )


def installment_distribution(ds: Dataset, max_installments: int = 12) -> pd.DataFrame:
    """Question 8.4 - distribution of ``payment_installments``.

    The 2 rows with zero installments are excluded from this distribution (they
    are payment-sequence fragments of a multi-part payment) and reported
    separately by :func:`zero_or_single_installments`.
    """
    payments = ds.payments
    valid = payments[payments["payment_installments"] > 0]
    counts = valid["payment_installments"].value_counts().sort_index()
    out = pd.DataFrame(
        {"payment_installments": counts.index, "n_transactions": counts.to_numpy()}
    )
    out["pct_transactions"] = out["n_transactions"].map(lambda n: pct(n, len(valid)))
    out["cum_pct"] = out["pct_transactions"].cumsum().round(4)
    out["bucket"] = np.where(
        out["payment_installments"] <= max_installments,
        out["payment_installments"].astype(str),
        f">{max_installments}",
    )
    return out.reset_index(drop=True)


def zero_or_single_installments(ds: Dataset) -> dict:
    """Question 8.5 - how many payments are single-shot, per method."""
    payments = ds.payments
    n = len(payments)
    zero = int((payments["payment_installments"] == 0).sum())
    single = int((payments["payment_installments"] == 1).sum())
    by_type = (
        payments.assign(single_shot=payments["payment_installments"] <= 1)
        .groupby("payment_type", as_index=False)
        .agg(n_transactions=("payment_sequential", "size"), n_single_shot=("single_shot", "sum"))
    )
    by_type["pct_single_shot"] = (100 * by_type["n_single_shot"] / by_type["n_transactions"]).round(4)
    return {
        "n_transactions": int(n),
        "n_zero_installments": zero,
        "n_single_installment": single,
        "n_zero_or_single": zero + single,
        "pct_zero_or_single": pct(zero + single, n),
        "pct_single_of_positive": pct(single, n - zero),
        "by_type": by_type.sort_values("n_transactions", ascending=False).reset_index(drop=True),
    }


def installments_by_type_summary(ds: Dataset) -> pd.DataFrame:
    """Question 8.6 - installment structure per payment method."""
    payments = ds.payments
    grouped = payments.groupby("payment_type", as_index=False).agg(
        n_transactions=("payment_sequential", "size"),
        min_installments=("payment_installments", "min"),
        median_installments=("payment_installments", "median"),
        mean_installments=("payment_installments", "mean"),
        max_installments=("payment_installments", "max"),
    )
    grouped["n_unique_installment_values"] = grouped["payment_type"].map(
        payments.groupby("payment_type")["payment_installments"].nunique()
    )
    return _round(grouped.sort_values("n_transactions", ascending=False).reset_index(drop=True))


# =========================================================================== #
# 9. Delivery performance
# =========================================================================== #
def delivery_duration_summary(ds: Dataset) -> pd.DataFrame:
    """Question 9.1/9.2 - duration statistics for delivered orders."""
    delivered = ds.delivered
    series = delivered["delivery_days"]
    stats = {
        "n_delivered_orders": int(len(delivered)),
        "n_missing_duration": int(len(ds.orders) - len(delivered)),
        "mean_days": round(float(series.mean()), 4),
        "median_days": round(float(series.median()), 4),
        "min_days": round(float(series.min()), 4),
        "max_days": round(float(series.max()), 4),
        "std_days": round(float(series.std()), 4),
        "p25_days": round(float(series.quantile(0.25)), 4),
        "p75_days": round(float(series.quantile(0.75)), 4),
        "p90_days": round(float(series.quantile(0.90)), 4),
        "p99_days": round(float(series.quantile(0.99)), 4),
        "mean_promised_days": round(float(delivered["promised_days"].mean()), 4),
        "median_promised_days": round(float(delivered["promised_days"].median()), 4),
        "mean_days_earlier_than_promise": round(
            float((delivered["promised_days"] - delivered["delivery_days"]).mean()), 4
        ),
    }
    return pd.DataFrame([stats])


def delivery_distribution_stats(ds: Dataset) -> dict:
    """Question 9.3 - shape of the delivery-time distribution and its outliers."""
    series = ds.delivered["delivery_days"]
    q1, q3 = float(series.quantile(0.25)), float(series.quantile(0.75))
    iqr = q3 - q1
    fence = q3 + 1.5 * iqr
    return {
        "n": int(len(series)),
        "q1_days": round(q1, 4),
        "q3_days": round(q3, 4),
        "iqr_days": round(iqr, 4),
        "upper_fence_days": round(fence, 4),
        "n_outliers": int((series > fence).sum()),
        "pct_outliers": pct((series > fence).sum(), len(series)),
        "pct_within_7_days": pct((series <= 7).sum(), len(series)),
        "pct_within_15_days": pct((series <= 15).sum(), len(series)),
        "pct_within_30_days": pct((series <= 30).sum(), len(series)),
        "pct_over_30_days": pct((series > 30).sum(), len(series)),
        "skewness": round(float(series.skew()), 4),
        "mean_minus_median_days": round(float(series.mean() - series.median()), 4),
    }


def delivery_class_summary(ds: Dataset) -> pd.DataFrame:
    """Questions 9.4/9.5 - early / on-time / late split of delivered orders.

    Definition used (documented in ``docs/methodology.md``):
    ``delay_days`` = calendar date of the real delivery - calendar date of the
    estimated delivery.  ``early`` < 0, ``on_time`` = 0, ``late`` > 0.
    """
    delivered = ds.delivered_with_delay
    counts = delivered["delivery_class"].value_counts()
    order = ["early", "on_time", "late"]
    labels = {
        "early": "delivered before the promised date",
        "on_time": "delivered on the promised date",
        "late": "delivered after the promised date",
    }
    out = pd.DataFrame({"delivery_class": order})
    out["n_orders"] = out["delivery_class"].map(counts).fillna(0).astype(int)
    out["pct_of_delivered"] = out["n_orders"].map(lambda n: pct(n, len(delivered)))
    out["definition"] = out["delivery_class"].map(labels)
    out["avg_delay_days"] = out["delivery_class"].map(
        delivered.groupby("delivery_class")["delay_days"].mean().round(2)
    )
    return out.reset_index(drop=True)


def delay_summary(ds: Dataset) -> pd.DataFrame:
    """Questions 9.5/9.6 - how long the late deliveries are."""
    delivered = ds.delivered_with_delay
    late = delivered[delivered["delivery_class"] == "late"]
    rows = [
        ("delivered orders analysed", len(delivered)),
        ("late orders", len(late)),
        ("late share of delivered (%)", pct(len(late), len(delivered))),
        ("late orders > 7 days", int((late["delay_days"] > 7).sum())),
        ("late orders 4-7 days", int(late["delay_days"].between(4, 7).sum())),
        ("late orders 1-3 days", int(late["delay_days"].between(1, 3).sum())),
        ("late orders > 15 days", int((late["delay_days"] > 15).sum())),
        ("mean delay days (late only)", round(float(late["delay_days"].mean()), 4)),
        ("median delay days (late only)", round(float(late["delay_days"].median()), 4)),
        ("p90 delay days (late only)", round(float(late["delay_days"].quantile(0.90)), 4)),
        ("max delay days (late only)", int(late["delay_days"].max())),
    ]
    out = pd.DataFrame(rows, columns=["metric", "value"])
    out["value"] = out["value"].astype(float).round(4)
    return out.reset_index(drop=True)


def delivery_by_state(ds: Dataset, min_orders: int = MIN_ORDERS_PER_STATE) -> pd.DataFrame:
    """Questions 9.7/9.8 - delivery performance per customer state."""
    delivered = ds.delivered_with_delay
    grouped = delivered.groupby("customer_state", as_index=False).agg(
        n_orders=("order_id", "size"),
        mean_delivery_days=("delivery_days", "mean"),
        median_delivery_days=("delivery_days", "median"),
        mean_promised_days=("promised_days", "mean"),
        n_late=("delivery_class", lambda s: int((s == "late").sum())),
        mean_early_days=("delay_days", "mean"),
    )
    grouped["pct_late"] = (100 * grouped["n_late"] / grouped["n_orders"]).round(4)
    grouped["meets_min_sample"] = grouped["n_orders"] >= min_orders
    grouped = _round(grouped).sort_values("mean_delivery_days", ascending=False).reset_index(drop=True)
    grouped["rank_slowest"] = grouped.index + 1
    return grouped


def monthly_delivery_trend(ds: Dataset) -> pd.DataFrame:
    """Questions 9.9/9.10 - delivery time and lateness rate over time."""
    delivered = ds.delivered_with_delay
    grouped = delivered.groupby("purchase_ym", as_index=False).agg(
        n_orders=("order_id", "size"),
        mean_delivery_days=("delivery_days", "mean"),
        median_delivery_days=("delivery_days", "median"),
        n_late=("delivery_class", lambda s: int((s == "late").sum())),
        in_core_window=("in_core_window", "first"),
    )
    grouped["pct_late"] = (100 * grouped["n_late"] / grouped["n_orders"]).round(4)
    grouped["order_month"] = pd.PeriodIndex(grouped["purchase_ym"], freq="M").to_timestamp()
    return _round(grouped.sort_values("purchase_ym").reset_index(drop=True))


# =========================================================================== #
# 10. Customer satisfaction
# =========================================================================== #
def review_score_distribution(ds: Dataset) -> pd.DataFrame:
    """Question 10.1 - frequency and share of each review score."""
    scores = ds.reviews_per_order["review_score"]
    counts = scores.value_counts().sort_index()
    out = pd.DataFrame({"review_score": counts.index.astype(int), "n_reviews": counts.to_numpy()})
    out["pct_reviews"] = out["n_reviews"].map(lambda n: pct(n, len(scores)))
    out["cum_pct"] = out["pct_reviews"].cumsum().round(4)
    return out.reset_index(drop=True)


def satisfaction_kpis(ds: Dataset) -> dict:
    """Questions 10.2/10.3 - headline satisfaction indicators."""
    scores = ds.reviews_per_order["review_score"]
    items = ds.items
    return {
        "n_orders_with_review": int(len(scores)),
        "n_orders_without_review": int(len(ds.orders) - len(scores)),
        "pct_orders_with_review": pct(len(scores), len(ds.orders)),
        "mean_score": round(float(scores.mean()), 4),
        "median_score": float(scores.median()),
        "pct_4_or_5": pct((scores >= 4).sum(), len(scores)),
        "pct_5": pct((scores == 5).sum(), len(scores)),
        "pct_1_or_2": pct((scores <= 2).sum(), len(scores)),
        "pct_1": pct((scores == 1).sum(), len(scores)),
        "n_orders": int(len(ds.orders)),
        "n_items": int(len(items)),
    }


def category_satisfaction(ds: Dataset, min_reviews: int = MIN_REVIEWS_PER_GROUP) -> pd.DataFrame:
    """Questions 10.4-10.6 and 10.9 - score and revenue per category.

    Grain: one row per (order, category), so an order that bought three items
    from the same category contributes its score exactly once.
    """
    order_category = ds.order_category
    grouped = order_category.groupby("category_label", as_index=False).agg(
        n_orders=("order_id", "nunique"),
        n_reviews=("review_score", "count"),
        mean_score=("review_score", "mean"),
        revenue=("revenue", "sum"),
        mean_item_price=("mean_item_price", "mean"),
    )
    overall = float(order_category["review_score"].mean())
    grouped["pct_revenue"] = grouped["revenue"].map(lambda r: pct(r, grouped["revenue"].sum()))
    grouped["overall_mean_score"] = round(overall, 4)
    grouped["score_vs_overall"] = (grouped["mean_score"] - overall).round(4)
    grouped["meets_min_reviews"] = grouped["n_reviews"] >= min_reviews
    grouped = _round(grouped).sort_values("revenue", ascending=False).reset_index(drop=True)
    return grouped


def category_satisfaction_ranked(
    ds: Dataset, which: str = "best", k: int = 10, min_reviews: int = MIN_REVIEWS_PER_GROUP
) -> pd.DataFrame:
    """Question 10.4 - top / bottom categories by mean score, sample-size aware."""
    table = category_satisfaction(ds)
    table = table[table["meets_min_reviews"] & (table["category_label"] != "unknown")]
    ascending = which == "worst"
    return (
        table.sort_values(["mean_score", "n_reviews"], ascending=[ascending, False])
        .head(k)
        .reset_index(drop=True)
    )


def low_volume_categories(ds: Dataset, min_reviews: int = MIN_REVIEWS_PER_GROUP) -> pd.DataFrame:
    """Question 10.5 - why the review count matters: extremes on tiny samples."""
    table = category_satisfaction(ds)
    small = table[~table["meets_min_reviews"]].sort_values("n_reviews")
    return small[["category_label", "n_orders", "n_reviews", "mean_score", "revenue"]].reset_index(
        drop=True
    )


def monthly_satisfaction_trend(ds: Dataset) -> pd.DataFrame:
    """Question 10.7 - mean score over time."""
    scores = ds.reviews_per_order.merge(
        ds.orders[["order_id", "purchase_ym", "in_core_window"]], on="order_id",
        how="inner", validate="one_to_one",
    )
    grouped = scores.groupby("purchase_ym", as_index=False).agg(
        n_reviews=("review_score", "size"),
        mean_score=("review_score", "mean"),
        pct_1_or_2=("review_score", lambda s: pct((s <= 2).sum(), len(s))),
        in_core_window=("in_core_window", "first"),
    )
    grouped["order_month"] = pd.PeriodIndex(grouped["purchase_ym"], freq="M").to_timestamp()
    return _round(grouped.sort_values("purchase_ym").reset_index(drop=True))


# =========================================================================== #
# 11. Delivery delay vs satisfaction
# =========================================================================== #
def delay_satisfaction_comparison(ds: Dataset) -> pd.DataFrame:
    """Questions 11.1/11.2/11.4 - on-time vs late groups and their scores."""
    delivered = ds.delivered_with_delay
    delivered = delivered[delivered["review_score"].notna()]
    grouped = delivered.assign(
        group=np.where(delivered["delivery_class"] == "late", "late", "on_time_or_early")
    ).groupby("group", as_index=False).agg(
        n_orders=("order_id", "size"),
        mean_score=("review_score", "mean"),
        pct_5=("review_score", lambda s: pct((s == 5).sum(), len(s))),
        pct_1_or_2=("review_score", lambda s: pct((s <= 2).sum(), len(s))),
        n_1_or_2=("review_score", lambda s: int((s <= 2).sum())),
    )
    grouped["pct_of_orders"] = (100 * grouped["n_orders"] / grouped["n_orders"].sum()).round(4)
    grouped = _round(grouped).sort_values("mean_score", ascending=False).reset_index(drop=True)
    return grouped


def delay_satisfaction_difference(ds: Dataset) -> dict:
    """Question 11.3 - size of the gap and whether the samples suffice."""
    table = delay_satisfaction_comparison(ds)
    scores = dict(zip(table["group"], table["mean_score"]))
    sizes = dict(zip(table["group"], table["n_orders"]))
    on_time = scores.get("on_time_or_early", float("nan"))
    late = scores.get("late", float("nan"))
    return {
        "n_on_time_or_early": int(sizes.get("on_time_or_early", 0)),
        "n_late": int(sizes.get("late", 0)),
        "mean_score_on_time_or_early": round(float(on_time), 4),
        "mean_score_late": round(float(late), 4),
        "score_gap": round(float(on_time - late), 4),
        "min_sample_reached": bool(
            sizes.get("late", 0) >= 30 and sizes.get("on_time_or_early", 0) >= 30
        ),
        "late_orders_at_risk": int(sizes.get("late", 0)),
    }


def delay_bucket_satisfaction(ds: Dataset) -> pd.DataFrame:
    """Questions 11.4/11.5 - satisfaction by delay severity bucket."""
    delivered = ds.delivered_with_delay
    delivered = delivered[delivered["review_score"].notna()]
    grouped = delivered.groupby("delay_bucket", as_index=False).agg(
        n_orders=("order_id", "size"),
        mean_score=("review_score", "mean"),
        median_score=("review_score", "median"),
        pct_1_or_2=("review_score", lambda s: pct((s <= 2).sum(), len(s))),
        pct_5=("review_score", lambda s: pct((s == 5).sum(), len(s))),
    )
    grouped["delay_bucket"] = pd.Categorical(
        grouped["delay_bucket"], categories=DELAY_BUCKET_ORDER, ordered=True
    )
    grouped["label"] = grouped["delay_bucket"].map(
        {
            "on_time_or_early": "on time or early",
            "1_3_days": "1-3 days late",
            "4_7_days": "4-7 days late",
            "more_than_7_days": "more than 7 days late",
        }
    )
    return _round(grouped.sort_values("delay_bucket").reset_index(drop=True))


def category_delay_satisfaction(
    ds: Dataset, min_orders: int = 200, k: int = 8
) -> pd.DataFrame:
    """Question 11.6 - the same comparison inside large categories."""
    # ``order_category`` already carries the order-level delivery_class, so no
    # extra join is needed (and merging it again would duplicate the column).
    order_category = ds.order_category
    merged = order_category[
        order_category["review_score"].notna() & order_category["delivery_class"].notna()
    ].copy()
    merged["group"] = np.where(merged["delivery_class"] == "late", "late", "on_time_or_early")

    pivot = (
        merged.pivot_table(
            index="category_label", columns="group", values="review_score",
            aggfunc=["mean", "size"],
        )
    )
    pivot.columns = [f"{stat}_{group}" for stat, group in pivot.columns]
    pivot = pivot.reset_index()
    for column in ("mean_late", "mean_on_time_or_early", "size_late", "size_on_time_or_early"):
        if column not in pivot.columns:
            pivot[column] = np.nan
    pivot["total_orders"] = pivot["size_late"] + pivot["size_on_time_or_early"]
    pivot["score_gap"] = (pivot["mean_on_time_or_early"] - pivot["mean_late"]).round(4)
    pivot = pivot[
        (pivot["total_orders"] >= min_orders)
        & (pivot["size_late"] >= MIN_REVIEWS_PER_GROUP)
        & (pivot["category_label"] != "unknown")
    ]
    pivot = _round(pivot).sort_values("score_gap", ascending=False).head(k)
    return pivot[
        ["category_label", "total_orders", "size_on_time_or_early", "size_late",
         "mean_on_time_or_early", "mean_late", "score_gap"]
    ].reset_index(drop=True)


# =========================================================================== #
# 12. Seller performance
# =========================================================================== #
def sellers_by_state(ds: Dataset) -> pd.DataFrame:
    """Question 12.1 - sellers per state."""
    grouped = ds.sellers.groupby("seller_state", as_index=False).agg(
        n_sellers=("seller_id", "nunique")
    )
    grouped["pct_sellers"] = grouped["n_sellers"].map(
        lambda n: pct(n, grouped["n_sellers"].sum())
    )
    grouped = grouped.sort_values("n_sellers", ascending=False).reset_index(drop=True)
    grouped["rank"] = grouped.index + 1
    return grouped


def seller_performance(ds: Dataset) -> pd.DataFrame:
    """Questions 12.2-12.5 - revenue, volume and rating per seller."""
    order_seller = ds.order_seller
    grouped = order_seller.groupby(["seller_id", "seller_state"], as_index=False).agg(
        n_items=("n_items", "sum"),
        n_orders=("order_id", "nunique"),
        revenue=("revenue", "sum"),
        n_reviews=("review_score", "count"),
        mean_score=("review_score", "mean"),
    )
    overall = float(order_seller["review_score"].mean())
    grouped["revenue_share_pct"] = grouped["revenue"].map(lambda r: pct(r, grouped["revenue"].sum()))
    grouped["overall_mean_score"] = round(overall, 4)
    grouped["score_vs_overall"] = (grouped["mean_score"] - overall).round(4)
    grouped["rank_revenue"] = grouped["revenue"].rank(ascending=False, method="min").astype(int)
    grouped["rank_items"] = grouped["n_items"].rank(ascending=False, method="min").astype(int)
    grouped["rank_gap_revenue_minus_items"] = grouped["rank_revenue"] - grouped["rank_items"]
    grouped["meets_min_reviews"] = grouped["n_reviews"] >= MIN_REVIEWS_PER_GROUP
    return _round(grouped).sort_values("revenue", ascending=False).reset_index(drop=True)


def seller_overview(ds: Dataset) -> dict:
    """Question 12.1/12.3 - how concentrated the marketplace is."""
    perf = seller_performance(ds)
    top10 = perf.head(10)
    return {
        "n_sellers": int(len(perf)),
        "n_states": int(ds.sellers["seller_state"].nunique()),
        "median_items_per_seller": float(perf["n_items"].median()),
        "median_revenue_per_seller": round(float(perf["revenue"].median()), 2),
        "total_revenue": round(float(perf["revenue"].sum()), 2),
        "top10_revenue": round(float(top10["revenue"].sum()), 2),
        "top10_revenue_share_pct": pct(top10["revenue"].sum(), perf["revenue"].sum()),
        "top10_items_share_pct": pct(top10["n_items"].sum(), perf["n_items"].sum()),
        "sellers_with_min_reviews": int(perf["meets_min_reviews"].sum()),
        "sellers_pct_with_min_reviews": pct(perf["meets_min_reviews"].sum(), len(perf)),
    }


def top_sellers(ds: Dataset, by: str = "revenue", k: int = 10) -> pd.DataFrame:
    """Question 12.2/12.4 - top sellers by revenue or by items sold."""
    perf = seller_performance(ds)
    column = "revenue" if by == "revenue" else "n_items"
    return perf.sort_values(column, ascending=False).head(k).reset_index(drop=True)


def high_revenue_low_rating_sellers(
    ds: Dataset, revenue_quantile: float = 0.90, score_gap: float = 0.5, k: int = 10
) -> pd.DataFrame:
    """Questions 12.6/12.7 - sellers with strong sales but weak ratings.

    The threshold is *relative*: revenue must be in the top decile of the
    marketplace **and** the mean score must sit at least ``score_gap`` below the
    marketplace average, with at least ``MIN_REVIEWS_PER_GROUP`` reviews.
    """
    perf = seller_performance(ds)
    threshold = float(perf["revenue"].quantile(revenue_quantile))
    candidates = perf[
        (perf["revenue"] >= threshold)
        & (perf["score_vs_overall"] <= -score_gap)
        & (perf["meets_min_reviews"])
    ].sort_values("revenue", ascending=False)
    return candidates.head(k).reset_index(drop=True), threshold


# =========================================================================== #
# 13. Combined analyses
# =========================================================================== #
def combined_revenue_vs_satisfaction(
    ds: Dataset, revenue_quantile: float = 0.75, min_reviews: int = MIN_REVIEWS_PER_GROUP
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Combined analysis 1 - high revenue categories with below-average ratings."""
    table = category_satisfaction(ds)
    table = table[(table["category_label"] != "unknown") & table["meets_min_reviews"]].copy()
    threshold = float(table["revenue"].quantile(revenue_quantile))
    table["is_high_revenue"] = table["revenue"] >= threshold
    table["below_average_score"] = table["score_vs_overall"] < 0
    flagged = table[table["is_high_revenue"] & table["below_average_score"]].sort_values(
        "revenue", ascending=False
    )
    return table[["category_label", "revenue", "pct_revenue", "n_reviews", "mean_score",
                  "score_vs_overall", "is_high_revenue", "below_average_score"]].reset_index(
        drop=True
    ), flagged[["category_label", "revenue", "pct_revenue", "n_reviews", "mean_score",
                "score_vs_overall"]].reset_index(drop=True)


def combined_geography_delivery(ds: Dataset, min_orders: int = MIN_ORDERS_PER_STATE):
    """Combined analysis 2 - states that are slow *and* late often."""
    table = delivery_by_state(ds, min_orders=min_orders)
    eligible = table[table["meets_min_sample"]].copy()
    slow_threshold = float(eligible["mean_delivery_days"].median())
    late_threshold = float(eligible["pct_late"].median())
    eligible["is_slow"] = eligible["mean_delivery_days"] > slow_threshold
    eligible["is_late_prone"] = eligible["pct_late"] > late_threshold
    eligible["needs_attention"] = eligible["is_slow"] & eligible["is_late_prone"]
    return (
        table,
        eligible.sort_values(["needs_attention", "mean_delivery_days"], ascending=False).reset_index(
            drop=True
        ),
        {"slow_threshold_days": round(slow_threshold, 4), "late_threshold_pct": round(late_threshold, 4)},
    )


def combined_price_vs_satisfaction(ds: Dataset, bins: int = 10) -> tuple[pd.DataFrame, dict]:
    """Combined analysis 3 - does a higher item price go with a better score?"""
    orders = ds.orders
    data = orders[orders["review_score"].notna() & orders["item_mean_price"].notna()].copy()
    correlation = float(
        data[["item_mean_price", "review_score"]].corr(method="spearman").iloc[0, 1]
    )
    data["price_decile"] = pd.qcut(
        data["item_mean_price"], q=bins, duplicates="drop", labels=False
    )
    grouped = data.groupby("price_decile", as_index=False).agg(
        n_orders=("order_id", "size"),
        min_price=("item_mean_price", "min"),
        max_price=("item_mean_price", "max"),
        median_price=("item_mean_price", "median"),
        mean_score=("review_score", "mean"),
        pct_1_or_2=("review_score", lambda s: pct((s <= 2).sum(), len(s))),
        pct_5=("review_score", lambda s: pct((s == 5).sum(), len(s))),
    )
    grouped["price_band"] = [
        f"{lo:,.0f}-{hi:,.0f}" for lo, hi in zip(grouped["min_price"], grouped["max_price"])
    ]
    stats = {
        "n_orders": int(len(data)),
        "spearman_rho": round(correlation, 4),
        "mean_score_lowest_decile": round(float(grouped.iloc[0]["mean_score"]), 4),
        "mean_score_highest_decile": round(float(grouped.iloc[-1]["mean_score"]), 4),
        "score_range_across_deciles": round(
            float(grouped["mean_score"].max() - grouped["mean_score"].min()), 4
        ),
        "currency": CURRENCY,
    }
    return _round(grouped), stats


def combined_payment_vs_installments(ds: Dataset) -> tuple[pd.DataFrame, dict]:
    """Combined analysis 4 - payment amount vs number of installments."""
    payments = ds.payments
    tx = payments[payments["payment_installments"] > 0]
    tx_rho = float(
        tx[["payment_value", "payment_installments"]].corr(method="spearman").iloc[0, 1]
    )
    credit = tx[tx["payment_type"] == "credit_card"]
    credit_rho = float(
        credit[["payment_value", "payment_installments"]].corr(method="spearman").iloc[0, 1]
    )

    binned = tx.copy()
    binned["value_decile"] = pd.qcut(
        binned["payment_value"], q=10, duplicates="drop", labels=False
    )
    grouped = binned.groupby("value_decile", as_index=False).agg(
        n_transactions=("payment_sequential", "size"),
        min_value=("payment_value", "min"),
        max_value=("payment_value", "max"),
        median_value=("payment_value", "median"),
        mean_installments=("payment_installments", "mean"),
        median_installments=("payment_installments", "median"),
        pct_multi_installment=("payment_installments", lambda s: pct((s > 1).sum(), len(s))),
    )
    grouped["value_band"] = [
        f"{lo:,.0f}-{hi:,.0f}" for lo, hi in zip(grouped["min_value"], grouped["max_value"])
    ]

    orders = ds.orders
    order_level = orders[orders["payment_total"].notna()].copy()
    order_rho = float(
        order_level[["payment_total", "payment_max_installments"]]
        .corr(method="spearman")
        .iloc[0, 1]
    )
    stats = {
        "n_transactions": int(len(tx)),
        "n_orders_with_payment": int(len(order_level)),
        "spearman_rho_transaction_level": round(tx_rho, 4),
        "spearman_rho_credit_card_only": round(credit_rho, 4),
        "spearman_rho_order_level": round(order_rho, 4),
        "mean_installments_lowest_decile": round(float(grouped.iloc[0]["mean_installments"]), 4),
        "mean_installments_highest_decile": round(float(grouped.iloc[-1]["mean_installments"]), 4),
        "pct_multi_installment_lowest_decile": round(
            float(grouped.iloc[0]["pct_multi_installment"]), 4
        ),
        "pct_multi_installment_highest_decile": round(
            float(grouped.iloc[-1]["pct_multi_installment"]), 4
        ),
    }
    return _round(grouped), stats


def combined_category_revenue_over_time(
    ds: Dataset, top_n: int = 5
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Combined analysis 5 - is category growth sustained or a one-month spike?"""
    items = ds.items[ds.items["in_core_window"]]
    revenue = (
        items.groupby(["category_label", "purchase_ym"], as_index=False)
        .agg(revenue=("price", "sum"), n_items=("order_item_id", "size"))
    )
    top_categories_list = (
        revenue.groupby("category_label")["revenue"].sum().sort_values(ascending=False).head(top_n).index
    )
    selected = revenue[revenue["category_label"].isin(top_categories_list)]

    pivot = selected.pivot_table(
        index="purchase_ym", columns="category_label", values="revenue", aggfunc="sum"
    ).fillna(0.0).sort_index()
    pivot["total"] = pivot.sum(axis=1)

    months = list(pivot.index)
    half = len(months) // 2
    rows = []
    for category in top_categories_list:
        series = pivot[category] if category in pivot.columns else pd.Series(0.0, index=pivot.index)
        first_half = float(series.iloc[:half].mean())
        second_half = float(series.iloc[half:].mean())
        cv = float(series.std() / series.mean()) if series.mean() else float("nan")
        rows.append(
            {
                "category_label": category,
                "total_revenue": round(float(series.sum()), 2),
                "mean_monthly_revenue_first_half": round(first_half, 2),
                "mean_monthly_revenue_second_half": round(second_half, 2),
                "pct_change_second_vs_first_half": pct(second_half - first_half, first_half),
                "coefficient_of_variation": round(cv, 4),
                "peak_month": str(series.idxmax()),
                "peak_month_share_pct": pct(float(series.max()), float(series.sum())),
                "months_used": len(months),
            }
        )
    trend = pd.DataFrame(rows)
    trend["is_sustained_growth"] = (
        (trend["pct_change_second_vs_first_half"] > 10) & (trend["coefficient_of_variation"] < 0.8)
    )
    trend["is_spike_driven"] = trend["peak_month_share_pct"] > 12
    return pivot.reset_index(), trend
