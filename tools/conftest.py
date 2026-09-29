"""Shared pytest helpers for the document-workflow status suites.

Every ``doc_status`` phase test starts from the same on-disk shapes, so the
builders live here once instead of being copy-pasted per file. They are plain
functions rather than fixtures: a test may call a builder as many times as its
scenario needs. Slice 2a adds the intake/research shapes; slice 2b-i adds the
approval shape and its marker builder; slice 2b-ii adds the final-PDF builder
and the timestamp helper its mtime comparison needs; slice 2b-iii adds the
validation receipt and the published-PDF builder the validate/deliver phases
read. new-report-flow T5 adds the format-choice builder and binds the content
check to the rubric and bib hashes.

The helpers never touch production code. ``doc_status`` stays a pure, read-only
derivation; these functions only materialize the artifacts it reads and the
``ReportConfig`` the phase handlers take as an argument.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from report_config import ReportConfig, read_yaml

DEFAULT_BODY = "# Informe\n\nCuerpo del documento.\n"
DEFAULT_MATRIX = "| claim | source |\n| --- | --- |\n"
APPROVAL_SCHEMA = "academic.doc-approval/v1"
FINAL_REVIEW_SCHEMA = "academic.doc-final-review/v1"
VALIDATION_SCHEMA = "academic.doc-validation/v1"
RUBRIC_SCHEMA = "academic.rubric/v1"
CONTENT_CHECK_SCHEMA = "academic.content-check/v1"

# new-report-flow T3: the default plan shape (two criteria mapped to body.md
# headings) and a body that cites the five eligible keys ``_sources_bib``
# writes, so a content check can pass with its minimum source count met.
DEFAULT_RUBRIC_CRITERIA = (
    {"id": "objetivo", "title": "Objetivo claro", "section": "Objetivos"},
    {"id": "metodologia", "title": "Metodologia descrita", "section": "Metodologia"},
)
DEFAULT_CITED_BODY = "# Informe\n\nCuerpo con fuentes [@key1] y [@key2], mas [@key3], [@key4] y [@key5].\n"

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

    Declares an explicit ``pdf:`` outside ``outputs/`` (``final/report.pdf``, the
    same location ``_pdf()`` writes to by default): these fixtures exist to test
    phase-status logic, not ``ReportConfig``'s own default-path derivation, and a
    report with nothing declared now derives its final path under the content
    root by route/subject -- a location these tests have no reason to depend on.
    A test that wants a different declared path (or none) still writes its own
    ``pdf:``/``docx:`` line after calling this, and the later line wins.
    """
    folder.mkdir(parents=True, exist_ok=True)
    lines = ["type: ensayo", "pdf: final/report.pdf"]
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
    """Append the legacy top-level ``research:`` key to an existing ``report.yml``.

    new-report-flow T2 removed the recorded-skip shortcut: the research phase no
    longer reads this key as ``done``. The builder stays only so tests can write
    the key and prove it is ignored.
    """
    report = folder / "report.yml"
    report.write_text(report.read_text(encoding="utf-8") + f"research: {value}\n", encoding="utf-8")


