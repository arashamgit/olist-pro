"""Analytical feature engineering: from cleaned tables to three analysis grains.

Three grains are built once and reused by every notebook:

``order_features``     one row per order (99,441 rows, key = ``order_id``)
``item_features``      one row per order item (112,650 rows)
``order_category``     one row per (order, category) pair
``order_seller``       one row per (order, seller) pair

The last two exist to make satisfaction analysis honest: an order can contain
several items from the same category and several sellers, so summing review
scores at item level would count the same opinion twice. De-duplicating to
(order, category) guarantees **one score per order per group**.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd

from .cleaning import CleanTables, build_clean_tables
from .config import (
    CORE_WINDOW_END,
    CORE_WINDOW_START,
    DATA_PROCESSED_DIR,
    RAW_TABLES,
)
from .data_loader import load_raw_tables

_MANIFEST = DATA_PROCESSED_DIR / "_manifest.json"

_ORDER_COLUMNS = [
    "order_id",
    "customer_id",
    "order_status",
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
    "purchase_date",
    "purchase_year",
    "purchase_month",
    "purchase_ym",
    "purchase_weekday",
    "purchase_weekday_num",
    "purchase_hour",
    "is_delivered",
    "in_core_window",
    "delivery_days",
    "promised_days",
    "delay_days",
    "delivery_class",
    "delay_bucket",
    "approval_days",
    "handover_days",
    "last_mile_days",
    "customer_unique_id",
    "customer_city",
    "customer_state",
    "customer_zip_code_prefix",
    "review_score",
    "review_id",
    "payment_rows",
    "payment_total",
    "payment_max_installments",
    "payment_types",
    "payment_type_main",
    "item_count",
    "item_total_price",
    "item_total_freight",
    "item_mean_price",
    "item_max_price",
    "n_sellers",
    "main_category",
    "order_total_value",
]


def _merge(frame: pd.DataFrame, other: pd.DataFrame, on, how: str, validate: str, label: str):
    """Merge with a cardinality assertion so a join can never silently fan out."""
    before = len(frame)
    merged = frame.merge(other, on=on, how=how, validate=validate, suffixes=("", "_y"))
    assert len(merged) == before, (
        f"Join '{label}' changed the row count from {before} to {len(merged)}"
    )
    return merged


# --------------------------------------------------------------------------- #
# Order grain
# --------------------------------------------------------------------------- #
def build_order_features(tables: CleanTables) -> pd.DataFrame:
    """One row per order, enriched with customer, item, payment and review data."""
    orders = tables.orders
    customers = tables.customers
    items = tables.order_items
    payments = tables.order_payments
    reviews = tables.reviews_per_order

    base = _merge(
        orders,
        customers[
            ["customer_id", "customer_unique_id", "customer_city", "customer_state",
             "customer_zip_code_prefix"]
        ],
        on="customer_id",
        how="left",
        validate="one_to_one",
        label="orders x customers",
    )

    item_agg = items.groupby("order_id", as_index=False).agg(
        item_count=("order_item_id", "size"),
        item_total_price=("price", "sum"),
        item_total_freight=("freight_value", "sum"),
        item_mean_price=("price", "mean"),
        item_max_price=("price", "max"),
        n_sellers=("seller_id", "nunique"),
    )
    base = _merge(base, item_agg, on="order_id", how="left", validate="one_to_one",
                  label="orders x item aggregates")

    payment_agg = payments.groupby("order_id", as_index=False).agg(
        payment_rows=("payment_sequential", "size"),
        payment_total=("payment_value", "sum"),
        payment_max_installments=("payment_installments", "max"),
        payment_types=("payment_type", "nunique"),
    )
    dominant = (
        payments.sort_values(["order_id", "payment_value"], ascending=[True, False])
        .drop_duplicates(subset=["order_id"])
        .rename(columns={"payment_type": "payment_type_main"})[
            ["order_id", "payment_type_main"]
        ]
    )
    payment_agg = payment_agg.merge(dominant, on="order_id", how="left", validate="one_to_one")
    base = _merge(base, payment_agg, on="order_id", how="left", validate="one_to_one",
                  label="orders x payment aggregates")

    review_cols = reviews[["order_id", "review_id", "review_score"]]
    base = _merge(base, review_cols, on="order_id", how="left", validate="one_to_one",
                  label="orders x reviews-per-order")

    # Main category: the category of the most expensive item of the order.
    ranked_items = items.sort_values(["order_id", "price"], ascending=[True, False])
    product_category = tables.products[["product_id", "category_label"]]
    ranked_items = ranked_items.merge(product_category, on="product_id", how="left",
                                      validate="many_to_one")
    main_category = (
        ranked_items.drop_duplicates(subset=["order_id"])
        .rename(columns={"category_label": "main_category"})[["order_id", "main_category"]]
    )
    base = _merge(base, main_category, on="order_id", how="left", validate="one_to_one",
                  label="orders x main category")

    base["order_total_value"] = base["item_total_price"].fillna(0) + base[
        "item_total_freight"
    ].fillna(0)

    return _add_calendar_and_delivery_features(base)


def _add_calendar_and_delivery_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Calendar keys plus the delivery/delay definitions used everywhere."""
    out = frame.copy()
    purchase = out["order_purchase_timestamp"]
    delivered = out["order_delivered_customer_date"]
    estimated = out["order_estimated_delivery_date"]

    out["purchase_date"] = purchase.dt.normalize()
    out["purchase_year"] = purchase.dt.year.astype("Int64")
    out["purchase_month"] = purchase.dt.month.astype("Int64")
    out["purchase_month_name"] = purchase.dt.month_name()
    out["purchase_ym"] = purchase.dt.strftime("%Y-%m")
    out["purchase_weekday"] = purchase.dt.day_name()
    out["purchase_weekday_num"] = purchase.dt.dayofweek.astype("Int64")
    out["purchase_hour"] = purchase.dt.hour.astype("Int64")

    out["is_delivered"] = out["order_status"].eq("delivered")

    window_start = pd.Timestamp(CORE_WINDOW_START)
    window_end = pd.Timestamp(CORE_WINDOW_END) + pd.Timedelta(days=1)
    out["in_core_window"] = purchase.ge(window_start) & purchase.lt(window_end)

    day = pd.Timedelta(days=1).total_seconds()
    out["delivery_days"] = (delivered - purchase).dt.total_seconds() / day
    out["promised_days"] = (estimated - purchase).dt.total_seconds() / day
    out["approval_days"] = (
        out["order_approved_at"] - purchase
    ).dt.total_seconds() / day
    out["handover_days"] = (
        out["order_delivered_carrier_date"] - purchase
    ).dt.total_seconds() / day
    out["last_mile_days"] = (
        delivered - out["order_delivered_carrier_date"]
    ).dt.total_seconds() / day

    # Delay is measured on CALENDAR DATES, not on raw timestamps.
    # order_estimated_delivery_date is stored at 00:00:00, so a difference of
    # raw timestamps would classify almost every on-time delivery as "early"
    # and would make the "on time" class empty (verified: 0 rows with a raw
    # difference of exactly zero, vs 4,059 orders delivered on the promised
    # calendar date). Comparing dates matches how the promise is communicated.
    delay = (delivered.dt.normalize() - estimated.dt.normalize()).dt.days
    out["delay_days"] = delay.astype("Int64")

    out["delivery_class"] = pd.Series(pd.NA, index=out.index, dtype="str")
    has_delay = out["delay_days"].notna()
    out.loc[has_delay & (out["delay_days"] < 0), "delivery_class"] = "early"
    out.loc[has_delay & (out["delay_days"] == 0), "delivery_class"] = "on_time"
    out.loc[has_delay & (out["delay_days"] > 0), "delivery_class"] = "late"

    bucket = pd.Series(pd.NA, index=out.index, dtype="str")
    bucket.loc[has_delay & (out["delay_days"] <= 0)] = "on_time_or_early"
    bucket.loc[has_delay & out["delay_days"].between(1, 3)] = "1_3_days"
    bucket.loc[has_delay & out["delay_days"].between(4, 7)] = "4_7_days"
    bucket.loc[has_delay & (out["delay_days"] > 7)] = "more_than_7_days"
    out["delay_bucket"] = bucket

    return out


