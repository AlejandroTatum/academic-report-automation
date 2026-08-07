"""Runtime tests for how `visual_pdf_validation()` classifies auditor findings.

The auditor produces evidence, not authority. An orphan heading is advisory:
it must reach the caller as a WARNING so a report still builds, while the
findings that genuinely indicate a broken page — a near-blank page, content
clipped at an edge, or an interior page that is almost empty — must be
ERRORS.

This distinction was previously only guaranteed by reading the source. These
tests exercise `visual_pdf_validation()` for real, so inverting the
classification fails the suite instead of silently changing what blocks a
build.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import validate_report  # noqa: E402
import visual_pdf_auditor as auditor  # noqa: E402


def make_config(tmp_path: Path) -> "validate_report.ReportConfig":
    """A minimal PDF-output report whose target PDF exists on disk."""
    import yaml

    import report_config

    folder = tmp_path / "r"
    folder.mkdir(parents=True, exist_ok=True)
    raw = {
        "type": "technical_report",
        "backend": "latex",
        "output": "pdf",
        "metadata": {"title": "T", "subject": "S", "teacher": "D", "student": "A"},
        "body": "body.md",
        "pdf": "out.pdf",
    }
    (folder / "report.yml").write_text(yaml.safe_dump(raw), encoding="utf-8")
    (folder / "body.md").write_text("# T\n\ncontent\n", encoding="utf-8")
    config = report_config.ReportConfig.load(folder)
    config.pdf_path.parent.mkdir(parents=True, exist_ok=True)
    config.pdf_path.write_bytes(b"%PDF-1.7\n%stub\n")
    return config


def audit_result(severity: str, findings: list) -> "auditor.AuditResult":
    result = auditor.AuditResult(pdf_path="stub.pdf")
    result.severity = severity
    result.total_pages = 5
    result.findings = findings
    return result


def orphan_page(page: int) -> "auditor.PageFinding":
    return auditor.PageFinding(page=page, orphan_heading=True, orphan_confidence=0.9)


def near_blank_page(page: int) -> "auditor.PageFinding":
    return auditor.PageFinding(page=page, near_blank=True, blank_reason="ink=0.0001")


def run_validation(config, result):
    with patch.object(validate_report, "audit_pdf", return_value=result):
        return validate_report.visual_pdf_validation(config)


@pytest.mark.parametrize("severity", ["FAIL", "PASS_WITH_WARNINGS"])
def test_orphan_finding_is_a_warning_never_an_error(
    tmp_path: Path, severity: str,
) -> None:
    """An orphan heading is advisory in both severity branches."""
    config = make_config(tmp_path)
    result = run_validation(config, audit_result(severity, [orphan_page(3)]))

    assert any("ORPHAN_HEADING" in w for w in result.warnings)
    assert not any("ORPHAN_HEADING" in e for e in result.errors)


@pytest.mark.parametrize("severity", ["FAIL", "PASS_WITH_WARNINGS"])
def test_orphan_alone_never_produces_an_error(
    tmp_path: Path, severity: str,
) -> None:
    """A page whose only finding is an orphan heading must not block a build."""
    config = make_config(tmp_path)
    result = run_validation(config, audit_result(severity, [orphan_page(2)]))

    assert result.errors == []


def test_near_blank_is_an_error_not_a_warning(tmp_path: Path) -> None:
    """Guards the other side of the boundary: real defects still block."""
    config = make_config(tmp_path)
    result = run_validation(config, audit_result("FAIL", [near_blank_page(4)]))

    assert any("NEAR_BLANK" in e for e in result.errors)


def test_interior_low_density_is_an_error_but_orphan_stays_a_warning(
    tmp_path: Path,
) -> None:
    """Both classifications hold when the two findings arrive together."""
    config = make_config(tmp_path)
    low = auditor.PageFinding(page=3, low_density=True, density_frac=0.004)
    result = run_validation(config, audit_result("FAIL", [low, orphan_page(2)]))

    assert any("LOW_DENSITY" in e for e in result.errors)
    assert any("ORPHAN_HEADING" in w for w in result.warnings)
    assert not any("ORPHAN_HEADING" in e for e in result.errors)
