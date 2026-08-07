"""Tests for where the auditor puts its artifacts.

The default output directory used to be `<CONTENT_ROOT>/build/visual-audits/
<pdf-stem>/` no matter where the audited PDF actually lived. Two consequences,
both observed: auditing a throwaway PDF in a temp directory deposited renders
and a `visual_qa.md` inside the real academic tree, and two PDFs sharing a
basename but living in different directories overwrote each other's results.

The rule these tests pin: a PDF inside the content root keeps its artifacts in
the content build tree (existing workflows read them there), a PDF outside it
keeps them next to itself, and the leaf directory is derived from the PDF's
own location so two same-named PDFs can never collide.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import visual_pdf_auditor as auditor  # noqa: E402


def make_pdf(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.7\n%stub\n")
    return path


@pytest.fixture()
def content_root(tmp_path: Path) -> Path:
    root = tmp_path / "content"
    root.mkdir()
    return root


# ---------------------------------------------------------------------------
# Inside the content root — the documented location is preserved
# ---------------------------------------------------------------------------


def test_a_report_inside_the_content_root_stays_in_the_build_tree(
    content_root: Path,
) -> None:
    pdf = make_pdf(content_root / "reports" / "c4" / "outputs" / "doc.pdf")

    outdir = auditor.default_output_dir(pdf, content_root=content_root)

    assert outdir.is_relative_to(content_root / "build" / "visual-audits")


def test_two_same_named_reports_inside_the_tree_do_not_collide(
    content_root: Path,
) -> None:
    first = make_pdf(content_root / "reports" / "a" / "outputs" / "doc.pdf")
    second = make_pdf(content_root / "reports" / "b" / "outputs" / "doc.pdf")

    assert auditor.default_output_dir(
        first, content_root=content_root,
    ) != auditor.default_output_dir(second, content_root=content_root)


def test_the_same_pdf_always_resolves_to_the_same_directory(
    content_root: Path,
) -> None:
    pdf = make_pdf(content_root / "reports" / "a" / "outputs" / "doc.pdf")

    assert auditor.default_output_dir(
        pdf, content_root=content_root,
    ) == auditor.default_output_dir(pdf, content_root=content_root)


# ---------------------------------------------------------------------------
# Outside the content root — nothing may be written into the academic tree
# ---------------------------------------------------------------------------


def test_a_pdf_outside_the_content_root_never_writes_into_it(
    tmp_path: Path, content_root: Path,
) -> None:
    pdf = make_pdf(tmp_path / "scratch" / "doc.pdf")

    outdir = auditor.default_output_dir(pdf, content_root=content_root)

    assert not outdir.is_relative_to(content_root)
    assert outdir.is_relative_to(pdf.parent)


def test_two_same_named_pdfs_outside_the_tree_do_not_collide(
    tmp_path: Path, content_root: Path,
) -> None:
    first = make_pdf(tmp_path / "one" / "doc.pdf")
    second = make_pdf(tmp_path / "two" / "doc.pdf")

    assert auditor.default_output_dir(
        first, content_root=content_root,
    ) != auditor.default_output_dir(second, content_root=content_root)


def test_a_relative_path_resolves_like_its_absolute_twin(
    tmp_path: Path, content_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = make_pdf(tmp_path / "scratch" / "doc.pdf")
    monkeypatch.chdir(tmp_path / "scratch")

    assert auditor.default_output_dir(
        Path("doc.pdf"), content_root=content_root,
    ) == auditor.default_output_dir(pdf, content_root=content_root)


# ---------------------------------------------------------------------------
# The CLI honours both the default and the override
# ---------------------------------------------------------------------------


def _capture_output_dir(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    seen: list[Path] = []

    def fake_audit(pdf: Path, output_dir: Path, dpi: int = 150):
        seen.append(Path(output_dir))
        result = auditor.AuditResult(pdf_path=str(pdf))
        result.severity = "PASS"
        return result

    monkeypatch.setattr(auditor, "audit_pdf", fake_audit)
    return seen


def test_the_cli_default_never_targets_the_content_root_for_a_foreign_pdf(
    tmp_path: Path, content_root: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    pdf = make_pdf(tmp_path / "scratch" / "doc.pdf")
    monkeypatch.setattr(auditor, "CONTENT_ROOT", content_root)
    seen = _capture_output_dir(monkeypatch)

    assert auditor.main([str(pdf)]) == 0
    assert not seen[0].is_relative_to(content_root)


def test_the_output_override_wins(
    tmp_path: Path, content_root: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    pdf = make_pdf(content_root / "reports" / "a" / "outputs" / "doc.pdf")
    monkeypatch.setattr(auditor, "CONTENT_ROOT", content_root)
    seen = _capture_output_dir(monkeypatch)
    chosen = tmp_path / "elsewhere"

    assert auditor.main([str(pdf), "-o", str(chosen)]) == 0
    assert seen[0] == chosen
