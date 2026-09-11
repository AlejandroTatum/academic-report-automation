#!/usr/bin/env python3
"""The shared approval-marker contract.

An approval is a file on disk, not a session variable: ``approval.yml`` binds a
human decision to the exact bytes of ``preview.md`` through ``preview_sha256``.
Two consumers share this predicate with different presentation: ``doc_status``
maps the state onto a phase state and a blocked-reason token, and
``publish_validated_pdf`` maps it onto a user-facing abort message. Keeping the
predicate here -- and the presentation at each boundary -- is what stops the
routing layer and the irreversible publisher from disagreeing about approval.

The module is pure and read-only. ``approval_state`` never writes, never creates
a directory, and never raises for a bad marker: an unreadable or invalid marker
is ``malformed`` data the caller can report, never a crash and never something
this module "repairs".
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from report_config import read_yaml

PREVIEW_NAME = "preview.md"
MARKER_NAME = "approval.yml"
MARKER_SCHEMA = "academic.doc-approval/v1"
REQUIRED_KEYS = ("preview_sha256", "approved_at", "approved_by")


@dataclass(frozen=True)
class ApprovalState:
    """The approval marker as derived from disk.

    ``state`` is exactly one of ``current|absent|stale|malformed``; ``reason`` is
    the bounded token ``"" | approval_marker_absent | approval_marker_stale |
    approval_marker_malformed``; ``detail`` is a short ASCII description naming
    the offending file or key.
    """

    state: str
    reason: str
    detail: str


def sha256_file(path: Path) -> str:
    """Return the lowercase SHA-256 of a file's raw bytes.

    Canonical home for the hash; ``publish_pdf`` re-exports it so existing
    callers (``build_report_auto.py``) keep working unchanged.
    """
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _malformed(detail: str) -> ApprovalState:
    return ApprovalState(state="malformed", reason="approval_marker_malformed", detail=detail)


def _is_missing_or_blank(value: object) -> bool:
    """A required key must be present and carry visible text."""
    return value is None or not str(value).strip()


def approval_state(work_folder: Path) -> ApprovalState:
    """Derive the approval state of a work folder without touching disk."""
    folder = Path(work_folder)
    marker_path = folder / MARKER_NAME
    preview_path = folder / PREVIEW_NAME

    if not marker_path.is_file():
        return ApprovalState(
            state="absent", reason="approval_marker_absent", detail=f"{MARKER_NAME} missing"
        )

    # A bad marker is data, not an exception: unreadable files and invalid YAML
    # both become `malformed` so a caller can fail closed with a named reason.
    try:
        data = read_yaml(marker_path)
    except Exception:
        return _malformed(f"{MARKER_NAME} is not valid YAML")

    for key in REQUIRED_KEYS:
        if _is_missing_or_blank(data.get(key)):
            return _malformed(f"{MARKER_NAME} missing or blank {key}")

    if not preview_path.is_file():
        return _malformed(f"{PREVIEW_NAME} missing")

    try:
        preview_hash = sha256_file(preview_path)
    except OSError:
        return _malformed(f"{PREVIEW_NAME} unreadable")

    if str(data["preview_sha256"]).strip().lower() != preview_hash:
        return ApprovalState(
            state="stale",
            reason="approval_marker_stale",
            detail=f"{MARKER_NAME} preview_sha256 does not match {PREVIEW_NAME}",
        )

    return ApprovalState(state="current", reason="", detail="")
