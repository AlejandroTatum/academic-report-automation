"""Tests for edge-clipping detection — a single clipped line must trip it.

`check_edge_clipping()` used to average one 5 px strip over the FULL page
height and require 2 % of it to be dark. At 150 DPI that strip is 8 770 px;
one clipped line of text contributes about 100 of them — 1.1 %, below the
threshold, always. The check was mathematically incapable of firing for the
exact defect it exists for, and a real report whose page 3 ran off the right
edge audited as a clean PASS.

Ink at the paper edge is local evidence, so it is measured locally: the strip
is scanned in one-line-tall bands and a single inked band is enough. These
tests pin both directions — the clipped line fires, and the things that live
near a margin by design (footers, page numbers, header rules, and the
decorative cover artwork that `has_full_bleed_background()` exempts) do not.
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


def _text_line(
    draw: ImageDraw.ImageDraw, x0: int, x1: int, y: int, dpi: int,
) -> None:
    """Draw a line of glyph-like marks (not a solid bar) from x0 to x1."""
    thickness = max(2, round(0.09 * dpi))
    glyph = max(2, round(0.05 * dpi))
    gap = max(1, round(0.02 * dpi))
    x = x0
    while x < x1:
        draw.rectangle([x, y, min(x + glyph, x1), y + thickness], fill=0)
        x += glyph + gap


def body_page(dpi: int) -> Image.Image:
    """An ordinary text page: 1-inch margins, a footer page number."""
    img, draw, w, h = _page(dpi)
    margin = dpi
    y = margin
    while y < h - 2 * margin:
        _text_line(draw, margin, w - margin, y, dpi)
        y += round(0.22 * dpi)
    # Page number in the footer band, close to the bottom margin by design.
    _text_line(draw, w // 2, w // 2 + round(0.1 * dpi), h - round(0.7 * dpi), dpi)
    # A header rule just under the top margin, also by design.
    draw.rectangle([margin, round(0.7 * dpi), w - margin, round(0.71 * dpi)], fill=0)
    return img


def clipped_line_page(dpi: int, side: str = "right") -> Image.Image:
    """A body page with exactly ONE line running off the given paper edge."""
    img = body_page(dpi)
    draw = ImageDraw.Draw(img)
    w, h = img.size
    if side == "right":
        _text_line(draw, round(w * 0.6), w, round(h * 0.55), dpi)
    elif side == "left":
        _text_line(draw, 0, round(w * 0.4), round(h * 0.55), dpi)
    elif side == "top":
        _text_line(draw, round(w * 0.3), round(w * 0.7), 0, dpi)
    elif side == "bottom":
        _text_line(
            draw, round(w * 0.3), round(w * 0.7), h - round(0.06 * dpi), dpi,
        )
    return img


def decorated_cover(dpi: int) -> Image.Image:
    """Cover artwork bleeding off the top-right corner, as the UNL cover does."""
    img, draw, w, h = _page(dpi)
    draw.rectangle([round(w * 0.15), 0, w, round(0.27 * dpi)], fill=40)
    draw.rectangle([w - round(0.2 * dpi), 0, w, round(h * 0.15)], fill=40)
    for y in range(round(h * 0.35), round(h * 0.45), round(0.2 * dpi)):
        draw.rectangle(
            [round(w * 0.25), y, round(w * 0.75), y + round(0.09 * dpi)], fill=0,
        )
    return img


def _edge_strip_ink(img: Image.Image, side: str) -> float:
    """Dark fraction of the whole edge strip — the old, diluted measurement."""
    w, h = img.size
    m = auditor.EDGE_MARGIN_PX
    boxes = {
        "left": (0, 0, m, h),
        "right": (w - m, 0, w, h),
        "top": (0, 0, w, m),
        "bottom": (0, h - m, w, h),
    }
    px = auditor._pixels(img.crop(boxes[side]).convert("L"))
    return sum(1 for p in px if p < auditor.EDGE_BAND_DARK) / len(px)


# ---------------------------------------------------------------------------
# The defect
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dpi", DPIS)
@pytest.mark.parametrize("side", ["left", "right", "top", "bottom"])
def test_a_single_clipped_line_is_detected(dpi: int, side: str) -> None:
    page = clipped_line_page(dpi, side)

    assert auditor.check_edge_clipping(page, dpi=dpi) == side


@pytest.mark.parametrize("dpi", DPIS)
def test_the_clipped_line_stays_invisible_to_a_whole_strip_average(dpi: int) -> None:
    """Why the check has to be local: one line never moves the page average."""
    page = clipped_line_page(dpi, "right")

    assert _edge_strip_ink(page, "right") < 0.02  # the old threshold
    assert auditor.check_edge_clipping(page, dpi=dpi) == "right"


# ---------------------------------------------------------------------------
# No false-positive storm
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dpi", DPIS)
def test_an_ordinary_page_with_footer_and_header_is_clean(dpi: int) -> None:
    assert auditor.check_edge_clipping(body_page(dpi), dpi=dpi) is None


@pytest.mark.parametrize("dpi", DPIS)
def test_a_blank_page_is_clean(dpi: int) -> None:
    img, _, _, _ = _page(dpi)

    assert auditor.check_edge_clipping(img, dpi=dpi) is None


@pytest.mark.parametrize("dpi", DPIS)
def test_the_full_bleed_cover_exemption_still_holds(dpi: int) -> None:
    """Designed artwork reaching the paper edge is not a clipping defect."""
    cover = decorated_cover(dpi)

    assert auditor.has_full_bleed_background(cover) is True
    assert auditor.check_edge_clipping(cover, dpi=dpi) is None


@pytest.mark.parametrize("dpi", DPIS)
def test_faint_speckle_at_the_edge_is_not_clipping(dpi: int) -> None:
    """Anti-aliasing dust must not be enough — a band has to be truly inked."""
    img, draw, w, h = _page(dpi)
    for y in range(0, h, round(0.25 * dpi)):
        draw.point((w - 1, y), fill=0)

    assert auditor.check_edge_clipping(img, dpi=dpi) is None
