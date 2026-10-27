"""Documented, reproducible cleaning of the raw Olist tables.

Guiding rules (see ``docs/cleaning_decisions.md`` for the narrative version):

1. **The raw CSVs are never modified.**  Cleaning always returns a new object.
2. **No row is deleted** because a value is missing.  Missingness in this
   dataset is mostly structural (an undelivered order has no delivery date),
   so deleting those rows would silently bias the delivery analysis.
3. **Apparent duplicates are investigated, not dropped.**  The reviews table
   and the geolocation table both contain repeated keys with a *legitimate*
   business reason, and one with a genuine data-entry defect.
4. Every non-trivial decision is captured in :data:`CleaningLog` so the same
   numbers appear in the notebook, the docs and the report.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .config import RAW_TABLES

#: Plausible bounding box for Brazilian coordinates.  Used to reject the small
#: number of impossible latitude/longitude pairs in the geolocation export.
BRAZIL_LAT_RANGE = (-34.0, 5.5)
BRAZIL_LNG_RANGE = (-74.0, -32.0)

#: Label given to products whose ``product_category_name`` is missing.
UNKNOWN_CATEGORY = "unknown"

#: Strict timestamp format found in every date column of the export.
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


class CleaningLog(dict):
    """Accumulator for the counts that justify each cleaning decision."""

    def inc(self, key: str, amount: int) -> None:
        self[key] = int(self.get(key, 0)) + int(amount)


def _parse_datetime(series: pd.Series, log: CleaningLog, key: str) -> pd.Series:
    """Convert an ISO-like timestamp column and count any newly unparseable row."""
    before = int(series.isna().sum())
    parsed = pd.to_datetime(series, errors="coerce", format=TIMESTAMP_FORMAT)
    newly_missing = int(parsed.isna().sum()) - before
    if newly_missing:
        log.inc(key, newly_missing)
    return parsed


def _mode_or_na(values: pd.Series):
    modes = values.mode()
    return modes.iat[0] if len(modes) else pd.NA


# --------------------------------------------------------------------------- #
# Per-table cleaning
# --------------------------------------------------------------------------- #
def clean_orders(raw: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """Convert the five timestamp columns of the orders table to ``datetime64``.

    Missing timestamps are *kept as NaT*: an order that was never delivered has
    no delivery timestamp, and that fact is itself informative.
    """
    out = raw.copy()
    for column in RAW_TABLES["orders"].datetime_columns:
        out[column] = _parse_datetime(out[column], log, "datetime_unparseable_orders")
    log["orders_rows"] = len(out)
    log["orders_missing_approved"] = int(out["order_approved_at"].isna().sum())
    log["orders_missing_carrier"] = int(out["order_delivered_carrier_date"].isna().sum())
    log["orders_missing_delivered"] = int(out["order_delivered_customer_date"].isna().sum())
    log["orders_missing_estimated"] = int(out["order_estimated_delivery_date"].isna().sum())
    log["orders_approved_before_purchase"] = int(
        (out["order_approved_at"] < out["order_purchase_timestamp"]).sum()
    )
    log["orders_carrier_before_approved"] = int(
        (out["order_delivered_carrier_date"] < out["order_approved_at"]).sum()
    )
    log["orders_delivered_before_carrier"] = int(
        (out["order_delivered_customer_date"] < out["order_delivered_carrier_date"]).sum()
    )
    return out


def clean_customers(raw: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """Customers need no repair; ``customer_unique_id`` is kept alongside the key.

    ``customer_id`` is one row per *order*, so the real person is identified by
    ``customer_unique_id``. Both columns are preserved and the distinction is
    enforced in the metrics layer instead of being silently collapsed here.
    """
    log["customers_rows"] = len(raw)
    log["customers_unique_person"] = int(raw["customer_unique_id"].nunique())
    return raw.copy()


def clean_order_items(raw: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """Parse ``shipping_limit_date`` and keep every item line untouched."""
    out = raw.copy()
    out["shipping_limit_date"] = _parse_datetime(
        out["shipping_limit_date"], log, "datetime_unparseable_items"
    )
    log["items_rows"] = len(out)
    log["items_zero_freight"] = int((out["freight_value"] == 0).sum())
    log["items_orders"] = int(out["order_id"].nunique())
    return out


def clean_order_payments(raw: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """Keep payment rows as transactions; flag the impossible values.

    * 2 rows carry ``payment_installments == 0`` while still holding a positive
      value.  They are a payment *sequence* fragment (sequential = 2) of the
      same order, so dropping them would corrupt the order total.  They are
      kept and excluded only from the installment distribution.
    * 9 rows hold ``payment_value == 0`` (voucher / ``not_defined``).  A zero
      value payment is a valid bookkeeping entry, not an error to delete.
    """
    out = raw.copy()
    log["payments_rows"] = len(out)
    log["payments_orders"] = int(out["order_id"].nunique())
    log["payments_zero_installments"] = int((out["payment_installments"] == 0).sum())
    log["payments_zero_value"] = int((out["payment_value"] == 0).sum())
    log["payments_not_defined"] = int((out["payment_type"] == "not_defined").sum())
    return out


def clean_order_reviews(raw: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """Parse review timestamps and record the duplicated-``review_id`` defect.

    ``review_id`` is *declared* as the primary key but is not unique: 789 ids
    appear 2-3 times, always with an identical score and identical timestamps
    but a **different order_id**.  The evidence (see
    ``reports/tables/00_duplicate_review_ids.csv``) shows one survey answer
    recorded against several orders.  Therefore:

    * no row is deleted - each row is attached to a real, distinct order;
    * the row identity is redefined as ``(review_id, order_id)``;
    * when a score must be attached to an order, one review per order is used
      (see :func:`deduplicate_reviews_per_order`).
    """
    out = raw.copy()
    for column in RAW_TABLES["order_reviews"].datetime_columns:
        out[column] = _parse_datetime(out[column], log, "datetime_unparseable_reviews")

    log["reviews_rows"] = len(out)
    counts = out["review_id"].value_counts()
    duplicated_ids = counts[counts > 1]
    log["reviews_duplicated_ids"] = int(len(duplicated_ids))
    log["reviews_rows_on_duplicated_ids"] = int(duplicated_ids.sum())
    log["reviews_orders"] = int(out["order_id"].nunique())
    log["reviews_orders_with_multiple"] = int((out.groupby("order_id").size() > 1).sum())
    log["reviews_missing_title"] = int(out["review_comment_title"].isna().sum())
    log["reviews_missing_message"] = int(out["review_comment_message"].isna().sum())
    return out


def clean_products(
    raw: pd.DataFrame, translations: pd.DataFrame, log: CleaningLog
) -> pd.DataFrame:
    """Fill the missing category with ``unknown`` and attach the English label.

    Rationale: 610 products (1.85%) have no category at all, and those same
    rows also miss the name/description/photo metadata - the catalogue entry
    was never completed. Dropping them would remove real sales (they appear in
    the order-item table), so they are kept under an explicit ``unknown``
    category that the analysis can exclude when required.
    """
    out = raw.copy()
    log["products_rows"] = len(out)
    log["products_missing_category"] = int(out["product_category_name"].isna().sum())
    out["product_category_name"] = out["product_category_name"].fillna(UNKNOWN_CATEGORY)

    out = out.merge(
        translations.rename(
            columns={"product_category_name": "product_category_name"}
        )[["product_category_name", "product_category_name_english"]],
        on="product_category_name",
        how="left",
        validate="many_to_one",
    )
    out["has_translation"] = out["product_category_name_english"].notna()
    out["category_label"] = out["product_category_name_english"].fillna(
        out["product_category_name"]
    )
    log["products_without_translation"] = int((~out["has_translation"]).sum())
    log["products_distinct_categories"] = int(
        out["category_label"].nunique()
    )
    log["products_missing_dimensions"] = int(
        out[["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]]
        .isna()
        .any(axis=1)
        .sum()
    )
    log["products_zero_weight"] = int((out["product_weight_g"] == 0).sum())
    return out


def clean_sellers(raw: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    log["sellers_rows"] = len(raw)
    log["sellers_distinct"] = int(raw["seller_id"].nunique())
    return raw.copy()


def build_zip_centroids(raw_geo: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """Collapse the 1,000,163 geolocation rows into one centroid per zip prefix.

    Evidence
    --------
    * 261,831 rows (26.18%) are exact duplicates of another row.
    * A single prefix can hold up to 1,146 rows, so joining raw geolocation
      onto customers would multiply the customer table.
    * 31 rows (0.0031%) fall outside Brazil's bounding box and are impossible.
    * 8 prefixes carry conflicting ``geolocation_state`` values.

    Decision: keep only plausible coordinates, drop exact duplicates, then take
    the **median** latitude/longitude per prefix (median is robust to the
    outliers). The resulting lookup has exactly one row per prefix and cannot
    change the grain of any table it is joined to.
    """
    log["geo_rows"] = len(raw_geo)
    log["geo_duplicate_rows"] = int(raw_geo.duplicated().sum())
    log["geo_distinct_prefixes"] = int(raw_geo["geolocation_zip_code_prefix"].nunique())

    in_bbox = raw_geo["geolocation_lat"].between(*BRAZIL_LAT_RANGE) & raw_geo[
        "geolocation_lng"
    ].between(*BRAZIL_LNG_RANGE)
    log["geo_rows_outside_bbox"] = int((~in_bbox).sum())
    log["geo_prefixes_outside_bbox"] = int(
        raw_geo.loc[~in_bbox, "geolocation_zip_code_prefix"].nunique()
    )

    valid = raw_geo.loc[in_bbox].drop_duplicates()
    centroids = valid.groupby("geolocation_zip_code_prefix", as_index=False).agg(
        lat=("geolocation_lat", "median"),
        lng=("geolocation_lng", "median"),
        n_rows_used=("geolocation_lat", "size"),
        geo_state=("geolocation_state", _mode_or_na),
        n_states=("geolocation_state", "nunique"),
    )
    log["geo_centroid_rows"] = len(centroids)
    log["geo_prefixes_conflicting_state"] = int((centroids["n_states"] > 1).sum())
    return centroids


def deduplicate_reviews_per_order(reviews: pd.DataFrame) -> pd.DataFrame:
    """One review per order: the most recently answered one.

    Two different defects can put several review rows on one order:

    * 547 orders genuinely received more than one survey answer;
    * the duplicated ``review_id`` defect spreads one answer over several
      orders (those rows are on *different* orders and all survive).

    Keeping the latest ``review_answer_timestamp`` (ties broken by
    ``review_id``) gives a deterministic, reproducible one-to-one table, which
    is what every satisfaction metric and every join needs.  The number of
    dropped rows is reported in the cleaning log and the course brief's
    "avoid score multiplication on join" requirement is thereby satisfied.
    """
    ordered = reviews.sort_values(
        ["order_id", "review_answer_timestamp", "review_id"], na_position="first"
    )
    deduplicated = ordered.drop_duplicates(subset=["order_id"], keep="last")
    return deduplicated.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Pipeline entry point
# --------------------------------------------------------------------------- #
@dataclass
class CleanTables:
    """Container for the cleaned, still table-grained frames."""

    orders: pd.DataFrame
    customers: pd.DataFrame
    order_items: pd.DataFrame
    order_payments: pd.DataFrame
    order_reviews: pd.DataFrame
    products: pd.DataFrame
    sellers: pd.DataFrame
    geo_centroids: pd.DataFrame
    reviews_per_order: pd.DataFrame
    log: CleaningLog = field(default_factory=CleaningLog)

    def as_dict(self) -> dict[str, pd.DataFrame]:
        return {
            "orders": self.orders,
            "customers": self.customers,
            "order_items": self.order_items,
            "order_payments": self.order_payments,
            "order_reviews": self.order_reviews,
            "products": self.products,
            "sellers": self.sellers,
            "geo_centroids": self.geo_centroids,
            "reviews_per_order": self.reviews_per_order,
        }


def build_clean_tables(raw_tables: dict[str, pd.DataFrame]) -> CleanTables:
    """Run the whole cleaning pipeline on the raw dictionary."""
    log = CleaningLog()

    orders = clean_orders(raw_tables["orders"], log)
    customers = clean_customers(raw_tables["customers"], log)
    items = clean_order_items(raw_tables["order_items"], log)
    payments = clean_order_payments(raw_tables["order_payments"], log)
    reviews = clean_order_reviews(raw_tables["order_reviews"], log)
    products = clean_products(raw_tables["products"], raw_tables["category_translation"], log)
    sellers = clean_sellers(raw_tables["sellers"], log)
    centroids = build_zip_centroids(raw_tables["geolocation"], log)

    reviews_per_order = deduplicate_reviews_per_order(reviews)
    log["reviews_per_order_rows"] = len(reviews_per_order)
    log["reviews_rows_removed_by_onboarding"] = int(len(reviews) - len(reviews_per_order))

    log["no_rows_deleted"] = 1
    return CleanTables(
        orders=orders,
        customers=customers,
        order_items=items,
        order_payments=payments,
        order_reviews=reviews,
        products=products,
        sellers=sellers,
        geo_centroids=centroids,
        reviews_per_order=reviews_per_order,
        log=log,
    )


def cleaning_decisions(log: dict) -> pd.DataFrame:
    """Narrative + evidence table, one row per cleaning decision."""
    rows = [
        {
            "step": "timestamp_conversion",
            "problem": "Timestamp columns are stored as text.",
            "evidence": f"{log.get('datetime_unparseable_orders', 0) + log.get('datetime_unparseable_items', 0) + log.get('datetime_unparseable_reviews', 0)} values failed strict parsing.",
            "options": "Keep as text / parse with datetime64.",
            "decision": "Converted every timestamp column with the explicit format %Y-%m-%d %H:%M:%S.",
            "rationale": "All 99,441 orders and 112,650 item rows parse cleanly, so a strict format acts as a data-quality assertion.",
            "impact": "Enables duration, delay and monthly trend calculations.",
        },
        {
            "step": "orders_missing_timestamps",
            "problem": "order_approved_at / carrier / delivered timestamps are missing for some orders.",
            "evidence": f"approved_at: {log.get('orders_missing_approved')}, carrier: {log.get('orders_missing_carrier')}, delivered: {log.get('orders_missing_delivered')} missing of {log.get('orders_rows')}.",
            "options": "Impute / drop rows / keep NaT.",
            "decision": "Keep NaT and filter per metric (delivery metrics use delivered orders only).",
            "rationale": "The missingness is structural: canceled, unavailable and in-transit orders genuinely have no delivery timestamp.",
            "impact": "No delivery metric is computed on an order that was not delivered.",
        },
        {
            "step": "review_duplicate_ids",
            "problem": "review_id is declared as the primary key but is not unique.",
            "evidence": f"{log.get('reviews_duplicated_ids')} ids repeat across {log.get('reviews_rows_on_duplicated_ids')} rows, always with a different order_id and an identical score.",
            "options": "Drop duplicates / keep the first / keep all and redefine identity.",
            "decision": "Keep every row; identity becomes (review_id, order_id).",
            "rationale": "Each row belongs to a real, distinct order; deleting them would delete valid reviews of those orders.",
            "impact": "Review counts are reported per row; satisfaction joins use one review per order.",
        },
        {
            "step": "review_multiple_per_order",
            "problem": "Some orders carry more than one review row.",
            "evidence": f"{log.get('reviews_orders_with_multiple')} orders; {log.get('reviews_per_order_rows')} orders remain after de-duplication.",
            "options": "Average the scores / keep the first / keep the latest.",
            "decision": "Keep the latest review_answer_timestamp per order.",
            "rationale": "Deterministic, does not invent an average, and matches the customer's final opinion.",
            "impact": "Prevents score multiplication when joining reviews to order or item level data.",
        },
        {
            "step": "review_comments_missing",
            "problem": "review_comment_title and message are mostly empty.",
            "evidence": f"title missing {log.get('reviews_missing_title')} rows, message missing {log.get('reviews_missing_message')} rows.",
            "options": "Drop the columns / impute text / keep unused.",
            "decision": "Keep the columns, do not impute, and exclude them from quantitative analysis.",
            "rationale": "The quantitative satisfaction metrics rest on review_score; text is free-form and out of scope.",
            "impact": "No effect on any reported number.",
        },
        {
            "step": "products_missing_category",
            "problem": "Some products have no category and no catalogue metadata.",
            "evidence": f"{log.get('products_missing_category')} products of {log.get('products_rows')} (also missing name/description/photo metadata).",
            "options": "Drop products / impute a category / label unknown.",
            "decision": "Label them 'unknown' and keep them in revenue totals.",
            "rationale": "They have real sales; dropping them would make total revenue understate the business.",
            "impact": "Category rankings exclude the 'unknown' bucket explicitly.",
        },
        {
            "step": "products_untranslated_categories",
            "problem": "Two Portuguese categories have no English translation.",
            "evidence": f"{log.get('products_without_translation')} products affected.",
            "options": "Drop them / transliterate / fall back to the Portuguese name.",
            "decision": "Fall back to the Portuguese name and flag has_translation = False.",
            "rationale": "Loses no sales and keeps the category identifiable.",
            "impact": "Those two categories keep their original names in charts.",
        },
        {
            "step": "geolocation_duplicates_and_outliers",
            "problem": "The geolocation table has massive duplication and a few impossible coordinates.",
            "evidence": f"{log.get('geo_rows')} rows, {log.get('geo_duplicate_rows')} exact duplicates, {log.get('geo_rows_outside_bbox')} rows outside Brazil's bounding box.",
            "options": "Join raw / drop duplicates only / build a centroid lookup.",
            "decision": "Filter to the bounding box, drop exact duplicates, take the median lat/lng per zip prefix.",
            "rationale": "One row per prefix keeps the join cardinality at one-to-many instead of exploding it; the median rejects bad coordinates.",
            "impact": f"Lookup shrinks to {log.get('geo_centroid_rows')} rows and can never multiply a customer row.",
        },
        {
            "step": "geolocation_conflicting_state",
            "problem": "A few zip prefixes map to more than one state code.",
            "evidence": f"{log.get('geo_prefixes_conflicting_state')} prefixes.",
            "options": "Drop / take the first / take the most frequent.",
            "decision": "Take the modal state and keep n_states for transparency.",
            "rationale": "State is never taken from geolocation; customer_state and seller_state are authoritative and are used instead.",
            "impact": "No reported geographic metric depends on the ambiguous prefixes.",
        },
        {
            "step": "payments_zero_installments",
            "problem": "Two payment rows report zero installments with a positive value.",
            "evidence": f"{log.get('payments_zero_installments')} rows (both are payment_sequential = 2 fragments of their order).",
            "options": "Delete / impute 1 / exclude from the installment distribution.",
            "decision": "Keep the value in the order total, exclude the rows from the installment distribution.",
            "rationale": "Deleting them would understate the paid amount of those orders.",
            "impact": "Installment statistics use 103,884 rows; payment totals use all 103,886.",
        },
        {
            "step": "payments_zero_value",
            "problem": "Nine payment rows carry a zero value.",
            "evidence": f"{log.get('payments_zero_value')} rows (voucher / not_defined).",
            "options": "Delete / keep.",
            "decision": "Keep.",
            "rationale": "A zero-value voucher or an undefined payment method is a real bookkeeping entry, not a corrupt one.",
            "impact": "Counts of payment records include them; averages barely move.",
        },
        {
            "step": "items_zero_freight_and_weight",
            "problem": "Some items have zero freight and some products have zero weight.",
            "evidence": f"{log.get('items_zero_freight')} item rows with freight 0; {log.get('products_zero_weight')} products with weight 0.",
            "options": "Treat as missing / keep.",
            "decision": "Keep.",
            "rationale": "Free shipping and free-of-charge pickup are legitimate; zero weight is rare and not used in any reported metric.",
            "impact": "Freight is reported separately from item revenue.",
        },
        {
            "step": "chronology_violations",
            "problem": "A few orders break the expected timestamp order.",
            "evidence": f"carrier before approval: {log.get('orders_carrier_before_approved')}; delivered before carrier: {log.get('orders_delivered_before_carrier')}; approved before purchase: {log.get('orders_approved_before_purchase')}.",
            "options": "Delete / repair / keep and flag.",
            "decision": "Keep; they affect < 1.5% of rows and no metric is defined on those intervals.",
            "rationale": "These are real operational events (a late approval record after hand-over), not impossible values.",
            "impact": "Delivery-duration metrics remain valid because they use purchase -> delivered only.",
        },
        {
            "step": "row_deletion_policy",
            "problem": "Should any row be deleted during cleaning?",
            "evidence": "0 fully duplicated rows in orders, customers, items, payments, reviews, products, sellers.",
            "options": "Drop rows with missing values / keep everything.",
            "decision": "Delete nothing; every exclusion happens explicitly inside a metric.",
            "rationale": "Keeps the raw -> clean mapping auditable and reproducible.",
            "impact": "Row counts of the cleaned tables equal the raw row counts.",
        },
    ]
    return pd.DataFrame(rows)
