"""Approval-phase tests for ``tools/doc_status.py`` (slice 2b-i).

Slice 2b-i ships the approval derivation. Like the 2a suite, these tests call the
handler directly and assert its raw ``done|pending|blocked`` token, detail and
blocked reason; ``derive``, the renderers and the CLI are slice 2c, and the
generate/validate/deliver derivations are slices 2b-ii/2b-iii. The approval handler
maps ``tools/approval_marker.py`` onto a phase state, so these tests drive that
predicate through its four disk shapes (absent, current, stale, malformed).
Artifact shapes come from ``tools/conftest.py``.
"""
from __future__ import annotations

from pathlib import Path

import doc_status
from conftest import (
    _approval,
    _body,
    _config,
    _marker_text,
    _preview,
    _report,
)


def test_approval_absent_is_pending_not_blocked(tmp_path: Path) -> None:
    """A missing marker is ordinary progress, so later phases wait, not abort."""
    folder = tmp_path / "wf"
    _report(folder)
    _preview(folder)

    phase = doc_status._phase_approval(folder, _config(folder), None)

    assert phase.name == "approval"
    assert phase.state == doc_status.PENDING
    assert phase.blocked_reason == ""
    assert "approval.yml" in phase.detail
    assert not (folder / "approval.yml").exists()


def test_approval_current_is_done(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder)
    _approval(folder)

    phase = doc_status._phase_approval(folder, _config(folder), None)

    assert phase.state == doc_status.DONE
    assert phase.blocked_reason == ""
    assert phase.state != doc_status.BLOCKED


def test_approval_stale_hash_is_blocked_with_stale_reason(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder)
    _approval(folder, preview_sha256="0" * 64)

    phase = doc_status._phase_approval(folder, _config(folder), None)

    assert phase.state == doc_status.BLOCKED
    assert phase.blocked_reason == "approval_marker_stale"
    assert "approval.yml" in phase.detail
    assert phase.state != doc_status.DONE


def test_approval_preview_edited_after_approval_is_blocked(tmp_path: Path) -> None:
    """TRIANGULATE: editing the preview after approval invalidates the marker."""
    folder = tmp_path / "wf"
    _report(folder)
    _approval(folder)
    _preview(folder, "# Content Preview: Informe\n\nOtro cuerpo.\n")

    phase = doc_status._phase_approval(folder, _config(folder), None)

    assert phase.state == doc_status.BLOCKED
    assert phase.blocked_reason == "approval_marker_stale"


def test_approval_body_edited_after_approval_is_blocked(tmp_path: Path) -> None:
    """TRIANGULATE: editing body.md after approval invalidates the marker."""
    folder = tmp_path / "wf"
    _report(folder)
    _approval(folder)
    _body(folder, "# Informe\n\nOtro cuerpo.\n")

    phase = doc_status._phase_approval(folder, _config(folder), None)

    assert phase.state == doc_status.BLOCKED
    assert phase.blocked_reason == "approval_marker_stale"


def test_approval_marker_without_body_hash_is_malformed(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder)
    _approval(folder, drop=("body_sha256",))

    phase = doc_status._phase_approval(folder, _config(folder), None)

    assert phase.state == doc_status.BLOCKED
    assert phase.blocked_reason == "approval_marker_malformed"
    assert phase.state != doc_status.DONE


def test_approval_body_missing_with_marker_present_is_malformed(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder)
    _approval(folder)
    (folder / "body.md").unlink()

    phase = doc_status._phase_approval(folder, _config(folder), None)

    assert phase.state == doc_status.BLOCKED
    assert phase.blocked_reason == "approval_marker_malformed"


def test_approval_blank_required_key_is_malformed(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder)
    _approval(folder, approved_by="   ")

    phase = doc_status._phase_approval(folder, _config(folder), None)

    assert phase.state == doc_status.BLOCKED
    assert phase.blocked_reason == "approval_marker_malformed"
    assert phase.state != doc_status.DONE


def test_approval_unparsable_marker_is_malformed_not_absent(tmp_path: Path) -> None:
    """TRIANGULATE: a bad marker is named, never silently treated as absent."""
    folder = tmp_path / "wf"
    _report(folder)
    _preview(folder)
    _marker_text(folder, "preview_sha256: [unclosed\n")

    phase = doc_status._phase_approval(folder, _config(folder), None)

    assert phase.state == doc_status.BLOCKED
    assert phase.blocked_reason == "approval_marker_malformed"


def test_approval_derivation_never_repairs_the_marker(tmp_path: Path) -> None:
    """A stale or malformed marker is data the tool reports, never rewrites."""
    folder = tmp_path / "wf"
    _report(folder)
    marker = _approval(folder, preview_sha256="0" * 64)
    before = marker.read_bytes()

    doc_status._phase_approval(folder, _config(folder), None)

    assert marker.read_bytes() == before
