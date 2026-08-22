"""Static contract tests for the research-to-report evidence handoff."""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESEARCH_ROOT = ROOT / "skills" / "research-workflow"
RESEARCH_SKILL = RESEARCH_ROOT / "SKILL.md"
PROTOCOL = RESEARCH_ROOT / "references" / "research-protocol.md"
MATRIX = RESEARCH_ROOT / "assets" / "evidence-matrix-template.md"
REPORT_SKILL = ROOT / "skills" / "academic-report-builder" / "SKILL.md"
SYNC_SCRIPT = ROOT / "scripts" / "sync_skills.sh"


def read(path: Path) -> str:
    assert path.is_file(), f"missing required contract file: {path}"
    return path.read_text(encoding="utf-8")


def test_research_skill_has_runtime_structure_and_discovery_metadata() -> None:
    text = read(RESEARCH_SKILL)
    assert re.search(r"^name:\s*research-workflow$", text, re.MULTILINE)
    assert re.search(r'^description:\s*"Trigger: research', text, re.MULTILINE)
    expected = (
        "Activation Contract",
        "Hard Rules",
        "Decision Gates",
        "Execution Steps",
        "Output Contract",
        "References",
    )
    positions = [text.index(f"## {heading}") for heading in expected]
    assert positions == sorted(positions)


def test_research_skill_owns_evidence_not_document_creation() -> None:
    text = read(RESEARCH_SKILL).lower()
    assert "does not create, format, export, or deliver a report" in text
    assert "evidence package" in text
    assert "academic-report-builder" in text


def test_protocol_requires_traceable_claim_level_evidence() -> None:
    text = read(PROTOCOL).lower()
    for required in (
        "research question",
        "inclusion",
        "exclusion",
        "claim",
        "source locator",
        "verbatim evidence",
        "confidence",
        "limitations",
        "contradiction",
    ):
        assert required in text, f"protocol must define {required!r}"


def test_evidence_matrix_has_required_traceability_fields() -> None:
    text = read(MATRIX).lower()
    for field in (
        "claim id",
        "claim",
        "source",
        "source locator",
        "verbatim evidence",
        "source type",
        "publication date",
        "confidence",
        "limitations",
        "citation key",
        "source eligibility/status",
    ):
        assert field in text, f"matrix template must include {field!r}"


def test_source_eligibility_rules_preserve_bibliography_boundary() -> None:
    skill = read(RESEARCH_SKILL).lower()
    protocol = read(PROTOCOL).lower()
    matrix = read(MATRIX).lower()

    assert "every source-inventory and evidence-matrix entry" in skill
    assert "local source with `inspected: true` is eligible for final citation" in skill
    assert "local source without that inspection flag as `lead`, not bibliography-eligible" in protocol
    assert "externally discovered but unverified source as `lead`, not bibliography-eligible" in protocol
    assert "until it is inspected and its provenance is complete" in protocol
    assert "only `eligible` bibliography-ready entries in the bibliography handoff" in protocol
    assert "keep `lead` entries separately visible for follow-up" in protocol
    assert "source inventory (include eligibility/status for every entry)" in matrix
    assert "bibliography-ready handoff (eligible entries only)" in matrix
    assert "leads for follow-up (separate; not bibliography-eligible)" in matrix


def test_report_builder_accepts_the_research_evidence_handoff() -> None:
    text = read(REPORT_SKILL).lower()
    assert "research-workflow evidence package" in text
    assert "do not treat the package as confirmed document intake" in text
    assert "preserve claim-to-source traceability" in text


def test_sync_script_includes_research_workflow() -> None:
    text = read(SYNC_SCRIPT)
    assert re.search(r"^\s+research-workflow$", text, re.MULTILINE)
