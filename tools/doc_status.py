#!/usr/bin/env python3
"""Derive the document-workflow phases from on-disk artifacts (read-only).

Slice 2b-ii of the status layer: the phase vocabulary, the two value dataclasses and
the intake/research/preview/approval/generate derivations. Each function answers for
exactly one phase and returns a raw ``done|pending|blocked`` token; there is no
composition, renderer or CLI yet, so no function here has to know what follows the
phase it answers for. The route projection (``current``/``next``/``gate``) and the
validate/deliver phases arrive in slices 2b-iii/2c.

Approval delegates to ``approval_marker.approval_state`` -- the same predicate
``publish_validated_pdf`` enforces -- so routing and the irreversible publisher
cannot disagree about which marker is current.

The module is pure and read-only. ``_phase_intake`` builds ``ReportConfig``
directly instead of calling ``load_report_config``, which raises ``SystemExit``
on an unknown route -- a status tool reports what it finds, it never exits.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from approval_marker import approval_state
from report_config import ReportConfig

PHASES = ("intake", "research", "preview", "approval", "generate", "validate", "deliver")
DONE, CURRENT, PENDING, BLOCKED = "done", "current", "pending", "blocked"
STATE_TOKENS = (DONE, CURRENT, PENDING, BLOCKED)


@dataclass(frozen=True)
class PhaseState:
    """One phase of the route: a ``done|pending|blocked`` token plus its evidence."""

    name: str
    state: str
    detail: str = ""
    blocked_reason: str = ""


@dataclass(frozen=True)
class DocStatus:
    """The whole route derived once from disk, ready to render or serialize."""

    work_folder: Path
    phases: tuple[PhaseState, ...]
    current: str
    next_token: str
    gate: str
    blocked_reasons: tuple[str, ...]


def _read_text(path: Path) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return None


def _phase_intake(folder: Path, config: ReportConfig, _documents_root: Path | None) -> PhaseState:
    if not (folder / "report.yml").is_file():
        return PhaseState("intake", PENDING, "report.yml missing")
    if not config.route_is_known:
        return PhaseState("intake", BLOCKED, f"route={config.route} not recognized", "unknown_route")
    missing = [key for key in config.required_metadata if not config.metadata.get(key)]
    if missing:
        return PhaseState("intake", PENDING, f"missing metadata: {', '.join(missing)}")
    return PhaseState("intake", DONE, f"route={config.route}, metadata complete")


def _phase_research(folder: Path, config: ReportConfig, _documents_root: Path | None) -> PhaseState:
    matrix = _read_text(folder / "research" / "evidence-matrix.md")
    if matrix is not None and matrix.strip():
        return PhaseState("research", DONE, "research/evidence-matrix.md present")
    if str(config.raw.get("research") or "").strip().lower() == "skipped":
        return PhaseState("research", DONE, "skipped in report.yml")
    return PhaseState("research", PENDING, "no evidence matrix and research not skipped")


def _phase_preview(folder: Path, _config: ReportConfig, _documents_root: Path | None) -> PhaseState:
    preview = folder / "preview.md"
    if not preview.is_file():
        return PhaseState("preview", PENDING, "preview.md missing")
    text = _read_text(preview)
    if text is None:
        return PhaseState("preview", BLOCKED, "preview.md unreadable", "preview_unreadable")
    if not text.strip():
        return PhaseState("preview", PENDING, "preview.md empty")
    return PhaseState("preview", DONE, "preview.md present")


def _phase_approval(folder: Path, _config: ReportConfig, _documents_root: Path | None) -> PhaseState:
    """Map the shared approval predicate onto one phase state.

    Only ``current`` is ``done``: an absent marker stays ``pending`` so the route
    waits at approval, and a stale or malformed marker is ``blocked`` with the
    predicate's own bounded reason. The marker is never written here.
    """
    state = approval_state(folder)
    if state.state == "current":
        return PhaseState("approval", DONE, "approval.yml matches preview.md")
    if state.state == "absent":
        return PhaseState("approval", PENDING, state.detail)
    return PhaseState("approval", BLOCKED, state.detail, state.reason)


def _phase_generate(folder: Path, config: ReportConfig, _documents_root: Path | None) -> PhaseState:
    """Report whether the final PDF is the one the approval marker authorized.

    Bounded to the mtime comparison the design specifies: the artifact is ``done``
    when ``config.pdf_path`` exists and is not older than ``approval.yml``. A missing
    PDF, a missing marker, or a PDF that predates the marker is ordinary progress --
    generate is never ``blocked``; a stale build simply has to be redone. Only the
    timestamps are read: nothing is written, hashed or repaired here.
    """
    pdf = config.pdf_path
    if not pdf.is_file():
        return PhaseState("generate", PENDING, "final PDF missing")
    marker = folder / "approval.yml"
    if not marker.is_file():
        return PhaseState("generate", PENDING, "approval.yml missing")
    if pdf.stat().st_mtime >= marker.stat().st_mtime:
        return PhaseState("generate", DONE, f"final PDF {pdf.name} is not older than approval.yml")
    return PhaseState("generate", PENDING, f"final PDF {pdf.name} older than approval.yml")
