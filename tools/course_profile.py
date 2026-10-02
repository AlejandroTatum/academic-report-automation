#!/usr/bin/env python3
"""Apply a course profile's report.yml defaults when the subject matches.

A profile is a Markdown file under ``references/profiles/`` that starts with
YAML front matter:

    match:                      # every key is compared accent/case-insensitively
      subject: Simulación       # against the report's metadata
    report_defaults: {...}      # report.yml keys; explicit report.yml values win
    delivery_dir_template: "~/.../unidad-{unit}/ape-{practice_number}-{slug}/"

Profiles without front matter are prose-only and ignored. Missing keys are
written as text (appended, or inserted under an existing top-level block) so
the rest of report.yml keeps its comments and ordering.
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

import yaml

from guide_facts import load_guide_facts
from report_config import load_report_config

PROFILES_DIR = Path(__file__).resolve().parent.parent / "skills" / "academic-report-flow" / "references" / "profiles"
_FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    return "".join(c for c in text if not unicodedata.combining(c)).casefold().strip()


def load_profile(path: Path) -> dict[str, Any] | None:
    """Front matter of a profile, or ``None`` when it has none (prose-only)."""
    found = _FRONT_MATTER.match(path.read_text(encoding="utf-8"))
    if not found:
        return None
    data = yaml.safe_load(found.group(1))
    return data if isinstance(data, dict) and isinstance(data.get("match"), dict) else None


def _matches(profile: dict[str, Any], metadata: dict[str, Any]) -> bool:
    return all(_fold(metadata.get(key, "")) == _fold(want) for key, want in profile["match"].items())


def _missing(defaults: dict[str, Any], raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Split defaults into absent top-level keys and absent keys of existing blocks."""
    top = {k: v for k, v in defaults.items() if k not in raw}
    nested = {}
    for key, value in defaults.items():
        if key in raw and isinstance(value, dict) and isinstance(raw[key], dict):
            gap = {k: v for k, v in value.items() if k not in raw[key]}
            if gap:
                nested[key] = gap
    return top, nested


def _dump(data: dict[str, Any], indent: int = 0) -> str:
    block = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    return "".join(" " * indent + line for line in block.splitlines(keepends=True))


def _write_defaults(text: str, top: dict[str, Any], nested: dict[str, dict[str, Any]]) -> tuple[str, list[str]]:
    skipped = []
    for key, gap in nested.items():
        header = re.search(rf"^{re.escape(key)}:[ \t]*(#.*)?$", text, re.MULTILINE)
        if header is None:
            skipped.append(key)
            continue
        text = text[: header.end()] + "\n" + _dump(gap, 2).rstrip("\n") + text[header.end():]
    if top:
        text = text.rstrip("\n") + "\n" + _dump(top)
    return text, skipped


def _number(value: Any) -> str | None:
    """Bare number in a unit or practice label ("U1: Intro" -> "1", "01" -> "1")."""
    found = re.search(r"\d+", str(value or ""))
    return str(int(found.group())) if found else None


def _resolve_template(template: str, config: Any, folder: Path) -> tuple[str | None, list[str]]:
    meta = config.metadata
    facts = {"slug": config.document_slug}
    if not meta.get("practice_number"):
        facts["practice_number"] = load_guide_facts(folder, config).get("practice_number", "")
    values = {"unit": _number(meta.get("unit")),
              "practice_number": _number(meta.get("practice_number") or facts.get("practice_number")),
              "slug": facts["slug"]}
    missing = [n for n in dict.fromkeys(_PLACEHOLDER.findall(template)) if not values.get(n)]
    if missing:
        return None, missing
    return _PLACEHOLDER.sub(lambda m: str(values[m.group(1)]).strip(), template), []


def _valid(text: str) -> str | None:
    """Error message when ``text`` is not a loadable report.yml, else ``None``.

    The bibliography is only a stub here: it is created later in the flow, and
    its absence must not reject a profile that sets ``uncited_bibliography``.
    """
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "report.yml").write_text(text, encoding="utf-8")
        bib = (yaml.safe_load(text) or {}).get("bibliography", "sources.bib")
        if isinstance(bib, str) and not Path(bib).is_absolute() and ".." not in Path(bib).parts:
            (Path(tmp) / bib).parent.mkdir(parents=True, exist_ok=True)
            (Path(tmp) / bib).touch()
        try:
            load_report_config(Path(tmp))
        except SystemExit as exc:
            return str(exc)
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path)
    parser.add_argument("--check", action="store_true", help="print what would be applied; write nothing")
    parser.add_argument("--profiles", type=Path, default=PROFILES_DIR, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    report_yml = args.folder / "report.yml"
    config = load_report_config(args.folder)
    candidates = [
        (path, profile) for path in sorted(args.profiles.glob("*.md"))
        if (profile := load_profile(path)) and _matches(profile, config.metadata)
    ]
    if not candidates:
        print("no profile")
        return 0
    if len(candidates) > 1:
        print("error: several profiles match: " + ", ".join(p.name for p, _ in candidates), file=sys.stderr)
        return 2

    path, profile = candidates[0]
    defaults = dict(profile.get("report_defaults") or {})
    template = profile.get("delivery_dir_template")
    if isinstance(template, str) and "delivery_dir" not in config.raw:
        resolved, missing = _resolve_template(template, config, args.folder)
        if resolved:
            defaults["delivery_dir"] = resolved
        else:
            print(f"delivery_dir not set; unresolved placeholders: {', '.join(missing)}")

    top, nested = _missing(defaults, config.raw)
    text, skipped = _write_defaults(report_yml.read_text(encoding="utf-8"), top, nested)
    error = _valid(text)
    if error:
        print(f"error: profile {path.name} produces an invalid report.yml: {error}", file=sys.stderr)
        return 1
    applied = {**top, **{f"{k}.{n}": v for k, gap in nested.items() if k not in skipped for n, v in gap.items()}}
    print(f"profile {path.name}: " + (", ".join(f"{k}={v}" for k, v in applied.items()) or "nothing to apply (report.yml already sets every key)"))
    for key in skipped:
        print(f"not applied: {key} is not a block-style mapping; edit it by hand")
    if not args.check and text != report_yml.read_text(encoding="utf-8"):
        report_yml.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
