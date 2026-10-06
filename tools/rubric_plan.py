#!/usr/bin/env python3
"""The rubric-plan artifact: the teacher's rubric as a machine-checkable plan.

new-report-flow T3 makes the plan phase produce ``rubric.yml`` (schema
``academic.rubric/v1``): one criterion per rubric item, each mapped to the
``body.md`` heading that satisfies it. The draft writes against this plan and
the content check (``tools/content_check.py``) judges one criterion at a time,
so the schema here is the contract between those two phases.

``validate_rubric`` is the pure shape checker; ``rubric_state`` is the
folder-level predicate (``absent|malformed|valid``) status tools consume, and
``load_rubric`` returns the criteria of a valid plan. Like every marker
predicate in this repo, ``rubric_state`` never raises and never writes: an
unreadable, non-UTF-8 or non-mapping file is ``malformed`` data the caller can
report, never a crash and never something this module "repairs".
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from report_config import read_yaml

RUBRIC_NAME = "rubric.yml"
RUBRIC_SCHEMA = "academic.rubric/v1"

# Criterion ids are slugs: they name judgments in content-check.yml and the
# agent's judgments file, so they stay lowercase ASCII with hyphens.
_ID_PATTERN = re.compile(r"[a-z0-9-]+")


def _is_text(value: object) -> bool:
    """A required text key must be a string carrying visible content."""
    return isinstance(value, str) and value.strip() != ""


CHECK_PARAMS = {
    "heading_present": (("section",), ()),
    "contains": (("text",), ("section",)),
    "matches": (("pattern",), ("section",)),
    "verbatim_from_guide": (("section", "source", "text"), ()),
    "ordered_list": (("section",), ("min_items",)),
    "min_citations": (("count",), ("section",)),
    "figure_referenced": ((), ("section", "count")),
    "link_present": ((), ("section", "pattern")),
    "keywords_from_section": (("section", "from_section"), ("min",)),
}


# Numeric parameters: presence is checked with the required keys, the value by
# the positive-integer rule below.
_INT_KEYS = ("count", "min_items", "min")


def count_checked_criteria(criteria: list[dict]) -> int:
    """Count criteria that carry at least one deterministic check."""
    return sum(bool(c.get("checks")) for c in criteria)


def _check_errors(check: object, label: str) -> list[str]:
    if not isinstance(check, dict):
        return [f"{label} must be a mapping"]
    kind = check.get("type")
    if kind not in CHECK_PARAMS:
        return [f"{label} unknown type '{kind}'"]
    required, optional = CHECK_PARAMS[kind]
    errors = []
    for key in required:
        if key in _INT_KEYS:
            if key not in check:
                errors.append(f"{label} {key} is required")
        elif not _is_text(check.get(key)):
            errors.append(f"{label} {key} must be a non-empty string")
    for key in ("section", "source", "text", "from_section", "pattern"):
        if key in check and not _is_text(check[key]):
            errors.append(f"{label} {key} must be a non-empty string")
    for key in _INT_KEYS:
        if key in check and (type(check[key]) is not int or check[key] <= 0):
            errors.append(f"{label} {key} must be a positive integer")
    for key in check.keys() - {"type", *required, *optional}:
        errors.append(f"{label} unexpected parameter '{key}'")
    if kind in ("matches", "link_present") and isinstance(check.get("pattern"), str):
        try:
            re.compile(check["pattern"])
        except re.error as exc:
            errors.append(f"{label} invalid regex: {exc}")
    return errors


def _is_positive_int(value: object) -> bool:
    # A word ceiling: a whole number above zero (bool is an int subclass).
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def validate_rubric(data: object) -> list[str]:
    """Return the schema errors of a parsed ``rubric.yml`` (empty = valid)."""
    if not isinstance(data, dict):
        return [f"{RUBRIC_NAME} must be a YAML mapping"]

    errors: list[str] = []
    if data.get("schema") != RUBRIC_SCHEMA:
        errors.append(f"{RUBRIC_NAME} schema must be '{RUBRIC_SCHEMA}'")
    if not _is_text(data.get("source")):
        errors.append(f"{RUBRIC_NAME} source must be a non-empty string")
    if "max_words" in data and not _is_positive_int(data["max_words"]):
        errors.append(f"{RUBRIC_NAME} max_words must be a positive integer")

    criteria = data.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        errors.append(f"{RUBRIC_NAME} criteria must be a non-empty list")
        return errors

    seen: set[str] = set()
    for index, criterion in enumerate(criteria, start=1):
        if not isinstance(criterion, dict):
            errors.append(f"{RUBRIC_NAME} criterion {index} must be a mapping")
            continue
        cid = criterion.get("id")
        if not isinstance(cid, str) or not _ID_PATTERN.fullmatch(cid):
            errors.append(f"{RUBRIC_NAME} criterion {index} id must match [a-z0-9-]+")
        elif cid in seen:
            errors.append(f"{RUBRIC_NAME} duplicate criterion id '{cid}'")
        else:
            seen.add(cid)
        for key in ("title", "section"):
            if not _is_text(criterion.get(key)):
                errors.append(f"{RUBRIC_NAME} criterion {index} {key} must be a non-empty string")
        weight = criterion.get("weight")
        if weight is not None:
            # bool is an int subclass: a True/False weight is never a number > 0.
            if isinstance(weight, bool) or not isinstance(weight, (int, float)):
                errors.append(f"{RUBRIC_NAME} criterion {index} weight must be a number greater than 0")
            elif weight <= 0:
                errors.append(f"{RUBRIC_NAME} criterion {index} weight must be greater than 0")
        if "max_words" in criterion and not _is_positive_int(criterion["max_words"]):
            errors.append(f"{RUBRIC_NAME} criterion {index} max_words must be a positive integer")
        if "checks" in criterion:
            checks = criterion["checks"]
            if not isinstance(checks, list):
                errors.append(f"{RUBRIC_NAME} criterion {index} checks must be a list")
            else:
                for check_index, check in enumerate(checks, start=1):
                    errors.extend(_check_errors(check, f"criterion {index} check {check_index}"))
    return errors


def rubric_state(report_dir: Path) -> str:
    """Derive the plan state of a report folder without touching anything.

    Exactly one of ``absent|malformed|valid``; a file that cannot be read or
    parsed, or whose parsed shape fails ``validate_rubric``, is ``malformed``.
    """
    folder = Path(report_dir)
    path = folder / RUBRIC_NAME
    if not path.is_file():
        return "absent"

    try:
        data = read_yaml(path)
    except Exception:
        return "malformed"
    if validate_rubric(data):
        return "malformed"
    return "valid"


def load_rubric(report_dir: Path) -> list[dict]:
    """Return the criteria of a valid plan, in file order (empty otherwise)."""
    folder = Path(report_dir)
    if rubric_state(folder) != "valid":
        return []
    try:
        data = read_yaml(folder / RUBRIC_NAME)
    except Exception:
        return []
    criteria = data.get("criteria")
    return [criterion for criterion in criteria if isinstance(criterion, dict)]


def load_max_words(report_dir: Path) -> int | None:
    """Return the plan's total word ceiling (``max_words``), or None."""
    folder = Path(report_dir)
    if rubric_state(folder) != "valid":
        return None
    try:
        data = read_yaml(folder / RUBRIC_NAME)
    except Exception:
        return None
    value = data.get("max_words")
    return value if _is_positive_int(value) else None


def main(argv: list[str] | None = None) -> int:
    """CLI: validate ``<folder>/rubric.yml``; print problems, exit 1 on failure."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: rubric_plan.py <report-folder>")
        return 2
    path = Path(args[0]) / RUBRIC_NAME
    if not path.is_file():
        print(f"{RUBRIC_NAME} missing in {args[0]}")
        return 1
    try:
        problems = validate_rubric(read_yaml(path))
    except Exception as exc:
        problems = [f"{RUBRIC_NAME} unreadable: {exc}"]
    if problems:
        print("rubric_malformed:\n- " + "\n- ".join(problems))
        return 1
    print(f"{RUBRIC_NAME} OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
