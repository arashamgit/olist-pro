"""Reproduce the whole project from a fresh checkout.

    python scripts/run_all.py            # full pipeline + notebooks + report
    python scripts/run_all.py --quick    # pipeline + report only

Steps
-----
1. verify that every raw CSV is present and report its size / hash
2. build the cleaned tables and the analysis grains
3. run every metric and write ``reports/tables/``
4. render every figure into ``reports/figures/``
5. write ``reports/metrics.json``
6. execute every notebook in order (skipped with ``--quick``)
7. build the executive report (Markdown + PDF)
8. run the test suite
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def step(number: int, title: str) -> None:
    print(f"\n{'=' * 78}\n[{number}] {title}\n{'=' * 78}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full olist-pro pipeline")
    parser.add_argument("--quick", action="store_true", help="skip the notebooks")
    parser.add_argument("--skip-tests", action="store_true", help="skip the test suite")
    args = parser.parse_args()

    started = time.time()

    step(1, "Validating the raw data")
    from olist_analysis.data_loader import file_inventory, load_raw_tables

    inventory = file_inventory()
    print(inventory.to_string(index=False))
    missing = inventory[~inventory["exists"]]
    if len(missing):
        print("\nERROR: missing raw files:", ", ".join(missing["filename"]))
        print("See data/README.md for download instructions.")
        return 2

    step(2, "Building the analysis dataset")
    from olist_analysis.features import load_dataset, save_dataset

    raw = load_raw_tables()
    print(f"loaded {len(raw)} raw tables")
    dataset = load_dataset(force_rebuild=True)
    save_dataset(dataset)
    print(
        f"orders={len(dataset.orders):,}  items={len(dataset.items):,}  "
        f"delivered={len(dataset.delivered):,}"
    )

    step(3, "Running the analysis pipeline")
    from olist_analysis.pipeline import run_pipeline

    results = run_pipeline(dataset)
    print(f"{len(results.tables)} tables and {len(results.figures)} figures written")

    if not args.quick:
        step(4, "Executing the notebooks")
        from scripts.execute_notebooks import execute_all

        executed, failed = execute_all()
        print(f"executed: {executed}, failed: {failed}")
        if failed:
            return 3

    step(5, "Building the executive report")
    from olist_analysis.reporting import build_report

    report = build_report()
    print(f"markdown: {report['markdown']}")
    print(f"pdf     : {report['pdf']}")

    if not args.skip_tests:
        step(6, "Running the test suite")
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"], cwd=PROJECT_ROOT
        )
        if completed.returncode != 0:
            print("TESTS FAILED")
            return 4
        print("all tests passed")

    print(f"\nDone in {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
