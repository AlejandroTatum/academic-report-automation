#!/usr/bin/env python3
"""Print the single approval packet for a report folder (verify-concise-drafts T8, S2).

One Markdown message holds everything the approver needs: clickable links to the
draft PDF preview, ``body.md`` and the latest DOCX draft, the verify result, the
requirement -> evidence matrix, the missing items, the deletion candidates and
the findings. It is read-only: it never runs the verifier, builds or approves.
A stale or absent verification shows no matrix, so an old verdict is never
presented as current.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import content_check
import pdf_viewer
import yaml
from approval_marker import BODY_NAME, draft_is_fresh
from draft_docx import DRAFT_DIR
from report_config import ReportConfig, read_yaml

_DOCX_VERSION = re.compile(r"-borrador-v(\d+)\.docx$")


def preview_pdf(folder: Path) -> Path:
    return ReportConfig(folder=folder, raw=read_yaml(folder / "report.yml")).pdf_path


def _link(path: Path) -> str:
    return f"[{path.name}]({path.resolve().as_uri()})"


def _latest_docx(folder: Path) -> Path | None:
    drafts = [(int(m.group(1)), p) for p in (folder / DRAFT_DIR).glob("*.docx")
              if (m := _DOCX_VERSION.search(p.name))]
    return max(drafts)[1] if drafts else None


def _cell(value: object) -> str:
    return " ".join(str(value or "").split()).replace("|", "\\|")


def _files_section(folder: Path) -> list[str]:
    pdf, body = preview_pdf(folder), folder / BODY_NAME
    rebuild = "build_report_auto.py --no-approval-check"
    if not pdf.is_file():
        pdf_line = f"- Draft PDF: missing: build the preview with {rebuild}"
    elif not draft_is_fresh(pdf, body):
        pdf_line = f"- Draft PDF: {_link(pdf)} STALE: rebuild the preview with {rebuild}"
    else:
        pdf_line = f"- Draft PDF: {_link(pdf)}"
    lines = [pdf_line, f"- {BODY_NAME}: {_link(body)}"]
    docx = _latest_docx(folder)
    if docx is not None:
        lines.append(f"- DOCX draft: {_link(docx)}")
    return lines


def _listing(title: str, items: list[str]) -> list[str]:
    return ["", f"### {title} ({len(items)})", *([f"- {item}" for item in items] or ["- none"])]


def _verify_section(folder: Path) -> list[str]:
    state = content_check.content_check_state(folder)
    if state == "absent":
        return ["## Verify: absent: run the verifier first (content_check.py --verify-brief)"]
    if state == "stale":
        return ["## Verify: stale: re-run the verifier (content_check.py --verify-brief --since verification.yml)"]
    if state not in ("pass", "fail"):
        return [f"## Verify: {state}: content-check.yml cannot be read; re-run the verifier"]
    marker = yaml.safe_load((folder / content_check.CONTENT_CHECK_NAME).read_text(encoding="utf-8")) or {}
    requirements = [r for r in marker.get("requirements") or [] if isinstance(r, dict)]
    lines = [f"## Verify: {state}", "", "| Criterion | Requirement | Status | Location | Evidence |",
             "|---|---|---|---|---|"]
    lines += [f"| {_cell(r.get('criterion'))} | {_cell(r.get('requirement'))} | {_cell(r.get('status'))} "
              f"| {_cell(r.get('location'))} | {_cell(r.get('evidence'))} |" for r in requirements]
    missing = [f"{r.get('criterion')}: {r.get('requirement')}" for r in requirements if r.get("status") != "found"]
    lines += _listing("Missing", missing)
    lines += _listing("Deletion candidates", [str(p) for p in marker.get("unmapped_paragraphs") or []])
    lines += _listing("Findings", [str(f) for f in marker.get("findings") or []])
    return lines


def render(folder: Path) -> str:
    folder = Path(folder)
    return "\n".join([f"# Approval packet: {folder.name}", "", *_files_section(folder), "",
                      *_verify_section(folder)]) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print the approval packet (preview links, verify matrix, missing items); read-only."
    )
    parser.add_argument("folder", type=Path)
    parser.add_argument("--open", action="store_true",
                        help="also open the preview PDF for the reviewer, only when it is fresh")
    args = parser.parse_args(argv)
    if not (args.folder / "report.yml").is_file():
        print(f"approval packet input error: report folder not found: {args.folder}", file=sys.stderr)
        return 2
    try:
        print(render(args.folder), end="")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"approval packet input error: {exc}", file=sys.stderr)
        return 2
    if args.open:
        _open_preview(args.folder)
    return 0


def _open_preview(folder: Path) -> None:
    pdf = preview_pdf(folder)
    if not pdf.is_file() or not draft_is_fresh(pdf, folder / BODY_NAME):
        print("preview not opened: rebuild the preview first", file=sys.stderr)
        return
    error = pdf_viewer.open_pdf(pdf)
    print(f"preview not opened: {error}" if error else f"opened {pdf.resolve()}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
