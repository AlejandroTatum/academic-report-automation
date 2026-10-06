"""Visual pass covers only changed pages after a rebuild (verify-concise-drafts T7, S2).

Every audit records a pixel hash per rendered page in ``page_hashes.json``. A
later audit into the same output directory compares against it and lists the
changed pages in ``visual_qa.md`` with their own contact sheet, so the manual
inspection after an edit covers only what changed.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import visual_pdf_auditor as auditor  # noqa: E402

DPI = 50
W, H = round(8.27 * DPI), round(11.69 * DPI)

pytestmark = pytest.mark.skipif(
    shutil.which("pdftoppm") is None, reason="pdftoppm (poppler-utils) not installed",
)


def _page(lines: int) -> Image.Image:
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    for row in range(lines):
        y = DPI + row * 12
        draw.rectangle([DPI, y, W - DPI, y + 5], fill=0)
    return img


def _pdf(path: Path, line_counts: list[int]) -> Path:
    pages = [_page(n) for n in line_counts]
    pages[0].save(path, save_all=True, append_images=pages[1:], resolution=float(DPI))
    return path


def _report(outdir: Path) -> str:
    return (outdir / "visual_qa.md").read_text(encoding="utf-8")


def test_first_audit_records_page_hashes_and_inspects_every_page(tmp_path: Path) -> None:
    outdir = tmp_path / "audit"
    result = auditor.audit_pdf(_pdf(tmp_path / "r.pdf", [20, 30, 40]), outdir, dpi=DPI)
    hashes = json.loads((outdir / "page_hashes.json").read_text(encoding="utf-8"))
    assert len(hashes["pages"]) == 3
    assert result.changed_pages is None
    assert "- **Changed pages**: first audit, inspect every page" in _report(outdir)
    assert not (outdir / "changed_contact_sheet.png").exists()


def test_rebuild_lists_only_the_changed_pages(tmp_path: Path) -> None:
    outdir = tmp_path / "audit"
    auditor.audit_pdf(_pdf(tmp_path / "r.pdf", [20, 30, 40]), outdir, dpi=DPI)
    result = auditor.audit_pdf(_pdf(tmp_path / "r.pdf", [20, 35, 40]), outdir, dpi=DPI)
    assert result.changed_pages == [2]
    assert "- **Changed pages**: 2 (inspect these; unchanged pages keep the previous verdict)" in _report(outdir)
    assert (outdir / "changed_contact_sheet.png").is_file()


def test_rebuild_with_identical_pixels_reports_no_changed_pages(tmp_path: Path) -> None:
    outdir = tmp_path / "audit"
    auditor.audit_pdf(_pdf(tmp_path / "r.pdf", [20, 30]), outdir, dpi=DPI)
    (outdir / "changed_contact_sheet.png").write_bytes(b"stale")
    result = auditor.audit_pdf(_pdf(tmp_path / "r.pdf", [20, 30]), outdir, dpi=DPI)
    assert result.changed_pages == []
    assert "- **Changed pages**: none" in _report(outdir)
    assert not (outdir / "changed_contact_sheet.png").exists()


def test_added_page_counts_as_changed(tmp_path: Path) -> None:
    outdir = tmp_path / "audit"
    auditor.audit_pdf(_pdf(tmp_path / "r.pdf", [20, 30]), outdir, dpi=DPI)
    result = auditor.audit_pdf(_pdf(tmp_path / "r.pdf", [20, 30, 40]), outdir, dpi=DPI)
    assert result.changed_pages == [3]


def test_unreadable_previous_hashes_mean_a_first_audit(tmp_path: Path) -> None:
    outdir = tmp_path / "audit"
    outdir.mkdir()
    (outdir / "page_hashes.json").write_text("{broken", encoding="utf-8")
    result = auditor.audit_pdf(_pdf(tmp_path / "r.pdf", [20]), outdir, dpi=DPI)
    assert result.changed_pages is None
    assert len(json.loads((outdir / "page_hashes.json").read_text(encoding="utf-8"))["pages"]) == 1


def test_different_dpi_is_a_first_audit(tmp_path: Path) -> None:
    outdir = tmp_path / "audit"
    auditor.audit_pdf(_pdf(tmp_path / "r.pdf", [20]), outdir, dpi=DPI)
    result = auditor.audit_pdf(tmp_path / "r.pdf", outdir, dpi=DPI + 10)
    assert result.changed_pages is None
