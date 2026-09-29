"""Read-only deterministic assertions over a planned rubric and draft."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from validate_ieee_refs import cited_keys


@dataclass(frozen=True)
class CheckResult:
    criterion_id: str
    check_index: int
    type: str
    ok: bool
    detail: str


def _fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.casefold()) if not unicodedata.combining(c))


def _section(body: str, title: str) -> str | None:
    lines = body.splitlines()
    start = None
    for index, line in enumerate(lines):
        match = re.match(r"^#\s+(.+?)\s*#*\s*$", line)
        if match:
            if start is not None:
                return "\n".join(lines[start:index])
            if _fold(match.group(1).strip()) == _fold(title.strip()):
                start = index + 1
    return "\n".join(lines[start:]) if start is not None else None


def _words(text: str) -> set[str]:
    stop = {"sobre", "entre", "desde", "hasta", "these", "those", "their", "there", "which", "where", "para", "como", "todos", "todas", "through"}
    return {word for word in re.findall(r"[^\W\d_]+", _fold(text)) if len(word) >= 5 and word not in stop}


def _evaluate(folder: Path, check: dict, body: str) -> tuple[bool, str]:
    kind = check["type"]
    if kind == "heading_present":
        ok = _section(body, check["section"]) is not None
        return ok, f"heading '{check['section']}' {'present' if ok else 'missing'}"
    scope = body if "section" not in check else _section(body, check["section"])
    if scope is None:
        return False, f"section '{check['section']}' missing"
    if kind == "contains":
        ok = check["text"].casefold() in scope.casefold()
        return ok, f"text '{check['text']}' {'found' if ok else 'missing'}"
    if kind == "matches":
        ok = re.search(check["pattern"], scope) is not None
        return ok, f"pattern '{check['pattern']}' {'matched' if ok else 'missing'}"
    if kind == "verbatim_from_guide":
        source = Path(check["source"])
        if source.is_absolute() or ".." in source.parts:
            return False, "source must be relative to report folder"
        try:
            guide = (folder / source).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return False, f"guide '{source}' missing or unreadable"
        needle = " ".join(check["text"].split())
        in_guide = needle in " ".join(guide.split())
        in_body = needle in " ".join(scope.split())
        return in_guide and in_body, f"verbatim text in guide={in_guide}, section={in_body}"
    if kind == "ordered_list":
        items = re.findall(r"^\s*\d+[.)]\s+\S", scope, re.MULTILINE)
        return len(items) >= check.get("min_items", 1), f"{len(items)}/{check.get('min_items', 1)} ordered items"
    if kind == "min_citations":
        count = len(cited_keys(scope))
        return count >= check["count"], f"{count}/{check['count']} distinct citations"
    if kind == "figure_referenced":
        count = len(re.findall(r"!\[[^]]*\]\([^)]+\)", scope))
        return count >= check.get("count", 1), f"{count}/{check.get('count', 1)} figures"
    if kind == "link_present":
        links = re.findall(r"<https?://[^>]+>|(?<!!)\[[^]]+\]\(https?://[^)]+\)", scope)
        matched = [link for link in links if "pattern" not in check or re.search(check["pattern"], link)]
        return bool(matched), f"{len(matched)} matching links"
    if kind == "keywords_from_section":
        origin = _section(body, check["from_section"])
        if origin is None:
            return False, f"source section '{check['from_section']}' missing"
        common = _words(origin) & _words(scope)
        return len(common) >= check.get("min", 2), f"{len(common)}/{check.get('min', 2)} shared keywords: {', '.join(sorted(common))}"
    return False, f"unknown check type '{kind}'"


def run_checks(report_dir: Path, criteria: list[dict], body_text: str) -> list[CheckResult]:
    """Evaluate checks in rubric order without writing or changing the draft."""
    results = []
    for criterion in criteria:
        for index, check in enumerate(criterion.get("checks", []), start=1):
            try:
                ok, detail = _evaluate(Path(report_dir), check, body_text)
            except (re.error, KeyError, TypeError, ValueError) as exc:
                ok, detail = False, f"invalid check: {exc}"
            results.append(CheckResult(criterion["id"], index, check["type"], ok, detail))
    return results
