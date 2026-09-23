"""R12 `test_issue_13_grayscale_accessibility`.

Computes WCAG 2.1 contrast ratios for every color this feature actually
emits (status indicator symbols, header text-on-fill pairs, and the
column-emphasis/alternating-row shades), against the exact background each
color renders on in the token mappers (`tools/table_latex_tokens.py`,
`tools/table_docx_tokens.py`, `tools/table_html_tokens.py`). This is a pure
computation, not a rendered/visual check -- it proves the chosen colors are
accessible by contract, independent of any backend's actual pixel output.

Thresholds (WCAG 2.1, https://www.w3.org/TR/WCAG21/):
- 1.4.3 Contrast (Minimum): normal text needs >= 4.5:1.
- 1.4.11 Non-text Contrast: graphical objects (the status symbols, which
  never carry text) need >= 3:1.

Never color alone (approved 2026-09-22): every status marker also renders
a distinct symbol shape and a same-default-color text label (see
`tools/table_directives.py::STATUS_MARKER_RE` and each token mapper's
`_indicator_*` helper) -- verified separately, by string presence, in
`tools/test_table_backend_contracts.py`. This file only checks contrast.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from table_styles import load_catalog  # noqa: E402

CATALOG = load_catalog()

WHITE = "#FFFFFF"
BLACK = "#000000"

# Backgrounds the token mappers actually paint, and the WCAG threshold that
# applies to whatever renders on top of them.
HEADER_GRAY_SHADED = "#EAEAEA"      # table_docx_tokens._HEADER_FILL["gray_shaded"], table_html_tokens/_HEADER_STYLE
HEADER_DARK_SHADED = "#404040"      # ditto, "dark_shaded" -- white bold header text on top
ROW_ALTERNATING = "#F2F2F2"         # table_docx_tokens._shade_cell/table_html_tokens alternating rows
COLUMN_EMPHASIS = "#D9D9D9"         # table_docx_tokens/table_html_tokens column_emphasis cell shading


def _channel(value: int) -> float:
    ratio = value / 255
    return ratio / 12.92 if ratio <= 0.03928 else ((ratio + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(foreground: str, background: str) -> float:
    l1, l2 = relative_luminance(foreground), relative_luminance(background)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def test_issue_13_status_indicator_symbols_meet_non_text_contrast() -> None:
    """WCAG 1.4.11: every status symbol against its typical light cell
    background (white, and the alternating-row tint) reaches 3:1 --
    graphical-object contrast, since the symbol carries no text itself."""
    for value, indicator in CATALOG.status_indicators.items():
        for background in (WHITE, ROW_ALTERNATING):
            ratio = contrast_ratio(indicator.color, background)
            assert ratio >= 3.0, f"{value} ({indicator.color}) on {background}: {ratio:.2f}:1 < 3:1"


def test_issue_13_header_text_meets_normal_text_contrast() -> None:
    """WCAG 1.4.3: header text reaches 4.5:1 against its own fill --
    black-on-gray_shaded (the default/current header) and white-on-dark_shaded."""
    assert contrast_ratio(BLACK, HEADER_GRAY_SHADED) >= 4.5
    assert contrast_ratio(WHITE, HEADER_DARK_SHADED) >= 4.5


def test_issue_13_column_emphasis_text_meets_normal_text_contrast() -> None:
    """TAB-CE-05's protagonist column: black bold text on its shaded
    background -- normal-size text (the density tokens top out at 11pt),
    so this needs the stricter 4.5:1, not the large-text 3:1 exemption."""
    assert contrast_ratio(BLACK, COLUMN_EMPHASIS) >= 4.5


def test_issue_13_status_indicator_symbols_are_distinguishable_in_grayscale() -> None:
    """Grayscale printing collapses hue but keeps luminance: distinct
    luminance values across the five approved symbols mean two different
    statuses never look identical once color is removed -- the symbol
    SHAPE (already asserted never-color-alone elsewhere) is the primary
    grayscale signal, luminance spread is the secondary one."""
    luminances = {value: relative_luminance(ind.color) for value, ind in CATALOG.status_indicators.items()}
    assert len(set(round(l, 3) for l in luminances.values())) == len(luminances)
