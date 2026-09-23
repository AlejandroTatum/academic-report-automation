#!/usr/bin/env python3
"""Claim-to-evidence matrix contract (#11).

Research produces a traceable evidence package before drafting begins: one
row per material claim, mapping section, source, exact evidence, a locator,
a persistent identifier or URL, an access date where applicable, a citation
key, a use-type classification (quotation, paraphrase, synthesis, or common
knowledge), confidence, limitations, and conflicts.

Persisted at ``research/evidence.yml`` alongside the existing prose
``research/evidence-matrix.md`` the ``research-workflow`` skill already
produces. The gate only activates once a report writes ``evidence.yml`` at
all -- exactly the same presence-gated pattern as ``structure_contract``:
absence means the report never engaged this flow and keeps its current
behaviour (the markdown-only, non-empty check ``doc_status`` already runs).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from validate_ieee_refs import ValidationResult

EVIDENCE_RELATIVE_PATH = Path("research") / "evidence.yml"

USE_TYPES = ("quotation", "paraphrase", "synthesis", "common_knowledge")

# Traceability fields every non-common-knowledge claim must carry. `locator`
# and `identifier` name where the evidence lives; `access_date` is required
# only when the source is web-accessed (see `_requires_access_date`).
REQUIRED_CLAIM_FIELDS = (
    "claim_id",
    "section",
    "source_id",
    "source_class",
    "evidence",
    "locator",
    "citation_key",
    "use_type",
    "confidence",
)

CONFIDENCE_LEVELS = ("high", "medium", "low")


def evidence_path(folder: Path) -> Path:
    return Path(folder) / EVIDENCE_RELATIVE_PATH


def evidence_gate_engaged(folder: Path) -> bool:
    """True once a report has written ``research/evidence.yml`` at all."""
    return evidence_path(folder).is_file()


def _requires_access_date(claim: dict[str, Any]) -> bool:
    """Web-accessed evidence must record when it was accessed."""
    identifier = str(claim.get("identifier") or "")
    return identifier.startswith("http://") or identifier.startswith("https://")


def _is_common_knowledge(claim: dict[str, Any]) -> bool:
    return str(claim.get("use_type") or "").strip().lower() == "common_knowledge"


def validate_claim(claim: dict[str, Any]) -> list[str]:
    """Field-level checks for one evidence-matrix row (R9/R10/R11).

    A ``common_knowledge`` claim may omit ``source_id``/``locator``/
    ``identifier`` only when it carries a non-empty ``justification`` (spec:
    "Common knowledge MAY omit a source only with justification"). Every
    other claim needs every field in ``REQUIRED_CLAIM_FIELDS``, plus
    ``identifier`` (a DOI/ISBN/stable URL/persistent identifier), plus
    ``access_date`` when that identifier is a URL.
    """
    errors: list[str] = []
    claim_id = str(claim.get("claim_id") or "<sin id>")

    use_type = str(claim.get("use_type") or "").strip().lower()
    if use_type not in USE_TYPES:
        errors.append(
            f"Claim {claim_id}: use_type debe ser uno de {', '.join(USE_TYPES)}"
        )

    common_knowledge = use_type == "common_knowledge"
    if common_knowledge and str(claim.get("justification") or "").strip():
        # A justified common-knowledge claim may omit source/locator/identifier.
        required = ("claim_id", "section", "evidence", "confidence", "use_type")
    else:
        required = REQUIRED_CLAIM_FIELDS

    missing = [field for field in required if not str(claim.get(field) or "").strip()]
    if missing:
        errors.append(f"Claim {claim_id}: faltan campos requeridos: {', '.join(missing)}")

    if not common_knowledge or not str(claim.get("justification") or "").strip():
        if not str(claim.get("identifier") or "").strip():
            errors.append(
                f"Claim {claim_id}: falta identifier (DOI, ISBN, URL estable u otro identificador persistente)"
            )
        elif _requires_access_date(claim) and not str(claim.get("access_date") or "").strip():
            errors.append(f"Claim {claim_id}: falta access_date para un identifier basado en URL")

    if use_type == "quotation" and not str(claim.get("locator") or "").strip():
        errors.append(f"Claim {claim_id}: una cita textual (quotation) requiere locator exacto")

    confidence = str(claim.get("confidence") or "").strip().lower()
    if confidence and confidence not in CONFIDENCE_LEVELS:
        errors.append(
            f"Claim {claim_id}: confidence debe ser uno de {', '.join(CONFIDENCE_LEVELS)}"
        )

    return errors


def _drafting_block_reason(claim: dict[str, Any]) -> str | None:
    """R12: unsupported, conflicting, or insufficient evidence blocks drafting."""
    claim_id = str(claim.get("claim_id") or "<sin id>")
    if not str(claim.get("evidence") or "").strip():
        return f"Claim {claim_id}: sin evidencia de soporte (unsupported)"
    conflicts = claim.get("conflicts")
    if conflicts and not str(claim.get("conflict_resolution") or "").strip():
        return f"Claim {claim_id}: conflicto de fuentes sin resolver"
    confidence = str(claim.get("confidence") or "").strip().lower()
    if confidence == "insufficient" or (not confidence and not claim.get("justification")):
        return f"Claim {claim_id}: evidencia insuficiente (confidence no declarada)"
    return None


def validate_evidence_package(raw: dict[str, Any]) -> ValidationResult:
    """Structural validation of a parsed ``evidence.yml`` document.

    Every claim is checked field-by-field (R9/R10/R11); drafting-blocking
    conditions (R12) are reported as named errors so a caller can lock the
    draft phase on them exactly like any other final-gate failure.
    """
    result = ValidationResult()
    claims = raw.get("claims") if isinstance(raw, dict) else None
    if not isinstance(claims, list) or not claims:
        result.errors.append("evidence.yml debe declarar al menos un claim en 'claims'")
        return result

    seen_ids: set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict):
            result.errors.append("cada claim de evidence.yml debe ser un mapeo")
            continue
        claim_id = str(claim.get("claim_id") or "").strip()
        if claim_id and claim_id in seen_ids:
            result.errors.append(f"claim_id duplicado en evidence.yml: {claim_id}")
        seen_ids.add(claim_id)

        result.errors.extend(validate_claim(claim))
        block_reason = _drafting_block_reason(claim)
        if block_reason:
            result.errors.append(block_reason)

    return result


def load_evidence_package(folder: Path) -> dict[str, Any] | None:
    path = evidence_path(folder)
    if not path.is_file():
        return None
    from report_config import read_yaml

    return read_yaml(path) or {}
