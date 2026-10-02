"""Generate-phase tests for ``tools/doc_status.py`` (slice 2b-ii).

Slice 2b-ii ships the generate derivation: the final PDF is ``done`` when it
exists, is not older than the ``approval.yml`` that authorized it, and is not
older than ``report.yml`` (new-report-flow T5: changing the format after a build
requires a rebuild), and falls back to ``pending`` in every other shape. Like the
2a/2b-i suites these tests call the handler directly and assert its raw
``done|pending`` token and detail; ``derive``/renderers/CLI are slice 2c and
validate/deliver are slice 2b-iii. Artifact shapes come from ``tools/conftest.py``.
"""
from __future__ import annotations

from pathlib import Path

import doc_status
from conftest import _approval, _choose_format, _config, _mtime, _pdf, _report

# A fixed clock: generate is a pure mtime comparison, so every side is pinned
# (report.yml, approval.yml and the PDF) and the tests never depend on wall-clock
# ordering or the filesystem's timestamp resolution.
T0 = 1_700_000_000.0


def _generate_fixtures(folder: Path) -> None:
    """report.yml older than approval.yml, so a built PDF can beat both."""
    _report(folder)
    _approval(folder)
    _mtime(folder / "report.yml", T0)
    _mtime(folder / "approval.yml", T0 + 60)


def test_generate_pdf_newer_than_marker_is_done(tmp_path: Path) -> None:
    """A PDF built after the approval is the artifact the marker authorized."""
    folder = tmp_path / "wf"
    _generate_fixtures(folder)
    pdf = _pdf(folder, mtime=T0 + 120)

    phase = doc_status._phase_generate(folder, _config(folder), None)

    assert phase.name == "generate"
    assert phase.state == doc_status.DONE
    assert phase.blocked_reason == ""
    assert pdf.name in phase.detail


def test_generate_pdf_older_than_marker_is_pending(tmp_path: Path) -> None:
    """A PDF built before the approval is stale: regenerate, never ship it."""
    folder = tmp_path / "wf"
    _generate_fixtures(folder)
    _pdf(folder, mtime=T0 + 30)

    phase = doc_status._phase_generate(folder, _config(folder), None)

    assert phase.state == doc_status.PENDING
    assert phase.blocked_reason == ""
    assert phase.state != doc_status.DONE


def test_generate_pdf_older_than_report_yml_is_pending(tmp_path: Path) -> None:
    """new-report-flow T5: changing report.yml (e.g. the format) after a build
    makes the PDF stale even though it still postdates the approval."""
    folder = tmp_path / "wf"
    _generate_fixtures(folder)
    _pdf(folder, mtime=T0 + 120)
    _choose_format(folder, "aa")
    _mtime(folder / "report.yml", T0 + 200)

    phase = doc_status._phase_generate(folder, _config(folder), None)

    assert phase.state == doc_status.PENDING
    assert "report.yml" in phase.detail
    assert phase.state != doc_status.DONE


def test_generate_pdf_matching_marker_mtime_is_done(tmp_path: Path) -> None:
    """TRIANGULATE: the boundary is ``>=``; an equal timestamp is still fresh."""
    folder = tmp_path / "wf"
    _generate_fixtures(folder)
    _pdf(folder, mtime=T0 + 60)

    phase = doc_status._phase_generate(folder, _config(folder), None)

    assert phase.state == doc_status.DONE


def test_generate_missing_pdf_is_pending(tmp_path: Path) -> None:
    """TRIANGULATE: an approved folder that was never built waits at generate."""
    folder = tmp_path / "wf"
    _generate_fixtures(folder)

    phase = doc_status._phase_generate(folder, _config(folder), None)

    assert phase.state == doc_status.PENDING
    assert phase.blocked_reason == ""
    assert "missing" in phase.detail


def test_generate_missing_approval_marker_is_pending(tmp_path: Path) -> None:
    """TRIANGULATE: without the authorizing marker there is no freshness reference."""
    folder = tmp_path / "wf"
    _report(folder)
    _mtime(folder / "report.yml", T0)
    _pdf(folder, mtime=T0 + 120)

    phase = doc_status._phase_generate(folder, _config(folder), None)

    assert phase.state == doc_status.PENDING
    assert phase.blocked_reason == ""


def test_generate_missing_report_yml_is_pending(tmp_path: Path) -> None:
    """TRIANGULATE: without report.yml there is no format-change reference."""
    folder = tmp_path / "wf"
    _report(folder)
    _approval(folder)
    _pdf(folder, mtime=T0 + 120)
    config = _config(folder)
    (folder / "report.yml").unlink()

    phase = doc_status._phase_generate(folder, config, None)

    assert phase.state == doc_status.PENDING
    assert "report.yml" in phase.detail


def test_generate_honours_the_configured_pdf_path(tmp_path: Path) -> None:
    """TRIANGULATE: a declared ``pdf:`` key, not the default, names the final artifact."""
    folder = tmp_path / "wf"
    _report(folder)
    report = folder / "report.yml"
    report.write_text(report.read_text(encoding="utf-8") + "pdf: outputs/final.pdf\n", encoding="utf-8")
    _approval(folder)
    _mtime(folder / "report.yml", T0)
    _mtime(folder / "approval.yml", T0 + 60)
    _pdf(folder, path="outputs/final.pdf", mtime=T0 + 120)

    phase = doc_status._phase_generate(folder, _config(folder), None)

    assert phase.state == doc_status.DONE
    assert "final.pdf" in phase.detail


def test_preview_built_before_approval_never_satisfies_generate(tmp_path: Path) -> None:
    """Task 11(a): a --no-approval-check preview is older than the marker, so it is never the final artifact."""
    folder = tmp_path / "wf"
    _report(folder)
    _mtime(folder / "report.yml", T0)
    _pdf(folder, mtime=T0 + 30)  # preview built at Decision 2, before approval.yml exists
    assert doc_status._phase_generate(folder, _config(folder), None).state == doc_status.PENDING

    _approval(folder)
    _mtime(folder / "approval.yml", T0 + 60)  # the approval lands after the preview
    phase = doc_status._phase_generate(folder, _config(folder), None)

    assert phase.state == doc_status.PENDING
    assert "older than approval.yml" in phase.detail
