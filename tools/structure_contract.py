#!/usr/bin/env python3
"""Confirmed report structure contract (#12).

A teacher-required document structure — exact ordered section titles,
mandatory per-section content/rubric criteria, and optional quantitative
limits (words, pages, tables, figures, references) — is combined from every
supplied assignment source, confirmed once, and frozen into
``report.yml.structure``. No parallel ``confirmed``/``stale`` flag is
persisted (design decision, ``sdd/academic-structure-and-research-contract``):
presence of a well-formed, current ``structure:`` block IS the confirmation.
Reconfirmation is forced structurally, by comparing recorded source hashes
against the files on disk, never by a mutable status field.

Gate scope: a report that never engages this flow (no ``structure:`` key at
all) is untouched — that is the existing, already-shipped behaviour every
report before this feature relied on. The gate only activates once a report
declares ``structure:`` — as the ``"proposed"`` marker (a proposal exists,
pending explicit confirmation) or as a confirmed contract — matching the
design's migration note that new gates activate only where the new contract
is actually present.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from validate_ieee_refs import ValidationResult

STRUCTURE_KEY = "structure"
PROPOSED_MARKER = "proposed"

# The only quantitative limits a section may declare (#6408: mandatory
# rubric/content criteria plus OPTIONAL quantitative limits). A section that
# declares none of these is still valid — no limit is ever inferred.
RECOGNIZED_LIMIT_KEYS = ("words", "pages", "tables", "figures", "references")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fold_title(title: str) -> str:
    """Case/accent-insensitive fold, reusing the same rule as body headings."""
    from build_latex_report import fold_heading

    return fold_heading(title)


def parse_structure(raw: dict[str, Any]) -> Any:
    """Return the raw ``structure`` value, or ``None`` when the key is absent."""
    return raw.get(STRUCTURE_KEY)


# ---------------------------------------------------------------------------
# R1 — combine every supplied assignment source
# ---------------------------------------------------------------------------


def combine_assignment_sources(sources: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine section requirements from every supplied assignment source.

    ``sources`` is a list of
    ``{"kind": "brief|rubric|template|transcription", "path": "...",
    "sections": [{"title": "...", "criteria": ["...", ...],
    "limits": {...}}]}``.

    Sections are matched by exact (case/accent-insensitive) title across
    sources. Criteria from every source that names a section are unioned,
    each one carrying its originating source path as ``source_ref`` — so the
    combined draft keeps provenance per criterion, not just per source.

    A quantitative limit that two sources declare with different values for
    the same section/key is NOT silently merged: it is recorded as a
    conflict and excluded from the combined limits, so confirmation cannot
    proceed until a human resolves it (spec: "contradictions block
    confirmation pending resolution"). The relative ORDER two sources imply
    for their shared sections is a contradiction too (document-intake.md:
    "a section required by one and forbidden or reordered by another blocks
    confirmation") — the combined order keeps first-seen-source precedence,
    but a later source that disagrees with it is recorded as its own
    ``"order"`` conflict rather than silently overruled.
    """
    combined: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    provenance: list[dict[str, str]] = []
    conflicts: list[dict[str, Any]] = []
    source_sequences: list[tuple[str, list[str]]] = []

    for source in sources:
        kind = source.get("kind")
        path = source.get("path")
        provenance.append({"kind": kind, "path": path})
        sequence: list[str] = []
        for section in source.get("sections", []):
            title = str(section.get("title") or "").strip()
            norm = fold_title(title)
            sequence.append(norm)
            if norm not in combined:
                combined[norm] = {"title": title, "criteria": [], "limits": {}}
                order.append(norm)
            entry = combined[norm]
            for text in section.get("criteria", []):
                entry["criteria"].append({"text": text, "source_ref": path})
            for key, value in (section.get("limits") or {}).items():
                if key in entry["limits"]:
                    if entry["limits"][key] != value:
                        conflicts.append(
                            {
                                "section_title": entry["title"],
                                "field": key,
                                "values": (entry["limits"][key], value),
                            }
                        )
                        del entry["limits"][key]
                        entry.setdefault("_rejected_limits", set()).add(key)
                    continue
                if key in entry.get("_rejected_limits", set()):
                    continue
                entry["limits"][key] = value
        source_sequences.append((path, sequence))

    sections = []
    for norm in order:
        entry = combined[norm]
        entry.pop("_rejected_limits", None)
        sections.append(entry)

    # Order conflict pass: a source's own sequence, restricted to sections
    # that ended up in the combined structure, must be non-decreasing under
    # the combined order's index -- otherwise this source ordered a shared
    # section differently than the combined draft does.
    order_index = {norm: index for index, norm in enumerate(order)}
    for path, sequence in source_sequences:
        relative = [norm for norm in sequence if norm in order_index]
        last_index = -1
        for norm in relative:
            index = order_index[norm]
            if index < last_index:
                conflicts.append(
                    {
                        "type": "order",
                        "source": path,
                        "section_title": combined[norm]["title"],
                        "detail": (
                            f"assignment source '{path}' orders "
                            f"'{combined[norm]['title']}' differently than "
                            "the combined structure"
                        ),
                    }
                )
                break
            last_index = index

    return {"sections": sections, "provenance": provenance, "conflicts": conflicts}