# --------------------------------------------------------------------------- #
# Item grain
# --------------------------------------------------------------------------- #
def build_item_features(tables: CleanTables, order_features: pd.DataFrame) -> pd.DataFrame:
    """One row per order item, with product category, seller location and order context."""
    items = tables.order_items
    out = items.merge(
        tables.products[
            ["product_id", "product_category_name", "category_label", "has_translation",
             "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]
        ],
        on="product_id",
        how="left",
        validate="many_to_one",
    )
    out = out.merge(
        tables.sellers[["seller_id", "seller_city", "seller_state"]],
        on="seller_id",
        how="left",
        validate="many_to_one",
    )
    order_context = order_features[
        ["order_id", "order_status", "is_delivered", "purchase_ym", "purchase_year",
         "purchase_month", "in_core_window", "review_score", "customer_state",
         "delivery_class", "delay_days", "delivery_days"]
    ]
    out = out.merge(order_context, on="order_id", how="left", validate="many_to_one")

    # Each row of the items table represents one unit, so item revenue = price.
    out["item_revenue"] = out["price"]
    out["line_total"] = out["price"] + out["freight_value"]
    out["product_volume_cm3"] = (
        out["product_length_cm"] * out["product_height_cm"] * out["product_width_cm"]
    )
    return out


def build_order_category(item_features: pd.DataFrame) -> pd.DataFrame:
    """One row per (order, category) with revenue and the single order-level score."""
    revenue = item_features.groupby(["order_id", "category_label"], as_index=False).agg(
        revenue=("price", "sum"),
        n_items=("order_item_id", "size"),
        mean_item_price=("price", "mean"),
    )
    context = item_features.drop_duplicates(subset=["order_id"])[
        ["order_id", "review_score", "purchase_ym", "purchase_year", "in_core_window",
         "order_status", "delivery_class", "delay_days", "customer_state"]
    ]
    return revenue.merge(context, on="order_id", how="left", validate="many_to_one")


def build_order_seller(item_features: pd.DataFrame) -> pd.DataFrame:
    """One row per (order, seller) with revenue and the single order-level score."""
    revenue = item_features.groupby(["order_id", "seller_id"], as_index=False).agg(
        revenue=("price", "sum"),
        n_items=("order_item_id", "size"),
        seller_state=("seller_state", "first"),
    )
    context = item_features.drop_duplicates(subset=["order_id"])[
        ["order_id", "review_score", "purchase_ym", "in_core_window", "order_status",
         "delivery_class", "delay_days"]
    ]
    return revenue.merge(context, on="order_id", how="left", validate="many_to_one")


# --------------------------------------------------------------------------- #
# Dataset container
# --------------------------------------------------------------------------- #
@dataclass
class Dataset:
    """Everything the analysis layer needs, already validated at build time."""

    tables: CleanTables
    order_features: pd.DataFrame
    item_features: pd.DataFrame
    order_category: pd.DataFrame
    order_seller: pd.DataFrame

    @property
    def orders(self) -> pd.DataFrame:
        return self.order_features

    @property
    def items(self) -> pd.DataFrame:
        return self.item_features

    @property
    def core_orders(self) -> pd.DataFrame:
        """Orders inside the contiguous 2017-01 .. 2018-08 analysis window."""
        return self.order_features[self.order_features["in_core_window"]]

    @property
    def delivered(self) -> pd.DataFrame:
        """Delivered orders with a usable actual delivery timestamp."""
        return self.order_features[
            self.order_features["is_delivered"] & self.order_features["delivery_days"].notna()
        ]

    @property
    def delivered_with_delay(self) -> pd.DataFrame:
        return self.delivered[self.delivered["delay_days"].notna()]

    @property
    def log(self) -> dict:
        return self.tables.log

    # Convenience accessors for the clean base tables
    @property
    def customers(self) -> pd.DataFrame:
        return self.tables.customers

    @property
    def payments(self) -> pd.DataFrame:
        return self.tables.order_payments

    @property
    def reviews(self) -> pd.DataFrame:
        return self.tables.order_reviews

    @property
    def products(self) -> pd.DataFrame:
        return self.tables.products

    @property
    def sellers(self) -> pd.DataFrame:
        return self.tables.sellers

    @property
    def geo_centroids(self) -> pd.DataFrame:
        return self.tables.geo_centroids

    @property
    def reviews_per_order(self) -> pd.DataFrame:
        return self.tables.reviews_per_order


def build_dataset(raw_tables: dict[str, pd.DataFrame] | None = None) -> Dataset:
    """Build every grain from scratch."""
    raw = raw_tables if raw_tables is not None else load_raw_tables()
    tables = build_clean_tables(raw)
    order_features = build_order_features(tables)
    item_features = build_item_features(tables, order_features)
    order_category = build_order_category(item_features)
    order_seller = build_order_seller(item_features)
    return Dataset(
        tables=tables,
        order_features=order_features,
        item_features=item_features,
        order_category=order_category,
        order_seller=order_seller,
    )


# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #
def _dataset_frames(dataset: Dataset) -> dict[str, pd.DataFrame]:
    return {
        "order_features": dataset.order_features,
        "item_features": dataset.item_features,
        "order_category": dataset.order_category,
        "order_seller": dataset.order_seller,
        "customers": dataset.customers,
        "payments": dataset.payments,
        "reviews": dataset.reviews,
        "reviews_per_order": dataset.reviews_per_order,
        "products": dataset.products,
        "sellers": dataset.sellers,
        "geo_centroids": dataset.geo_centroids,
    }


def save_dataset(dataset: Dataset) -> None:
    """Persist the analysis grains as parquet plus a manifest of row counts."""
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for name, frame in _dataset_frames(dataset).items():
        frame.to_parquet(DATA_PROCESSED_DIR / f"{name}.parquet", index=False)
    manifest = {
        "rows": {name: int(len(frame)) for name, frame in _dataset_frames(dataset).items()},
        "cleaning_log": {k: int(v) for k, v in dataset.log.items()},
        "raw_fingerprint": {
            name: spec.path.stat().st_mtime_ns for name, spec in RAW_TABLES.items()
        },
    }
    _MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _manifest_is_current() -> bool:
    if not _MANIFEST.exists():
        return False
    try:
        manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    stored = manifest.get("raw_fingerprint", {})
    current = {name: spec.path.stat().st_mtime_ns for name, spec in RAW_TABLES.items()}
    return stored == current


def load_dataset(force_rebuild: bool = False) -> Dataset:
    """Load the cached analysis grains, rebuilding when the raw data changed."""
    if not force_rebuild and _manifest_is_current():
        frames = {
            name: pd.read_parquet(DATA_PROCESSED_DIR / f"{name}.parquet")
            for name in _dataset_frames_placeholder()
        }
        manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
        raw = load_raw_tables()
        tables = build_clean_tables(raw)
        # The clean per-table frames are cheap to rebuild from the raw cache and
        # keep a single source of truth for the cleaning log.
        dataset = Dataset(
            tables=tables,
            order_features=frames["order_features"],
            item_features=frames["item_features"],
            order_category=frames["order_category"],
            order_seller=frames["order_seller"],
        )
        assert manifest["rows"]["order_features"] == len(dataset.order_features)
        return dataset

    dataset = build_dataset()
    save_dataset(dataset)
    return dataset


def _dataset_frames_placeholder() -> list[str]:
    return [
        "order_features",
        "item_features",
        "order_category",
        "order_seller",
        "customers",
        "payments",
        "reviews",
        "reviews_per_order",
        "products",
        "sellers",
        "geo_centroids",
    ]
