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


def test_failed_verify_guidance_requires_user_orders_and_reapproval(tmp_path: Path) -> None:
    import doc_status
    from conftest import _report, _body, _sources_bib, _rubric, _approval, _content_check

    folder = tmp_path / "wf"
    _report(folder)
    _sources_bib(folder)
    _rubric(folder)
    _body(folder)
    _approval(folder)
    _content_check(folder, result="fail", criteria=[{"id": "objetivo", "status": "flojo"}, {"id": "metodologia", "status": "cumple"}])
    status = doc_status.derive(folder)
    assert "user's literal edit orders" in status.gate
    assert "re-approve" in status.gate
    assert "run the check" not in status.gate


import doc_status
from conftest import (
    _approval,
    _body,
    _config,
    _marker_text,
    _report,
    _sources_bib,
)


def test_approval_absent_is_pending_not_blocked(tmp_path: Path) -> None:
    """A missing marker is ordinary progress, so later phases wait, not abort."""
    folder = tmp_path / "wf"
    _report(folder)

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
    # The marker binds exactly one artifact, body.md (approval_marker.py
    # REQUIRED_KEYS); the detail must name it and nothing else.
    assert "body.md" in phase.detail
    assert "preview.md" not in phase.detail


def test_approval_body_hash_mismatch_is_pending_for_reapproval(tmp_path: Path) -> None:
    """A body edited after approval routes back to approval, never blocks the route."""
    folder = tmp_path / "wf"
    _report(folder)
    _approval(folder, body_sha256="0" * 64)

    phase = doc_status._phase_approval(folder, _config(folder), None)

    assert phase.state == doc_status.PENDING
    assert phase.blocked_reason == ""
    assert "body.md" in phase.detail
    assert "re-approve" in phase.detail
    assert phase.state != doc_status.DONE


def test_approval_unrelated_edit_after_approval_stays_done(tmp_path: Path) -> None:
    """TRIANGULATE: the marker binds only body.md; editing an unrelated artifact
    (sources.bib) is not an approval event, so the phase stays done."""
    folder = tmp_path / "wf"
    _report(folder)
    _approval(folder)
    _sources_bib(folder, count=6)

    phase = doc_status._phase_approval(folder, _config(folder), None)

    assert phase.state == doc_status.DONE
    assert phase.blocked_reason == ""


def test_approval_body_edited_after_approval_is_pending(tmp_path: Path) -> None:
    """TRIANGULATE: editing body.md after approval sends the route back to approval."""
    folder = tmp_path / "wf"
    _report(folder)
    _approval(folder)
    _body(folder, "# Informe\n\nOtro cuerpo.\n")

    phase = doc_status._phase_approval(folder, _config(folder), None)

    assert phase.state == doc_status.PENDING
    assert phase.blocked_reason == ""
    assert "re-approve" in phase.detail


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
    _marker_text(folder, "body_sha256: [unclosed\n")

    phase = doc_status._phase_approval(folder, _config(folder), None)

    assert phase.state == doc_status.BLOCKED
    assert phase.blocked_reason == "approval_marker_malformed"


def test_approval_derivation_never_repairs_the_marker(tmp_path: Path) -> None:
    """A stale or malformed marker is data the tool reports, never rewrites."""
    folder = tmp_path / "wf"
    _report(folder)
    marker = _approval(folder, body_sha256="0" * 64)
    before = marker.read_bytes()

    doc_status._phase_approval(folder, _config(folder), None)

    assert marker.read_bytes() == before
