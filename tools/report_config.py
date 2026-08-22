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
import re
import unicodedata
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

# ---------------------------------------------------------------------------
# Document routes
# ---------------------------------------------------------------------------
#
# `route:` in report.yml binds a report to one of the five routes defined in
# skills/academic-report-builder/references/document-routing.md. It is a
# CONTENT classification and is deliberately independent of `type:`/`backend:`
# (LATEX_TYPES/VISUAL_TYPES/DOCX_TYPES above are BACKEND classifications: they
# choose a renderer, they say nothing about whether the document is university
# coursework).
#
# Accepted values — the canonical name, or the route letter used by the
# contract:
#
#     route: academic   (or `a`)  Route A — university academic work
#     route: project    (or `b`)  Route B — project documentation
#     route: business   (or `c`)  Route C — professional/business report
#     route: technical  (or `d`)  Route D — technical document
#     route: other      (or `e`)  Route E — other
#
# Values are compared case-insensitively and trimmed. An absent key means
# Route A, which is what every existing report already relies on. An
# unrecognised value is a hard error: the routing contract is emphatic that
# nothing may fall back silently to the academic route.
ROUTE_KEY = "route"
DEFAULT_ROUTE = "academic"

ROUTE_ALIASES = {
    "a": "academic",
    "b": "project",
    "c": "business",
    "d": "technical",
    "e": "other",
}

PUBLICATION_CATEGORIES = {
    "academic": "Academicos",
    "project": "Proyectos",
    "business": "Profesionales",
    "technical": "Tecnicos",
    "other": "Otros",
}


def ascii_slug(value: object) -> str:
    """Return a stable filesystem-safe ASCII slug for a confirmed identity."""
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "documento"

# Metadata report.yml must carry, per route. Only Route A may demand the
# academic machinery (`subject`, `teacher`); the other routes are forbidden by
# the contract from auto-including it, so requiring it there forced users to
# invent fake values. Title, author and date stay universal: every document has
# a name, someone who wrote it and a date.
ROUTE_REQUIRED_METADATA: dict[str, tuple[str, ...]] = {
    "academic": ("title", "subject", "teacher", "student", "date"),
    "project": ("title", "student", "date"),
    "business": ("title", "student", "date"),
    "technical": ("title", "student", "date"),
    "other": ("title", "student", "date"),
}

# Metadata that belongs to the academic shell only. Present on another route it
# is a contract smell, not a build failure — hence a warning.
ACADEMIC_ONLY_METADATA = ("subject", "teacher")


def unknown_route_message(route: str) -> str:
    """Spanish guidance for a `route:` value no route table recognises."""
    accepted = ", ".join(sorted(ROUTE_REQUIRED_METADATA))
    return (
        f"Ruta de documento desconocida en report.yml: '{route}'. "
        f"Valores aceptados en 'route': {accepted} "
        "(o las letras a, b, c, d, e). Sin 'route' se asume ruta académica."
    )


# ---------------------------------------------------------------------------
# Final-output layout rule
# ---------------------------------------------------------------------------

LOCAL_OUTPUTS_ERROR = (
    "No guardar resultados finales en reports/<trabajo>/outputs/: "
    "usar solamente outputs/<materia>/ para evitar duplicados"
)


