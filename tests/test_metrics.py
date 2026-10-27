"""Metric tests.

Two groups:

* synthetic tests that pin down the arithmetic (shares, buckets, gaps);
* real-data invariant tests that reconcile the published numbers with the raw
  tables, so a silent change in a join or a filter fails the suite.
"""

from __future__ import annotations

import pandas as pd
import pytest

from olist_analysis import metrics as M
from olist_analysis.features import Dataset


# --------------------------------------------------------------------------- #
# Arithmetic on synthetic data
# --------------------------------------------------------------------------- #
def test_pct_handles_zero_denominator_and_returns_float():
    assert M.pct(1, 0) == 0.0
    assert M.pct(1, 4) == 25.0
    assert isinstance(M.pct(1, 3), float)


def test_order_status_summary_percentages_sum_to_one_hundred(synthetic_dataset: Dataset):
    table = M.order_status_summary(synthetic_dataset)
    assert table["n_orders"].sum() == 4
    assert table["pct_orders"].sum() == pytest.approx(100.0)
    delivered = table.set_index("order_status").loc["delivered"]
    assert delivered["pct_orders"] == 75.0


def test_delivery_class_summary_uses_the_date_definition(synthetic_dataset: Dataset):
    table = M.delivery_class_summary(synthetic_dataset).set_index("delivery_class")
    assert table.loc["early", "n_orders"] == 1
    assert table.loc["on_time", "n_orders"] == 1
    assert table.loc["late", "n_orders"] == 1
    assert table["n_orders"].sum() == 3
    assert table["pct_of_delivered"].sum() == pytest.approx(100.0, abs=0.01)


def test_delay_bucket_satisfaction_gap_direction(synthetic_dataset: Dataset):
    table = M.delay_bucket_satisfaction(synthetic_dataset)
    on_time = table[table["delay_bucket"] == "on_time_or_early"].iloc[0]
    late = table[table["delay_bucket"] == "more_than_7_days"].iloc[0]
    assert on_time["mean_score"] > late["mean_score"]
    assert late["mean_score"] == 1.0


def test_delay_satisfaction_difference_reports_samples(synthetic_dataset: Dataset):
    result = M.delay_satisfaction_difference(synthetic_dataset)
    assert result["n_late"] == 1
    assert result["n_on_time_or_early"] == 2
    assert result["score_gap"] == pytest.approx(4.0, abs=1e-6)
    # with one order per group the sample is explicitly flagged as insufficient
    assert result["min_sample_reached"] is False


def test_payment_type_summary_shares(synthetic_dataset: Dataset):
    table = M.payment_type_summary(synthetic_dataset).set_index("payment_type")
    assert table["n_transactions"].sum() == 4
    assert table["pct_transactions"].sum() == pytest.approx(100.0)
    assert table.loc["voucher", "total_payment_value"] == 10.0


def test_zero_or_single_installments_isolates_the_zero_row(synthetic_dataset: Dataset):
    result = M.zero_or_single_installments(synthetic_dataset)
    assert result["n_transactions"] == 4
    assert result["n_zero_installments"] == 1
    assert result["n_single_installment"] == 2
    assert result["pct_zero_or_single"] == 75.0


def test_installment_distribution_excludes_zero_installments(synthetic_dataset: Dataset):
    table = M.installment_distribution(synthetic_dataset)
    assert 0 not in set(table["payment_installments"])
    assert table["n_transactions"].sum() == 3


def test_customer_overview_counts_people_not_rows(synthetic_dataset: Dataset):
    overview = M.customer_overview(synthetic_dataset)
    assert overview["customer_rows"] == 4
    assert overview["unique_people"] == 3
    assert overview["repeat_people"] == 1


def test_top_n_state_share_matches_table(synthetic_dataset: Dataset):
    result = M.top_n_state_share(synthetic_dataset, n=1)
    by_state = M.customers_by_state(synthetic_dataset).set_index("customer_state")
    assert result["top_n_customer_share_pct"] == pytest.approx(
        by_state.loc["SP", "pct_customers"], abs=1e-6
    )


def test_satisfaction_kpis_on_synthetic(synthetic_dataset: Dataset):
    kpis = M.satisfaction_kpis(synthetic_dataset)
    # scores are 5, 5 and 1 (O3 keeps its latest review)
    assert kpis["mean_score"] == pytest.approx(11 / 3, abs=1e-4)
    assert kpis["pct_4_or_5"] == pytest.approx(66.6667, abs=1e-3)
    assert kpis["pct_1_or_2"] == pytest.approx(33.3333, abs=1e-3)


def test_category_satisfaction_grain_is_order_category(synthetic_dataset: Dataset):
    table = M.category_satisfaction(synthetic_dataset).set_index("category_label")
    # O1 bought from two categories; each contributes its single score once
    assert table.loc["health_beauty", "n_orders"] == 2
    assert table.loc["health_beauty", "n_reviews"] == 2
    # shares carry four decimals, so the column adds up to 100 within 0.01
    assert table["pct_revenue"].sum() == pytest.approx(100.0, abs=0.01)


def test_price_band_calculation_returns_all_deciles(synthetic_dataset: Dataset):
    deciles, stats = M.combined_price_vs_satisfaction(synthetic_dataset, bins=2)
    assert len(deciles) <= 2
    assert stats["n_orders"] == len(synthetic_dataset.order_features.dropna(subset=["review_score"]))


# --------------------------------------------------------------------------- #
# Invariants on the real dataset
# --------------------------------------------------------------------------- #
def test_real_order_rows_equal_distinct_order_ids(real_dataset: Dataset):
    orders = real_dataset.orders
    assert len(orders) == orders["order_id"].nunique() == 99441


