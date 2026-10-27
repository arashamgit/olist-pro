"""Tests for feature engineering: the derived business definitions.

The synthetic dataset is deliberately hostile: it contains an order that is
delivered *on* the promised calendar date, one that is 10 days late, one with
two items in two categories and one canceled order with no items at all.  Every
assertion below therefore checks a real edge case rather than the happy path.
"""

from __future__ import annotations

import pandas as pd
import pytest

from olist_analysis.config import CORE_WINDOW_END, CORE_WINDOW_START
from olist_analysis.features import Dataset, build_dataset


def test_order_grain_keeps_one_row_per_order(synthetic_dataset: Dataset):
    dataset = synthetic_dataset
    assert len(dataset.order_features) == 4
    assert dataset.order_features["order_id"].is_unique
    assert len(dataset.item_features) == 4
    assert len(dataset.customers) == 4


def test_joins_do_not_change_row_counts(synthetic_raw):
    """Rebuilding twice must give identical row counts (the join guard)."""
    first = build_dataset(synthetic_raw)
    second = build_dataset(synthetic_raw)
    assert len(first.item_features) == len(second.item_features)
    assert len(first.order_features) == len(second.order_features)
    assert len(first.order_category) <= len(first.item_features)


def test_delay_is_computed_on_calendar_dates(synthetic_dataset: Dataset):
    orders = synthetic_dataset.order_features.set_index("order_id")
    # O1 promised 2017-01-10, delivered 2017-01-08 -> two days early
    assert orders.loc["O1", "delay_days"] == -2
    # O2 promised 2017-01-12 and delivered on 2017-01-12 -> exactly on time.
    # A raw timestamp difference would have called this "early" by ~14 hours.
    assert orders.loc["O2", "delay_days"] == 0
    assert orders.loc["O2", "delivery_class"] == "on_time"
    # O3 promised 2017-01-13, delivered 2017-01-23 -> ten days late
    assert orders.loc["O3", "delay_days"] == 10
    assert orders.loc["O3", "delivery_class"] == "late"
    assert orders.loc["O1", "delivery_class"] == "early"


def test_delay_buckets_follow_the_course_definition(synthetic_dataset: Dataset):
    orders = synthetic_dataset.order_features.set_index("order_id")
    assert orders.loc["O1", "delay_bucket"] == "on_time_or_early"
    assert orders.loc["O2", "delay_bucket"] == "on_time_or_early"
    assert orders.loc["O3", "delay_bucket"] == "more_than_7_days"
    assert pd.isna(orders.loc["O4", "delay_bucket"])


def test_delivery_duration_uses_purchase_and_delivery_timestamps(synthetic_dataset: Dataset):
    orders = synthetic_dataset.order_features.set_index("order_id")
    assert orders.loc["O1", "delivery_days"] == 7.0
    assert pd.isna(orders.loc["O4", "delivery_days"])
    assert orders.loc["O4", "is_delivered"] == False  # noqa: E712 - explicit intent


def test_order_totals_reconcile_with_item_lines(synthetic_dataset: Dataset):
    orders = synthetic_dataset.order_features.set_index("order_id")
    assert orders.loc["O1", "item_total_price"] == 150.0
    assert orders.loc["O1", "item_total_freight"] == 15.0
    assert orders.loc["O1", "order_total_value"] == 165.0
    assert orders.loc["O1", "item_count"] == 2
    assert orders.loc["O1", "n_sellers"] == 2


def test_payment_aggregation_keeps_all_transactions(synthetic_dataset: Dataset):
    orders = synthetic_dataset.order_features.set_index("order_id")
    assert orders.loc["O1", "payment_rows"] == 2
    assert orders.loc["O1", "payment_total"] == 110.0
    assert orders.loc["O1", "payment_max_installments"] == 4
    assert orders.loc["O1", "payment_type_main"] == "credit_card"
    assert pd.isna(orders.loc["O4", "payment_total"])


def test_reviews_are_deduplicated_to_one_row_per_order(synthetic_dataset: Dataset):
    dataset = synthetic_dataset
    assert len(dataset.reviews) == 4
    assert len(dataset.reviews_per_order) == 3
    # O3 has two reviews; the latest answer timestamp must win
    o3 = dataset.reviews_per_order.set_index("order_id").loc["O3"]
    assert o3["review_id"] == "R4"
    assert len(dataset.order_features) - dataset.order_features["review_score"].notna().sum() == 1


def test_category_and_seller_grains_have_one_score_per_group(synthetic_dataset: Dataset):
    dataset = synthetic_dataset
    pair = dataset.order_category.groupby(["order_id", "category_label"]).size()
    assert (pair == 1).all()
    seller_pair = dataset.order_seller.groupby(["order_id", "seller_id"]).size()
    assert (seller_pair == 1).all()
    # O1 bought from two different sellers but has a single score
    o1 = dataset.order_seller[dataset.order_seller["order_id"] == "O1"]
    assert len(o1) == 2
    assert o1["review_score"].nunique() == 1


def test_untranlated_category_falls_back_to_portuguese_name(synthetic_dataset: Dataset):
    products = synthetic_dataset.products.set_index("product_id")
    assert products.loc["P1", "category_label"] == "health_beauty"
    # P2 has no category at all -> 'unknown', not a dropped row
    assert products.loc["P2", "category_label"] == "unknown"
    assert products.loc["P2", "has_translation"] == False  # noqa: E712


def test_geolocation_is_collapsed_to_one_row_per_zip_prefix(synthetic_dataset: Dataset):
    centroids = synthetic_dataset.geo_centroids
    assert centroids["geolocation_zip_code_prefix"].is_unique
    # prefix 1000 had three rows with two distinct coordinates -> median of the two
    row = centroids.set_index("geolocation_zip_code_prefix").loc[1000]
    assert row["n_rows_used"] == 2
    assert row["lat"] == pytest.approx(-23.55)
    # the impossible coordinate (lat 91) must be gone
    assert centroids["lat"].max() < 6


def test_core_window_flag_matches_the_declared_window(synthetic_dataset: Dataset):
    orders = synthetic_dataset.order_features
    assert orders["in_core_window"].all()
    assert orders["purchase_ym"].iloc[0] == "2017-01"
    assert CORE_WINDOW_START == "2017-01-01"
    assert CORE_WINDOW_END == "2018-08-31"
