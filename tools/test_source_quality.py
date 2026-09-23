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
