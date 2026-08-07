"""End-to-end proof that a defective page survives the whole audit pipeline.

The page-level checks are pinned by their own test modules. This one renders a
real (synthetic) PDF through `audit_pdf()` — pdftoppm, per-page analysis,
classification, severity, artifacts — because the defects being fixed here were
not in the checks alone: the auditor reported a clean PASS on a document whose
page 3 ran off the right edge and stopped a third of a page short of the bottom.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import visual_pdf_auditor as auditor  # noqa: E402

DPI = 150
W, H = round(8.27 * DPI), round(11.69 * DPI)

pytestmark = pytest.mark.skipif(
    shutil.which("pdftoppm") is None, reason="pdftoppm (poppler-utils) not installed",
)


def _text(draw: ImageDraw.ImageDraw, x0: int, x1: int, y: int) -> None:
    """A line of glyph-like marks, not a solid bar."""
    x = x0
    while x < x1:
        draw.rectangle([x, y, min(x + 8, x1), y + 13], fill=0)
        x += 11


def _text_page(stop_frac: float = 0.89) -> Image.Image:
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    y = DPI
    while y < H * stop_frac:
        _text(draw, DPI, W - DPI, y)
        y += 33
    return img


def defective_page() -> Image.Image:
    """Text stopping at mid-page, plus one line running off the right edge."""
    img = _text_page(stop_frac=0.52)
    draw = ImageDraw.Draw(img)
    _text(draw, round(W * 0.6), W, round(H * 0.55))
    return img


@pytest.fixture(scope="module")
def audit(tmp_path_factory) -> tuple["auditor.AuditResult", Path]:
    """Audit a four-page PDF whose page 3 carries both defects. Run once."""
    workdir = tmp_path_factory.mktemp("visual-audit")
    pages = [_text_page(), _text_page(), defective_page(), _text_page()]
    pdf = workdir / "report.pdf"
    pages[0].save(
        pdf, save_all=True, append_images=pages[1:], resolution=float(DPI),
    )
    outdir = workdir / "audit"
    return auditor.audit_pdf(pdf, outdir, dpi=DPI), outdir


def test_the_defective_page_makes_the_whole_audit_fail(audit) -> None:
    result, _ = audit

    assert result.severity == "FAIL"
    assert auditor.count_flagged_pages(result, auditor.FAILURE) == 1


def test_page_three_is_reported_as_clipped_and_half_empty(audit) -> None:
    result, _ = audit
    page = next(f for f in result.findings if f.page == 3)
    issues = {i.tag: i.level for i in auditor.page_issues(page, result.total_pages)}

    assert issues["EDGE_CLIPPING"] == auditor.FAILURE
    assert issues["EXCESSIVE_WHITESPACE"] == auditor.WARNING
    assert page.edge_side == "right"


def test_the_intact_pages_stay_clean(audit) -> None:
    result, _ = audit

    for page in (1, 2, 4):
        finding = next(f for f in result.findings if f.page == page)
        levels = {i.level for i in auditor.page_issues(finding, result.total_pages)}
        assert auditor.FAILURE not in levels
        assert auditor.WARNING not in levels


def test_the_written_report_agrees_with_the_severity(audit) -> None:
    _, outdir = audit
    text = (outdir / "visual_qa.md").read_text(encoding="utf-8")

    assert "❌ FAIL" in text
    assert "- **Failure pages**: 1" in text
    assert "**FAILURE** · EDGE_CLIPPING" in text
    assert (outdir / "contact_sheet.png").exists()
