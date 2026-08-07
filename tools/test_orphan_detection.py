"""Tests for the orphan-heading detector — blank-tail signature.

No fixture PNGs are committed to this repo (it is a sanitized public toolkit;
page 01 of the real fixture carries the author's name and institution, and
pages 02-27 carry a private university project). Instead, these tests build
synthetic ``PIL.Image`` pages calibrated to the geometry measured on the real
fixture (see the design doc for ``breakable-tables-and-orphan-detection``)
and assert directly against ``check_orphan_heading()`` — no PDF, no Docker,
no `pdftoppm`.

Every builder is parametrized over ``dpi in (150, 300)`` and expresses ink
thickness/gaps in *inches*, scaled by ``dpi``, so the same physical layout is
reproduced at both resolutions — this is what proves DPI independence.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import visual_pdf_auditor as auditor  # noqa: E402

DPIS = (150, 300)


# ---------------------------------------------------------------------------
# Synthetic page builders
# ---------------------------------------------------------------------------


def _page_size(dpi: int) -> tuple[int, int]:
    """A4 page size in pixels at the given DPI (8.27in x 11.69in)."""
    return round(8.27 * dpi), round(11.69 * dpi)


def _band(draw: ImageDraw.ImageDraw, w: int, y0: int, y1: int, width_frac: float, x0_frac: float) -> None:
    """Draw a solid black horizontal band from y0 to y1 (inclusive-ish)."""
    x0 = int(w * x0_frac)
    x1 = x0 + int(w * width_frac)
    draw.rectangle([x0, y0, x1, y1], fill=0)


def page_with_orphan_heading(dpi: int, heading_top_frac: float = 0.295, heading_height_in: float = 0.15) -> Image.Image:
    """Short heading strip ending around ``heading_top_frac + a bit``, blank tail to the bottom.

    Calibrated to the measured page 02 geometry: heading strip ~0.295h-0.31h,
    body content above it (0.13h-0.26h) so the content-above guard passes,
    and a thin footer mark inside the excluded bottom 10% band.
    """
    w, h = _page_size(dpi)
    img = Image.new("L", (w, h), color=255)
    draw = ImageDraw.Draw(img)

    # Body content block (section text) — 0.13h .. 0.26h, several lines.
    line_h = max(1, round(0.04 * dpi))
    y = int(h * 0.13)
    while y < int(h * 0.26):
        _band(draw, w, y, y + line_h, width_frac=0.80, x0_frac=0.08)
        y += line_h + max(1, round(0.03 * dpi))

    # Orphan heading strip — short, ~28% width.
    top = int(h * heading_top_frac)
    bottom = top + max(1, round(heading_height_in * dpi))
    _band(draw, w, top, bottom, width_frac=0.28, x0_frac=0.08)

    # Footer mark (page number) confined to the bottom 10% footer band.
    footer_y = int(h * 0.935)
    _band(draw, w, footer_y, footer_y + max(1, round(0.03 * dpi)), width_frac=0.06, x0_frac=0.46)

    return img


def page_with_full_table(dpi: int) -> Image.Image:
    """A table block spanning 0.13h .. 0.725h, with vertical rules at 7 x-positions.

    The vertical rules are load-bearing: without them the table would not
    form one contiguous ink strip during the grow-up merge, and the height
    guard would not reliably reject it as a single oversized block.
    Blank tail after the table is ~0.175 — below the 0.20 threshold too.
    """
    w, h = _page_size(dpi)
    img = Image.new("L", (w, h), color=255)
    draw = ImageDraw.Draw(img)

    top = int(h * 0.13)
    bottom = int(h * 0.725)

    # Horizontal row rules every ~0.35in (typical table row).
    row_pitch = max(1, round(0.35 * dpi))
    for y in range(top, bottom, row_pitch):
        draw.rectangle([int(w * 0.08), y, int(w * 0.90), y + max(1, round(0.02 * dpi))], fill=0)

    # 7 vertical column rules spanning the whole table height — this keeps
    # every row in [top, bottom) above ORPHAN_BLANK_ROW_MAX so the region
    # merges into one contiguous strip.
    rule_w = max(1, round(0.02 * dpi))
    for i in range(7):
        x = int(w * 0.08) + i * int(w * 0.82 / 6)
        draw.rectangle([x, top, x + rule_w, bottom], fill=0)

    return img


def page_ending_with_bibliography(dpi: int) -> Image.Image:
    """Multi-line bibliography-style block ending at 0.79h, blank tail 0.11.

    The tail (0.11) sits below ORPHAN_BLANK_TAIL_MIN_FRAC (0.20), so this is
    rejected on blank-tail grounds alone — matching the measured page 27.
    """
    w, h = _page_size(dpi)
    img = Image.new("L", (w, h), color=255)
    draw = ImageDraw.Draw(img)

    line_h = max(1, round(0.04 * dpi))
    gap = max(1, round(0.03 * dpi))
    y = int(h * 0.60)
    end = int(h * 0.79)
    while y < end:
        _band(draw, w, y, y + line_h, width_frac=0.82, x0_frac=0.08)
        y += line_h + gap

    return img


def page_ending_with_paragraph(dpi: int) -> Image.Image:
    """A tall multi-line paragraph block (0.40h .. ~0.52h), blank tail > 0.20.

    This guards the precision regression a naive "short strip + blank tail"
    rule would introduce: the paragraph lines are close enough together
    (< ORPHAN_LINE_MERGE_GAP_IN) that the grow-up step merges them into one
    contiguous strip whose total height is far above ORPHAN_MAX_HEIGHT_IN,
    so the height guard — not the blank-tail check — is what rejects it.
    """
    w, h = _page_size(dpi)
    img = Image.new("L", (w, h), color=255)
    draw = ImageDraw.Draw(img)

    line_h_in = 0.05
    gap_in = 0.05  # well under ORPHAN_LINE_MERGE_GAP_IN (0.14in) — lines merge
    n_lines = 14  # (2*14 - 1) * 0.05in = 1.35in — far above ORPHAN_MAX_HEIGHT_IN (0.45in)

    line_h = max(1, round(line_h_in * dpi))
    gap = max(1, round(gap_in * dpi))
    y = int(h * 0.40)
    for _ in range(n_lines):
        _band(draw, w, y, y + line_h, width_frac=0.82, x0_frac=0.08)
        y += line_h + gap

    return img


def page_with_dense_top_half(dpi: int) -> Image.Image:
    """Dense content confined to the top half (0.05h .. 0.45h), nothing below.

    Blank tail from the content's end (0.45h) to the scan bottom is large
    (~0.45), but the dense block itself merges into a strip far taller than
    ORPHAN_MAX_HEIGHT_IN, so it is rejected — not an orphan heading.
    """
    w, h = _page_size(dpi)
    img = Image.new("L", (w, h), color=255)
    draw = ImageDraw.Draw(img)

    line_h_in = 0.05
    gap_in = 0.05
    line_h = max(1, round(line_h_in * dpi))
    gap = max(1, round(gap_in * dpi))
    y = int(h * 0.05)
    end = int(h * 0.45)
    while y < end:
        _band(draw, w, y, y + line_h, width_frac=0.82, x0_frac=0.08)
        y += line_h + gap

    return img


def page_blank() -> Image.Image:
    """A fully blank page — no ink anywhere."""
    w, h = _page_size(150)
    return Image.new("L", (w, h), color=255)


# ---------------------------------------------------------------------------
# Positive scenarios — orphan detected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dpi", DPIS)
def test_orphan_at_31_percent_depth_59_percent_blank_tail(dpi: int) -> None:
    """Measured page 02: last ink at 0.31h, blank tail 0.59 -> (True, 1.0)."""
    img = page_with_orphan_heading(dpi, heading_top_frac=0.295, heading_height_in=0.15)
    is_orphan, confidence = auditor.check_orphan_heading(img, dpi=dpi)
    assert is_orphan is True
    assert confidence == 1.0


@pytest.mark.parametrize("dpi", DPIS)
def test_orphan_at_57_5_percent_depth_32_5_percent_blank_tail(dpi: int) -> None:
    """Measured page 04: last ink at 0.575h, blank tail 0.325 -> (True, >0.2)."""
    img = page_with_orphan_heading(dpi, heading_top_frac=0.575, heading_height_in=0.15)
    is_orphan, confidence = auditor.check_orphan_heading(img, dpi=dpi)
    assert is_orphan is True
    assert confidence is not None
    assert confidence > 0.2


@pytest.mark.parametrize("dpi", DPIS)
def test_footer_content_does_not_suppress_detection(dpi: int) -> None:
    """A thin footer mark confined to the bottom 10% must not hide the orphan.

    ``page_with_orphan_heading`` already draws a footer mark at 0.935h; this
    test asserts that its presence still yields a positive detection.
    """
    img = page_with_orphan_heading(dpi)
    is_orphan, confidence = auditor.check_orphan_heading(img, dpi=dpi)
    assert is_orphan is True
    assert confidence is not None
    assert confidence > 0.2


@pytest.mark.parametrize("dpi", DPIS)
def test_same_result_at_150_and_300_dpi(dpi: int) -> None:
    """DPI independence: the same physical layout yields the same verdict."""
    img_150 = page_with_orphan_heading(150)
    img_300 = page_with_orphan_heading(300)
    result_150 = auditor.check_orphan_heading(img_150, dpi=150)
    result_300 = auditor.check_orphan_heading(img_300, dpi=300)
    assert result_150[0] == result_300[0] is True
    assert result_150[1] == result_300[1]


# ---------------------------------------------------------------------------
# Negative scenarios — no false positive
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dpi", DPIS)
def test_heading_followed_by_paragraph_is_not_flagged(dpi: int) -> None:
    """A merged multi-line paragraph is rejected on height grounds, not misread
    as a short orphan heading, even though its blank tail exceeds threshold."""
    img = page_ending_with_paragraph(dpi)
    is_orphan, confidence = auditor.check_orphan_heading(img, dpi=dpi)
    assert is_orphan is False
    assert confidence is None


@pytest.mark.parametrize("dpi", DPIS)
def test_full_table_is_not_a_heading(dpi: int) -> None:
    """Measured page 03: table ends at 0.725h, 0.175 blank tail -> (False, None)."""
    img = page_with_full_table(dpi)
    is_orphan, confidence = auditor.check_orphan_heading(img, dpi=dpi)
    assert is_orphan is False
    assert confidence is None


@pytest.mark.parametrize("dpi", DPIS)
def test_bibliography_last_page_rejected_on_its_own_merits(dpi: int) -> None:
    """Measured page 27: last ink at 0.79h, 0.11 blank tail -> (False, None)."""
    img = page_ending_with_bibliography(dpi)
    is_orphan, confidence = auditor.check_orphan_heading(img, dpi=dpi)
    assert is_orphan is False
    assert confidence is None


@pytest.mark.parametrize("dpi", DPIS)
def test_no_ink_below_top_half_not_flagged(dpi: int) -> None:
    """Dense content confined to the top half, nothing below -> (False, None)."""
    img = page_with_dense_top_half(dpi)
    is_orphan, confidence = auditor.check_orphan_heading(img, dpi=dpi)
    assert is_orphan is False
    assert confidence is None


def test_blank_page_not_flagged() -> None:
    """A page with no ink at all must not be flagged (near_blank owns it)."""
    img = page_blank()
    is_orphan, confidence = auditor.check_orphan_heading(img, dpi=150)
    assert is_orphan is False
    assert confidence is None


# ---------------------------------------------------------------------------
# Cover-page exclusion by index
# ---------------------------------------------------------------------------


def test_is_cover_short_circuits_regardless_of_content() -> None:
    """``is_cover=True`` returns (False, None) even for content that would
    otherwise be flagged as an orphan heading."""
    img = page_with_orphan_heading(150)
    is_orphan, confidence = auditor.check_orphan_heading(img, dpi=150, is_cover=True)
    assert is_orphan is False
    assert confidence is None


def test_is_cover_defaults_to_false() -> None:
    """Without is_cover, the same orphan-heading image is still flagged."""
    img = page_with_orphan_heading(150)
    is_orphan, _confidence = auditor.check_orphan_heading(img, dpi=150)
    assert is_orphan is True


# ---------------------------------------------------------------------------
# Signature: keyword-only additions, backward-compatible positional call
# ---------------------------------------------------------------------------


def test_signature_has_keyword_only_dpi_and_is_cover() -> None:
    sig = inspect.signature(auditor.check_orphan_heading)
    params = sig.parameters
    assert params["dpi"].kind == inspect.Parameter.KEYWORD_ONLY
    assert params["dpi"].default == auditor.DEFAULT_DPI
    assert params["is_cover"].kind == inspect.Parameter.KEYWORD_ONLY
    assert params["is_cover"].default is False


def test_old_positional_call_still_valid() -> None:
    """``check_orphan_heading(img)`` — the historical call shape — must still work."""
    img = page_with_orphan_heading(auditor.DEFAULT_DPI)
    is_orphan, confidence = auditor.check_orphan_heading(img)
    assert is_orphan is True
    assert confidence is not None


# ---------------------------------------------------------------------------
# Last-page exclusion by index
# ---------------------------------------------------------------------------
#
# An orphan heading means the heading's own content was pushed onto the
# FOLLOWING page. The last page has no following page, so a stranded heading
# cannot exist there by definition — whatever blank space trails the final
# block is simply where the document ends.
#
# This is the same deterministic, DPI-free index exemption already used for
# the cover, and it is not a threshold tweak: no calibration constant moves.


def test_is_last_page_short_circuits_regardless_of_content() -> None:
    """``is_last_page=True`` returns (False, None) even for content that would
    otherwise be flagged as an orphan heading."""
    img = page_with_orphan_heading(150)
    is_orphan, confidence = auditor.check_orphan_heading(
        img, dpi=150, is_last_page=True,
    )
    assert is_orphan is False
    assert confidence is None


def test_is_last_page_defaults_to_false() -> None:
    """Without is_last_page, the same orphan-heading image is still flagged."""
    img = page_with_orphan_heading(150)
    is_orphan, _confidence = auditor.check_orphan_heading(img, dpi=150)
    assert is_orphan is True


def test_trailing_blank_on_a_final_page_is_not_an_orphan() -> None:
    """The real regression: the rebuilt fixture's page 24 ends with a short
    bibliography entry followed by ~49 % blank space. Flagged when treated as
    an interior page, exempt as the final one."""
    img = page_with_orphan_heading(150, heading_top_frac=0.42)
    assert auditor.check_orphan_heading(img, dpi=150)[0] is True
    assert auditor.check_orphan_heading(img, dpi=150, is_last_page=True)[0] is False


def test_signature_has_keyword_only_is_last_page() -> None:
    params = inspect.signature(auditor.check_orphan_heading).parameters
    assert params["is_last_page"].kind == inspect.Parameter.KEYWORD_ONLY
    assert params["is_last_page"].default is False
