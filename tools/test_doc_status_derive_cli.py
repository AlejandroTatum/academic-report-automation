"""Derive/CLI tests for ``tools/doc_status.py`` (slice 2c-i).

Slice 2c-i ships the composition layer. ``derive()`` runs every phase handler
once, wraps an unexpected exception as ``blocked`` with a reason -- never
``done`` -- pins every later phase to ``pending``, and projects the first
incomplete phase to ``current``. ``main(argv)`` resolves its single work-folder
argument: exit 2 with a message for a missing, non-directory or unreadable
folder (creating nothing), exit 0 for any derivable folder because a blocked
phase is data, not a process failure. The renderers are slice 2c-ii, so no test
here asserts the human/machine block. Artifact shapes come from
``tools/conftest.py``.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import doc_status
from conftest import _approval, _pdf, _preview, _report, _skip_research


def _snapshot(folder: Path) -> list[tuple[str, str, int, str]]:
    """Record every entry under ``folder`` as (path, kind, size, content hash)."""
    if not folder.exists():
        return []
    entries: list[tuple[str, str, int, str]] = []
    for path in sorted(folder.rglob("*")):
        relative = str(path.relative_to(folder))
        if path.is_dir():
            entries.append((relative, "dir", 0, ""))
        else:
            data = path.read_bytes()
            entries.append((relative, "file", len(data), hashlib.sha256(data).hexdigest()))
    return entries


def _working_folder(folder: Path) -> Path:
    """Build a folder that reaches the approval phase: report, research, preview."""
    _report(folder)
    _skip_research(folder)
    _preview(folder)
    return folder


# ---------------------------------------------------------------------------
# 2.16 derive composition and purity
# ---------------------------------------------------------------------------


def test_derive_purity_and_error_wrapping(tmp_path: Path, monkeypatch) -> None:
    """Acceptance for 2.16: derive writes nothing and a crash is blocked data."""
    folder = _working_folder(tmp_path / "wf")
    _pdf(folder)
    documents_root = tmp_path / "Documents"
    before = _snapshot(tmp_path)

    def _boom(*_args: object, **_kwargs: object) -> doc_status.PhaseState:
        raise RuntimeError("boom")

    monkeypatch.setattr(doc_status, "_phase_approval", _boom)

    status = doc_status.derive(folder, documents_root=documents_root)

    states = {phase.name: phase.state for phase in status.phases}
    assert states["approval"] == doc_status.BLOCKED
    assert states["approval"] != doc_status.DONE
    assert states["generate"] == doc_status.PENDING
    assert states["deliver"] == doc_status.PENDING
    assert _snapshot(tmp_path) == before
    assert not documents_root.exists()


def test_derive_composes_every_phase_and_leaves_the_folder_byte_identical(tmp_path: Path) -> None:
    """One derive() call answers all seven phases without writing anywhere."""
    folder = _working_folder(tmp_path / "wf")
    documents_root = tmp_path / "Documents"
    before = _snapshot(tmp_path)

    status = doc_status.derive(folder, documents_root=documents_root)

    assert [phase.name for phase in status.phases] == list(doc_status.PHASES)
    assert status.work_folder == folder
    assert all(phase.state in doc_status.STATE_TOKENS for phase in status.phases)
    assert _snapshot(tmp_path) == before
    assert not documents_root.exists()


def test_derive_fresh_folder_focus_is_intake_and_later_phases_pending(tmp_path: Path) -> None:
    """TRIANGULATE: with no artifacts at all the route stops at intake."""
    status = doc_status.derive(tmp_path / "fresh")

    assert status.current == "intake"
    assert status.next_token == "intake"
    assert status.phases[0].state == doc_status.CURRENT
    assert all(phase.state == doc_status.PENDING for phase in status.phases[1:])


def test_derive_projects_first_incomplete_phase_as_current(tmp_path: Path) -> None:
    """A folder with intake done focuses on research and leaves the rest pending."""
    folder = tmp_path / "wf"
    _report(folder)

    status = doc_status.derive(folder)

    states = {phase.name: phase.state for phase in status.phases}
    assert states["intake"] == doc_status.DONE
    assert status.current == "research"
    assert status.next_token == "research"
    assert states["research"] == doc_status.CURRENT
    assert all(states[name] == doc_status.PENDING for name in doc_status.PHASES[2:])
    assert status.gate == "research pending"


def test_derive_keeps_focus_on_blocked_phase_and_forces_later_phases_pending(
    tmp_path: Path,
) -> None:
    """A stale approval stops the route even when a newer PDF already exists."""
    folder = _working_folder(tmp_path / "wf")
    _approval(folder, preview_sha256="0" * 64)
    _pdf(folder)

    status = doc_status.derive(folder)

    states = {phase.name: phase.state for phase in status.phases}
    assert states["approval"] == doc_status.BLOCKED
    assert "approval_marker_stale" in status.blocked_reasons
    assert status.current == "approval"
    assert status.next_token == "approval"
    assert status.gate == "approval blocked"
    assert states["generate"] != doc_status.DONE
    assert all(
        states[name] == doc_status.PENDING for name in ("generate", "validate", "deliver")
    )


def test_derive_wraps_unexpected_exception_as_blocked_never_done(
    tmp_path: Path, monkeypatch
) -> None:
    """A crashing phase handler becomes blocked data; later phases stay pending."""
    folder = _working_folder(tmp_path / "wf")
    _pdf(folder)

    def _boom(*_args: object, **_kwargs: object) -> doc_status.PhaseState:
        raise RuntimeError("boom")

    monkeypatch.setattr(doc_status, "_phase_preview", _boom)

    status = doc_status.derive(folder)

    preview = next(phase for phase in status.phases if phase.name == "preview")
    states = {phase.name: phase.state for phase in status.phases}
    assert preview.state == doc_status.BLOCKED
    assert preview.state != doc_status.DONE
    assert preview.blocked_reason == "derivation_error"
    assert "boom" in preview.detail
    assert status.current == "preview"
    assert status.next_token == "preview"
    assert all(
        states[name] == doc_status.PENDING for name in ("approval", "generate", "validate", "deliver")
    )


def test_derive_wraps_exception_in_the_first_phase_and_locks_the_route(
    tmp_path: Path, monkeypatch
) -> None:
    """TRIANGULATE: a crash at the head of the route is still blocked data."""
    folder = _working_folder(tmp_path / "wf")

    def _boom(*_args: object, **_kwargs: object) -> doc_status.PhaseState:
        raise ValueError("no config")

    monkeypatch.setattr(doc_status, "_phase_intake", _boom)

    status = doc_status.derive(folder)

    states = {phase.name: phase.state for phase in status.phases}
    assert states["intake"] == doc_status.BLOCKED
    assert status.current == "intake"
    assert status.next_token == "intake"
    assert status.gate == "intake blocked"
    assert all(states[name] == doc_status.PENDING for name in doc_status.PHASES[1:])


# ---------------------------------------------------------------------------
# 2.17 CLI argument/path validation
# ---------------------------------------------------------------------------


def test_main_missing_argument_exits_two_with_message(tmp_path: Path, capsys) -> None:
    """No work-folder argument is a usage error, not a derivation."""
    before = _snapshot(tmp_path)

    rc = doc_status.main([])

    captured = capsys.readouterr()
    assert rc == 2
    assert captured.err.strip() != ""
    assert captured.out == ""
    assert _snapshot(tmp_path) == before


def test_main_missing_folder_exits_two_and_creates_nothing(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "does-not-exist"
    before = _snapshot(tmp_path)

    rc = doc_status.main([str(missing)])

    captured = capsys.readouterr()
    assert rc == 2
    assert str(missing) in captured.err
    assert not missing.exists()
    assert _snapshot(tmp_path) == before


def test_main_file_instead_of_directory_exits_two_and_creates_nothing(
    tmp_path: Path, capsys
) -> None:
    not_a_folder = tmp_path / "report.yml"
    not_a_folder.write_text("type: ensayo\n", encoding="utf-8")
    before = _snapshot(tmp_path)

    rc = doc_status.main([str(not_a_folder)])

    captured = capsys.readouterr()
    assert rc == 2
    assert str(not_a_folder) in captured.err
    assert _snapshot(tmp_path) == before


def test_main_unreadable_folder_exits_two(tmp_path: Path, monkeypatch, capsys) -> None:
    folder = tmp_path / "wf"
    folder.mkdir()
    before = _snapshot(tmp_path)
    monkeypatch.setattr(doc_status.os, "access", lambda *_args, **_kwargs: False)

    rc = doc_status.main([str(folder)])

    captured = capsys.readouterr()
    assert rc == 2
    assert str(folder) in captured.err
    assert _snapshot(tmp_path) == before


def test_main_derivable_folder_exits_zero_and_creates_nothing(tmp_path: Path, capsys) -> None:
    folder = _working_folder(tmp_path / "wf")
    before = _snapshot(tmp_path)

    rc = doc_status.main([str(folder)])

    captured = capsys.readouterr()
    assert rc == 0
    assert captured.err == ""
    assert folder.name in captured.out
    assert _snapshot(tmp_path) == before


def test_main_blocked_phase_still_exits_zero(tmp_path: Path, capsys) -> None:
    """TRIANGULATE: a blocked phase is data, not a process failure."""
    folder = _working_folder(tmp_path / "wf")
    _approval(folder, preview_sha256="0" * 64)

    rc = doc_status.main([str(folder)])

    captured = capsys.readouterr()
    assert rc == 0
    assert "approval" in captured.out
