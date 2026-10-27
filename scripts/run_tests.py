"""Run the test suite with a readable summary.

    python scripts/run_tests.py            # everything
    python scripts/run_tests.py -m "not real"   # synthetic logic only
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str]) -> int:
    command = [sys.executable, "-m", "pytest", "-q", "--no-header"] + argv
    print("running:", " ".join(command))
    completed = subprocess.run(command, cwd=PROJECT_ROOT)
    print(f"\nexit code: {completed.returncode}")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
