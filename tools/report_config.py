#!/usr/bin/env python3
"""Shared configuration helpers for university report automation."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FORMAT = ROOT / "templates" / "academic_format.yml"

LATEX_TYPES = {
    "essay",
    "ensayo",
    "research",
    "investigation",
    "investigacion",
    "informe",
    "report",
    "mixed_report",
    "technical_report",
}
VISUAL_TYPES = {
    "visual",
    "visual_map",
    "mapa_conceptual",
    "concept_map",
    "infographic",
    "infografia",
    "diagram",
    "diagrama",
}
DOCX_TYPES = {"docx", "word", "docx_required", "plantilla_word"}


@dataclass
class ReportConfig:
    folder: Path
    raw: dict[str, Any]
    academic_format: dict[str, Any] = field(default_factory=dict)

    @property
    def type(self) -> str:
        return str(self.raw.get("type") or self.raw.get("tipo") or "essay").strip().lower()

    @property
    def backend(self) -> str:
        backend = str(self.raw.get("backend") or "auto").strip().lower()
        if backend != "auto":
            return backend
        if self.type in VISUAL_TYPES:
            return "visual"
        if self.type in DOCX_TYPES or str(self.raw.get("output", "")).lower() == "docx":
            return "docx"
        return "latex"

    @property
    def output_format(self) -> str:
        return str(self.raw.get("output") or "pdf").strip().lower()

    @property
    def publish_global(self) -> bool:
        if "publish_global" in self.raw:
            return bool(self.raw.get("publish_global"))
        return not self.folder.name.startswith("_")

    @property
    def body_path(self) -> Path:
        value = self.raw.get("body") or "body.md"
        return resolve_in_folder(self.folder, value)

    @property
    def bib_path(self) -> Path | None:
        value = self.raw.get("bibliography") or self.raw.get("bib") or "sources.bib"
        path = resolve_in_folder(self.folder, value)
        return path if path.exists() else None

    @property
    def tex_path(self) -> Path:
        value = self.raw.get("tex") or "build/main.tex"
        return resolve_in_folder(self.folder, value)

    @property
    def pdf_path(self) -> Path:
        value = self.raw.get("pdf") or self.raw.get("output_pdf") or "outputs/report.pdf"
        return resolve_in_folder(self.folder, value)

    @property
    def docx_path(self) -> Path:
        value = self.raw.get("docx") or self.raw.get("output_docx") or "outputs/report.docx"
        return resolve_in_folder(self.folder, value)

    @property
    def log_path(self) -> Path:
        value = self.raw.get("latex_log") or "build/main.log"
        return resolve_in_folder(self.folder, value)

    @property
    def quality_report_path(self) -> Path:
        value = self.raw.get("quality_report") or "backups/quality_report.md"
        return resolve_in_folder(self.folder, value)

    @property
    def metadata(self) -> dict[str, Any]:
        meta = dict(self.raw.get("metadata") or {})
        aliases = {
            "title": ["title", "titulo", "tema"],
            "subject": ["subject", "asignatura"],
            "teacher": ["teacher", "docente"],
            "student": ["student", "estudiante", "nombre"],
            "date": ["date", "fecha"],
            "career": ["career", "carrera"],
            "parallel": ["parallel", "paralelo"],
        }
        for canonical, keys in aliases.items():
            if canonical in meta and meta[canonical]:
                continue
            for key in keys:
                if self.raw.get(key):
                    meta[canonical] = self.raw[key]
                    break
        return meta

    @property
    def validators(self) -> dict[str, bool]:
        configured = dict(self.raw.get("validators") or {})
        validators = {
            "common": True,
            "ieee": True,
            "pdf_layout": self.output_format == "pdf" or self.pdf_path.exists(),
            "latex": self.backend == "latex",
            "latex_log": self.backend == "latex",
            "visual": self.backend == "visual" or self.type in VISUAL_TYPES,
            "docx": self.backend == "docx" or self.output_format == "docx",
        }
        for key, value in configured.items():
            validators[str(key)] = bool(value)
        return validators

    def academic_value(self, *keys: str, default: Any = None) -> Any:
        cursor: Any = self.academic_format
        for key in keys:
            if not isinstance(cursor, dict) or key not in cursor:
                return default
            cursor = cursor[key]
        return cursor


def resolve_in_folder(folder: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else folder / path


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def load_report_config(folder: Path) -> ReportConfig:
    folder = folder.resolve()
    report_yml = folder / "report.yml"
    if not report_yml.exists():
        raise SystemExit(f"No existe report.yml en {folder}")
    raw = read_yaml(report_yml)
    academic = read_yaml(DEFAULT_FORMAT)
    return ReportConfig(folder=folder, raw=raw, academic_format=academic)


def latex_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)
