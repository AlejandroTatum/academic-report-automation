#!/usr/bin/env python3
"""Route final academic deliverables into subject-filtered output folders."""
from __future__ import annotations

import argparse
import re
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from report_config import CONTENT_ROOT, relative_label, relative_subpath

# Code root kept for callers that still import it; every path this module
# touches (deliverables, sources, reports, backups) is content, not code.
ROOT = Path(__file__).resolve().parents[1]
GLOBAL_OUTPUTS = CONTENT_ROOT / "outputs"
BACKUPS = CONTENT_ROOT / "backups"
FINAL_EXTENSIONS = {".pdf", ".docx"}
DELIVERY_BACKUP_EXTENSIONS = {".zip", ".md", ".html"}
INTERMEDIATE_EXTENSIONS = DELIVERY_BACKUP_EXTENSIONS | {".tex", ".log", ".aux", ".bbl", ".bcf", ".blg", ".out", ".toc", ".xml"}

SUBJECT_ALIASES: dict[str, str] = {
    "sistemas operativos": "sistemas-operativos",
    "sistema operativo": "sistemas-operativos",
    "operating systems": "sistemas-operativos",
    "diseno software": "diseno-software",
    "diseno de software": "diseno-software",
    "diseño software": "diseno-software",
    "diseño de software": "diseno-software",
    "software design": "diseno-software",
    "ecuaciones diferenciales": "ecuaciones-diferenciales",
    "ecuacion diferencial": "ecuaciones-diferenciales",
    "differential equations": "ecuaciones-diferenciales",
    "complejidad computacional": "complejidad-computacional",
    "complejidad": "complejidad-computacional",
    "computational complexity": "complejidad-computacional",
    "investigacion": "investigacion",
    "investigación": "investigacion",
    "metodologia investigacion": "investigacion",
    "metodologia de investigacion": "investigacion",
    "metodología de la investigación": "investigacion",
    "metodologia de la investigacion": "investigacion",
    "metodologia de la investigacion en computacion": "investigacion",
    "metodología de la investigación en computación": "investigacion",
}

FILENAME_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(sistemas?_operativos?|vm|contenedores|prompting_ia_so|\bso\b)", re.I), "sistemas-operativos"),
    (re.compile(r"(dis[eñ]o_software|ieee\s*830|rsd|der|cata_club)", re.I), "diseno-software"),
    (re.compile(r"(ecuaciones?_diferenciales?|equipotenciales?)", re.I), "ecuaciones-diferenciales"),
    (re.compile(r"(monte_?carlo|complejidad)", re.I), "complejidad-computacional"),
    (re.compile(r"(investigacion|investigaci[oó]n|metodologia|metodolog[ií]a|mapa_conceptual)", re.I), "investigacion"),
]


def slugify(value: str) -> str:
    """Normalize a human subject into the repo's ASCII folder slug style."""
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def known_subject_slugs() -> set[str]:
    slugs: set[str] = set()
    for base in (CONTENT_ROOT / "academic-sources", GLOBAL_OUTPUTS):
        if not base.exists():
            continue
        for child in base.iterdir():
            if child.is_dir() and not child.name.startswith(".") and child.name not in {"inbox", "_inbox"}:
                slugs.add(child.name)
    slugs.update(SUBJECT_ALIASES.values())
    return slugs


def subject_slug(subject: str | None) -> str | None:
    if not subject:
        return None
    normalized = " ".join(slugify(subject).split("-"))
    if normalized in SUBJECT_ALIASES:
        return SUBJECT_ALIASES[normalized]
    slug = slugify(subject)
    if slug in known_subject_slugs():
        return slug
    return None


def metadata_subject(metadata: dict[str, Any] | None) -> str | None:
    if not metadata:
        return None
    for key in ("subject", "asignatura", "materia"):
        value = metadata.get(key)
        if value:
            return str(value)
    return None


def infer_subject_for_path(path: Path, metadata: dict[str, Any] | None = None) -> str | None:
    """Return the output subject folder for a deliverable.

    Metadata wins. Filename hints are only a fallback for legacy loose files.
    """
    from_meta = subject_slug(metadata_subject(metadata))
    if from_meta:
        return from_meta

    name = path.name.replace("-", "_")
    for pattern, slug in FILENAME_HINTS:
        if pattern.search(name):
            return slug
    return None


def global_output_path(source: Path, metadata: dict[str, Any] | None = None) -> Path | None:
    slug = infer_subject_for_path(source, metadata)
    if not slug:
        return None
    return GLOBAL_OUTPUTS / slug / source.name


def publish_global_output(source: Path, metadata: dict[str, Any] | None = None) -> Path | None:
    """Copy a deliverable PDF/DOCX to outputs/<subject>/, preserving report-local output."""
    if not source.exists() or source.suffix.lower() not in FINAL_EXTENSIONS:
        return None
    destination = global_output_path(source, metadata)
    if not destination:
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    return destination


