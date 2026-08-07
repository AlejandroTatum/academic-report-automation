"""Tests for the excessive-whitespace check the module docstring promises.

The docstring advertises "near-blank pages / excessive whitespace", but the
only thing implemented was `MIN_CONTENT_FRAC`: a page had to fall under 0.5 %
ink before anything was said. A page that is half empty still carries 2-4 %
ink, so the converter injecting `\\Needspace{16\\baselineskip}` before every
section — which pushes sections onto fresh pages and leaves a third of the
previous page blank — audited as a clean PASS.

The check answers one question: does content stop well short of the bottom
while more content follows? It is a WARNING, never a failure: whether the
whitespace is a defect or a deliberate break is a human judgement, and the
auditor's job is only to point at it. Pages that are short for legitimate
reasons — the cover, the closing page, a page dominated by one figure, a page
too empty to be content at all — are excluded.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import visual_pdf_auditor as auditor  # noqa: E402

DPIS = (150, 300)


# ---------------------------------------------------------------------------
# Synthetic page builders — physical sizes in inches, scaled by DPI
# ---------------------------------------------------------------------------


def _page(dpi: int) -> tuple[Image.Image, ImageDraw.ImageDraw, int, int]:
    w, h = round(8.27 * dpi), round(11.69 * dpi)
    img = Image.new("L", (w, h), color=255)
    return img, ImageDraw.Draw(img), w, h


def _text_block(
    draw: ImageDraw.ImageDraw, w: int, dpi: int, top: int, bottom: int,
) -> None:
    """Fill the vertical range with glyph-like text lines."""
    margin = dpi
    thickness = max(2, round(0.09 * dpi))
    glyph = max(2, round(0.05 * dpi))
    gap = max(1, round(0.02 * dpi))
    y = top
    while y < bottom:
        x = margin
        while x < w - margin:
            draw.rectangle([x, y, min(x + glyph, w - margin), y + thickness], fill=0)
            x += glyph + gap
        y += round(0.22 * dpi)


def full_page(dpi: int) -> Image.Image:
    """Text from the top margin down to the footer band — nothing to report."""
    img, draw, w, h = _page(dpi)
    _text_block(draw, w, dpi, dpi, round(h * 0.89))
    return img


def short_page(dpi: int, stop_frac: float = 0.55) -> Image.Image:
    """Text stopping at *stop_frac* of the page height, blank below it."""
    img, draw, w, h = _page(dpi)
    _text_block(draw, w, dpi, dpi, round(h * stop_frac))
    # A page number in the footer band — it must not count as content.
    draw.rectangle(
        [w // 2, round(h * 0.94), w // 2 + round(0.1 * dpi), round(h * 0.95)], fill=0,
    )
    return img


def figure_page(dpi: int) -> Image.Image:
    """A page dominated by one figure: a dense block, then blank to the bottom."""
    img, draw, w, h = _page(dpi)
    draw.rectangle([dpi, dpi, w - dpi, round(h * 0.55)], fill=90)
    return img


def near_blank_page(dpi: int) -> Image.Image:
    """One stranded line and nothing else — low_density already owns this."""
    img, draw, w, h = _page(dpi)
    draw.rectangle(
        [dpi, dpi, dpi + round(w * 0.25), dpi + round(0.09 * dpi)], fill=0,
    )
    return img


def whitespace(img: Image.Image, **kwargs) -> tuple[bool, float | None]:
    return auditor.check_excessive_whitespace(img, **kwargs)


# ---------------------------------------------------------------------------
# The defect
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dpi", DPIS)
def test_an_interior_page_ending_early_is_flagged(dpi: int) -> None:
    flagged, tail = whitespace(short_page(dpi), is_cover=False, is_last_page=False)

    assert flagged is True
    assert tail is not None and tail > auditor.WHITESPACE_TAIL_MIN_FRAC


@pytest.mark.parametrize("dpi", DPIS)
def test_the_flagged_page_carries_ordinary_ink(dpi: int) -> None:
    """The point of the check: this page is far above the low-density floor."""
    page = short_page(dpi)

    assert auditor.ink_fraction(page) > auditor.MIN_CONTENT_FRAC
    assert auditor.check_low_density(page)[0] is False
    assert whitespace(page, is_cover=False, is_last_page=False)[0] is True


# ---------------------------------------------------------------------------
# Legitimately short pages are not flagged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dpi", DPIS)
def test_a_full_page_is_not_flagged(dpi: int) -> None:
    assert whitespace(full_page(dpi), is_cover=False, is_last_page=False)[0] is False


@pytest.mark.parametrize("dpi", DPIS)
def test_the_last_page_is_never_flagged(dpi: int) -> None:
    """A document simply ends; there is no following content to pull up."""
    assert whitespace(short_page(dpi), is_cover=False, is_last_page=True)[0] is False


@pytest.mark.parametrize("dpi", DPIS)
def test_the_cover_is_never_flagged(dpi: int) -> None:
    assert whitespace(short_page(dpi), is_cover=True, is_last_page=False)[0] is False


@pytest.mark.parametrize("dpi", DPIS)
def test_a_figure_dominated_page_is_not_flagged(dpi: int) -> None:
    """A float page ends where its figure ends — that is not stray whitespace."""
    assert whitespace(figure_page(dpi), is_cover=False, is_last_page=False)[0] is False


@pytest.mark.parametrize("dpi", DPIS)
def test_a_near_blank_page_is_left_to_the_density_checks(dpi: int) -> None:
    page = near_blank_page(dpi)

    assert auditor.check_low_density(page)[0] is True
    assert whitespace(page, is_cover=False, is_last_page=False)[0] is False


@pytest.mark.parametrize("dpi", DPIS)
def test_a_blank_page_is_left_to_the_density_checks(dpi: int) -> None:
    img, _, _, _ = _page(dpi)

    assert whitespace(img, is_cover=False, is_last_page=False)[0] is False


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def test_excessive_whitespace_is_a_warning_never_a_failure() -> None:
    finding = auditor.PageFinding(
        page=3, excessive_whitespace=True, whitespace_frac=0.33,
    )
    issues = auditor.page_issues(finding, total_pages=9)

    assert [i.level for i in issues] == [auditor.WARNING]
    assert issues[0].tag == "EXCESSIVE_WHITESPACE"
