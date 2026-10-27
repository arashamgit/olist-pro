"""Shared pytest fixtures.

Two kinds of input are used on purpose:

* **synthetic micro-datasets** for every piece of pure logic (classification,
  bucketing, share arithmetic).  They are tiny, deterministic and allow exact
  expected values.
* **the real dataset** for invariant checks (row counts, join cardinality, sums
  that must reconcile).  Synthetic output is never presented as an Olist
  finding.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from olist_analysis.features import Dataset, build_dataset  # noqa: E402


def _synthetic_raw() -> dict[str, pd.DataFrame]:
    """Four orders covering: early, on-time, very late and a canceled order.

    * O1 - delivered 2 days before the promise, 2 items in 2 categories
    * O2 - delivered on the promised date (calendar date equal)
    * O3 - delivered 10 days after the promise
    * O4 - canceled, no items, no payment, no review
    """
    orders = pd.DataFrame(
        {
            "order_id": ["O1", "O2", "O3", "O4"],
            "customer_id": ["C1", "C2", "C3", "C4"],
            "order_status": ["delivered", "delivered", "delivered", "canceled"],
            "order_purchase_timestamp": [
                "2017-01-01 10:00:00",
                "2017-01-02 10:00:00",
                "2017-01-03 10:00:00",
                "2017-01-04 10:00:00",
            ],
            "order_approved_at": [
                "2017-01-01 12:00:00",
                "2017-01-02 12:00:00",
                "2017-01-03 12:00:00",
                None,
            ],
            "order_delivered_carrier_date": [
                "2017-01-02 10:00:00",
                "2017-01-03 10:00:00",
                "2017-01-04 10:00:00",
                None,
            ],
            "order_delivered_customer_date": [
                "2017-01-08 10:00:00",
                "2017-01-12 10:00:00",
                "2017-01-23 10:00:00",
                None,
            ],
            "order_estimated_delivery_date": [
                "2017-01-10 00:00:00",
                "2017-01-12 00:00:00",
                "2017-01-13 00:00:00",
                "2017-01-20 00:00:00",
            ],
        }
    )
    customers = pd.DataFrame(
        {
            "customer_id": ["C1", "C2", "C3", "C4"],
            "customer_unique_id": ["U1", "U1", "U3", "U4"],
            "customer_zip_code_prefix": [1000, 1000, 2000, 3000],
            "customer_city": ["sao paulo", "sao paulo", "rio", "bahia"],
            "customer_state": ["SP", "SP", "RJ", "BA"],
        }
    )
    order_items = pd.DataFrame(
        {
            "order_id": ["O1", "O1", "O2", "O3"],
            "order_item_id": [1, 2, 1, 1],
            "product_id": ["P1", "P2", "P1", "P3"],
            "seller_id": ["S1", "S2", "S1", "S3"],
            "shipping_limit_date": [
                "2017-01-05 10:00:00",
                "2017-01-05 10:00:00",
                "2017-01-06 10:00:00",
                "2017-01-07 10:00:00",
            ],
            "price": [100.0, 50.0, 100.0, 200.0],
            "freight_value": [10.0, 5.0, 10.0, 20.0],
        }
    )
    order_payments = pd.DataFrame(
        {
            "order_id": ["O1", "O1", "O2", "O3"],
            "payment_sequential": [1, 2, 1, 1],
            "payment_type": ["credit_card", "voucher", "boleto", "credit_card"],
            "payment_installments": [4, 1, 1, 0],
            "payment_value": [100.0, 10.0, 110.0, 220.0],
        }
    )
    order_reviews = pd.DataFrame(
        {
            "review_id": ["R1", "R2", "R3", "R4"],
            "order_id": ["O1", "O2", "O3", "O3"],
            "review_score": [5, 5, 1, 1],
            "review_comment_title": [None, None, None, None],
            "review_comment_message": [None, "ok", None, "late"],
            "review_creation_date": [
                "2017-01-09 00:00:00",
                "2017-01-13 00:00:00",
                "2017-01-24 00:00:00",
                "2017-01-25 00:00:00",
            ],
            "review_answer_timestamp": [
                "2017-01-09 10:00:00",
                "2017-01-13 10:00:00",
                "2017-01-24 10:00:00",
                "2017-01-26 10:00:00",
            ],
        }
    )
    products = pd.DataFrame(
        {
            "product_id": ["P1", "P2", "P3"],
            "product_category_name": ["beleza_saude", None, "moveis_decoracao"],
            "product_name_lenght": [50.0, None, 60.0],
            "product_description_lenght": [500.0, None, 600.0],
            "product_photos_qty": [2.0, None, 3.0],
            "product_weight_g": [500.0, 300.0, 1000.0],
            "product_length_cm": [20.0, 15.0, 30.0],
            "product_height_cm": [10.0, 8.0, 12.0],
            "product_width_cm": [15.0, 10.0, 20.0],
        }
    )
    sellers = pd.DataFrame(
        {
            "seller_id": ["S1", "S2", "S3"],
            "seller_zip_code_prefix": [1000, 2000, 3000],
            "seller_city": ["sao paulo", "rio", "bahia"],
            "seller_state": ["SP", "RJ", "BA"],
        }
    )
    geolocation = pd.DataFrame(
        {
            "geolocation_zip_code_prefix": [1000, 1000, 1000, 2000, 3000],
            "geolocation_lat": [-23.5, -23.5, -23.6, -22.9, 91.0],
            "geolocation_lng": [-46.6, -46.6, -46.7, -43.2, 100.0],
            "geolocation_city": ["sao paulo"] * 3 + ["rio", "nowhere"],
            "geolocation_state": ["SP"] * 3 + ["RJ", "XX"],
        }
    )
    translation = pd.DataFrame(
        {
            "product_category_name": ["beleza_saude", "moveis_decoracao"],
            "product_category_name_english": ["health_beauty", "furniture_decor"],
        }
    )
    return {
        "orders": orders,
        "customers": customers,
        "order_items": order_items,
        "order_payments": order_payments,
        "order_reviews": order_reviews,
        "products": products,
        "sellers": sellers,
        "geolocation": geolocation,
        "category_translation": translation,
    }


@pytest.fixture(scope="session")
def synthetic_raw() -> dict[str, pd.DataFrame]:
    return _synthetic_raw()


@pytest.fixture(scope="session")
def synthetic_dataset(synthetic_raw) -> Dataset:
    return build_dataset(synthetic_raw)


@pytest.fixture(scope="session")
def real_dataset() -> Dataset:
    """The real Olist dataset, skipped when ``data/raw`` is not populated."""
    from olist_analysis.config import RAW_TABLES

    missing = [spec.filename for spec in RAW_TABLES.values() if not spec.path.exists()]
    if missing:
        pytest.skip(f"raw data missing: {missing}")
    from olist_analysis.features import load_dataset

    return load_dataset()