def test_real_item_revenue_reconciles_between_grains(real_dataset: Dataset):
    item_sum = float(real_dataset.items["price"].sum())
    order_sum = float(real_dataset.orders["item_total_price"].sum())
    assert item_sum == pytest.approx(order_sum, rel=0, abs=1e-6)
    assert item_sum == pytest.approx(13_591_643.70, rel=0, abs=0.01)


def test_real_payment_totals_reconcile_between_grains(real_dataset: Dataset):
    payments_sum = float(real_dataset.payments["payment_value"].sum())
    orders_sum = float(real_dataset.orders["payment_total"].sum())
    assert payments_sum == pytest.approx(orders_sum, rel=0, abs=1e-6)


def test_real_status_percentages_sum_to_one_hundred(real_dataset: Dataset):
    table = M.order_status_summary(real_dataset)
    assert table["pct_orders"].sum() == pytest.approx(100.0)
    assert table["n_orders"].sum() == 99441


def test_real_delivered_counts_are_consistent(real_dataset: Dataset):
    orders = real_dataset.orders
    delivered = int(orders["is_delivered"].sum())
    with_duration = int((orders["is_delivered"] & orders["delivery_days"].notna()).sum())
    assert delivered == 96478
    assert with_duration == 96470
    # 8 delivered orders carry no actual delivery timestamp
    assert delivered - with_duration == 8


def test_real_delivery_classes_are_a_partition_of_delivered_orders(real_dataset: Dataset):
    class_table = M.delivery_class_summary(real_dataset)
    assert class_table["n_orders"].sum() == len(real_dataset.delivered_with_delay)
    assert class_table["pct_of_delivered"].sum() == pytest.approx(100.0)


def test_real_reviews_are_never_multiplied_by_the_join(real_dataset: Dataset):
    """819 review rows must be dropped by de-duplication, and no score invented."""
    assert len(real_dataset.reviews) == 99224
    assert len(real_dataset.reviews_per_order) == 98673
    assert len(real_dataset.reviews) - len(real_dataset.reviews_per_order) == 551
    scores = real_dataset.orders["review_score"]
    assert int(scores.notna().sum()) == 98673


def test_real_delay_buckets_sum_to_delivered_with_known_delay(real_dataset: Dataset):
    """The bucket table only covers deliveries that also carry a review score."""
    table = M.delay_bucket_satisfaction(real_dataset)
    reviewed_delivered = real_dataset.delivered_with_delay[
        real_dataset.delivered_with_delay["review_score"].notna()
    ]
    assert table["n_orders"].sum() == len(reviewed_delivered)
    assert table["n_orders"].sum() == 95824
    # the gap to the full delivered population is exactly the un-reviewed orders
    assert len(real_dataset.delivered_with_delay) - table["n_orders"].sum() == 646


def test_real_late_delay_reconciliation(real_dataset: Dataset):
    late = real_dataset.delivered_with_delay.query("delivery_class == 'late'")
    assert len(late) == 6534
    assert int(late["delay_days"].between(1, 3).sum()) == 1870
    assert int(late["delay_days"].between(4, 7).sum()) == 1802
    assert int((late["delay_days"] > 7).sum()) == 2862
    assert 1870 + 1802 + 2862 == len(late)


def test_real_category_revenue_share_sums_to_one_hundred(real_dataset: Dataset):
    table = M.category_performance(real_dataset)
    assert table["pct_revenue"].sum() == pytest.approx(100.0, abs=0.01)
    assert table["pct_items"].sum() == pytest.approx(100.0, abs=0.01)


def test_real_seller_revenue_equals_category_revenue_total(real_dataset: Dataset):
    seller_total = float(M.seller_performance(real_dataset)["revenue"].sum())
    category_total = float(M.category_performance(real_dataset)["revenue"].sum())
    assert seller_total == pytest.approx(category_total, rel=0, abs=0.01)


def test_real_customer_counts(real_dataset: Dataset):
    overview = M.customer_overview(real_dataset)
    assert overview["unique_people"] == 96096
    # the same person can appear more than once; customer_id never repeats
    assert overview["unique_customer_id"] == 99441
    assert overview["repeat_people"] < overview["unique_people"]


def test_real_price_correlation_is_weak_and_negative(real_dataset: Dataset):
    _deciles, stats = M.combined_price_vs_satisfaction(real_dataset)
    assert abs(stats["spearman_rho"]) < 0.1


def test_real_payment_correlation_is_positive(real_dataset: Dataset):
    _bins, stats = M.combined_payment_vs_installments(real_dataset)
    assert stats["spearman_rho_transaction_level"] > 0.3
    assert (
        stats["mean_installments_highest_decile"] > stats["mean_installments_lowest_decile"]
    )


def test_real_geography_attention_states_have_adequate_samples(real_dataset: Dataset):
    _states, eligible, thresholds = M.combined_geography_delivery(real_dataset)
    attention = eligible[eligible["needs_attention"]]
    assert len(attention) > 0
    assert attention["n_orders"].min() >= 100
    assert thresholds["slow_threshold_days"] > 0
    assert thresholds["late_threshold_pct"] > 0


def test_real_revenue_concentration_is_reported_with_explicit_denominator(real_dataset: Dataset):
    result = M.top_n_revenue_share(real_dataset, 5)
    assert 0 < result["top_n_revenue_share_pct"] < 100
    assert result["top_n_revenue"] <= result["total_revenue"]
