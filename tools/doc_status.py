#!/usr/bin/env python3
"""Derive the document-workflow phases from on-disk artifacts (read-only).

Slice 2c-i of the status layer: the phase vocabulary, the two value dataclasses,
the seven per-phase derivations, and the ``derive``/``main`` composition on top of
them. Each ``_phase_*`` function answers for exactly one phase and returns a raw
``done|pending|blocked`` token; ``derive`` runs them in order, wraps an unexpected
exception as ``blocked``, locks every phase after the first incomplete one to
``pending``, and projects the route (``current``/``next``/``gate``). ``render_human``
and ``render_machine`` project that value: the portable human block and the
``academic.doc-status/v1`` markdown shape. ``main`` renders both on every invocation.

Approval delegates to ``approval_marker.approval_state`` -- the same predicate
``publish_validated_pdf`` enforces -- so routing and the irreversible publisher
cannot disagree about which marker is current.

The module is pure and read-only. ``_phase_intake`` builds ``ReportConfig``
directly instead of calling ``load_report_config``, which raises ``SystemExit``
on an unknown route -- a status tool reports what it finds, it never exits.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path

from approval_marker import approval_state, sha256_file
from report_config import ReportConfig, read_yaml

PHASES = ("intake", "research", "preview", "approval", "generate", "validate", "deliver")
DONE, CURRENT, PENDING, BLOCKED = "done", "current", "pending", "blocked"
STATE_TOKENS = (DONE, CURRENT, PENDING, BLOCKED)
SCHEMA_NAME = "academic.doc-status"
SCHEMA_VERSION = 1

# One action sentence per phase: the closing ``**Next**`` line for the routed token,
# and the front-loaded gate's consequence for the phase that still waits.
_GUIDANCE = {
    "intake": "complete reports/{wf}/report.yml, then re-run doc_status",
    "research": (
        "write reports/{wf}/research/evidence-matrix.md or record research: skipped, "
        "then re-run doc_status"
    ),
    "preview": "draft reports/{wf}/preview.md, then re-run doc_status",
    "approval": "generation runs only after you approve reports/{wf}/preview.md",
    "generate": "build the final PDF, then re-run doc_status",
    "validate": "record reports/{wf}/validation.yml for the final PDF, then re-run doc_status",
    "deliver": "publish the validated PDF, then re-run doc_status",
}


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


def _phase_validate(folder: Path, config: ReportConfig, _documents_root: Path | None) -> PhaseState:
    """Map the validation receipt onto one phase state.

    ``done`` requires both halves of the design's predicate: the receipt records
    ``result: pass`` and its ``artifact_sha256`` equals the final PDF's bytes. A
    recorded ``result: fail`` is the only ``blocked`` outcome the design names; a
    missing, unreadable or mismatched receipt returns to ``pending`` so validation
    simply reruns. The receipt is never written or repaired here.
    """
    receipt = folder / "validation.yml"
    if not receipt.is_file():
        return PhaseState("validate", PENDING, "validation.yml missing")
    try:
        data = read_yaml(receipt)
    except Exception:
        return PhaseState("validate", PENDING, "validation.yml unreadable")
    result = str(data.get("result") or "").strip().lower()
    if result == "fail":
        return PhaseState("validate", BLOCKED, "validation.yml recorded result: fail", "validation_failed")
    pdf = config.pdf_path
    if not pdf.is_file():
        return PhaseState("validate", PENDING, "final PDF missing")
    try:
        artifact_hash = sha256_file(pdf)
    except OSError:
        return PhaseState("validate", PENDING, "final PDF unreadable")
    if result != "pass":
        return PhaseState("validate", PENDING, "validation.yml result is not pass")
    if str(data.get("artifact_sha256") or "").strip().lower() != artifact_hash:
        return PhaseState("validate", PENDING, "validation.yml artifact_sha256 does not match final PDF")
    return PhaseState("validate", DONE, f"validation.yml passes for {pdf.name}")


def _phase_deliver(folder: Path, config: ReportConfig, documents_root: Path | None) -> PhaseState:
    """Report whether the final PDF is the one already delivered to Documents.

    ``done`` when a ``<slug>-vNNN.pdf`` under
    ``<documents_root>/<category>/<slug>/`` hashes equal to the final PDF
    (published or a hash-matched reuse); ``pending`` otherwise. Delivery is never
    ``blocked``: the design gives it no failure state, so an absent copy -- or one
    made from other bytes -- is ordinary progress, not an abort.
    """
    pdf = config.pdf_path
    if not pdf.is_file():
        return PhaseState("deliver", PENDING, "final PDF missing")
    try:
        category = config.publication_category
        slug = config.document_slug
    except (KeyError, ValueError):
        return PhaseState("deliver", PENDING, "publication identity unavailable")
    root = Path.home() / "Documents" if documents_root is None else Path(documents_root)
    delivery = root / category / slug
    if not delivery.is_dir():
        return PhaseState("deliver", PENDING, f"no published {slug}-vNNN.pdf")
    try:
        source_hash = sha256_file(pdf)
    except OSError:
        return PhaseState("deliver", PENDING, "final PDF unreadable")
    pattern = re.compile(rf"^{re.escape(slug)}-v(\d{{3,}})\.pdf$")
    for candidate in sorted(delivery.iterdir()):
        if not candidate.is_file() or not pattern.match(candidate.name):
            continue
        try:
            if sha256_file(candidate) == source_hash:
                return PhaseState("deliver", DONE, f"{candidate.name} published and hash-matched")
        except OSError:
            continue
    return PhaseState("deliver", PENDING, f"no published {slug}-vNNN.pdf matches the final PDF")


def derive(folder: Path, *, documents_root: Path | None = None) -> DocStatus:
    """Compose every phase derivation into one route projection.

    The handlers run in ``PHASES`` order and each one is wrapped: an unexpected
    exception becomes that phase's ``blocked`` state with a ``derivation_error``
    reason, so a status call never crashes and never claims a phase ``done`` by
    accident. Once a phase is not ``done`` the route locks: every later phase is
    reported ``pending`` regardless of the artifacts on disk, because nothing
    downstream has been authorized. The first incomplete phase becomes
    ``current`` and is also the ``next`` token; an all-done route reports
    ``done``. The whole derivation is read-only.
    """
    folder = Path(folder)
    config = ReportConfig(folder=folder, raw=read_yaml(folder / "report.yml"))
    handlers = (
        _phase_intake,
        _phase_research,
        _phase_preview,
        _phase_approval,
        _phase_generate,
        _phase_validate,
        _phase_deliver,
    )
    phases: list[PhaseState] = []
    locked = False
    for name, handler in zip(PHASES, handlers):
        try:
            phase = handler(folder, config, documents_root)
        except Exception as exc:  # one phase must never abort the whole status
            phase = PhaseState(name, BLOCKED, f"derivation error: {exc}", "derivation_error")
        if locked:
            phase = PhaseState(name, PENDING, "waiting for an earlier phase")
        elif phase.state != DONE:
            locked = True
        phases.append(phase)

    focus = next((phase for phase in phases if phase.state != DONE), None)
    if focus is None:
        current, next_token, gate = DONE, DONE, ""
    else:
        current = next_token = focus.name
        gate = f"{focus.name} {focus.state}"
        if focus.state == PENDING:
            phases[PHASES.index(focus.name)] = replace(focus, state=CURRENT)
    blocked_reasons = tuple(
        phase.blocked_reason for phase in phases if phase.state == BLOCKED and phase.blocked_reason
    )
    return DocStatus(folder, tuple(phases), current, next_token, gate, blocked_reasons)


def _guidance(phase_name: str, work_folder: Path) -> str:
    """Action sentence for ``phase_name``, bound to the real work-folder name."""
    template = _GUIDANCE.get(phase_name)
    return "" if template is None else template.format(wf=Path(work_folder).name)


def _payload(status: DocStatus) -> dict[str, object]:
    """The ``academic.doc-status/v1`` JSON projection of a derived ``DocStatus``."""
    return {
        "schemaName": SCHEMA_NAME,
        "schemaVersion": SCHEMA_VERSION,
        "workFolder": str(status.work_folder),
        "phases": [
            {"name": p.name, "state": p.state, "detail": p.detail, "blockedReason": p.blocked_reason}
            for p in status.phases
        ],
        "current": status.current,
        "next": status.next_token,
        "gate": status.gate,
        "blockedReasons": list(status.blocked_reasons),
    }


def _route(status: DocStatus) -> str:
    """The one route line, always bracketing exactly the current token."""
    names = [phase.name for phase in status.phases]
    if status.current in names:
        tokens = [f"[{name}]" if name == status.current else name for name in names]
    else:  # route complete: the bracket advances past the last phase to `done`
        tokens = [*names, f"[{status.current}]"]
    return " > ".join(tokens)


def _gate(status: DocStatus) -> str:
    """Front-loaded gate text: approval until it passes, else the waiting focus."""
    focus = next((phase for phase in status.phases if phase.state != DONE), None)
    if focus is None:
        return ""
    approval = next((phase for phase in status.phases if phase.name == "approval"), None)
    gate_phase = approval if approval is not None and approval.state != DONE else focus
    return f"{gate_phase.name} {gate_phase.state} - {_guidance(gate_phase.name, status.work_folder)}"


def _summary_lines(status: DocStatus) -> list[str]:
    """Flat summary bullets; ``pending`` phases stay terse because they only wait."""
    return [
        f"- {phase.name}: {phase.state}"
        + (f" - {phase.detail}" if phase.state != PENDING and phase.detail else "")
        for phase in status.phases
    ]


def render_human(status: DocStatus) -> str:
    """Render the portable human block: optional gate, one bracketed route line,
    a flat ``**Summary**``, and a closing ``**Next**`` -- ASCII only, no tables."""
    lines: list[str] = []
    gate = _gate(status)
    if gate:
        lines.append(f"**Gate**: {gate}")
    lines.append(f"Route: {_route(status)}")
    lines.extend(["", "**Summary**", *_summary_lines(status), ""])
    next_line = f"**Next**: {status.next_token}"
    if status.next_token in PHASES:
        next_line += f" - {_guidance(status.next_token, status.work_folder)}"
    lines.append(next_line)
    return "\n".join(lines) + "\n"


def render_machine(status: DocStatus) -> str:
    """Render the ``academic.doc-status/v1`` machine block (sdd-status shape)."""
    payload = _payload(status)
    reasons = [f"- {reason}" for reason in status.blocked_reasons] or ["- none"]
    lines = [
        "## Document Workflow Status",
        "",
        f"schema: {SCHEMA_NAME}/v{SCHEMA_VERSION}",
        f"next: {status.next_token}",
        "",
        "### Summary",
        *[f"- {phase.name}: {phase.state}" for phase in status.phases],
        "",
        "### Blocked Reasons",
        *reasons,
        "",
        "### JSON",
        "```json",
        json.dumps(payload, indent=2),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _is_readable_dir(folder: Path) -> bool:
    """True when ``folder`` is an existing, listable directory."""
    try:
        return folder.is_dir() and os.access(folder, os.R_OK | os.X_OK)
    except OSError:
        return False


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: ``python tools/doc_status.py <work-folder> [--json]``.

    Exit 2 for a missing, non-directory or unreadable folder (creating nothing); exit
    0 for any derivable folder. Both blocks render every time: human then machine on
    stdout, and under ``--json`` machine on stdout with human on stderr.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in args
    positional = [arg for arg in args if arg != "--json"]
    if len(positional) != 1:
        print("usage: doc_status.py <work-folder> [--json]", file=sys.stderr)
        return 2
    folder = Path(positional[0])
    if not _is_readable_dir(folder):
        print(f"work folder missing, not a directory, or unreadable: {folder}", file=sys.stderr)
        return 2
    status = derive(folder)
    if json_mode:
        sys.stdout.write(render_machine(status))
        sys.stderr.write(render_human(status))
    else:
        sys.stdout.write(render_human(status))
        sys.stdout.write(render_machine(status))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
