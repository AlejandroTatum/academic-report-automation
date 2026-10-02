#!/usr/bin/env python3
"""Extract only explicitly stated facts from a teacher's guide."""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path


def extract_guide_facts(text: str) -> dict:
    """Return explicit guide facts without interpreting missing information."""
    try:
        normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
        facts: dict = {}
        conflicts: dict[str, list[str]] = {}

        def record(key: str, values: list[str]) -> None:
            unique = list(dict.fromkeys(values))
            if len(unique) > 1:
                conflicts[key] = unique
            elif unique:
                facts[key] = unique[0]

        record("family", [value for pattern, value in (
            (r"\bape\b|\bpractico[\s-]+experimental(?:es)?\b", "ape"),
            (r"\baprendizaje\s+autonomo\b", "aa"),
        ) if re.search(pattern, normalized)])
        record("practice_number", [value.lstrip("0") or "0" for value in re.findall(
            r"\b(?:semana|practica)\s+(?:nro\.?\s*)?(\d+)\b", normalized)])
        record("practice_type", [value for pattern, value in (
            (r"\bindividual\b", "Individual"),
            (r"\bgrupal\b|\ben\s+grupo\b", "Grupal"),
        ) if re.search(pattern, normalized)])
        record("planned_time", [f"{value} horas" for value in re.findall(
            r"\btiempo\s+planificado(?:\s+en\s+el\s+silabo)?\s*:?\s*(\d+)(?:\s+horas)?\b", normalized)])
        if conflicts:
            facts["conflicts"] = conflicts
        return facts
    except (TypeError, ValueError, UnicodeError):
        return {}


def load_guide_facts(report_dir: Path, config: object) -> dict[str, str]:
    """Read a declared UTF-8 guide only when it resolves within the report folder."""
    try:
        raw = config.raw if hasattr(config, "raw") else config
        declared = raw.get("guide")
        if not isinstance(declared, str) or not declared.strip():
            return {}
        root = Path(report_dir).resolve()
        target = (root / declared).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            return {}
        return extract_guide_facts(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError, AttributeError):
        return {}


def main(argv: list[str] | None = None) -> int:
    import yaml
    from report_config import read_yaml

    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: guide_facts.py <folder>", file=sys.stderr)
        return 2
    folder = Path(args[0])
    try:
        config = read_yaml(folder / "report.yml")
    except (OSError, UnicodeError, yaml.YAMLError):
        config = {}
    print(yaml.safe_dump(load_guide_facts(folder, config), allow_unicode=True, sort_keys=False), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
