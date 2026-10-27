"""Data validation and quality gate.

    python scripts/validate_data.py

Prints a console report about the raw dataset and fails with a non-zero exit
code when a *blocking* problem is found, so it can be used as a gate in CI or
before a release.  The persisted evidence tables (``reports/tables/00_*``,
``01_*``) are written by ``scripts/run_all.py``; this script reads the same
files and checks them instead of duplicating the write logic.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from olist_analysis import data_quality as dq  # noqa: E402
from olist_analysis.config import MIN_ORDERS_PER_MONTH, RAW_TABLES  # noqa: E402
from olist_analysis.data_loader import file_inventory, load_raw_tables  # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    CHECKS.append((label, bool(condition)))
    mark = "PASS" if condition else "FAIL"
    print(f"[{mark}] {label}" + (f" -> {detail}" if detail else ""))


def main() -> int:
    print("=" * 78)
    print("1. FILE INVENTORY")
    print("=" * 78)
    inventory = file_inventory()
    print(inventory.to_string(index=False))
    print(f"total size: {inventory['size_mb'].sum():.2f} MB")
    check("all 9 raw files are present", inventory["exists"].all())
    check("total raw size is plausible (>100 MB)", inventory["size_mb"].sum() > 100)

    raw = load_raw_tables()

    print("\n" + "=" * 78)
    print("2. SHAPES AND REQUIRED TABLES")
    print("=" * 78)
    for name in RAW_TABLES:
        frame = raw[name]
        print(f"{name:<22} rows={len(frame):>9,} columns={frame.shape[1]}")
    check("orders has 99,441 rows", len(raw["orders"]) == 99441, str(len(raw["orders"])))
    check("geolocation has 1,000,163 rows", len(raw["geolocation"]) == 1000163)
    check("orders and customers have the same row count", len(raw["orders"]) == len(raw["customers"]))

    print("\n" + "=" * 78)
    print("3. PRIMARY KEY UNIQUENESS")
    print("=" * 78)
    keys = dq.key_uniqueness_table(raw, RAW_TABLES)
    print(keys.to_string(index=False))
    for _, row in keys.iterrows():
        if row["key"] == "(none declared)":
            continue
        if row["table"] == "order_reviews":
            check(
                "review_id uniqueness violation is a KNOWN, documented defect",
                row["status"] == "NOT_UNIQUE",
                f"{row['n_duplicated_keys']} duplicated ids",
            )
        else:
            check(f"{row['table']}.{row['key']} is unique", row["status"] == "UNIQUE")

    print("\n" + "=" * 78)
    print("4. MISSING VALUES")
    print("=" * 78)
    missing = pd.concat(
        [dq.missing_values_table(raw[name], name) for name in raw], ignore_index=True
    )
    print(missing.to_string(index=False) if len(missing) else "no missing values")
    check(
        "no amount column is missing",
        not set(["price", "freight_value", "payment_value"])
        & set(missing["column"]),
    )

    print("\n" + "=" * 78)
    print("5. REFERENTIAL INTEGRITY")
    print("=" * 78)
    orders_ids = set(raw["orders"]["order_id"])
    customer_ids = set(raw["customers"]["customer_id"])
    product_ids = set(raw["products"]["product_id"])
    seller_ids = set(raw["sellers"]["seller_id"])
    relationships = pd.DataFrame(
        [
            dq.referential_integrity(
                raw["orders"], "customer_id", customer_ids, "orders", "customers"
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
    )
    print(relationships.to_string(index=False))
    check(
        "no orphan foreign keys anywhere",
        (relationships["n_orphan_distinct"] == 0).all(),
    )

    print("\n" + "=" * 78)
    print("6. VALUE RANGES")
    print("=" * 78)
    ranges = pd.concat(
        [
            dq.numeric_range_check(raw["order_items"], ["price", "freight_value"], "order_items"),
            dq.numeric_range_check(raw["order_payments"], ["payment_value", "payment_installments"], "order_payments"),
        ],
        ignore_index=True,
    )
    print(ranges.to_string(index=False))
    check("no negative price", ranges.query("column == 'price'")["n_negative"].sum() == 0)
    check("no negative payment value", ranges.query("column == 'payment_value'")["n_negative"].sum() == 0)
    check(
        "review scores stay inside 1..5",
        int(raw["order_reviews"]["review_score"].min()) >= 1
        and int(raw["order_reviews"]["review_score"].max()) <= 5,
    )

    print("\n" + "=" * 78)
    print("7. TIMESTAMPS AND ANALYSIS WINDOW")
    print("=" * 78)
    parsed = dq.datetime_parse_report(
        raw["orders"], list(RAW_TABLES["orders"].datetime_columns), "orders"
    )
    print(parsed.to_string(index=False))
    check("every timestamp parses", int(parsed["n_unparseable"].sum()) == 0)

    from olist_analysis.config import CORE_WINDOW_END, CORE_WINDOW_START

    purchase = pd.to_datetime(raw["orders"]["order_purchase_timestamp"], format="mixed")
    monthly = purchase.dt.to_period("M").value_counts().sort_index()
    print("\nmonthly order counts:")
    print(monthly.to_string())

    core = monthly[
        (monthly.index >= CORE_WINDOW_START[:7]) & (monthly.index <= CORE_WINDOW_END[:7])
    ]
    check(
        f"the declared core window ({CORE_WINDOW_START} .. {CORE_WINDOW_END}) holds 20 months",
        len(core) == 20,
        f"{len(core)} months",
    )
    check(
        "every core-window month passes the volume threshold",
        bool((core >= MIN_ORDERS_PER_MONTH).all()),
    )
    before = monthly[monthly.index < CORE_WINDOW_START[:7]]
    after = monthly[monthly.index > CORE_WINDOW_END[:7]]
    print(
        f"\nmonths before the window: {dict(before)} "
        f"(total {int(before.sum()):,} orders, not contiguous)"
    )
    print(f"months after the window : {dict(after)} (total {int(after.sum()):,} orders, truncated)")
    check(
        "excluded boundary months are sparse relative to the window",
        int(before.sum()) + int(after.sum())
        < 0.01 * int(monthly.sum()),
        f"{int(before.sum()) + int(after.sum())} orders excluded",
    )

    failed = [label for label, ok in CHECKS if not ok]
    print("\n" + "=" * 78)
    print(f"RESULT: {len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    if failed:
        print("FAILED CHECKS:")
        for label in failed:
            print(" -", label)
    print("=" * 78)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
