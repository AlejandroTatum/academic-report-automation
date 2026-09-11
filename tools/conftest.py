"""Shared pytest helpers for the document-workflow status suites.

Every ``doc_status`` phase test starts from the same on-disk shapes, so the
builders live here once instead of being copy-pasted per file. They are plain
functions rather than fixtures: a test may call a builder as many times as its
scenario needs. Slice 2a adds the intake/research/preview shapes; the
approval/generate/validate/deliver builders arrive with slice 2b.

The helpers never touch production code. ``doc_status`` stays a pure, read-only
derivation; these functions only materialize the artifacts it reads and the
``ReportConfig`` the early handlers take as an argument.
"""
from __future__ import annotations

from pathlib import Path

from report_config import ReportConfig, read_yaml

DEFAULT_PREVIEW = "# Content Preview: Informe\n\nCuerpo.\n"
DEFAULT_MATRIX = "| claim | source |\n| --- | --- |\n"

# Route-mandatory metadata for the default (academic) route the builders use.
_DEFAULT_METADATA = {
    "title": "Informe de Laboratorio",
    "subject": "Fisica",
    "teacher": "Ing. Perez",
    "student": "Alejandro",
    "date": "2026-09-10",
}


def _report(folder: Path, *, route: str | None = "academic", **metadata: object) -> Path:
    """Write a ``report.yml`` under ``folder`` and return its path.

    ``route=None`` omits the key entirely (Route A is the absent-key default).
    ``metadata`` overrides the default body; a ``None`` value drops that key, which
    is how a test builds a route with missing mandatory metadata.
    """
    folder.mkdir(parents=True, exist_ok=True)
    lines = ["type: ensayo"]
    if route is not None:
        lines.append(f"route: {route}")
    body = dict(_DEFAULT_METADATA)
    body.update(metadata)
    lines.append("metadata:")
    for key, value in body.items():
        if value is None:
            continue
        lines.append(f"  {key}: {value}")
    path = folder / "report.yml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _skip_research(folder: Path, value: str = "skipped") -> None:
    """Append the top-level ``research:`` key to an existing ``report.yml``."""
    report = folder / "report.yml"
    report.write_text(report.read_text(encoding="utf-8") + f"research: {value}\n", encoding="utf-8")


def _preview(folder: Path, text: str = DEFAULT_PREVIEW) -> Path:
    """Write a ``preview.md`` under ``folder`` and return its path."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "preview.md"
    path.write_text(text, encoding="utf-8")
    return path


def _evidence_matrix(folder: Path, text: str = DEFAULT_MATRIX) -> Path:
    """Write ``research/evidence-matrix.md`` under ``folder`` and return its path."""
    research = folder / "research"
    research.mkdir(parents=True, exist_ok=True)
    path = research / "evidence-matrix.md"
    path.write_text(text, encoding="utf-8")
    return path


def _config(folder: Path) -> ReportConfig:
    """Build the same ``ReportConfig`` the early handlers receive.

    Mirrors the production rule (build directly, never ``load_report_config``):
    a missing ``report.yml`` is an empty mapping, not a ``SystemExit``.
    """
    return ReportConfig(folder=folder, raw=read_yaml(folder / "report.yml"))
