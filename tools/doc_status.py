#!/usr/bin/env python3
"""Derive the document-workflow phases from on-disk artifacts (read-only).

Slice 2b-iii of the status layer: the phase vocabulary, the two value dataclasses
and the intake/research/preview/approval/generate/validate/deliver derivations. Each
function answers for exactly one phase and returns a raw ``done|pending|blocked``
token; there is no composition, renderer or CLI yet, so no function here has to know
what follows the phase it answers for. The route projection (``current``/``next``/
``gate``) and the renderers arrive in slice 2c.

Approval delegates to ``approval_marker.approval_state`` -- the same predicate
``publish_validated_pdf`` enforces -- so routing and the irreversible publisher
cannot disagree about which marker is current.

The module is pure and read-only. ``_phase_intake`` builds ``ReportConfig``
directly instead of calling ``load_report_config``, which raises ``SystemExit``
on an unknown route -- a status tool reports what it finds, it never exits.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from approval_marker import approval_state, sha256_file
from report_config import ReportConfig, read_yaml

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