def read_report_metadata(report_folder: Path) -> dict[str, Any]:
    report_yml = report_folder / "report.yml"
    if not report_yml.exists():
        return {}
    data = yaml.safe_load(report_yml.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {}
    meta = dict(data.get("metadata") or {})
    for canonical, keys in {
        "subject": ["subject", "asignatura", "materia"],
        "title": ["title", "titulo", "tema"],
    }.items():
        if meta.get(canonical):
            continue
        for key in keys:
            if data.get(key):
                meta[canonical] = data[key]
                break
    return meta


def backup_intermediate(path: Path, backup_dir: Path, dry_run: bool) -> Path:
    destination = backup_dir / path.name
    counter = 1
    while destination.exists():
        destination = backup_dir / f"{path.stem}_{counter}{path.suffix}"
        counter += 1
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), destination)
    return destination


def unique_destination(destination: Path) -> Path:
    final_destination = destination
    counter = 1
    while final_destination.exists():
        final_destination = destination.with_name(f"{destination.stem}_{counter}{destination.suffix}")
        counter += 1
    return final_destination


def move_file(path: Path, destination: Path, dry_run: bool, replacement_backup_dir: Path | None = None) -> Path:
    final_destination = destination
    if not dry_run:
        final_destination.parent.mkdir(parents=True, exist_ok=True)
        if final_destination.resolve() != path.resolve():
            if final_destination.exists() and replacement_backup_dir:
                backup_path = unique_destination(
                    replacement_backup_dir / relative_subpath(final_destination, GLOBAL_OUTPUTS)
                )
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(final_destination), backup_path)
            shutil.move(str(path), final_destination)
    return final_destination


def output_dirs() -> list[Path]:
    """Output folders that must contain deliverables only."""
    dirs: list[Path] = []
    if GLOBAL_OUTPUTS.exists():
        dirs.append(GLOBAL_OUTPUTS)
        dirs.extend(sorted(path for path in GLOBAL_OUTPUTS.iterdir() if path.is_dir()))
    reports = CONTENT_ROOT / "reports"
    if reports.exists():
        dirs.extend(sorted(path for path in reports.glob("*/outputs") if path.is_dir()))
    return dirs


def backup_non_delivery(path: Path, backup_root: Path, dry_run: bool) -> Path:
    destination = backup_root / relative_subpath(path, CONTENT_ROOT)
    destination = unique_destination(destination)
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), destination)
    return destination


def clean_global_outputs(dry_run: bool = False) -> list[str]:
    """Keep every outputs/ folder limited to PDF/DOCX deliverables.

    Loose PDFs/DOCX in the global outputs root are routed into outputs/<materia>/.
    ZIP/MD/HTML and other non-delivery files are moved to backups/.
    """
    actions: list[str] = []
    if not GLOBAL_OUTPUTS.exists():
        return actions

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    non_delivery_backup = BACKUPS / f"outputs-cleanup-{timestamp}" / "non_delivery_outputs"
    final_backup = BACKUPS / f"outputs-cleanup-{timestamp}" / "previous_finals"

    # First, route loose global PDF/DOCX deliverables into subject folders.
    for item in sorted(GLOBAL_OUTPUTS.iterdir()):
        if item.is_dir() or item.name == ".gitkeep":
            continue
        suffix = item.suffix.lower()
        if suffix in FINAL_EXTENSIONS:
            destination = global_output_path(item)
            if destination:
                final_destination = move_file(item, destination, dry_run, replacement_backup_dir=final_backup)
                actions.append(
                    f"route final: {relative_label(item, CONTENT_ROOT)}"
                    f" -> {relative_label(final_destination, CONTENT_ROOT)}"
                )
            else:
                actions.append(f"unclassified PDF/DOCX left in place: {relative_label(item, CONTENT_ROOT)}")

    # Then enforce the clean outputs contract everywhere: only PDF/DOCX/.gitkeep.
    for out_dir in output_dirs():
        for item in sorted(out_dir.iterdir()):
            if item.is_dir() or item.name == ".gitkeep":
                continue
            if item.suffix.lower() in FINAL_EXTENSIONS:
                continue
            destination = backup_non_delivery(item, non_delivery_backup, dry_run)
            actions.append(
                f"backup non-delivery: {relative_label(item, CONTENT_ROOT)}"
                f" -> {relative_label(destination, CONTENT_ROOT)}"
            )
    return actions


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean/publish academic outputs by subject folder")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without moving files")
    args = parser.parse_args()
    actions = clean_global_outputs(dry_run=args.dry_run)
    if actions:
        print("\n".join(actions))
    else:
        print("Global outputs already clean.")


if __name__ == "__main__":
    main()
