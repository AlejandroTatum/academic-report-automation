"""Tests for the bridge between validate_report and visual_pdf_auditor.

``visual_pdf_validation()`` used to re-implement the auditor's classification
instead of asking for it. That copy carried every bug the auditor's own copies
did — an interior low-density page was reported as an error AND as a warning —
and it could not drift into agreement on its own, because a finding the auditor
learned to detect stayed invisible here until someone remembered to add a
branch. It also computed its own artefact directory from the PDF's basename,
so two same-named PDFs overwrote each other's renders.

The auditor now owns one classifier, ``page_issues()``, and one artefact-path
rule, ``default_output_dir()``. These tests pin that this module consumes them
rather than guessing again.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import validate_report  # noqa: E402
import visual_pdf_auditor  # noqa: E402
from visual_pdf_auditor import AuditResult, PageFinding  # noqa: E402


def _config(pdf: Path) -> types.SimpleNamespace:
    return types.SimpleNamespace(output_format="pdf", pdf_path=pdf)


@pytest.fixture
def pdf(tmp_path: Path) -> Path:
    path = tmp_path / "reports" / "trabajo" / "outputs" / "informe.pdf"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"%PDF-1.5\n")
    return path


def _stub_audit(monkeypatch: pytest.MonkeyPatch, result: AuditResult) -> list[Path]:
    """Replace audit_pdf, recording the artefact directory it was handed."""
    seen: list[Path] = []

    def fake_audit(pdf_path, audit_dir, *args, **kwargs):
        seen.append(Path(audit_dir))
        return result

    monkeypatch.setattr(validate_report, "audit_pdf", fake_audit)
    monkeypatch.setattr(validate_report, "VISUAL_AUDITOR_AVAILABLE", True)
    return seen


def test_interior_low_density_page_is_reported_once_not_twice(
    pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An interior sparse page is a failure. It must not ALSO be a warning."""
    result = AuditResult(pdf_path=str(pdf), total_pages=5)
    result.findings = [PageFinding(page=3, low_density=True, density_frac=0.003)]
    result.severity = visual_pdf_auditor.decide_severity(result)
    _stub_audit(monkeypatch, result)

    outcome = validate_report.visual_pdf_validation(_config(pdf))

    low_density_mentions = [
        line for line in outcome.errors + outcome.warnings if "LOW_DENSITY" in line
    ]
    assert len(low_density_mentions) == 1, low_density_mentions
    assert any("LOW_DENSITY" in line for line in outcome.errors)


def test_last_page_low_density_is_a_warning_not_an_error(
    pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A closing bibliography page is sparse by design."""
    result = AuditResult(pdf_path=str(pdf), total_pages=4)
    result.findings = [PageFinding(page=4, low_density=True, density_frac=0.004)]
    result.severity = visual_pdf_auditor.decide_severity(result)
    _stub_audit(monkeypatch, result)

    outcome = validate_report.visual_pdf_validation(_config(pdf))

    assert not outcome.errors
    assert any("LOW_DENSITY" in line for line in outcome.warnings)


def test_excessive_whitespace_reaches_the_validator(
    pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A finding the auditor detects must surface without a bespoke branch here."""
    result = AuditResult(pdf_path=str(pdf), total_pages=4)
    result.findings = [
        PageFinding(page=2, excessive_whitespace=True, whitespace_frac=0.31),
    ]
    result.severity = visual_pdf_auditor.decide_severity(result)
    _stub_audit(monkeypatch, result)

    outcome = validate_report.visual_pdf_validation(_config(pdf))

    assert any("EXCESSIVE_WHITESPACE" in line for line in outcome.warnings)
    assert not outcome.errors


def test_edge_clipping_is_an_error_naming_the_page(
    pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = AuditResult(pdf_path=str(pdf), total_pages=4)
    result.findings = [PageFinding(page=3, edge_clipping=True, edge_side="right")]
    result.severity = visual_pdf_auditor.decide_severity(result)
    _stub_audit(monkeypatch, result)

    outcome = validate_report.visual_pdf_validation(_config(pdf))

    assert any(
        "EDGE_CLIPPING" in line and "3" in line for line in outcome.errors
    ), outcome.errors


def test_table_suspect_is_informational_and_never_reported(
    pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INFO findings are context for a human reading the audit, not validator noise."""
    result = AuditResult(pdf_path=str(pdf), total_pages=4)
    result.findings = [PageFinding(page=2, table_suspect=True, table_confidence=0.42)]
    result.severity = visual_pdf_auditor.decide_severity(result)
    _stub_audit(monkeypatch, result)

    outcome = validate_report.visual_pdf_validation(_config(pdf))

    assert not outcome.errors
    assert not any("TABLE_SUSPECT" in line for line in outcome.warnings)


def test_artifact_directory_comes_from_the_auditor_not_from_the_basename(
    pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two same-named PDFs must not share an artefact directory."""
    result = AuditResult(pdf_path=str(pdf), total_pages=2)
    seen = _stub_audit(monkeypatch, result)

    validate_report.visual_pdf_validation(_config(pdf))

    assert seen == [visual_pdf_auditor.default_output_dir(pdf)]
    assert seen[0] != validate_report.CONTENT_ROOT / "build" / "visual-audits" / pdf.stem
