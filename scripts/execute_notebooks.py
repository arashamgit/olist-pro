"""Execute every notebook in order and fail loudly on the first error.

    python scripts/execute_notebooks.py

Each notebook is executed in place with the ``olist-pro`` kernel so the saved
``.ipynb`` files contain real outputs and figures, which is what the course
brief asks for ("run the notebook from the beginning, no execution errors").
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
KERNEL_NAME = "olist-pro"


def ensure_kernel() -> None:
    """Register the project kernel so nbclient can find it."""
    from ipykernel.kernelspec import install

    # ipykernel >= 7 spells this argument ``kernel_name``
    install(user=True, kernel_name=KERNEL_NAME, display_name="olist-pro")


def execute_notebook(path: Path, timeout: int = 900) -> None:
    notebook = nbformat.read(path, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=timeout,
        kernel_name=KERNEL_NAME,
        resources={"metadata": {"path": str(path.parent)}},
        allow_errors=False,
    )
    client.execute()
    nbformat.write(notebook, path)


def execute_all(timeout: int = 900) -> tuple[int, int]:
    ensure_kernel()
    notebooks = sorted(NOTEBOOKS_DIR.glob("[0-9][0-9]_*.ipynb"))
    if not notebooks:
        print("no notebooks found; run scripts/build_notebooks.py first")
        return 0, 1

    executed = 0
    for path in notebooks:
        try:
            execute_notebook(path, timeout=timeout)
        except CellExecutionError as error:
            print(f"FAILED: {path.name}\n{error}")
            return executed, 1
        executed += 1
        print(f"OK: {path.name}")
    return executed, 0


def main() -> int:
    executed, failed = execute_all()
    print(f"\nexecuted={executed} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
