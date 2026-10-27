"""The end-to-end analysis pipeline.

``run_pipeline()`` executes every metric required by the course brief on the
real data, writes the tables to ``reports/tables/``, renders every figure into
``reports/figures/`` and stores all headline numbers in
``reports/metrics.json``.

Both the notebooks and ``scripts/run_all.py`` call this module, so the numbers
printed in a notebook, the CSV next to it and the executive report are produced
by one code path and cannot drift apart.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import data_quality as dq
from . import metrics as M
from . import plotting as P
from .cleaning import cleaning_decisions
from .config import FIGURES_DIR, RAW_TABLES, REPORTS_DIR, TABLES_DIR
from .data_loader import file_inventory, load_raw_tables, table_shapes
from .features import Dataset, load_dataset
from .font_utils import persian_available

METRICS_PATH = REPORTS_DIR / "metrics.json"
FIGURE_MANIFEST_PATH = TABLES_DIR / "figure_manifest.csv"


def _jsonable(value: Any) -> Any:
    """Convert NumPy / pandas scalars so ``json.dump`` never fails."""
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if value is pd.NA or (isinstance(value, float) and np.isnan(value)):
        return None
    return value


def _write_table(frame: pd.DataFrame, name: str) -> Path:
    path = TABLES_DIR / f"{name}.csv"
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return path


class Results:
    """Everything the pipeline produced, for the report and the notebooks."""

    def __init__(self) -> None:
        self.tables: dict[str, pd.DataFrame] = {}
        self.figures: dict[str, Path] = {}
        self.headline: dict[str, Any] = {}
        self.figures_captioned: list[dict[str, str]] = []

    def add(self, name: str, frame: pd.DataFrame) -> pd.DataFrame:
        self.tables[name] = frame
        return frame

    def figure(self, name: str, path: Path) -> Path:
        self.figures[name] = path
        return path


def compute_tables(ds: Dataset, results: Results) -> None:
    """Run every metric function and register the resulting tables."""

    # ---- 5. orders and business trend
    results.add("05_order_status_summary", M.order_status_summary(ds))
    results.add("05_monthly_orders", M.monthly_orders(ds))
    results.add("05_year_month_matrix", M.year_month_matrix(ds))
    results.add("05_weekday_orders", M.weekday_orders(ds))
    results.add("05_top_months", M.top_months(ds))
    growth = M.growth_evidence(ds)
    results.headline["growth"] = growth

    # ---- 6. customers and geography
    overview = M.customer_overview(ds)
    results.headline["customers"] = overview
    results.add("06_customers_by_state", M.customers_by_state(ds))
    results.add("06_customers_by_city", M.customers_by_city(ds, 10))
    results.headline["top5_state_share"] = M.top_n_state_share(ds, 5)
    results.add("06_state_customers_vs_orders", M.state_customers_vs_orders(ds))

    # ---- 7. products
    category = M.category_performance(ds)
    results.add("07_category_performance", category)
    results.headline["category_revenue_top5"] = M.top_n_revenue_share(ds, 5)
    results.add("07_top_categories_by_items", M.top_categories(ds, "items", 10))
    results.add("07_top_categories_by_revenue", M.top_categories(ds, "revenue", 10))
    results.add("07_top_categories_by_price", M.top_categories(ds, "mean_price", 5))
    results.add("07_category_rank_comparison", M.category_rank_comparison(ds, 20, 10))

    # ---- 8. payments
    results.add("08_payment_reconciliation", M.payment_reconciliation(ds))
    results.add("08_payment_type_summary", M.payment_type_summary(ds))
    results.add("08_installment_distribution", M.installment_distribution(ds))
    results.add("08_installments_by_type", M.installments_by_type_summary(ds))
    zero_single = M.zero_or_single_installments(ds)
    results.add("08_zero_or_single_installments", zero_single["by_type"])
    results.headline["zero_or_single_installments"] = {
        k: v for k, v in zero_single.items() if k != "by_type"
    }

    # ---- 9. delivery
    duration = M.delivery_duration_summary(ds)
    results.add("09_delivery_duration_summary", duration)
    results.headline["delivery_duration"] = duration.iloc[0].to_dict()
    distribution = M.delivery_distribution_stats(ds)
    results.headline["delivery_distribution"] = distribution
    results.add("09_delivery_class_summary", M.delivery_class_summary(ds))
    results.add("09_delay_summary", M.delay_summary(ds))
    results.add("09_delivery_by_state", M.delivery_by_state(ds))
    results.add("09_monthly_delivery_trend", M.monthly_delivery_trend(ds))

    # ---- 10. satisfaction
    results.add("10_review_score_distribution", M.review_score_distribution(ds))
    results.headline["satisfaction"] = M.satisfaction_kpis(ds)
    results.add("10_category_satisfaction", M.category_satisfaction(ds))
    results.add("10_category_satisfaction_best", M.category_satisfaction_ranked(ds, "best", 10))
    results.add("10_category_satisfaction_worst", M.category_satisfaction_ranked(ds, "worst", 10))
    results.add("10_low_volume_categories", M.low_volume_categories(ds))
    results.add("10_monthly_satisfaction_trend", M.monthly_satisfaction_trend(ds))

    # ---- 11. delay vs satisfaction
    results.add("11_delay_satisfaction_comparison", M.delay_satisfaction_comparison(ds))
    results.headline["delay_vs_satisfaction"] = M.delay_satisfaction_difference(ds)
    results.add("11_delay_bucket_satisfaction", M.delay_bucket_satisfaction(ds))
    results.add("11_category_delay_satisfaction", M.category_delay_satisfaction(ds))

    # ---- 12. sellers
    results.headline["sellers"] = M.seller_overview(ds)
    results.add("12_sellers_by_state", M.sellers_by_state(ds))
    results.add("12_seller_performance", M.seller_performance(ds))
    results.add("12_top_sellers_by_revenue", M.top_sellers(ds, "revenue", 10))
    results.add("12_top_sellers_by_items", M.top_sellers(ds, "items", 10))
    candidates, threshold = M.high_revenue_low_rating_sellers(ds)
    results.headline["seller_low_rating_threshold"] = round(float(threshold), 2)
    results.add("12_high_revenue_low_rating_sellers", candidates)

    # ---- 13. combined analyses (all six)
    scatter, flagged = M.combined_revenue_vs_satisfaction(ds)
    results.add("13_combined_revenue_vs_satisfaction", scatter)
    results.add("13_combined_revenue_vs_satisfaction_flagged", flagged)
    states, eligible, thresholds = M.combined_geography_delivery(ds)
    results.add("13_combined_geography_eligible", eligible)
    results.headline["geography_thresholds"] = thresholds
    price_deciles, price_stats = M.combined_price_vs_satisfaction(ds)
    results.add("13_combined_price_vs_satisfaction_deciles", price_deciles)
    results.headline["price_vs_satisfaction"] = price_stats
    payment_bins, payment_stats = M.combined_payment_vs_installments(ds)
    results.add("13_combined_payment_vs_installments_deciles", payment_bins)
    results.headline["payment_vs_installments"] = payment_stats
    pivot, trend = M.combined_category_revenue_over_time(ds)
    results.add("13_combined_category_revenue_trend", trend)
    results.headline["category_revenue_trend"] = trend.to_dict(orient="records")

    # ---- 1-4. data understanding and cleaning evidence
    raw = load_raw_tables()
    results.add("01_file_inventory", file_inventory())
    results.add("01_table_shapes", table_shapes(raw))
    compute_data_understanding(raw, results)
    results.add("02_cleaning_summary", pd.DataFrame(
        [{"metric": k, "value": v} for k, v in sorted(ds.log.items())]
    ))
    results.add("02_cleaning_decisions", cleaning_decisions(ds.log))


def compute_data_understanding(
    raw: dict[str, pd.DataFrame], results: "Results"
) -> None:
    """Persist the profiling evidence (notebooks 00 and 01 read these tables).

    Everything the notebooks need is produced by this single pipeline run, so no
    table in ``reports/tables/`` can come from a different, stale execution.
    """
    profiles = pd.concat(
        [dq.column_profile(raw[name], name) for name in raw], ignore_index=True
    )
    results.add("00_column_profiles", profiles)

    missing = pd.concat(
        [dq.missing_values_table(raw[name], name) for name in raw], ignore_index=True
    )
    results.add("00_missing_values", missing)

    duplicates = pd.concat(
        [dq.duplicate_rows_table(raw[name], name) for name in raw], ignore_index=True
    )
    results.add("00_duplicate_rows", duplicates)

    results.add("00_key_uniqueness", dq.key_uniqueness_table(raw, RAW_TABLES))
    results.add(
        "00_order_status",
        dq.value_counts_table(raw["orders"]["order_status"], "order_status"),
    )
    results.add(
        "00_orders_datetime_report",
        dq.datetime_parse_report(
            raw["orders"], list(RAW_TABLES["orders"].datetime_columns), "orders"
        ),
    )

    orders = raw["orders"]
    orders_status = orders.assign(
        missing_approved=orders["order_approved_at"].isna(),
        missing_carrier=orders["order_delivered_carrier_date"].isna(),
        missing_delivered=orders["order_delivered_customer_date"].isna(),
    )
    results.add(
        "00_orders_missing_by_status",
        orders_status.groupby("order_status")
        .agg(
            n_orders=("order_id", "size"),
            missing_approved=("missing_approved", "sum"),
            missing_carrier=("missing_carrier", "sum"),
            missing_delivered=("missing_delivered", "sum"),
        )
        .sort_values("n_orders", ascending=False)
        .reset_index(),
    )

    orders_ids = set(orders["order_id"])
    customer_ids = set(raw["customers"]["customer_id"])
    product_ids = set(raw["products"]["product_id"])
    seller_ids = set(raw["sellers"]["seller_id"])
    results.add(
        "00_referential_integrity",
        pd.DataFrame(
            [
                dq.referential_integrity(
                    orders, "customer_id", customer_ids, "orders", "customers"
                ),
                dq.referential_integrity(
                    raw["order_items"], "order_id", orders_ids, "order_items", "orders"
                ),
                dq.referential_integrity(
                    raw["order_items"], "product_id", product_ids, "order_items", "products"
                ),
                dq.referential_integrity(
                    raw["order_items"], "seller_id", seller_ids, "order_items", "sellers"
                ),
                dq.referential_integrity(
                    raw["order_payments"], "order_id", orders_ids, "order_payments", "orders"
                ),
                dq.referential_integrity(
                    raw["order_reviews"], "order_id", orders_ids, "order_reviews", "orders"
                ),
            ]
        ),
    )

    for name, key, value in (
        ("00_items_per_order", "order_id", "order_item_id"),
        ("00_payments_per_order", "order_id", "payment_sequential"),
        ("00_reviews_per_order", "order_id", "review_id"),
    ):
        source = {
            "00_items_per_order": raw["order_items"],
            "00_payments_per_order": raw["order_payments"],
            "00_reviews_per_order": raw["order_reviews"],
        }[name]
        results.add(
            name,
            pd.DataFrame([dq.group_size_distribution(source, key, value, name[3:])]),
        )


def render_figures(ds: Dataset, results: Results) -> None:
    """Render every chart from the tables computed above."""
    t = results.tables

    def fig(name: str, path: Path) -> None:
        results.figure(name, path)

    fig("fig_01_order_status", P.fig_order_status(t["05_order_status_summary"]))
    fig("fig_02_monthly_orders", P.fig_monthly_orders(t["05_monthly_orders"]))
    fig("fig_03_weekday_orders", P.fig_weekday_orders(t["05_weekday_orders"]))
    fig("fig_04_top_months", P.fig_top_months(t["05_top_months"]))
    fig("fig_05_state_customers", P.fig_state_customers(t["06_customers_by_state"].head(10)))
    fig("fig_06_top_cities", P.fig_top_cities(t["06_customers_by_city"]))
    fig("fig_07_state_customers_vs_orders",
        P.fig_state_customers_vs_orders(t["06_state_customers_vs_orders"]))
    fig("fig_08_top_categories_items", P.fig_top_categories_items(t["07_top_categories_by_items"]))
    fig("fig_09_top_categories_revenue",
        P.fig_top_categories_revenue(t["07_top_categories_by_revenue"]))
    fig("fig_10_category_items_vs_revenue",
        P.fig_category_items_vs_revenue(t["07_category_performance"]))
    fig("fig_11_top_categories_price", P.fig_top_categories_price(t["07_top_categories_by_price"]))
    fig("fig_12_payment_types", P.fig_payment_types(t["08_payment_type_summary"]))
    fig("fig_13_installments_distribution",
        P.fig_installments_distribution(t["08_installment_distribution"]))
    fig("fig_14_payment_value_vs_installments",
        P.fig_payment_value_vs_installments(t["13_combined_payment_vs_installments_deciles"]))
    fig("fig_15_delivery_histogram", P.fig_delivery_histogram(ds.delivered))
    fig("fig_16_delivery_class", P.fig_delivery_class(t["09_delivery_class_summary"]))
    fig("fig_17_state_delivery", P.fig_state_delivery(t["09_delivery_by_state"]))
    fig("fig_18_monthly_delivery_trend",
        P.fig_monthly_delivery_trend(t["09_monthly_delivery_trend"]))
    fig("fig_31_state_late_rate", P.fig_state_late_rate(t["09_delivery_by_state"]))
    fig("fig_19_review_scores", P.fig_review_scores(t["10_review_score_distribution"]))
    fig("fig_20_category_scores", P.fig_category_scores(
        t["10_category_satisfaction_best"], t["10_category_satisfaction_worst"]))
    fig("fig_21_monthly_score_trend",
        P.fig_monthly_score_trend(t["10_monthly_satisfaction_trend"]))
    fig("fig_22_delay_satisfaction",
        P.fig_delay_satisfaction(t["11_delay_satisfaction_comparison"]))
    fig("fig_23_delay_bucket_satisfaction",
        P.fig_delay_bucket_satisfaction(t["11_delay_bucket_satisfaction"]))
    fig("fig_24_top_sellers", P.fig_top_sellers(t["12_top_sellers_by_revenue"]))
    fig("fig_25_seller_revenue_vs_score", P.fig_seller_revenue_vs_score(
        t["12_seller_performance"], t["12_high_revenue_low_rating_sellers"]))
    fig("fig_26_combined_revenue_vs_score",
        P.fig_combined_revenue_vs_score(t["13_combined_revenue_vs_satisfaction"]))
    fig("fig_27_combined_geography_delivery", P.fig_combined_geography_delivery(
        t["13_combined_geography_eligible"], results.headline["geography_thresholds"]))
    fig("fig_28_combined_price_vs_score",
        P.fig_combined_price_vs_score(t["13_combined_price_vs_satisfaction_deciles"]))
    fig("fig_29_combined_category_revenue_trend",
        P.fig_combined_category_revenue_trend(_category_pivot(ds)))
    fig("fig_30_combined_seller_satisfaction", P.fig_combined_seller_satisfaction(
        t["12_seller_performance"], t["12_high_revenue_low_rating_sellers"]))

    manifest = []
    for name, path in sorted(results.figures.items()):
        caption_path = FIGURES_DIR / f"{path.stem}.txt"
        manifest.append(
            {
                "figure": path.name,
                "caption": caption_path.read_text(encoding="utf-8") if caption_path.exists() else "",
            }
        )
    results.figures_captioned = manifest
    _write_table(pd.DataFrame(manifest), "figure_manifest")


def _category_pivot(ds: Dataset) -> pd.DataFrame:
    pivot, _trend = M.combined_category_revenue_over_time(ds)
    return pivot


def write_headline_extra(ds: Dataset, results: Results) -> None:
    """Headline values that need several frames at once."""
    items = ds.items
    orders = ds.orders
    results.headline["business_totals"] = {
        "orders": int(len(orders)),
        "delivered_orders": int(orders["is_delivered"].sum()),
        "item_revenue_brl": round(float(items["price"].sum()), 2),
        "freight_brl": round(float(items["freight_value"].sum()), 2),
        "total_paid_brl": round(float(ds.payments["payment_value"].sum()), 2),
        "unique_products": int(ds.products["product_id"].nunique()),
        "product_categories": int(
            ds.products.loc[ds.products["category_label"] != "unknown", "category_label"].nunique()
        ),
        "unique_sellers": int(ds.sellers["seller_id"].nunique()),
        "unique_buyers": int(ds.customers["customer_unique_id"].nunique()),
        "mean_order_value_brl": round(float(orders["order_total_value"].mean()), 2),
        "mean_item_price_brl": round(float(items["price"].mean()), 2),
        "avg_items_per_order": round(float(orders["item_count"].mean()), 4),
    }
    results.headline["run_metadata"] = {
        "persian_font_available": persian_available(),
        "figures": len(results.figures),
        "tables": len(results.tables),
        "raw_files": {name: spec.filename for name, spec in RAW_TABLES.items()},
    }


def run_pipeline(dataset: Dataset | None = None) -> Results:
    """Run the complete analysis and persist every artifact."""
    P.setup_style()
    ds = dataset if dataset is not None else load_dataset()
    results = Results()

    compute_tables(ds, results)
    write_headline_extra(ds, results)
    render_figures(ds, results)

    for name, frame in results.tables.items():
        _write_table(frame, name)

    METRICS_PATH.write_text(
        json.dumps(_jsonable(results.headline), indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    return results


def load_headline() -> dict:
    """Read back the persisted headline numbers (used by the report builder)."""
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


def load_table(name: str) -> pd.DataFrame:
    return pd.read_csv(TABLES_DIR / f"{name}.csv")
