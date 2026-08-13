#!/usr/bin/env python3
"""Verify a run's clean-delivery folder (issue #9).

The delivery folder must hold only approved finals after a run: every expected
PDF/DOCX exists, is non-empty, is readable, and carries a recorded SHA-256 and
page count, and no stray working artifact leaked in. Page counts come from
``pdfinfo`` for PDFs and from the explicit page breaks in DOCX XML.
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

PAGE_BREAK_TOKENS = ('w:type="page"', "w:type='page'")


@dataclass
class FileEvidence:
    """What the verifier proved about one expected final."""

    path: Path
    exists: bool
    readable: bool
    size_bytes: int | None
    sha256: str | None
    page_count: int | None
    errors: list[str] = field(default_factory=list)


@dataclass
class DeliveryResult:
    folder: Path
    files: list[FileEvidence]
    stray: list[Path]
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _resolve(folder: Path, expected: Path) -> Path:
    return expected if expected.is_absolute() else folder / expected


def _pdf_pages(path: Path) -> int | None:
    result = subprocess.run(["pdfinfo", str(path)], text=True, capture_output=True)
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() == "Pages":
            try:
                return int(value.strip())
            except ValueError:
                return None
    return None


def _docx_pages(path: Path) -> int | None:
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, KeyError, OSError):
        return None
    return sum(xml.count(token) for token in PAGE_BREAK_TOKENS) + 1


def _page_count(path: Path) -> int | None:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _pdf_pages(path)
    if suffix == ".docx":
        return _docx_pages(path)
    return None


def _verify_file(path: Path) -> FileEvidence:
    evidence = FileEvidence(path, exists=False, readable=False, size_bytes=None, sha256=None, page_count=None)
    if not path.exists():
        evidence.errors.append(f"missing expected final: {path.name}")
        return evidence
    evidence.exists = True
    try:
        data = path.read_bytes()
    except OSError:
        evidence.errors.append(f"not readable: {path.name}")
        return evidence
    evidence.readable = True
    evidence.size_bytes = len(data)
    if evidence.size_bytes == 0:
        evidence.errors.append(f"empty final: {path.name}")
    evidence.sha256 = hashlib.sha256(data).hexdigest()
    if path.suffix.lower() not in (".pdf", ".docx"):
        evidence.errors.append(f"unsupported final type: {path.name} — only PDF/DOCX allowed")
        return evidence
    evidence.page_count = _page_count(path)
    if evidence.page_count is None:
        evidence.errors.append(f"could not read page count: {path.name}")
    return evidence


def verify_delivery(folder: Path, expected: list[Path]) -> DeliveryResult:
    """Verify ``folder`` holds exactly the ``expected`` clean finals.

    ``ok`` is True only when every expected final passed existence,
    non-emptiness, readability, hash and page-count checks and no stray
    working artifact was found in the folder.
    """
    result = DeliveryResult(folder, files=[], stray=[])
    expected_set: set[Path] = set()
    for candidate in expected:
        path = _resolve(folder, candidate)
        expected_set.add(path)
        result.files.append(_verify_file(path))
    result.stray = sorted(
        path for path in folder.iterdir() if path.is_file() and path not in expected_set
    )
    if result.stray:
        names = ", ".join(path.name for path in result.stray)
        result.errors.append(f"non-final artifact(s) in delivery folder: {names}")
    result.errors.extend(
        error for evidence in result.files for error in evidence.errors
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a clean-delivery folder.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("expected", type=Path, nargs="+")
    args = parser.parse_args(argv)
    result = verify_delivery(args.folder, args.expected)
    for evidence in result.files:
        print(f"{evidence.path.name}: exists={evidence.exists} "
              f"readable={evidence.readable} bytes={evidence.size_bytes} "
              f"sha256={evidence.sha256} pages={evidence.page_count}")
    if result.stray:
        print("stray: " + ", ".join(path.name for path in result.stray))
    for error in result.errors:
        print(f"ERROR: {error}")
    print("PASS" if result.ok else "FAIL")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
