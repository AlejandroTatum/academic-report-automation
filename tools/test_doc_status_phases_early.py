"""Early-phase tests for ``tools/doc_status.py`` (slice 2a).

Slice 2a ships the phase vocabulary, the value dataclasses and the
intake/research/preview derivations; ``derive``/renderers/CLI land in slices
2b/2c. These tests therefore call the three early handlers directly with a
throwaway ``ReportConfig`` and assert their raw ``done|pending|blocked`` token,
detail and blocked reason -- nothing here depends on a route projection that does
not exist yet. Artifact shapes come from ``tools/conftest.py``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import doc_status
from conftest import _config, _evidence_matrix, _preview, _report, _skip_research


def _early_phases(folder: Path) -> list[doc_status.PhaseState]:
    """Return the intake/research/preview handler results for ``folder``."""
    config = _config(folder)
    return [
        doc_status._phase_intake(folder, config, None),
        doc_status._phase_research(folder, config, None),
        doc_status._phase_preview(folder, config, None),
    ]


# ---------------------------------------------------------------------------
# 2.1 intake
# ---------------------------------------------------------------------------


def test_intake_missing_report_yml_is_pending_not_blocked(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    phase = doc_status._phase_intake(folder, _config(folder), None)

    assert phase.name == "intake"
    assert phase.state == doc_status.PENDING
    assert phase.blocked_reason == ""
    assert phase.detail == "report.yml missing"


def test_missing_report_yml_leaves_intake_as_route_focus_and_later_phases_pending(
    tmp_path: Path,
) -> None:
    """Missing ``report.yml`` means intake is the route focus and later phases wait.

    Slice 2a has no projection yet, so this asserts the raw states that slice 2c
    turns into ``current`` for the first phase and ``pending`` for the rest.
    """
    states = _early_phases(tmp_path / "wf")

    assert [phase.name for phase in states] == list(doc_status.PHASES[:3])
    assert states[0].state == doc_status.PENDING
    assert all(phase.state == doc_status.PENDING for phase in states[1:])
    assert all(phase.blocked_reason == "" for phase in states)


def test_intake_unknown_route_is_blocked(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder, route="galactic")

    phase = doc_status._phase_intake(folder, _config(folder), None)

    assert phase.state == doc_status.BLOCKED
    assert phase.blocked_reason == "unknown_route"
    assert "galactic" in phase.detail


def test_intake_incomplete_route_mandatory_metadata_is_pending(tmp_path: Path) -> None:
    """Academic intake needs subject/teacher; a missing one keeps intake pending."""
    folder = tmp_path / "wf"
    _report(folder, teacher=None)

    phase = doc_status._phase_intake(folder, _config(folder), None)

    assert phase.state == doc_status.PENDING
    assert phase.blocked_reason == ""
    assert "teacher" in phase.detail


def test_intake_complete_is_done(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder)

    phase = doc_status._phase_intake(folder, _config(folder), None)

    assert phase.state == doc_status.DONE
    assert "route=academic" in phase.detail


def test_intake_route_alias_uses_the_mapped_route_and_its_own_metadata(tmp_path: Path) -> None:
    """TRIANGULATE: route ``b`` maps to project, which never requires subject/teacher."""
    folder = tmp_path / "wf"
    _report(folder, route="b", subject=None, teacher=None)

    phase = doc_status._phase_intake(folder, _config(folder), None)

    assert phase.state == doc_status.DONE
    assert "route=project" in phase.detail


# ---------------------------------------------------------------------------
# 2.3 research
# ---------------------------------------------------------------------------


def test_research_evidence_matrix_present_is_done(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder)
    _evidence_matrix(folder)

    phase = doc_status._phase_research(folder, _config(folder), None)

    assert phase.state == doc_status.DONE
    assert "evidence-matrix.md" in phase.detail


def test_research_skipped_is_done(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder)
    _skip_research(folder)

    phase = doc_status._phase_research(folder, _config(folder), None)

    assert phase.state == doc_status.DONE
    assert "skipped" in phase.detail


def test_research_neither_matrix_nor_skip_is_pending(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder)

    phase = doc_status._phase_research(folder, _config(folder), None)

    assert phase.state == doc_status.PENDING
    assert phase.blocked_reason == ""


def test_research_skip_value_is_trimmed_and_case_insensitive(tmp_path: Path) -> None:
    """TRIANGULATE: ``research: '  SKIPPED  '`` still counts as skipped."""
    folder = tmp_path / "wf"
    _report(folder)
    _skip_research(folder, value="'  SKIPPED  '")

    phase = doc_status._phase_research(folder, _config(folder), None)

    assert phase.state == doc_status.DONE


# ---------------------------------------------------------------------------
# 2.5 preview
# ---------------------------------------------------------------------------


def test_preview_non_empty_is_done(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder)
    _preview(folder)

    phase = doc_status._phase_preview(folder, _config(folder), None)

    assert phase.state == doc_status.DONE


def test_preview_whitespace_only_is_pending(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder)
    _preview(folder, "   \n\t\n")

    phase = doc_status._phase_preview(folder, _config(folder), None)

    assert phase.state == doc_status.PENDING
    assert phase.blocked_reason == ""
    assert phase.detail == "preview.md empty"


def test_preview_missing_is_pending(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder)

    phase = doc_status._phase_preview(folder, _config(folder), None)

    assert phase.state == doc_status.PENDING
    assert phase.detail == "preview.md missing"


def test_preview_unreadable_is_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder = tmp_path / "wf"
    _report(folder)
    _preview(folder)
    original = Path.read_text

    def denied(self: Path, *args: object, **kwargs: object) -> str:
        if self.name == "preview.md":
            raise PermissionError("denied")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", denied)
    phase = doc_status._phase_preview(folder, _config(folder), None)

    assert phase.state == doc_status.BLOCKED
    assert phase.blocked_reason == "preview_unreadable"
    assert phase.state != doc_status.DONE
