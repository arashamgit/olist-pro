"""Build the executive report (Persian Markdown + Persian PDF).

    python scripts/build_report.py

Requires a previous run of ``scripts/run_all.py`` (or any code that produced
``reports/metrics.json`` and ``reports/tables/``).
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from olist_analysis.reporting import build_report  # noqa: E402


def main() -> int:
    result = build_report()
    print(f"Markdown : {result['markdown']}")
    if result["pdf"] is None:
        print("PDF      : SKIPPED - the bundled Persian font is missing.")
        return 1
    size_kb = result["pdf"].stat().st_size / 1024
    print(f"PDF      : {result['pdf']} ({size_kb:.1f} KB)")
    print(f"Persian font registered: {result['persian_font']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
