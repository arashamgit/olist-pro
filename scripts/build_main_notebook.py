"""Build the single self-contained analysis notebook.

The notebook is assembled from ``scripts/nb_cells_part*.py`` so that each part
stays readable, then executed with nbclient so the delivered file already
contains every table and figure as an output.

Usage
-----
    python scripts/build_main_notebook.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
TARGET = PROJECT_ROOT / "notebooks" / "olist_full_analysis.ipynb"
KERNEL_NAME = "olist-pro"
PARTS = ("part1", "part2", "part3")


def load_cells(part: str):
    """Import one cell module and return its ``CELLS`` list."""
    path = SCRIPTS_DIR / f"nb_cells_{part}.py"
    spec = importlib.util.spec_from_file_location(f"nb_cells_{part}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.CELLS


def ensure_kernel() -> None:
    """Register the project kernel once so nbclient can find it."""
    from ipykernel.kernelspec import install

    install(user=True, kernel_name=KERNEL_NAME, display_name="Python 3 (olist)")


def build() -> nbformat.NotebookNode:
    cells = []
    for part in PARTS:
        for kind, source in load_cells(part):
            text = source.strip("\n")
            cells.append(new_markdown_cell(text) if kind == "md" else new_code_cell(text))
    notebook = new_notebook(cells=cells)
    notebook.metadata.update({
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    })
    return notebook


def main() -> int:
    ensure_kernel()
    notebook = build()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, TARGET)
    print(f"نوشته شد: {TARGET.relative_to(PROJECT_ROOT)} ({len(notebook.cells)} سلول)")

    client = NotebookClient(
        notebook,
        timeout=900,
        kernel_name=KERNEL_NAME,
        resources={"metadata": {"path": str(PROJECT_ROOT)}},
        allow_errors=False,
    )
    client.execute()

    nbformat.validate(notebook)
    nbformat.write(notebook, TARGET)

    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    errors = [output for cell in code_cells for output in cell.get("outputs", []) if output.get("output_type") == "error"]
    images = sum(
        1
        for cell in code_cells
        for output in cell.get("outputs", [])
        for item in output.get("data", {})
        if item == "image/png"
    )
    print(f"سلول کد: {len(code_cells)} | نمودار: {images} | خطا: {len(errors)}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
