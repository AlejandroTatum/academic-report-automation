"""Tests for the shared approval-marker contract in ``tools/approval_marker.py``.

``approval_state()`` is the single predicate behind both the routing layer
(``doc_status``) and the irreversible publication step (``publish_pdf``): the
routing layer reports it, the publisher fails closed on it. The marker binds
exactly one artifact -- the approved ``body.md`` bytes; any other key (a legacy
``preview_sha256`` included) is ignored data. Because a stateless tool can only
fail closed against disk, the predicate must be a pure read -- it never writes,
never creates a directory, and never raises for a bad marker. Every invalid
shape becomes ``malformed`` so the caller can name the offender instead of
crashing or guessing.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import approval_marker


def _write_body(folder: Path, text: str = "# Informe\n\nCuerpo.\n") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    body = folder / "body.md"
    body.write_text(text, encoding="utf-8")
    return body


def _write_preview(folder: Path, text: str = "# Content Preview: Informe\n\nCuerpo.\n") -> Path:
    """A preview.md the marker no longer binds; present only to prove it is ignored."""
    folder.mkdir(parents=True, exist_ok=True)
    preview = folder / "preview.md"
    preview.write_text(text, encoding="utf-8")
    return preview


def _write_marker(folder: Path, body: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    marker = folder / "approval.yml"
    marker.write_text(body, encoding="utf-8")
    return marker


def _marker_body(body: Path, *, body_sha: str | None = None) -> str:
    if body_sha is None:
        body_sha = hashlib.sha256(body.read_bytes()).hexdigest()
    return (
        "schema: academic.doc-approval/v1\n"
        f"body_sha256: {body_sha}\n"
        "approved_at: 2026-09-10T14:03:11Z\n"
        "approved_by: Alejandro\n"
    )


def _snapshot(folder: Path) -> list[tuple[str, int, bool]]:
    return sorted(
        (path.name, path.stat().st_size, path.is_dir()) for path in folder.iterdir()
    )


def test_approval_state_absent_current_stale_malformed(tmp_path: Path) -> None:
    """The four on-disk states, with no writes and no exceptions raised."""
    # absent — there is no marker at all
    empty = tmp_path / "empty"
    empty.mkdir()
    absent = approval_marker.approval_state(empty)
    assert absent.state == "absent"
    assert absent.reason == "approval_marker_absent"
    assert "approval.yml" in absent.detail
    assert absent.detail.isascii()

    # current — the marker hash equals the exact body.md bytes; no preview needed
    current_folder = tmp_path / "current"
    body = _write_body(current_folder)
    _write_marker(current_folder, _marker_body(body))
    current = approval_marker.approval_state(current_folder)
    assert current.state == "current"
    assert current.reason == ""
    assert current.detail == ""

    # current — a preview.md present and never hashed is still just data
    with_preview = tmp_path / "with-preview"
    with_body = _write_body(with_preview)
    _write_preview(with_preview)
    _write_marker(with_preview, _marker_body(with_body))
    assert approval_marker.approval_state(with_preview).state == "current"

    # stale — the body changed after the marker was written
    stale_folder = tmp_path / "stale"
    stale_body = _write_body(stale_folder, "# Informe\n\noriginal\n")
    _write_marker(stale_folder, _marker_body(stale_body))
    stale_body.write_text("# Informe\n\neditado\n", encoding="utf-8")
    stale = approval_marker.approval_state(stale_folder)
    assert stale.state == "stale"
    assert stale.reason == "approval_marker_stale"
    assert "body.md" in stale.detail
    assert stale.detail.isascii()

    # malformed — every invalid shape names the offending file or key
    good_body = "# Informe\n\nCuerpo.\n"
    good_body_sha = hashlib.sha256(good_body.encode("utf-8")).hexdigest()
    approved_at = "2026-09-10T14:03:11Z"

    def case(name: str) -> Path:
        folder = tmp_path / name
        _write_body(folder, good_body)
        return folder

    bad_yaml = case("bad-yaml")
    _write_marker(bad_yaml, "body_sha256: [unclosed\napproved_at: x\n")

    missing_body_sha = case("missing-body-sha")
    _write_marker(
        missing_body_sha,
        f"approved_at: {approved_at}\napproved_by: Alejandro\n",
    )

    missing_at = case("missing-at")
    _write_marker(
        missing_at,
        f"body_sha256: {good_body_sha}\napproved_by: Alejandro\n",
    )

    missing_by = case("missing-by")
    _write_marker(
        missing_by,
        f"body_sha256: {good_body_sha}\napproved_at: {approved_at}\n",
    )

    blank_by = case("blank-by")
    _write_marker(
        blank_by,
        f"body_sha256: {good_body_sha}\napproved_at: {approved_at}\napproved_by: \"   \"\n",
    )

    no_body = tmp_path / "no-body"
    no_body.mkdir()
    _write_marker(
        no_body,
        f"body_sha256: {good_body_sha}\napproved_at: {approved_at}\napproved_by: Alejandro\n",
    )

    expectations = [
        (bad_yaml, "approval.yml"),
        (missing_body_sha, "body_sha256"),
        (missing_at, "approved_at"),
        (missing_by, "approved_by"),
        (blank_by, "approved_by"),
        (no_body, "body.md"),
    ]
    for folder, token in expectations:
        state = approval_marker.approval_state(folder)
        assert state.state == "malformed", f"{folder.name}: {state}"
        assert state.reason == "approval_marker_malformed", folder.name
        assert token in state.detail, f"{folder.name}: {state.detail!r}"
        assert state.detail.isascii(), folder.name


def test_extra_preview_sha256_key_is_ignored(tmp_path: Path) -> None:
    """A marker still carrying a legacy preview_sha256 key is accepted unchanged."""
    folder = tmp_path / "legacy"
    body = _write_body(folder)
    _write_preview(folder)
    legacy = _marker_body(body) + "preview_sha256: 0000000000000000\n"
    _write_marker(folder, legacy)

    state = approval_marker.approval_state(folder)

    assert state.state == "current"
    assert state.reason == ""


def test_preview_edited_after_approval_stays_current(tmp_path: Path) -> None:
    """TRIANGULATE: only body_sha256 is checked; a preview edit is not an approval event."""
    folder = tmp_path / "preview-edit"
    body = _write_body(folder)
    _write_preview(folder)
    _write_marker(folder, _marker_body(body))
    _write_preview(folder, "# Content Preview: edited\n")

    assert approval_marker.approval_state(folder).state == "current"


def test_sha256_file_is_the_canonical_hash(tmp_path: Path) -> None:
    """The shared helper hashes raw bytes exactly like hashlib does."""
    payload = b"%PDF-1.7\nvalidated content\n" * 3
    target = tmp_path / "validated.pdf"
    target.write_bytes(payload)

    assert approval_marker.sha256_file(target) == hashlib.sha256(payload).hexdigest()


def test_approval_state_is_read_only_and_never_raises(tmp_path: Path) -> None:
    """A bad marker is data, not a crash, and nothing on disk is created."""
    folder = tmp_path / "read-only"
    _write_body(folder)
    _write_marker(folder, "body_sha256: [unclosed\n")
    before = _snapshot(folder)

    for _ in range(2):
        state = approval_marker.approval_state(folder)
        assert state.state == "malformed"
        assert _snapshot(folder) == before

    missing = tmp_path / "missing"
    assert approval_marker.approval_state(missing).state == "absent"
    assert not missing.exists()


def test_marker_constants_are_declared() -> None:
    """The marker contract is a stable, importable surface for both consumers."""
    assert approval_marker.BODY_NAME == "body.md"
    assert approval_marker.MARKER_NAME == "approval.yml"
    assert approval_marker.MARKER_SCHEMA == "academic.doc-approval/v1"
    assert approval_marker.REQUIRED_KEYS == (
        "body_sha256",
        "approved_at",
        "approved_by",
    )
    assert approval_marker.bound_file_names() == ("body.md",)
