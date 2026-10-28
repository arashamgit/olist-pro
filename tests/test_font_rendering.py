"""Guards for the Persian output.

The figures and the PDF were once regenerated in an environment without
``arabic-reshaper``/``python-bidi``; the shaping code degrades silently in that
case, so every chart lost its Persian layout while the pipeline stayed green.
These tests turn that silent degradation into a failure.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from olist_analysis import font_utils  # noqa: E402
from olist_analysis.config import PERSIAN_FONT_PATH  # noqa: E402

PRESENTATION_FORMS = re.compile(r"[\uFE70-\uFEFF]")
SAMPLE = "توزیع وضعیت سفارش‌ها"


def _pins(path: Path) -> set[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


def test_bundled_persian_font_exists() -> None:
    assert PERSIAN_FONT_PATH.exists(), f"missing font: {PERSIAN_FONT_PATH}"


def test_persian_font_is_registered_with_matplotlib() -> None:
    assert font_utils.persian_available(), "Vazirmatn was not registered with Matplotlib"


def test_fa_shapes_text_for_reportlab() -> None:
    """ReportLab has no shaping engine, so fa() must emit presentation forms."""
    shaped = font_utils.fa(SAMPLE)
    assert shaped != SAMPLE, "arabic-reshaper or python-bidi is missing"
    assert PRESENTATION_FORMS.search(shaped), "fa() did not produce joined glyphs"


def test_t_never_pre_reorders_text_for_a_shaping_matplotlib() -> None:
    """Handing pre-reversed text to Matplotlib 3.11 mirrors the words."""
    if font_utils.matplotlib_handles_rtl():
        assert font_utils.t(SAMPLE) == SAMPLE
    else:
        assert font_utils.t(SAMPLE) == font_utils.fa(SAMPLE)


def test_binder_requirements_match_the_root_specification() -> None:
    """repo2docker only looks inside binder/ once that directory exists."""
    root = _pins(PROJECT_ROOT / "requirements.txt")
    binder = _pins(PROJECT_ROOT / "binder" / "requirements.txt")
    assert binder == root, "binder/requirements.txt drifted from requirements.txt"
