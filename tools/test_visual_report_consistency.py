"""One definition of "failure" and "warning", reused everywhere the auditor speaks.

The auditor used to compute what counts as a failure twice: once to decide the
severity, once to print the stderr header — and the two definitions had drifted.
An interior low-density page produced a report that contradicted itself::

    Severity:  FAIL
    Failures:  0

A human reading "0 failures" files the PDF and moves on. These tests pin the
single classifier (`page_issues`) as the only source of truth: the severity
decision, the stderr header, the per-page tag list and `visual_qa.md` must all
be derived from it, so the two counts can never diverge again.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import visual_pdf_auditor as auditor  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def build_result(findings: list, total_pages: int = 9) -> "auditor.AuditResult":
    """An AuditResult whose severity was decided by the module itself."""
    result = auditor.AuditResult(pdf_path="stub.pdf")
    result.total_pages = total_pages
    result.findings = findings
    result.severity = auditor.decide_severity(result)
    return result


def header_counts(capsys) -> tuple[str, int, int]:
    """Parse `Severity` / `Failures` / `Warnings` out of the printed header."""
    text = capsys.readouterr().err
    severity = re.search(r"Severity:\s+(\S+)", text).group(1)
    failures = int(re.search(r"Failures:\s+(\d+)", text).group(1))
    warnings = int(re.search(r"Warnings:\s+(\d+)", text).group(1))
    return severity, failures, warnings


def interior_low_density() -> list:
    """The exact D-13 reproduction: page 5 of 9 is almost empty."""
    return [auditor.PageFinding(page=5, low_density=True, density_frac=0.0028)]


def clipped_page() -> list:
    return [auditor.PageFinding(page=3, edge_clipping=True, edge_side="right")]


def orphan_page() -> list:
    return [auditor.PageFinding(page=4, orphan_heading=True, orphan_confidence=0.8)]


def whitespace_page() -> list:
    return [
        auditor.PageFinding(page=3, excessive_whitespace=True, whitespace_frac=0.31),
    ]


def sparse_last_page() -> list:
    """Low density on the closing page — sparse by nature, never a failure."""
    return [auditor.PageFinding(page=9, low_density=True, density_frac=0.004)]


def clean_page() -> list:
    return [auditor.PageFinding(page=2, table_suspect=True, table_confidence=0.4)]


CASES = [
    interior_low_density,
    clipped_page,
    orphan_page,
    whitespace_page,
    sparse_last_page,
    clean_page,
]


# ---------------------------------------------------------------------------
# The reproduction
# ---------------------------------------------------------------------------


def test_interior_low_density_is_a_failure_in_the_header_too(capsys) -> None:
    """FAIL with "0 failures" was the defect — the header must count it."""
    result = build_result(interior_low_density())
    auditor._print_summary(result)

    severity, failures, warnings = header_counts(capsys)
    assert severity == "FAIL"
    assert failures == 1
    assert warnings == 0


# ---------------------------------------------------------------------------
# The counts can never diverge from the severity decision
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("builder", CASES, ids=lambda f: f.__name__)
def test_header_counts_agree_with_the_severity_decision(capsys, builder) -> None:
    result = build_result(builder())
    auditor._print_summary(result)
    severity, failures, warnings = header_counts(capsys)

    assert severity == result.severity
    if severity == "FAIL":
        assert failures > 0
    elif severity == "PASS_WITH_WARNINGS":
        assert failures == 0
        assert warnings > 0
    else:
        assert (failures, warnings) == (0, 0)


@pytest.mark.parametrize("builder", CASES, ids=lambda f: f.__name__)
def test_header_counts_come_from_the_shared_classifier(capsys, builder) -> None:
    """Whatever the header prints must be what `page_issues` classified."""
    result = build_result(builder())
    auditor._print_summary(result)
    _, failures, warnings = header_counts(capsys)

    assert failures == auditor.count_flagged_pages(result, auditor.FAILURE)
    assert warnings == auditor.count_flagged_pages(result, auditor.WARNING)


@pytest.mark.parametrize("builder", CASES, ids=lambda f: f.__name__)
def test_markdown_report_flags_the_same_pages_as_the_header(
    capsys, tmp_path: Path, builder,
) -> None:
    result = build_result(builder())
    auditor._print_summary(result)
    _, failures, warnings = header_counts(capsys)

    report = auditor.write_visual_qa_report(result, tmp_path / "visual_qa.md")
    text = report.read_text(encoding="utf-8")

    assert f"- **Failure pages**: {failures}" in text
    assert f"- **Warning pages**: {warnings}" in text
    assert text.count(f"**{auditor.FAILURE}**") == sum(
        1
        for f in result.findings
        for issue in auditor.page_issues(f, result.total_pages)
        if issue.level == auditor.FAILURE
    )


@pytest.mark.parametrize("builder", CASES, ids=lambda f: f.__name__)
def test_per_page_tags_come_from_the_shared_classifier(capsys, builder) -> None:
    """The per-page tag list is a third mouth that must say the same thing."""
    result = build_result(builder())
    auditor._print_summary(result)
    text = capsys.readouterr().err

    for finding in result.findings:
        line = next(
            ln for ln in text.splitlines() if f"[Page {finding.page:2d}]" in ln
        )
        for issue in auditor.page_issues(finding, result.total_pages):
            assert issue.tag in line


# ---------------------------------------------------------------------------
# Classification boundaries
# ---------------------------------------------------------------------------


def test_low_density_is_a_failure_only_on_an_interior_page() -> None:
    interior = auditor.PageFinding(page=5, low_density=True, density_frac=0.003)
    cover = auditor.PageFinding(page=1, low_density=True, density_frac=0.003)
    last = auditor.PageFinding(page=9, low_density=True, density_frac=0.003)

    levels = {
        f.page: {i.level for i in auditor.page_issues(f, 9)}
        for f in (interior, cover, last)
    }
    assert levels[5] == {auditor.FAILURE}
    assert levels[1] == {auditor.WARNING}
    assert levels[9] == {auditor.WARNING}


def test_advisory_findings_are_warnings_not_failures() -> None:
    advisory = auditor.PageFinding(
        page=3, orphan_heading=True, excessive_whitespace=True, whitespace_frac=0.3,
    )
    levels = {i.level for i in auditor.page_issues(advisory, 9)}

    assert levels == {auditor.WARNING}
    assert auditor.decide_severity(build_result([advisory])) == "PASS_WITH_WARNINGS"


def test_table_suspicion_is_informational_only() -> None:
    table = auditor.PageFinding(page=3, table_suspect=True, table_confidence=0.6)

    assert {i.level for i in auditor.page_issues(table, 9)} == {auditor.INFO}
    assert auditor.decide_severity(build_result([table])) == "PASS"
