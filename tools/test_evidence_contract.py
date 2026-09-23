"""Named spec scenarios for #11: claim-to-evidence matrix (R9-R12).

Scenarios map one-to-one to the spec at
``sdd/academic-structure-and-research-contract`` (Engram #6410, #6413).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import yaml

from evidence_contract import validate_claim, validate_evidence_package  # noqa: E402


def complete_claim(**overrides: object) -> dict:
    claim = {
        "claim_id": "C-001",
        "section": "Desarrollo",
        "source_id": "smith2024",
        "source_class": "peer_reviewed_article",
        "evidence": "The measured latency dropped by 40% under load.",
        "locator": "p. 12",
        "identifier": "https://doi.org/10.1000/example",
        "access_date": "2026-09-01",
        "citation_key": "smith2024",
        "use_type": "paraphrase",
        "confidence": "high",
    }
    claim.update(overrides)
    return claim


# ---------------------------------------------------------------------------
# R9 — a complete, traceable claim is eligible for drafting
# ---------------------------------------------------------------------------


def test_matrix_accepts_complete_traceable_claim() -> None:
    claim = complete_claim()
    assert validate_claim(claim) == []

    result = validate_evidence_package({"claims": [claim]})
    assert result.errors == []


# ---------------------------------------------------------------------------
# R10 — missing locator, identifier, or access date blocks drafting, named
# ---------------------------------------------------------------------------


def test_matrix_rejects_missing_locator_identifier_or_access_date() -> None:
    missing_locator = complete_claim(locator="")
    errors = validate_claim(missing_locator)
    assert any("locator" in e for e in errors)

    missing_identifier = complete_claim(identifier="")
    errors = validate_claim(missing_identifier)
    assert any("identifier" in e for e in errors)

    missing_access_date = complete_claim(access_date="")
    errors = validate_claim(missing_access_date)
    assert any("access_date" in e for e in errors)


# ---------------------------------------------------------------------------
# R11 — quotation/paraphrase/synthesis/common knowledge are enforced
# ---------------------------------------------------------------------------


def test_matrix_classifies_evidence_use() -> None:
    # An unrecognized use_type is rejected outright.
    invalid = complete_claim(use_type="anecdote")
    assert any("use_type" in e for e in validate_claim(invalid))

    # A quotation without an exact locator is rejected -- quoting requires
    # pinpoint traceability, more than a paraphrase does.
    quotation_no_locator = complete_claim(use_type="quotation", locator="")
    errors = validate_claim(quotation_no_locator)
    assert any("quotation" in e for e in errors)

    # A quotation WITH a locator is accepted.
    quotation = complete_claim(use_type="quotation")
    assert validate_claim(quotation) == []

    # Common knowledge may omit source/locator/identifier only with an
    # explicit justification.
    common_knowledge_unjustified = {
        "claim_id": "C-002",
        "section": "Introducción",
        "evidence": "Water boils at 100C at sea level.",
        "confidence": "high",
        "use_type": "common_knowledge",
    }
    errors = validate_claim(common_knowledge_unjustified)
    assert errors, "unjustified common knowledge must still be rejected"

    common_knowledge_justified = dict(common_knowledge_unjustified)
    common_knowledge_justified["justification"] = "Widely known physical constant"
    assert validate_claim(common_knowledge_justified) == []


# ---------------------------------------------------------------------------
# R12 — unsupported, conflicting, or insufficient claims block drafting
# ---------------------------------------------------------------------------


def test_drafting_blocks_unsupported_conflicting_or_insufficient_claims() -> None:
    unsupported = complete_claim(claim_id="C-010", evidence="")
    result = validate_evidence_package({"claims": [unsupported]})
    assert any("C-010" in e and "unsupported" in e for e in result.errors)

    conflicting = complete_claim(
        claim_id="C-011",
        conflicts=["smith2024 vs doe2023 disagree on the measured effect"],
    )
    result = validate_evidence_package({"claims": [conflicting]})
    assert any("C-011" in e and "conflicto" in e.lower() for e in result.errors)

    # Recording a resolution clears the block.
    resolved = complete_claim(
        claim_id="C-012",
        conflicts=["smith2024 vs doe2023 disagree"],
        conflict_resolution="doe2023 used a larger sample; preferred here",
    )
    result = validate_evidence_package({"claims": [resolved]})
    assert not any("C-012" in e for e in result.errors)

    insufficient = complete_claim(claim_id="C-013", confidence="insufficient")
    result = validate_evidence_package({"claims": [insufficient]})
    assert any("C-013" in e and "insuficiente" in e.lower() for e in result.errors)


# ---------------------------------------------------------------------------
# Integration — the research phase gate validates the matrix structurally
# ---------------------------------------------------------------------------


def _write_report_yml(folder: Path) -> None:
    data = {
        "type": "essay",
        "route": "academic",
        "metadata": {
            "title": "Informe",
            "subject": "Sistemas Operativos",
            "teacher": "Ing. Hernán",
            "student": "Alejandro Padilla",
            "date": "2026-01-01",
        },
    }
    (folder / "report.yml").write_text(yaml.dump(data), encoding="utf-8")


def test_research_phase_gate_validates_evidence_yml_structurally(tmp_path: Path) -> None:
    import doc_status

    _write_report_yml(tmp_path)
    (tmp_path / "research").mkdir()
    (tmp_path / "research" / "evidence.yml").write_text(
        yaml.dump({"claims": [complete_claim(evidence="")]}), encoding="utf-8"
    )

    status = doc_status.derive(tmp_path)
    research = next(p for p in status.phases if p.name == "research")
    assert research.state in ("pending", "current")
    assert "evidence.yml" in research.detail

    (tmp_path / "research" / "evidence.yml").write_text(
        yaml.dump({"claims": [complete_claim()]}), encoding="utf-8"
    )
    status = doc_status.derive(tmp_path)
    research = next(p for p in status.phases if p.name == "research")
    assert research.state == "done"
