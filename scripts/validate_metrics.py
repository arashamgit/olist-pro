"""Exercise every metric function on the real data and print the evidence.

This script is the human-readable companion to ``tests/``: the tests assert
invariants, this script dumps the actual values so a reviewer can see the
numbers that end up in the notebooks and in the executive report.

    python scripts/validate_metrics.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from olist_analysis import metrics as M  # noqa: E402
from olist_analysis.features import load_dataset  # noqa: E402

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 80)


def show(title: str, obj) -> None:
    print(f"\n--- {title} ---")
    print(obj.to_string(index=False) if hasattr(obj, "to_string") else obj)


def main() -> int:
    ds = load_dataset()

    show("5.1 order_status_summary", M.order_status_summary(ds))
    show("5.2 monthly_orders", M.monthly_orders(ds))
    show("5.2 year_month_matrix", M.year_month_matrix(ds))
    show("5.3 weekday_orders", M.weekday_orders(ds))
    show("5.4 top_months", M.top_months(ds))
    show("5 growth_evidence", M.growth_evidence(ds))

    show("6.1 customer_overview", M.customer_overview(ds))
    show("6.2 customers_by_state(top10)", M.customers_by_state(ds, top=10))
    show("6.2 top_n_state_share(5)", M.top_n_state_share(ds, 5))
    show("6.3 customers_by_city(top10)", M.customers_by_city(ds, 10))
    show("6.4 state_customers_vs_orders", M.state_customers_vs_orders(ds).head(12))

    show(
        "7.2 top_categories by revenue",
        M.top_categories(ds, "revenue", 10)[
            ["category_label", "n_items", "revenue", "pct_revenue", "mean_item_price",
             "rank_items", "rank_revenue"]
        ],
    )
    show(
        "7.1 top_categories by items",
        M.top_categories(ds, "items", 10)[
            ["category_label", "n_items", "revenue", "rank_items", "rank_revenue",
             "rank_gap_revenue_minus_items"]
        ],
    )
    show(
        "7.4 top_categories by mean price",
        M.top_categories(ds, "mean_price", 5)[["category_label", "n_items", "mean_item_price"]],
    )
    show("7.5 top_n_revenue_share(5)", M.top_n_revenue_share(ds, 5))
    show("7.3 category_rank_comparison", M.category_rank_comparison(ds, 20, 10))

    show("8 payment_reconciliation", M.payment_reconciliation(ds))
    show("8.1-8.3 payment_type_summary", M.payment_type_summary(ds))
    show("8.4 installment_distribution", M.installment_distribution(ds))
    show("8.5 zero_or_single by type", M.zero_or_single_installments(ds)["by_type"])
    show(
        "8.5 zero_or_single summary",
        {k: v for k, v in M.zero_or_single_installments(ds).items() if k != "by_type"},
    )
    show("8.6 installments_by_type_summary", M.installments_by_type_summary(ds))

    show("9.1 delivery_duration_summary", M.delivery_duration_summary(ds))
    show("9.3 delivery_distribution_stats", M.delivery_distribution_stats(ds))
    show("9.4 delivery_class_summary", M.delivery_class_summary(ds))
    show("9.5 delay_summary", M.delay_summary(ds))
    show("9.7 delivery_by_state", M.delivery_by_state(ds))
    show("9.9 monthly_delivery_trend", M.monthly_delivery_trend(ds))

    show("10.1 review_score_distribution", M.review_score_distribution(ds))
    show("10.2 satisfaction_kpis", M.satisfaction_kpis(ds))
    show("10.4 best categories", M.category_satisfaction_ranked(ds, "best", 10))
    show("10.4 worst categories", M.category_satisfaction_ranked(ds, "worst", 10))
    show("10.5 low volume categories", M.low_volume_categories(ds))
    show("10.7 monthly_satisfaction_trend", M.monthly_satisfaction_trend(ds))

    show("11.1 delay_satisfaction_comparison", M.delay_satisfaction_comparison(ds))
    show("11.3 delay_satisfaction_difference", M.delay_satisfaction_difference(ds))
    show("11.5 delay_bucket_satisfaction", M.delay_bucket_satisfaction(ds))
    show("11.6 category_delay_satisfaction", M.category_delay_satisfaction(ds))

    show("12.1 sellers_by_state", M.sellers_by_state(ds))
    show("12 seller_overview", M.seller_overview(ds))
    show(
        "12.2 top_sellers by revenue",
        M.top_sellers(ds, "revenue", 10)[
            ["seller_id", "seller_state", "n_items", "n_orders", "revenue",
             "revenue_share_pct", "n_reviews", "mean_score", "score_vs_overall",
             "rank_revenue", "rank_items"]
        ],
    )
    show(
        "12.4 sellers rank comparison",
        M.seller_performance(ds).assign(
            gap=M.seller_performance(ds)["rank_gap_revenue_minus_items"].abs()
        ).query("gap >= 50").sort_values("gap", ascending=False).head(10)[
            ["seller_id", "n_items", "revenue", "rank_items", "rank_revenue"]
        ],
    )
    candidates, threshold = M.high_revenue_low_rating_sellers(ds)
    show(f"12.6 high revenue low rating (revenue >= {threshold:,.2f})", candidates)

    table, flagged = M.combined_revenue_vs_satisfaction(ds)
    show("13.1 flagged high revenue / low score categories", flagged)
    states, eligible, thresholds = M.combined_geography_delivery(ds)
    show("13.2 geography thresholds", thresholds)
    show("13.2 states needing attention", eligible)
    deciles, stats = M.combined_price_vs_satisfaction(ds)
    show("13.3 price vs satisfaction stats", stats)
    show("13.3 price deciles", deciles)
    payment_bins, payment_stats = M.combined_payment_vs_installments(ds)
    show("13.4 payment vs installments stats", payment_stats)
    show("13.4 payment value deciles", payment_bins)
    pivot, trend = M.combined_category_revenue_over_time(ds)
    show("13.5 category revenue trend", trend)

    print("\nAll metric functions executed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