def has_blocking_conflicts(combined: dict[str, Any]) -> bool:
    """True when a combined draft carries unresolved cross-source conflicts."""
    return bool(combined.get("conflicts"))


# ---------------------------------------------------------------------------
# R2/R3 — schema validation: exact titles, order, criteria, optional limits
# ---------------------------------------------------------------------------


def _is_number(value: Any) -> bool:
    """True for an int/float limit value -- excluding bool, which is
    technically an int subclass but never a meaningful word/page/etc count."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_structure_schema(structure: Any) -> ValidationResult:
    """Structural checks for a ``structure:`` contract (confirmed or draft).

    Every section needs a non-empty ``title`` and at least one non-empty
    content/rubric ``criteria`` entry (#6408: criteria are mandatory).
    ``limits`` stays entirely optional per section, and only the recognised
    quantitative keys may appear — no limit is ever invented for a key the
    assignment never declared (R3). Every declared limit value must itself
    be numeric (or a ``{min, max}`` mapping of numbers): a non-numeric value
    is rejected here, as a schema error, rather than crashing later when
    final validation compares a rendered section's word count against it.

    This function only validates the confirmed/draft MAPPING form. The
    ``"proposed"`` marker string is a separate, caller-level case (handled
    by ``structure_confirmation_state`` before this function is ever
    invoked) — the error message below names it only to describe every
    value ``structure:`` may legally hold in ``report.yml``, not because
    this function accepts it.
    """
    result = ValidationResult()
    if not isinstance(structure, dict):
        result.errors.append(
            "structure en report.yml debe ser 'proposed' o un mapeo con 'sections'"
        )
        return result

    sections = structure.get("sections")
    if not isinstance(sections, list) or not sections:
        result.errors.append("structure.sections debe ser una lista no vacía de secciones")
        return result

    sources = structure.get("sources")
    if sources is not None:
        if not isinstance(sources, list):
            result.errors.append("structure.sources debe ser una lista de fuentes")
        else:
            for source in sources:
                if not isinstance(source, dict):
                    result.errors.append("cada fuente de structure.sources debe ser un mapeo")

    seen_titles: set[str] = set()
    for section in sections:
        if not isinstance(section, dict):
            result.errors.append("cada sección de structure.sections debe ser un mapeo")
            continue
        title = str(section.get("title") or "").strip()
        if not title:
            result.errors.append("structure.sections requiere 'title' en cada sección")
            continue
        norm = fold_title(title)
        if norm in seen_titles:
            result.errors.append(f"Título de sección duplicado en structure: '{title}'")
        seen_titles.add(norm)

        criteria = section.get("criteria")
        if not isinstance(criteria, list) or not criteria:
            result.errors.append(
                f"La sección '{title}' requiere al menos un criterio de "
                "contenido/rúbrica en structure"
            )
        else:
            for criterion in criteria:
                text = criterion.get("text") if isinstance(criterion, dict) else None
                if not str(text or "").strip():
                    result.errors.append(
                        f"La sección '{title}' tiene un criterio sin 'text' en structure"
                    )

        limits = section.get("limits")
        if limits is not None:
            if not isinstance(limits, dict):
                result.errors.append(
                    f"La sección '{title}' tiene 'limits' inválido: debe ser un mapeo"
                )
            else:
                unknown = [key for key in limits if key not in RECOGNIZED_LIMIT_KEYS]
                if unknown:
                    result.errors.append(
                        f"La sección '{title}' declara límites no reconocidos: "
                        + ", ".join(unknown)
                    )
                for key, value in limits.items():
                    if key not in RECOGNIZED_LIMIT_KEYS:
                        continue
                    if isinstance(value, dict):
                        bad = [
                            bound
                            for bound in ("min", "max")
                            if bound in value and not _is_number(value[bound])
                        ]
                        if bad or any(k not in ("min", "max") for k in value):
                            result.errors.append(
                                f"La sección '{title}' declara un límite '{key}' inválido: "
                                "debe ser {min, max} numéricos"
                            )
                    elif not _is_number(value):
                        result.errors.append(
                            f"La sección '{title}' declara un límite '{key}' inválido: "
                            "debe ser un número o un mapeo {min, max}"
                        )
    return result


def declared_limit(section: dict[str, Any], key: str) -> Any:
    """Return the declared limit for ``key``, or ``None`` when never supplied.

    Distinguishes "no limit was declared" from "limit is zero" — used by
    final validation so an unsupplied limit is never enforced (R3).
    """
    limits = section.get("limits")
    if not isinstance(limits, dict):
        return None
    return limits.get(key)


# ---------------------------------------------------------------------------
# R4/R5/R6 — confirmation state and reconfirmation on change
# ---------------------------------------------------------------------------


def _stale_reason(folder: Path, structure: dict[str, Any]) -> str | None:
    """A confirmed contract is stale when a recorded source no longer hashes
    to the value it was confirmed against -- including a source that
    disappeared entirely. A missing source can no longer be re-verified
    against the frozen confirmation, so it must never fail open into
    "confirmed"; it is exactly as stale as a source whose bytes changed.
    """
    for source in structure.get("sources", []) or []:
        path = source.get("path")
        recorded = source.get("sha256")
        if not path or not recorded:
            continue
        candidate = Path(folder) / path
        if not candidate.is_file():
            return f"assignment source '{path}' is missing since structure was confirmed"
        if sha256_file(candidate) != recorded:
            return f"assignment source '{path}' changed since structure was confirmed"
    return None


def structure_confirmation_state(config: Any) -> tuple[str, str]:
    """One of ``absent`` | ``unconfirmed`` | ``stale`` | ``confirmed``, with detail.

    ``absent`` means the report never engaged the structure flow at all —
    the pre-existing, ungated behaviour every report before this feature
    already relies on. ``unconfirmed`` covers both the ``"proposed"``
    marker (R4: a structure was proposed but not yet confirmed) and a
    malformed draft. ``stale`` is a confirmed contract whose source changed
    on disk (R5). Only ``confirmed`` clears the gate.
    """
    raw = config.raw if hasattr(config, "raw") else config
    if STRUCTURE_KEY not in raw:
        return "absent", "no structure declared in report.yml"

    structure = raw[STRUCTURE_KEY]
    if isinstance(structure, str) and structure.strip().lower() == PROPOSED_MARKER:
        return "unconfirmed", "a structure was proposed but not yet confirmed"

    schema_result = validate_structure_schema(structure)
    if schema_result.errors:
        return "unconfirmed", "; ".join(schema_result.errors)

    folder = config.folder if hasattr(config, "folder") else Path(".")
    stale = _stale_reason(folder, structure)
    if stale:
        return "stale", stale
    return "confirmed", "structure confirmed and current"


def structure_gate_engaged(raw: dict[str, Any]) -> bool:
    """True once a report has declared a ``structure:`` key at all.

    The intake gate (R6) only consults confirmation state for a report that
    engaged the flow; a report that never declared ``structure:`` keeps its
    pre-existing behaviour untouched.
    """
    return STRUCTURE_KEY in raw
