#!/usr/bin/env python3
"""Shared configuration helpers for university report automation.

Two roots, on purpose
---------------------
``ROOT`` is the CODE root: the checkout that ships templates, logo/background
assets, the Node toolchain and these tools. ``CONTENT_ROOT`` is the CONTENT
root: the tree that holds the actual coursework — ``reports/``,
``academic-sources/``, ``assets/generated/``, ``outputs/``, ``backups/``,
``build/`` and ``visuals/``.

They are separate because they have different lifecycles and different privacy
profiles. The code lives in a shared monorepo: it is versioned, reviewed,
rebuilt (``node_modules``, ``.venv``) and potentially public. The content is
personal academic work: it is private, it is not part of the monorepo history,
it grows per semester and it may live on a different disk or be relocated
entirely. Deriving both from ``Path(__file__).parents[1]`` silently routed every
report, source and rendered figure into the code checkout the moment the code
moved, which is exactly the failure this split prevents.

``CONTENT_ROOT`` is resolved once at import time from ``REPORT_CONTENT_ROOT``
when that environment variable is set, otherwise from ``DEFAULT_CONTENT_ROOT``.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Where the coursework lives when REPORT_CONTENT_ROOT says nothing else.
DEFAULT_CONTENT_ROOT = Path("/home/alejo/devwork/.projects/university/.reports-system/automation")

CONTENT_ROOT_ENV = "REPORT_CONTENT_ROOT"


def resolve_content_root(environ: dict[str, str] | None = None) -> Path:
    """Return the absolute, resolved content root.

    Kept as a function so tests can exercise the environment override without
    reimplementing the precedence rule. Production code should read the
    module-level ``CONTENT_ROOT``, which binds this once at import time.
    """
    env = os.environ if environ is None else environ
    override = (env.get(CONTENT_ROOT_ENV) or "").strip()
    base = Path(override) if override else DEFAULT_CONTENT_ROOT
    return base.expanduser().resolve()


CONTENT_ROOT = resolve_content_root()

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

# Sentinel telling "key absent" apart from a stored None/False value.
MISSING = object()

# academic_format.yml sections a single report.yml may relax for itself.
# Deliberately narrow: every other section stays globally owned.
OVERRIDABLE_SECTIONS = frozenset({"cover"})


def dig(source: Any, keys: tuple[str, ...]) -> Any:
    """Walk nested mappings, returning MISSING when any key is absent."""
    cursor: Any = source
    for key in keys:
        if not isinstance(cursor, dict) or key not in cursor:
            return MISSING
        cursor = cursor[key]
    return cursor


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
            "visual_pdf": False,  # opt-in via report.yml: validators: {visual_pdf: true}
            "docx": self.backend == "docx" or self.output_format == "docx",
        }
        for key, value in configured.items():
            validators[str(key)] = bool(value)
        return validators

    def academic_value(self, *keys: str, default: Any = None) -> Any:
        """Resolve a format value: report.yml -> academic_format.yml -> default.

        A report may relax a global rule for itself only (e.g. `cover:
        {required: false}` for a non-institutional deliverable). The override is
        resolved per key, so a partial block never shadows the rest of its
        section in academic_format.yml.

        Only sections in OVERRIDABLE_SECTIONS may be overridden. Top-level
        report.yml keys share a namespace with academic_format.yml sections, and
        several names already collide by accident: 31 reports carry a
        `validators:` block, and 15 carry a list-shaped `figures:` key. Without
        the allowlist those would silently shadow the format defaults the day
        someone reads them through this method.
        """
        if keys and keys[0] in OVERRIDABLE_SECTIONS and isinstance(self.raw.get(keys[0]), dict):
            override = dig(self.raw, keys)
            if override is not MISSING:
                return override
        value = dig(self.academic_format, keys)
        return default if value is MISSING else value

    @classmethod
    def load(cls, folder: Path) -> "ReportConfig":
        """Load a report folder's configuration (alias of load_report_config)."""
        return load_report_config(folder)


def relative_label(path: Path, base: Path) -> str:
    """Return ``path`` relative to ``base`` for logs, never raising.

    ``Path.relative_to`` raises ValueError for anything outside ``base``. Now
    that reports may live anywhere on disk, that turned every log line into a
    potential crash. A log message must never kill a build, so a path outside
    ``base`` degrades to its absolute form.
    """
    for candidate, root in ((path, base), (path.resolve(), base.resolve())):
        try:
            return str(candidate.relative_to(root))
        except ValueError:
            continue
    return str(path)


def relative_subpath(path: Path, base: Path) -> Path:
    """Return a RELATIVE path for ``path`` under ``base``, never raising.

    Used when the result is joined onto another directory (a backup mirror, for
    instance). Falling back to the absolute path would be actively harmful
    there — ``Path("/backup") / Path("/etc/x")`` is ``/etc/x`` — so anything
    outside ``base`` degrades to its basename instead.
    """
    for candidate, root in ((path, base), (path.resolve(), base.resolve())):
        try:
            return candidate.relative_to(root)
        except ValueError:
            continue
    return Path(path.name)


def resolve_in_folder(folder: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else folder / path


def read_yaml(path: Path) -> dict[str, Any]:
    # Imported lazily so that importing this module (and therefore CONTENT_ROOT)
    # stays dependency-free: source_library.py deliberately runs without PyYAML.
    import yaml

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
