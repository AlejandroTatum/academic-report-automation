#!/usr/bin/env python3
"""Open a PDF for the human reviewer, detached from the agent session.

Each human gate (draft approval, final review) opens the exact PDF under review
so the user never has to locate and launch it by hand. The viewer is
``$REPORT_PDF_VIEWER`` when set (a command, split on whitespace), else brave
(it follows internal links, zathura does not), else ``xdg-open``. Opening is a
convenience only: it never grants approval or review.
"""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

VIEWER_ENV = "REPORT_PDF_VIEWER"
DEFAULT_VIEWERS = ("brave", "xdg-open")


def viewer_command() -> list[str] | None:
    configured = os.environ.get(VIEWER_ENV, "").strip()
    candidates = [shlex.split(configured)] if configured else [[name] for name in DEFAULT_VIEWERS]
    for argv in candidates:
        resolved = shutil.which(argv[0])
        if resolved:
            return [resolved, *argv[1:]]
    return None


def open_pdf(path: Path) -> str | None:
    """Launch the viewer on ``path``; return an error message, or None when launched."""
    pdf = Path(path).resolve()
    if not pdf.is_file():
        return f"PDF not found: {pdf}"
    command = viewer_command()
    if command is None:
        names = os.environ.get(VIEWER_ENV) or ", ".join(DEFAULT_VIEWERS)
        return f"no PDF viewer found ({names}); open {pdf} by hand"
    try:
        subprocess.Popen([*command, str(pdf)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError as exc:
        return f"viewer failed to start: {exc}"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open a PDF in the reviewer's viewer, detached.")
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args(argv)
    error = open_pdf(args.pdf)
    if error is None:
        print(f"opened {args.pdf.resolve()}")
        return 0
    print(error, file=sys.stderr)
    return 2 if error.startswith("PDF not found") else 1


if __name__ == "__main__":
    raise SystemExit(main())
