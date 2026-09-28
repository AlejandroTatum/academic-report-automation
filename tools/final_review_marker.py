#!/usr/bin/env python3
"""The final human review marker contract.

A final review is a file on disk, not a session variable: ``final-review.yml``
binds a human OK to the exact bytes of the final PDF through ``pdf_sha256``.
Two consumers share this predicate with different presentation: the delivery
gate in ``publish_validated_pdf`` maps it onto a user-facing abort message, and
``deliver_report`` names the missing evidence before delegating to that
publisher. Keeping the predicate here -- and the presentation at each boundary
-- is what stops the deliver entrypoint and the irreversible publisher from
disagreeing about whether the human saw the PDF that is about to ship.

The module is pure and read-only. ``final_review_state`` never writes, never
creates a directory, and never raises for a bad marker: an unreadable or
invalid marker is ``malformed`` data the caller can report, never a crash and
never something this module "repairs". Reviewed bytes that disappeared -- a
missing or rebuilt PDF -- are ``stale``: the human must review the current PDF
again, exactly as with approval.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from approval_marker import sha256_file
from report_config import read_yaml

MARKER_NAME = "final-review.yml"
MARKER_SCHEMA = "academic.doc-final-review/v1"
REQUIRED_KEYS = ("pdf_sha256", "reviewed_at", "reviewed_by")


@dataclass(frozen=True)
class FinalReviewState:
    """The final review marker as derived from disk.

    ``state`` is exactly one of ``current|absent|stale|malformed``; ``reason`` is
    the bounded token ``"" | final_review_marker_absent |
    final_review_marker_stale | final_review_marker_malformed``; ``detail`` is a
    short ASCII description naming the offending file or key.
    """

    state: str
    reason: str
    detail: str


def _malformed(detail: str) -> FinalReviewState:
    return FinalReviewState(
        state="malformed", reason="final_review_marker_malformed", detail=detail
    )


def _is_missing_or_blank(value: object) -> bool:
    """A required key must be present and carry visible text."""
    return value is None or not str(value).strip()


def final_review_state(report_dir: Path, pdf_path: Path) -> FinalReviewState:
    """Derive the final review state of ``pdf_path`` without touching disk."""
    folder = Path(report_dir)
    pdf = Path(pdf_path)
    marker_path = folder / MARKER_NAME

    if not marker_path.is_file():
        return FinalReviewState(
            state="absent",
            reason="final_review_marker_absent",
            detail=f"{MARKER_NAME} missing",
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

    if not pdf.is_file():
        return FinalReviewState(
            state="stale",
            reason="final_review_marker_stale",
            detail=f"final PDF {pdf.name} missing",
        )

    try:
        pdf_hash = sha256_file(pdf)
    except OSError:
        return FinalReviewState(
            state="stale",
            reason="final_review_marker_stale",
            detail=f"final PDF {pdf.name} unreadable",
        )

    if str(data["pdf_sha256"]).strip().lower() != pdf_hash:
        return FinalReviewState(
            state="stale",
            reason="final_review_marker_stale",
            detail=f"{MARKER_NAME} pdf_sha256 does not match {pdf.name}",
        )

    return FinalReviewState(state="current", reason="", detail="")
