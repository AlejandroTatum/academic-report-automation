#!/usr/bin/env python3
"""Source quality review and rejection (#11).

Research must evaluate authority, relevance, currency, primary/secondary
status, peer review, and accessibility before a source may support a claim.
Fabricated, unverifiable, irrelevant, superseded, or unsuitable sources are
rejected with a named reason; a qualified source's judgment and rationale
are retained instead.

A source here is a plain dict -- the same shape a manifest v2 entry
(`source_library.py`) or an evidence-matrix source snapshot already carries:
``authority``, ``peer_reviewed``, ``primary_or_secondary``, ``year``,
``relevant``, ``accessible``, ``verifiable``, ``fabricated``,
``superseded_by``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# One rejection reason per unmet criterion -- named exactly so a caller can
# report which spec condition (fabricated/unverifiable/irrelevant/superseded/
# unsuitable) excluded the source.
REJECTED_FABRICATED = "fabricated"
REJECTED_UNVERIFIABLE = "unverifiable"
REJECTED_IRRELEVANT = "irrelevant"
REJECTED_SUPERSEDED = "superseded"
REJECTED_UNSUITABLE = "unsuitable"


@dataclass
class QualityJudgment:
    status: str  # "eligible" | "rejected"
    rationale: str
    reasons: list[str] = field(default_factory=list)

    @property
    def eligible(self) -> bool:
        return self.status == "eligible"


def evaluate_source_quality(source: dict[str, Any]) -> QualityJudgment:
    """Evaluate one candidate source against every quality criterion.

    Every criterion is checked -- rejection is not short-circuited -- so the
    retained reasons name every unmet condition, not just the first one.
    """
    reasons: list[str] = []

    if bool(source.get("fabricated")):
        reasons.append(REJECTED_FABRICATED)
    if source.get("verifiable") is False:
        reasons.append(REJECTED_UNVERIFIABLE)
    if source.get("relevant") is False:
        reasons.append(REJECTED_IRRELEVANT)
    if source.get("superseded_by"):
        reasons.append(REJECTED_SUPERSEDED)

    authority = str(source.get("authority") or "").strip()
    accessible = source.get("accessible")
    primary_or_secondary = str(source.get("primary_or_secondary") or "").strip().lower()
    if not authority or accessible is False or primary_or_secondary not in (
        "primary",
        "secondary",
    ):
        reasons.append(REJECTED_UNSUITABLE)

    if reasons:
        return QualityJudgment(
            status="rejected",
            rationale="Fuente rechazada: " + ", ".join(reasons),
            reasons=reasons,
        )

    peer_reviewed = "revisada por pares" if source.get("peer_reviewed") else "no revisada por pares"
    rationale = (
        f"Fuente elegible: autoridad '{authority}', {primary_or_secondary}, "
        f"{peer_reviewed}, accesible, verificable, relevante, vigente"
    )
    return QualityJudgment(status="eligible", rationale=rationale, reasons=[])
