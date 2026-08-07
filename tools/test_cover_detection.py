"""Tests for cover-page detection in the visual auditor.

`has_full_bleed_background()` exists to answer one question: does this page
carry decorative artwork that reaches the paper edge? `check_edge_clipping()`
uses the answer to avoid reporting a designed cover as clipped content.

It used to answer "yes" for an ordinary body page and even for a blank one.
Three of its five criteria — left edge clean, bottom edge clean, no right-edge
ink — are satisfied by *any* page with tidy margins, and the threshold was two
criteria out of five. Absence of ink was being counted as evidence of artwork.

A cover is identified by what it HAS, not by what it lacks. These tests pin
that: positive edge decoration is required, and the clean-edge criteria only
act as disqualifiers.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import visual_pdf_auditor as auditor  # noqa: E402

# A4 at 150 DPI, matching what pdftoppm produces for these reports.
W, H = 1240, 1754


def blank_page() -> Image.Image:
    return Image.new("L", (W, H), 255)


def decorated_cover() -> Image.Image:
    """Artwork bleeding off the top-right corner, as the UNL cover does."""
    img = blank_page()
    d = ImageDraw.Draw(img)
    # Top edge, right of the first 15 % of the width — reaches the paper edge.
    d.rectangle([int(W * 0.15), 0, W, 40], fill=40)
    # Right edge, upper portion of the page.
    d.rectangle([W - 30, 0, W, int(H * 0.15)], fill=40)
    # Some title text in the middle, as any cover has.
    for y in range(int(H * 0.35), int(H * 0.45), 30):
        d.rectangle([int(W * 0.25), y, int(W * 0.75), y + 14], fill=0)
    return img


def body_page() -> Image.Image:
    """Ordinary text page: generous margins, nothing touching an edge."""
    img = blank_page()
    d = ImageDraw.Draw(img)
    for y in range(int(H * 0.12), int(H * 0.85), 26):
        d.rectangle([int(W * 0.1), y, int(W * 0.9), y + 10], fill=0)
    return img


def left_clipped_page() -> Image.Image:
    """Content running off the left edge — a defect, never a cover."""
    img = blank_page()
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(H * 0.2), int(W * 0.6), int(H * 0.8)], fill=60)
    return img


def test_decorated_cover_is_detected() -> None:
    assert auditor.has_full_bleed_background(decorated_cover()) is True


def test_ordinary_body_page_is_not_a_cover() -> None:
    assert auditor.has_full_bleed_background(body_page()) is False


def test_blank_page_is_not_a_cover() -> None:
    """The clearest symptom of the old bug: nothing at all counted as artwork."""
    assert auditor.has_full_bleed_background(blank_page()) is False


def test_left_clipped_content_is_not_a_cover() -> None:
    """Otherwise a genuine clipping defect would exempt itself from reporting."""
    assert auditor.has_full_bleed_background(left_clipped_page()) is False


@pytest.mark.parametrize(
    "builder", [blank_page, body_page, left_clipped_page], ids=lambda f: f.__name__,
)
def test_absence_of_ink_is_never_evidence_of_artwork(builder) -> None:
    """Clean edges alone must never be enough to call a page a cover."""
    assert auditor.has_full_bleed_background(builder()) is False
