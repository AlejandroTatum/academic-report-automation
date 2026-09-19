"""Shared pytest helpers for the document-workflow status suites.

Every ``doc_status`` phase test starts from the same on-disk shapes, so the
builders live here once instead of being copy-pasted per file. They are plain
functions rather than fixtures: a test may call a builder as many times as its
scenario needs. Slice 2a adds the intake/research/preview shapes; slice 2b-i adds
the approval shape and its marker builder; slice 2b-ii adds the final-PDF builder
and the timestamp helper its mtime comparison needs; slice 2b-iii adds the
validation receipt and the published-PDF builder the validate/deliver phases read.

The helpers never touch production code. ``doc_status`` stays a pure, read-only
derivation; these functions only materialize the artifacts it reads and the
``ReportConfig`` the phase handlers take as an argument.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from report_config import ReportConfig, read_yaml

DEFAULT_PREVIEW = "# Content Preview: Informe\n\nCuerpo.\n"
DEFAULT_BODY = "# Informe\n\nCuerpo del documento.\n"
DEFAULT_MATRIX = "| claim | source |\n| --- | --- |\n"
APPROVAL_SCHEMA = "academic.doc-approval/v1"
VALIDATION_SCHEMA = "academic.doc-validation/v1"

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


def _body(folder: Path, text: str = DEFAULT_BODY) -> Path:
    """Write a ``body.md`` under ``folder`` and return its path."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "body.md"
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
    """Build the same ``ReportConfig`` the phase handlers receive.

    Mirrors the production rule (build directly, never ``load_report_config``):
    a missing ``report.yml`` is an empty mapping, not a ``SystemExit``.
    """
    return ReportConfig(folder=folder, raw=read_yaml(folder / "report.yml"))


# ---------------------------------------------------------------------------
# Late-phase builders (slice 2b-i): approval
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    """Hash fixture bytes the way ``sha256_file`` would, without importing it."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _yaml(body: dict[str, object]) -> str:
    import yaml

    return yaml.safe_dump(body, sort_keys=False, allow_unicode=False)


def _approval(
    folder: Path,
    *,
    preview: str | None = None,
    preview_sha256: str | None = None,
    body: str | None = None,
    body_sha256: str | None = None,
    drop: tuple[str, ...] = (),
    **fields: object,
) -> Path:
    """Write ``preview.md`` and ``body.md`` plus an ``approval.yml`` bound to both.

    Defaults produce a current marker. ``preview``/``body`` rewrite those files
    before hashing (the normal shape), ``preview_sha256``/``body_sha256`` override
    the recorded hash (a stale marker), and ``drop`` removes required keys (a
    malformed marker).
    """
    folder.mkdir(parents=True, exist_ok=True)
    preview_path = folder / "preview.md"
    if preview is not None or not preview_path.is_file():
        preview_path.write_text(preview if preview is not None else DEFAULT_PREVIEW, encoding="utf-8")
    body_path = folder / "body.md"
    if body is not None or not body_path.is_file():
        body_path.write_text(body if body is not None else DEFAULT_BODY, encoding="utf-8")
    marker_body: dict[str, object] = {
        "schema": APPROVAL_SCHEMA,
        "preview_sha256": preview_sha256 or _sha256(preview_path),
        "body_sha256": body_sha256 or _sha256(body_path),
        "approved_at": "2026-09-10T14:03:11Z",
        "approved_by": "Alejandro",
    }
    marker_body.update(fields)
    for key in drop:
        marker_body.pop(key, None)
    marker = folder / "approval.yml"
    marker.write_text(_yaml(marker_body), encoding="utf-8")
    return marker


def _marker_text(folder: Path, text: str) -> Path:
    """Write raw ``approval.yml`` text, for unparsable-marker scenarios."""
    folder.mkdir(parents=True, exist_ok=True)
    marker = folder / "approval.yml"
    marker.write_text(text, encoding="utf-8")
    return marker


# ---------------------------------------------------------------------------
# Late-phase builders (slice 2b-ii): generate
# ---------------------------------------------------------------------------


def _mtime(path: Path, value: float) -> Path:
    """Pin ``path``'s modification time, so mtime ordering is explicit.

    The generate phase compares the final PDF against ``approval.yml`` by mtime;
    tests fix both sides instead of depending on wall-clock ordering or the
    filesystem's timestamp resolution.
    """
    os.utime(path, (value, value))
    return path


def _pdf(folder: Path, *, path: str = "outputs/report.pdf", mtime: float | None = None) -> Path:
    """Write the final PDF under ``folder`` and return its path.

    ``path`` mirrors the ``pdf:`` key the derivation resolves through
    ``ReportConfig``; it defaults to the same ``outputs/report.pdf`` the config
    uses when the report declares nothing. ``mtime`` pins the timestamp the
    generate phase compares against the approval marker.
    """
    target = Path(path)
    if not target.is_absolute():
        target = folder / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"%PDF-1.4\n%%EOF\n")
    if mtime is not None:
        _mtime(target, mtime)
    return target


# ---------------------------------------------------------------------------
# Late-phase builders (slice 2b-iii): validate + deliver
# ---------------------------------------------------------------------------


def _validation(
    folder: Path,
    *,
    pdf: Path | None = None,
    result: str = "pass",
    artifact_sha256: str | None = None,
    drop: tuple[str, ...] = (),
    **fields: object,
) -> Path:
    """Write ``validation.yml`` under ``folder`` and return its path.

    Defaults produce the pass receipt for the folder's configured final PDF:
    ``artifact_sha256`` is recomputed from that PDF unless a test overrides it
    (the mismatched-hash shape) or drops the key. ``result`` switches the receipt
    between pass and fail, mirroring the two branches the validate phase reads.
    """
    folder.mkdir(parents=True, exist_ok=True)
    target = pdf if pdf is not None else folder / "outputs" / "report.pdf"
    body: dict[str, object] = {
        "schema": VALIDATION_SCHEMA,
        "artifact_sha256": artifact_sha256 or _sha256(target),
        "result": result,
        "mode": "fallback",
        "gates": ["BUILD_PASS", "VALIDATION_PASS"],
        "recorded_at": "2026-09-10T15:00:00Z",
        "evidence": "backups/quality_report.md",
    }
    body.update(fields)
    for key in drop:
        body.pop(key, None)
    path = folder / "validation.yml"
    path.write_text(_yaml(body), encoding="utf-8")
    return path


def _published(
    root: Path,
    *,
    category: str,
    slug: str,
    source: Path | None = None,
    content: bytes | None = None,
    version: int = 1,
    name: str | None = None,
) -> Path:
    """Write a versioned PDF into ``root/<category>/<slug>/`` and return its path.

    The deliver phase hash-matches the final PDF against every ``<slug>-vNNN.pdf``
    in that folder. ``source`` copies an existing PDF byte-for-byte (the hash-equal
    shape), while ``content`` writes explicit bytes (the mismatched shape);
    ``version``/``name`` place the file at any version.
    """
    directory = root / category / slug
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (name or f"{slug}-v{version:03d}.pdf")
    if content is not None:
        target.write_bytes(content)
    elif source is not None:
        target.write_bytes(Path(source).read_bytes())
    else:
        target.write_bytes(b"%PDF-1.4\n%%EOF\n")
    return target
