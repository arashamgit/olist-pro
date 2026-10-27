"""Central configuration for the ``olist-pro`` analysis project.

Design notes
------------
* Every path is derived from :data:`PROJECT_ROOT`, which is resolved from this
  file's location.  Nothing in the project hard-codes an absolute, machine
  specific path (``C:\\Users\\...``), so the same checkout runs on Windows,
  Linux and macOS without edits.
* Table level metadata (file name, declared primary key, timestamp columns) is
  described declaratively in :data:`RAW_TABLES`.  Downstream modules iterate
  over that description instead of repeating literals.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW_DIR = DATA_DIR / "raw"
DATA_INTERIM_DIR = DATA_DIR / "interim"
DATA_PROCESSED_DIR = DATA_DIR / "processed"

REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
TABLES_DIR = REPORTS_DIR / "tables"

ASSETS_DIR = PROJECT_ROOT / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
PERSIAN_FONT_PATH = FONTS_DIR / "Vazirmatn-Regular.ttf"

DELIVERABLES_DIR = PROJECT_ROOT / "deliverables"

for _directory in (
    DATA_INTERIM_DIR,
    DATA_PROCESSED_DIR,
    FIGURES_DIR,
    TABLES_DIR,
    DELIVERABLES_DIR,
):
    _directory.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Table metadata
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TableSpec:
    """Declarative description of one raw CSV table.

    Attributes
    ----------
    name:
        Short, code friendly name used as the dictionary key everywhere.
    filename:
        Exact file name inside ``data/raw``.
    primary_key:
        *Declared* primary key candidate, taken from ``docs/images/database_structure.png``
        and from the business meaning of the table.  Uniqueness is **not**
        assumed: :mod:`olist_analysis.data_quality` verifies it and the result
        is documented in ``docs/data_relationships.md``.
    datetime_columns:
        Columns that must be converted to ``datetime64`` during cleaning.
    description:
        One line business meaning, reused by the data dictionary generator.
    """

    name: str
    filename: str
    primary_key: tuple[str, ...]
    datetime_columns: tuple[str, ...]
    description: str

    @property
    def path(self) -> Path:
        return DATA_RAW_DIR / self.filename


RAW_TABLES: dict[str, TableSpec] = {
    "orders": TableSpec(
        name="orders",
        filename="olist_orders_dataset.csv",
        primary_key=("order_id",),
        datetime_columns=(
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ),
        description="One row per order with its status and full timestamp trail.",
    ),
    "customers": TableSpec(
        name="customers",
        filename="olist_customers_dataset.csv",
        primary_key=("customer_id",),
        datetime_columns=(),
        description="Per-order customer record with city / state / zip code of the buyer.",
    ),
    "order_items": TableSpec(
        name="order_items",
        filename="olist_order_items_dataset.csv",
        primary_key=("order_id", "order_item_id"),
        datetime_columns=("shipping_limit_date",),
        description="One row per item line inside an order, with price, freight and seller.",
    ),
    "order_payments": TableSpec(
        name="order_payments",
        filename="olist_order_payments_dataset.csv",
        primary_key=("order_id", "payment_sequential"),
        datetime_columns=(),
        description="One row per payment transaction belonging to an order.",
    ),
    "order_reviews": TableSpec(
        name="order_reviews",
        filename="olist_order_reviews_dataset.csv",
        primary_key=("review_id",),
        datetime_columns=("review_creation_date", "review_answer_timestamp"),
        description="Customer satisfaction survey answers (score 1-5) linked to orders.",
    ),
    "products": TableSpec(
        name="products",
        filename="olist_products_dataset.csv",
        primary_key=("product_id",),
        datetime_columns=(),
        description="Product catalogue with category and physical dimensions.",
    ),
    "sellers": TableSpec(
        name="sellers",
        filename="olist_sellers_dataset.csv",
        primary_key=("seller_id",),
        datetime_columns=(),
        description="Marketplace sellers with the location they ship from.",
    ),
    "geolocation": TableSpec(
        name="geolocation",
        filename="olist_geolocation_dataset.csv",
        primary_key=(),
        datetime_columns=(),
        description="Zip-code-prefix to latitude / longitude lookup (many rows per prefix).",
    ),
    "category_translation": TableSpec(
        name="category_translation",
        filename="product_category_name_translation.csv",
        primary_key=("product_category_name",),
        datetime_columns=(),
        description="Portuguese to English translation of product category names.",
    ),
}

#: Column that identifies the *physical person* behind repeated purchases.
CUSTOMER_UNIQUE_KEY = "customer_unique_id"

#: Currency of every monetary column in the dataset.
CURRENCY = "BRL"


# --------------------------------------------------------------------------- #
# Analysis contracts (thresholds and definitions used across notebooks)
# --------------------------------------------------------------------------- #
#: Minimum group size before an average rating / average delay is reported as
#: comparable.  Verified against the real data in ``docs/methodology.md``.
MIN_GROUP_SIZE_DEFAULT = 30
MIN_REVIEWS_PER_GROUP = 30
MIN_ORDERS_PER_STATE = 100

#: The dataset contains a very sparse tail at both ends of the timeline
#: (a handful of orders in 2016-09 and a single order in 2018-10).  A month is
#: treated as *comparable* only when it holds at least this many orders.
MIN_ORDERS_PER_MONTH = 100

#: Core analysis window used for every time-series statement.
#:
#: Evidence (see ``reports/tables/00_monthly_orders.csv``):
#:   * 2016 holds 329 orders (0.33%) spread over three non-consecutive months
#:     and has no orders at all in 2016-11 -> the platform was still launching.
#:   * 2018-09 (16 orders) and 2018-10 (4 orders) are truncated at the end of
#:     the export.
#: The 20 months from 2017-01 to 2018-08 therefore hold 99,092 of the 99,441
#: orders (99.65%) and form the only contiguous, comparable window.
CORE_WINDOW_START = "2017-01-01"
CORE_WINDOW_END = "2018-08-31"

#: Downtime convention: a delivered order is "late" when the real delivery
#: timestamp is strictly after the estimated delivery date.
LATE_TOLERANCE_DAYS = 0

#: Delay buckets required by the course brief (question 11.2).
DELAY_BUCKETS: tuple[tuple[str, float, float], ...] = (
    ("on_time_or_early", float("-inf"), 0),
    ("1_3_days", 1, 3),
    ("4_7_days", 4, 7),
    ("more_than_7_days", 7.001, float("inf")),
)

#: Ordered "happy path" status of an order, used for timeline sanity checks.
ORDER_STATUS_ORDER = (
    "delivered",
    "shipped",
    "invoiced",
    "processing",
    "approved",
    "created",
    "unavailable",
    "canceled",
)

#: Palette shared by every figure so the deck looks consistent.
COLOR_PRIMARY = "#2E5F8A"
COLOR_SECONDARY = "#8AB6D6"
COLOR_ACCENT = "#C0392B"
COLOR_MUTED = "#95A5A6"
COLOR_GOOD = "#1E8449"
COLOR_PALETTE = [
    "#2E5F8A",
    "#8AB6D6",
    "#1E8449",
    "#E67E22",
    "#C0392B",
    "#7D3C98",
    "#16A085",
    "#F1C40F",
]

#: Figure geometry: 16:9-ish, exported at 150 dpi for crisp PDF embedding.
FIGURE_SIZE = (11.0, 6.0)
FIGURE_DPI = 150
