"""Persian (RTL) text helpers for Matplotlib and ReportLab.

Matplotlib performs no Arabic/Persian glyph shaping and does not apply the
bidi algorithm, so raw Persian strings are rendered as isolated, left-to-right
letters.  :func:`fa` fixes this by running the text through ``arabic-reshaper``
(which substitutes the contextual presentation forms) and then through
``python-bidi`` (which reorders the runs for a left-to-right renderer).

If the font or either helper library is unavailable the functions degrade to
returning the input unchanged, so the analysis pipeline never crashes because
of a missing cosmetic dependency.
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

    Mixed Persian/Latin strings (for example ``"دستهبندی health_beauty"``) are
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


def t(text: str) -> str:
    """Translate a chart string: reshape it when a Persian font is available.

    Charts are authored with Persian titles/labels.  When the bundled font is
    missing the raw string is returned so the figure is still produced (the
    letters simply will not be joined).
    """
    return fa(text) if persian_available() else text
