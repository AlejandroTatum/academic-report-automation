#!/usr/bin/env python3
"""DOCX draft round-trip: export body.md for paraphrasing in Word, import the edits.

``export`` renders ``body.md`` through pandoc so equations become native Word
math (``m:oMath``), into a new ``borrador/<slug>-borrador-vNN.docx`` that never
overwrites an earlier draft. ``import`` converts an edited DOCX back to
Markdown and shows a unified diff against ``body.md``; ``body.md`` changes only
with ``--apply`` and the previous bytes are backed up first. Both refuse while
an editor holds a LibreOffice lock file, because a draft that is open would be
overwritten or read half-saved.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from report_config import ReportConfig, read_yaml

DRAFT_DIR = "borrador"
BACKUP_DIR = "backups"
EXPORT_ARGS = ["--columns=40"]
# ATX headings, `$...$` math kept as written, no re-wrapping of the user's prose.
IMPORT_ARGS = ["--wrap=none", "--markdown-headings=atx"]
IMPORT_FORMAT = "markdown-smart-raw_html-fenced_divs-bracketed_spans-native_divs-native_spans-link_attributes-header_attributes-escaped_line_breaks"


def _pypandoc():
    try:
        import pypandoc
    except ImportError:
        raise SystemExit("pypandoc is not installed: pip install pypandoc-binary")
    return pypandoc


def _refuse_locks(directory: Path, pattern: str, what: str) -> None:
    locks = sorted(directory.glob(pattern)) if directory.is_dir() else []
    if locks:
        print(
            f"Refusing: {what} is open in an editor ({locks[0].name}). Close it and retry.",
            file=sys.stderr,
        )
        raise SystemExit(2)


def _config(folder: Path) -> ReportConfig:
    return ReportConfig(folder=folder, raw=read_yaml(folder / "report.yml"))


def _next_draft(directory: Path, slug: str) -> Path:
    pattern = re.compile(rf"^{re.escape(slug)}-borrador-v(\d+)\.docx$")
    taken = [int(m.group(1)) for p in directory.glob("*.docx") if (m := pattern.match(p.name))]
    return directory / f"{slug}-borrador-v{max(taken, default=0) + 1:02d}.docx"


def export_draft(folder: Path) -> Path:
    """Write the next free ``borrador/<slug>-borrador-vNN.docx`` and return it."""
    folder = Path(folder).resolve()
    body = folder / "body.md"
    if not body.is_file():
        raise SystemExit(f"body.md not found in {folder}")
    directory = folder / DRAFT_DIR
    _refuse_locks(directory, ".~lock.*#", "a draft")
    config = _config(folder)
    title = str(config.metadata.get("title") or "").strip()
    header = f"---\ntitle: {json.dumps(title, ensure_ascii=False)}\n---\n\n" if title else ""
    directory.mkdir(parents=True, exist_ok=True)
    target = _next_draft(directory, config.document_slug)
    _pypandoc().convert_text(
        header + body.read_text(encoding="utf-8"),
        "docx",
        format="markdown",
        outputfile=str(target),
        extra_args=[f"--resource-path={folder}", *EXPORT_ARGS],
    )
    return target


def docx_to_markdown(docx: Path) -> str:
    return _pypandoc().convert_file(str(docx), IMPORT_FORMAT, format="docx", extra_args=IMPORT_ARGS)


def import_draft(folder: Path, docx: Path, *, apply: bool) -> int:
    folder = Path(folder).resolve()
    docx = Path(docx).resolve()
    body = folder / "body.md"
    if not docx.is_file():
        raise SystemExit(f"DOCX not found: {docx}")
    _refuse_locks(docx.parent, f".~lock.{docx.name}#", f"{docx.name}")
    old = body.read_text(encoding="utf-8") if body.is_file() else ""
    new = docx_to_markdown(docx)
    diff = list(difflib.unified_diff(
        old.splitlines(), new.splitlines(), "body.md", docx.name, lineterm="",
    ))
    print("\n".join(diff) if diff else "no differences against body.md")
    if not apply:
        print("\nbody.md not modified: re-run with --apply to write these changes.")
        return 0
    if not diff:
        return 0
    if body.is_file():
        backups = folder / BACKUP_DIR
        backups.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        (backups / f"body-{stamp}.md").write_bytes(body.read_bytes())
    body.write_text(new if new.endswith("\n") else new + "\n", encoding="utf-8")
    print(f"body.md updated from {docx.name}; it is now stale for approval: re-run doc_status.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    exp = sub.add_parser("export", help="body.md -> borrador/<slug>-borrador-vNN.docx")
    exp.add_argument("folder", type=Path)
    imp = sub.add_parser("import", help="show the diff of an edited DOCX against body.md")
    imp.add_argument("folder", type=Path)
    imp.add_argument("docx", type=Path)
    imp.add_argument("--apply", action="store_true", help="write body.md (backs up the previous one)")
    args = parser.parse_args(argv)
    if args.command == "export":
        print(export_draft(args.folder).as_uri())
        return 0
    return import_draft(args.folder, args.docx, apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
