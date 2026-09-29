#!/usr/bin/env python3
"""Research source gate: count the eligible academic entries in a BibTeX file.

new-report-flow T2 makes research a hard requirement: every document needs at
least ``MIN_ACADEMIC_SOURCES`` book-or-paper entries in its own ``.bib`` file.
``doc_status._phase_research`` calls :func:`source_gate` on the report folder,
so ``bibliography:``/``bib:`` overrides declared in ``report.yml`` are honored
through ``ReportConfig.bib_path`` (default ``<report-folder>/sources.bib``).

Eligibility is by BibTeX entry type: books, parts of books, articles, and
conference/thesis/technical-report entries count; web-only types such as
``@misc``/``@online`` never do. ``@comment``/``@string``/``@preamble`` are
BibTeX directives, not entries, and are ignored. Entry-type matching is
case-insensitive (``@ARTICLE`` is an ``article``).

A missing or unreadable file never raises: the gate reports it as a short
count with a named reason, so a status tool can show it as ordinary pending
progress.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from report_config import ReportConfig

ELIGIBLE_ENTRY_TYPES = (
    "book",
    "inbook",
    "incollection",
    "article",
    "inproceedings",
    "conference",
    "phdthesis",
    "mastersthesis",
    "techreport",
)
MIN_ACADEMIC_SOURCES = 5

# The declared name mirrors ReportConfig.bib_path's own default, so a reason
# can name the file the report actually points at.
_DEFAULT_BIB = "sources.bib"

# BibTeX entry header: `@type{key,`. The first token after `{` is the citation
# key; directives like `@string{name = "..."}` (no key) fall out naturally
# because their type is not eligible.
_ENTRY_HEADER = re.compile(r"@(\w+)\s*\{\s*([^,\s{}]+)")


@dataclass(frozen=True)
class SourceCount:
    """Result of the research source gate for one report folder."""

    count: int
    keys: tuple[str, ...]
    ok: bool
    reason: str


def eligible_entry_keys(bib_text: str) -> tuple[str, ...]:
    """Return the deduplicated keys of eligible entries, in file order."""
    keys: list[str] = []
    for match in _ENTRY_HEADER.finditer(bib_text):
        entry_type = match.group(1).lower()
        if entry_type not in ELIGIBLE_ENTRY_TYPES:
            continue
        key = match.group(2)
        if key not in keys:
            keys.append(key)
    return tuple(keys)


def source_gate(folder: Path, config: ReportConfig) -> SourceCount:
    """Evaluate the ``>= MIN_ACADEMIC_SOURCES`` gate for a report folder.

    Reads the file ``ReportConfig.bib_path`` resolves (so ``bibliography:``/
    ``bib:`` overrides win over the ``sources.bib`` default) and returns the
    eligible count with a human-readable reason; ``ok`` is True only at or
    above the minimum.
    """
    bib = config.bib_path
    declared = str(config.raw.get("bibliography") or config.raw.get("bib") or _DEFAULT_BIB)
    if bib is None:
        return SourceCount(
            0,
            (),
            False,
            f"{declared} has 0/{MIN_ACADEMIC_SOURCES} book or paper sources",
        )
    try:
        text = bib.read_text(encoding="utf-8")
    except OSError:
        return SourceCount(0, (), False, f"{declared} unreadable")

    keys = eligible_entry_keys(text)
    count = len(keys)
    if count < MIN_ACADEMIC_SOURCES:
        return SourceCount(
            count,
            keys,
            False,
            f"{declared} has {count}/{MIN_ACADEMIC_SOURCES} book or paper sources",
        )
    return SourceCount(
        count,
        keys,
        True,
        f"{declared} has {count}/{MIN_ACADEMIC_SOURCES} book or paper sources",
    )
