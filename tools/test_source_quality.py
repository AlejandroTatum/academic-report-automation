"""Named spec scenarios for #11: source quality review and rejection (R13-R14)."""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from source_quality import evaluate_source_quality  # noqa: E402


def qualified_source(**overrides: object) -> dict:
    source = {
        "authority": "IEEE Transactions on Software Engineering",
        "peer_reviewed": True,
        "primary_or_secondary": "primary",
        "year": 2024,
        "relevant": True,
        "accessible": True,
        "verifiable": True,
    }
    source.update(overrides)
    return source


def test_research_accepts_qualified_sources_and_records_judgment() -> None:
    judgment = evaluate_source_quality(qualified_source())
    assert judgment.status == "eligible"
    assert judgment.eligible
    assert judgment.rationale
    assert judgment.reasons == []


def test_research_rejects_unverifiable_or_unfit_sources() -> None:
    fabricated = evaluate_source_quality(qualified_source(fabricated=True))
    assert fabricated.status == "rejected"
    assert "fabricated" in fabricated.reasons

    unverifiable = evaluate_source_quality(qualified_source(verifiable=False))
    assert unverifiable.status == "rejected"
    assert "unverifiable" in unverifiable.reasons

    irrelevant = evaluate_source_quality(qualified_source(relevant=False))
    assert irrelevant.status == "rejected"
    assert "irrelevant" in irrelevant.reasons

    superseded = evaluate_source_quality(qualified_source(superseded_by="smith2025"))
    assert superseded.status == "rejected"
    assert "superseded" in superseded.reasons

    unsuitable = evaluate_source_quality(qualified_source(authority=""))
    assert unsuitable.status == "rejected"
    assert "unsuitable" in unsuitable.reasons

    # Every rejection retains its reason -- never silently discarded.
    for judgment in (fabricated, unverifiable, irrelevant, superseded, unsuitable):
        assert judgment.rationale
        assert not judgment.eligible


def test_research_rejects_source_with_missing_quality_fields() -> None:
    """An unevaluated field (absent, never explicitly True) must not
    silently pass as if it had been positively confirmed -- only a field
    that fabrication defaults to false-when-absent (you cannot accuse
    fabrication without evidence); verifiable/relevant/accessible must each
    be positively established."""
    missing_verifiable = evaluate_source_quality(qualified_source(verifiable=None))
    assert missing_verifiable.status == "rejected"
    assert "unverifiable" in missing_verifiable.reasons

    missing_relevant = evaluate_source_quality(qualified_source(relevant=None))
    assert missing_relevant.status == "rejected"
    assert "irrelevant" in missing_relevant.reasons

    missing_accessible = evaluate_source_quality(qualified_source(accessible=None))
    assert missing_accessible.status == "rejected"
    assert "unsuitable" in missing_accessible.reasons

    # A source that never mentions any of these fields at all is rejected
    # the same way -- omission is not evidence of quality.
    unevaluated = {"authority": "IEEE", "primary_or_secondary": "primary"}
    result = evaluate_source_quality(unevaluated)
    assert result.status == "rejected"


def test_research_eligible_rationale_reports_actual_year_not_unverified_currency() -> None:
    """The rationale for an eligible source must not assert 'vigente'
    (current) unconditionally -- currency/year is never actually evaluated
    here, so claiming it is verified overclaims. The rationale should
    surface the recorded year transparently instead."""
    judgment = evaluate_source_quality(qualified_source(year=2024))
    assert "vigente" not in judgment.rationale
    assert "2024" in judgment.rationale