def targets_local_outputs(config: "ReportConfig") -> bool:
    """True when the configured final PDF lands in ``<report folder>/outputs/``.

    The rule has no exemptions, and this is the single predicate behind it: the
    load-time guard in ``load_report_config`` and the post-build check in
    ``validate_report`` both ask this function, so the two can never disagree
    about the same report.

    Folders named with a leading ``_`` used to be exempt, on the grounds that an
    example report kept its output next to itself. That justification named
    ``_example_latex_essay``, which is not versioned here — it lives in the
    private content tree — so a validation rule carved out an exception for a
    file no reader of this repository can open. It never needed the exception
    either: it writes its final PDF to ``build/``. The example that IS shipped
    here, ``examples/ejemplo_informe_academico``, satisfies this rule outright,
    which is the point of shipping it — the pattern people copy is the pattern
    the validator enforces.

    The ``_`` prefix keeps its one genuine meaning in ``publish_global``:
    scratch work, no global copy. That is a publication decision. Where the
    final file may be written is a layout decision. Reading one prefix as both
    meant that marking a report as scratch silently switched off a layout rule
    nobody asked to switch off.
    """
    if config.output_format != "pdf":
        return False
    return (config.folder / "outputs").resolve() in config.pdf_path.resolve().parents


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
    def route(self) -> str:
        """Canonical document route for this report.

        Returns the canonical name (``academic``, ``project``, ``business``,
        ``technical``, ``other``) for a recognised value, ``DEFAULT_ROUTE``
        when the key is absent, and the written value verbatim when it is not
        recognised — so the caller can name it in the error instead of
        guessing a route on the user's behalf.
        """
        written = str(self.raw.get(ROUTE_KEY) or "").strip().lower()
        if not written:
            return DEFAULT_ROUTE
        return ROUTE_ALIASES.get(written, written)

    @property
    def route_is_known(self) -> bool:
        return self.route in ROUTE_REQUIRED_METADATA

    @property
    def required_metadata(self) -> tuple[str, ...]:
        """Metadata keys this report's route genuinely needs.

        Raises ValueError for an unrecognised route: there is no defensible
        default here, and silently answering with the academic set is exactly
        the fallback the routing contract forbids. Callers check
        ``route_is_known`` first and report ``unknown_route_message``.
        """
        if not self.route_is_known:
            raise ValueError(unknown_route_message(self.route))
        return ROUTE_REQUIRED_METADATA[self.route]

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
        """Whether a copy of the final file belongs in ``outputs/<materia>/``.

        A leading ``_`` in the folder name is the default answer for scratch
        work — drafts and experiments are not deliverables, so they are not
        published. That is the prefix's only meaning: it says nothing about
        where the final file may be written, which is
        ``targets_local_outputs``' business. Writing ``publish_global:`` in
        report.yml overrides the guess in either direction, and a report whose
        ``pdf:`` already points into ``outputs/<materia>/`` normally sets it to
        false so the deliverable is not copied on top of itself.
        """
        if "publish_global" in self.raw:
            return bool(self.raw.get("publish_global"))
        return not self.folder.name.startswith("_")

    @property
    def publication_category(self) -> str:
        """Documents category derived only from the confirmed route."""
        return PUBLICATION_CATEGORIES[self.route]

    @property
    def document_slug(self) -> str:
        """Stable ASCII identity derived from the confirmed report title."""
        return ascii_slug(self.metadata.get("title") or self.folder.name)

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
            # Non-academic routes name the same field "author"; it is the same
            # person, so it resolves to the same canonical key.
            "student": ["student", "estudiante", "nombre", "author", "autor"],
            "date": ["date", "fecha"],
            "career": ["career", "carrera"],
            "parallel": ["parallel", "paralelo"],
            "members": ["members", "integrantes", "miembros"],
        }
        for canonical, keys in aliases.items():
            if canonical in meta and meta[canonical]:
                continue
            for key in keys:
                value = meta.get(key) or self.raw.get(key)
                if value:
                    meta[canonical] = value
                    break
        # Paralelo is data, not a question (#8): the intake never asks for it,
        # renderers default to A, and an explicit assignment value in report.yml
        # (metadata.parallel/metadata.paralelo) overrides the default.
        meta.setdefault("parallel", "A")
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
    """Load and sanity-check a report folder's configuration.

    Two rules are enforced here rather than after the build, because both are
    knowable from report.yml alone and both otherwise cost the user three
    LuaLaTeX passes before they hear about it:

    * an unrecognised ``route:`` value (no silent fallback to Route A);
    * a final PDF pointed at ``reports/<work>/outputs/``.

    The output rule only fires for a path the report actually declares. A
    report that never wrote ``pdf:`` has nothing to correct in its own file;
    the post-build check in ``validate_report`` still covers that case.
    """
    folder = folder.resolve()
    report_yml = folder / "report.yml"
    if not report_yml.exists():
        raise SystemExit(f"No existe report.yml en {folder}")
    raw = read_yaml(report_yml)
    academic = read_yaml(DEFAULT_FORMAT)
    config = ReportConfig(folder=folder, raw=raw, academic_format=academic)

    if not config.route_is_known:
        raise SystemExit(unknown_route_message(config.route))

    declares_final_pdf = any(key in raw for key in ("pdf", "output_pdf"))
    if declares_final_pdf and targets_local_outputs(config):
        raise SystemExit(f"{LOCAL_OUTPUTS_ERROR}\nRuta configurada: {config.pdf_path}")

    return config


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