def _sources_bib(folder: Path, count: int = 5, name: str = "sources.bib") -> Path:
    """Write a BibTeX file with ``count`` eligible book-or-paper entries.

    The research phase is done only when the report's BibTeX file holds at
    least five eligible entries (new-report-flow T2), so later-phase fixtures
    call this with the default ``count=5`` to get past research.
    """
    folder.mkdir(parents=True, exist_ok=True)
    types = ("book", "article", "inproceedings", "phdthesis", "incollection")
    lines = []
    for i in range(count):
        entry_type = types[i % len(types)]
        lines.append(f'@{entry_type}{{key{i + 1}, title = "Title {i + 1}"}}')
    path = folder / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _body(folder: Path, text: str = DEFAULT_BODY) -> Path:
    """Write a ``body.md`` under ``folder`` and return its path."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "body.md"
    path.write_text(text, encoding="utf-8")
    return path


def _cited_body(folder: Path, text: str = DEFAULT_CITED_BODY) -> Path:
    """Write a ``body.md`` that cites the five keys ``_sources_bib`` writes."""
    return _body(folder, text)


def _rubric(
    folder: Path,
    *,
    criteria: tuple[dict[str, object], ...] | None = None,
    source: str = "guia de la catedra",
    schema: str = RUBRIC_SCHEMA,
) -> Path:
    """Write a valid ``rubric.yml`` under ``folder`` and return its path.

    ``criteria`` replaces the default two-criterion plan; an empty tuple drops
    the key, which is how a test builds an invalid plan.
    """
    folder.mkdir(parents=True, exist_ok=True)
    body: dict[str, object] = {"schema": schema, "source": source}
    if criteria is None:
        body["criteria"] = [dict(c) for c in DEFAULT_RUBRIC_CRITERIA]
    elif criteria:
        body["criteria"] = [dict(c) for c in criteria]
    path = folder / "rubric.yml"
    path.write_text(_yaml(body), encoding="utf-8")
    return path


def _judgments(
    folder: Path,
    *,
    name: str = "judgments.yml",
    criteria: list[dict[str, object]] | None = None,
    findings: list[str] | None = None,
) -> Path:
    """Write an agent judgments file (content-check input) and return its path.

    Defaults judge every ``DEFAULT_RUBRIC_CRITERIA`` id ``cumple``; ``criteria``
    replaces the records verbatim and ``findings`` adds the free-text list.
    """
    folder.mkdir(parents=True, exist_ok=True)
    if criteria is None:
        criteria = [
            {"id": c["id"], "status": "cumple", "where": str(c["section"]), "note": "ok"}
            for c in DEFAULT_RUBRIC_CRITERIA
        ]
    config = _config(folder)
    inputs = ["rubric.yml", "body.md", config.bib_path.name if config.bib_path else "sources.bib"]
    if config.raw.get("guide"):
        inputs.append(Path(str(config.raw["guide"])).name)
    body: dict[str, object] = {
        "judge": {"role": "independent", "inputs": inputs},
        "body_sha256": _sha256(folder / "body.md") if (folder / "body.md").is_file() else "",
        "rubric_sha256": _sha256(folder / "rubric.yml") if (folder / "rubric.yml").is_file() else "",
        "criteria": criteria,
    }
    if findings is not None:
        body["findings"] = findings
    path = folder / name
    path.write_text(_yaml(body), encoding="utf-8")
    return path


def _content_check(
    folder: Path,
    *,
    body_sha256: str | None = None,
    result: str = "pass",
    drop: tuple[str, ...] = (),
    **fields: object,
) -> Path:
    """Write a well-formed ``content-check.yml`` bound to the current artifacts.

    Defaults produce a ``pass`` marker over whatever ``body.md`` holds (it must
    exist first); ``body_sha256`` overrides the recorded hash (stale), ``drop``
    removes required keys and ``result``/``criteria`` build honest fail shapes.
    The marker also binds ``rubric.yml`` and the document bib (new-report-flow
    T5): both files are created with their default shape when missing, so the
    recorded hashes match unless a test edits them afterwards.
    """
    folder.mkdir(parents=True, exist_ok=True)
    body_path = folder / "body.md"
    if not body_path.is_file():
        body_path.write_text(DEFAULT_BODY, encoding="utf-8")
    if not (folder / "rubric.yml").is_file():
        _rubric(folder)
    config = _config(folder)
    if config.bib_path is None:
        _sources_bib(folder)
        config = _config(folder)
    marker_body: dict[str, object] = {
        "schema": CONTENT_CHECK_SCHEMA,
        "body_sha256": body_sha256 or _sha256(body_path),
        "rubric_sha256": _sha256(folder / "rubric.yml"),
        "bib_sha256": _sha256(config.bib_path) if config.bib_path else "",
        "judge": {"role": "independent", "inputs": ["rubric.yml", "body.md", config.bib_path.name if config.bib_path else "sources.bib"]},
        "checked_at": "2026-09-28T10:00:00+00:00",
        "criteria": [
            {"id": c["id"], "status": "cumple", "where": str(c["section"]), "note": "ok"}
            for c in DEFAULT_RUBRIC_CRITERIA
        ],
        "findings": [],
        "mechanical": [
            {"check": name, "ok": True, "detail": "ok"}
            for name in ("citations_resolve", "eligible_sources_cited", "judgments_match_rubric", "rubric_checks")
        ],
        "result": result,
    }
    marker_body.update(fields)
    for key in drop:
        marker_body.pop(key, None)
    marker = folder / "content-check.yml"
    marker.write_text(_yaml(marker_body), encoding="utf-8")
    return marker


def _evidence_matrix(folder: Path, text: str = DEFAULT_MATRIX) -> Path:
    """Write ``research/evidence-matrix.md`` under ``folder`` and return its path."""
    research = folder / "research"
    research.mkdir(parents=True, exist_ok=True)
    path = research / "evidence-matrix.md"
    path.write_text(text, encoding="utf-8")
    return path


def _evidence_yml(folder: Path, text: str | None = None) -> Path:
    """Write a valid ``research/evidence.yml`` (the #11 structured package).

    A custom ``text`` replaces the default single valid claim, e.g. to build
    an invalid package for a negative test.
    """
    research = folder / "research"
    research.mkdir(parents=True, exist_ok=True)
    path = research / "evidence.yml"
    if text is None:
        text = (
            "claims:\n"
            "  - claim_id: c1\n"
            "    section: introduction\n"
            "    source_id: s1\n"
            "    source_class: book\n"
            "    locator: p. 12\n"
            "    citation_key: key1\n"
            "    evidence: Verbatim finding.\n"
            "    confidence: high\n"
            "    use_type: paraphrase\n"
            "    identifier: ISBN 9780134685991\n"
        )
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
    body: str | None = None,
    body_sha256: str | None = None,
    drop: tuple[str, ...] = (),
    **fields: object,
) -> Path:
    """Write ``body.md`` and an ``approval.yml`` bound to body.md.

    Defaults produce a current marker. ``body`` rewrites that file before hashing
    (the normal shape), ``body_sha256`` overrides the recorded hash (a stale
    marker), and ``drop`` removes required keys (a malformed marker). The marker
    binds only body.md.
    """
    folder.mkdir(parents=True, exist_ok=True)
    body_path = folder / "body.md"
    if body is not None or not body_path.is_file():
        body_path.write_text(body if body is not None else DEFAULT_BODY, encoding="utf-8")
    marker_body: dict[str, object] = {
        "schema": APPROVAL_SCHEMA,
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


def _final_review(
    folder: Path,
    *,
    pdf: Path | None = None,
    pdf_sha256: str | None = None,
    drop: tuple[str, ...] = (),
    **fields: object,
) -> Path:
    """Write ``final-review.yml`` bound to the final PDF bytes and return its path.

    Defaults produce a marker current for the folder's configured final PDF:
    ``pdf_sha256`` is recomputed from that PDF unless a test overrides it (the
    mismatched-hash shape) or drops the key. The PDF itself is never written
    here; a test that wants a missing-PDF stale shape passes an explicit
    ``pdf_sha256`` and removes the file itself.
    """
    folder.mkdir(parents=True, exist_ok=True)
    target = pdf if pdf is not None else folder / "final" / "report.pdf"
    body: dict[str, object] = {
        "schema": FINAL_REVIEW_SCHEMA,
        "pdf_sha256": pdf_sha256 or _sha256(target),
        "reviewed_at": "2026-09-10T16:30:00Z",
        "reviewed_by": "Alejandro",
    }
    body.update(fields)
    for key in drop:
        body.pop(key, None)
    marker = folder / "final-review.yml"
    marker.write_text(_yaml(body), encoding="utf-8")
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


# new-report-flow T4: per-format metadata the format phase requires. Only the
# APE identification table needs extra fields; ``aa`` is covered by the default
# route metadata and ``libre`` by a ``format_spec:`` line.
_APE_METADATA_DEFAULTS = {
    "cycle": "2026-2026 Ciclo I",
    "unit": "Unidad 1",
    "learning_outcome": "Modelar sistemas discretos",
    "practice_number": "3",
    "practice_type": "Laboratorio",
    "schedule": "Lunes 10:00-12:00",
    "place": "Lab. B",
    "planned_time": "4 horas",
}


def _choose_format(folder: Path, chosen: str = "aa", **metadata: object) -> Path:
    """Append a ``format:`` choice and its required metadata to ``report.yml``.

    Keys are written at the top level, which ``ReportConfig.metadata`` resolves
    through its alias map, so the existing ``metadata:`` block is untouched.
    The APE identification fields and the libre ``format_spec:`` are filled
    with placeholder-free defaults unless ``metadata`` overrides them.
    """
    folder.mkdir(parents=True, exist_ok=True)
    report = folder / "report.yml"
    lines = [f"format: {chosen}"]
    body: dict[str, object] = dict(_APE_METADATA_DEFAULTS) if chosen == "ape" else {}
    if chosen == "libre":
        body["format_spec"] = "Ensayo libre de 5 secciones con portada simple"
    body.update(metadata)
    lines.extend(f"{key}: {value}" for key, value in body.items())
    report.write_text(
        report.read_text(encoding="utf-8") + "\n".join(lines) + "\n", encoding="utf-8"
    )
    return report


def _mtime(path: Path, value: float) -> Path:
    """Pin ``path``'s modification time, so mtime ordering is explicit.

    The generate phase compares the final PDF against ``approval.yml`` by mtime;
    tests fix both sides instead of depending on wall-clock ordering or the
    filesystem's timestamp resolution.
    """
    os.utime(path, (value, value))
    return path


def _pdf(folder: Path, *, path: str = "final/report.pdf", mtime: float | None = None) -> Path:
    """Write the final PDF under ``folder`` and return its path.

    ``path`` mirrors the ``pdf:`` key ``_report()`` declares by default
    (``final/report.pdf``, outside ``outputs/``); pass a report built without
    ``_report()``'s default -- or one that overrode ``pdf:`` -- and give the
    matching ``path`` here. ``mtime`` pins the timestamp the generate phase
    compares against the approval marker.
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
    target = pdf if pdf is not None else folder / "final" / "report.pdf"
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
