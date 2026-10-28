"""Persian (RTL) text helpers for Matplotlib and ReportLab.

The two renderers need **opposite** treatment, which is why there are two
functions here and not one:

* **ReportLab** has no Arabic shaping engine: it draws every character in
  isolation, left to right.  :func:`fa` therefore runs the text through
  ``arabic-reshaper`` (which substitutes the contextual presentation forms) and
  then through ``python-bidi`` (which reorders the runs for a left-to-right
  renderer).  The PDF needs this.
* **Matplotlib** 3.11+ with Raqm performs the joining *and* the bidi reordering
  itself.  Giving it text that was already reordered flips the word order a
  second time, so the chart labels come out mirrored.  :func:`t` therefore
  returns the raw string whenever the installed Matplotlib can lay out Persian
  on its own, and only falls back to :func:`fa` on older builds.

If the font or either helper library is unavailable the functions degrade to
returning the input unchanged, so the pipeline never crashes because of a
missing cosmetic dependency.  ``tests/test_font_rendering.py`` turns that
silent degradation into a test failure.
"""

from __future__ import annotations

import functools

from .config import PERSIAN_FONT_PATH


@functools.lru_cache(maxsize=1)
def persian_font_family() -> str | None:
    """Register the bundled Persian font with Matplotlib.

    Returns the font family name, or ``None`` when the TTFs are missing.
    """
    if not PERSIAN_FONT_PATH.exists():
        return None
    try:
        from matplotlib import font_manager

        font_manager.fontManager.addfont(str(PERSIAN_FONT_PATH))
        return font_manager.FontProperties(fname=str(PERSIAN_FONT_PATH)).get_name()
    except Exception:  # pragma: no cover - cosmetic fallback
        return None


@functools.lru_cache(maxsize=512)
def fa(text: str) -> str:
    """Reshape and reorder Persian text for a left-to-right renderer.

    Used by the PDF builder (ReportLab).  Mixed Persian/Latin strings are
    handled by ``python-bidi``'s ``get_display``.
    """
    if not text:
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:  # pragma: no cover - cosmetic fallback
        return str(text)


def persian_available() -> bool:
    """True when a Persian-capable font is registered with Matplotlib."""
    return persian_font_family() is not None


@functools.lru_cache(maxsize=1)
def matplotlib_handles_rtl() -> bool:
    """True when Matplotlib lays Persian text out by itself (HarfBuzz + Raqm).

    Matplotlib 3.11 with Raqm joins the letters and applies the Unicode bidi
    algorithm internally.  Detecting that is not cosmetic: pre-reversed text
    handed to such a build renders in the wrong order.
    """
    try:
        import matplotlib
        from matplotlib import ft2font

        if not getattr(ft2font, "__libraqm_version__", ""):
            return False
        major, minor = (int(part) for part in matplotlib.__version__.split(".")[:2])
        return (major, minor) >= (3, 11)
    except Exception:  # pragma: no cover - cosmetic fallback
        return False


def t(text: str) -> str:
    """Prepare a chart string for the installed Matplotlib.

    With a shaping-capable Matplotlib the raw string is returned untouched and
    the renderer does the work.  Older builds get :func:`fa`, which produces the
    visual order they need.
    """
    if not text:
        return text
    return text if matplotlib_handles_rtl() else fa(text)
