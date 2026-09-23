#!/usr/bin/env python3
"""Report table-style directive coverage under a directory (issue #13).

Migration tool: for every Markdown file it finds, reports which tables
already carry a valid ``<!-- table-style: ... -->`` directive, which are
still undirected (candidates to migrate before a report opts into
``table_styles: {enabled: true}``), and which carry a malformed directive
-- a real error, never silently dropped. Read-only: never writes, never
selects a style, never touches ``build_latex_report.py``/DOCX/HTML.

Usage::

    .venv/bin/python tools/check_table_contexts.py <directory>
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from table_directives import TableDirectiveError, parse_table_blocks


@dataclass
class CheckReport:
    directed: list[tuple[str, str]] = field(default_factory=list)  # (file, table_key)
    undirected: list[tuple[str, int]] = field(default_factory=list)  # (file, table count)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when no malformed directive was found.

        Undirected tables are a migration note, not a failure -- they only
        become an error once a report opts into ``table_styles.enabled``,
        which this read-only checker does not know or decide.
        """
        return not self.errors


def scan_directory(directory: Path) -> CheckReport:
    report = CheckReport()
    for path in sorted(directory.rglob("*.md")):
        relative = str(path.relative_to(directory))
        try:
            blocks = parse_table_blocks(path.read_text(encoding="utf-8"))
        except TableDirectiveError as exc:
            report.errors.append(f"{relative}: {exc}")
            continue

        undirected_count = 0
        for block in blocks:
            if block.table_key is not None:
                report.directed.append((relative, block.table_key))
            else:
                undirected_count += 1
        if undirected_count:
            report.undirected.append((relative, undirected_count))

    return report


def render_report(report: CheckReport) -> str:
    lines = [
        f"Tablas con directiva: {len(report.directed)}",
        f"Tablas sin directiva (migración pendiente): {sum(count for _, count in report.undirected)}",
        f"Directivas inválidas: {len(report.errors)}",
    ]
    if report.undirected:
        lines.append("")
        lines.append("Archivos con tablas sin directiva:")
        lines.extend(f"  - {path}: {count}" for path, count in report.undirected)
    if report.errors:
        lines.append("")
        lines.append("Errores:")
        lines.extend(f"  - {message}" for message in report.errors)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Directorio con archivos .md a revisar")
    args = parser.parse_args()

    report = scan_directory(args.directory)
    print(render_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
