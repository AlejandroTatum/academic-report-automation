"""Tests for route-aware metadata requirements.

The document-routing contract
(``skills/academic-report-builder/references/document-routing.md``) says only
Route A may activate academic machinery — teacher, subject, institutional
cover. Every other route MUST NOT be forced to carry that metadata. These tests
pin the ``route:`` key in report.yml to that contract.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from report_config import (  # noqa: E402
    ROUTE_REQUIRED_METADATA,
    ReportConfig,
    load_report_config,
)
from validate_report import common_validation  # noqa: E402

ACADEMIC_META = {
    "title": "Planificación de CPU",
    "subject": "Sistemas Operativos",
    "teacher": "Ing. Hernán Torres",
    "student": "Alejandro Padilla",
    "date": "7 de agosto de 2026",
}
NON_ACADEMIC_META = {
    "title": "Documentación de proyecto",
    "student": "Equipo de plataforma",
    "date": "7 de agosto de 2026",
}


def make_config(folder: Path, **raw) -> ReportConfig:
    """Build a ReportConfig on a real folder without touching disk layout."""
    (folder / "outputs").mkdir(parents=True, exist_ok=True)
    payload = {"type": "essay", "pdf": "build/report.pdf"}
    payload.update(raw)
    return ReportConfig(folder=folder, raw=payload, academic_format={})


def metadata_errors(result) -> list[str]:
    return [e for e in result.errors if "Metadata incompleta" in e]


def route_errors(result) -> list[str]:
    return [e for e in result.errors if "Ruta de documento" in e]


# ---------------------------------------------------------------------------
# Backwards compatibility: no route key means today's academic behaviour
# ---------------------------------------------------------------------------


def test_report_without_a_route_key_keeps_requiring_academic_metadata(tmp_path):
    config = make_config(tmp_path, metadata={"title": "T", "student": "S", "date": "D"})

    result = common_validation(config)

    assert metadata_errors(result), "A report with no route must stay on Route A"
    assert "subject" in metadata_errors(result)[0]
    assert "teacher" in metadata_errors(result)[0]


def test_report_without_a_route_key_and_full_academic_metadata_passes(tmp_path):
    config = make_config(tmp_path, metadata=dict(ACADEMIC_META))

    assert metadata_errors(common_validation(config)) == []


def test_explicit_academic_route_is_not_weakened(tmp_path):
    config = make_config(
        tmp_path,
        route="academic",
        metadata={"title": "T", "student": "S", "date": "D"},
    )

    errors = metadata_errors(common_validation(config))

    assert errors and "subject" in errors[0] and "teacher" in errors[0]


# ---------------------------------------------------------------------------
# Non-academic routes require only what genuinely applies
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("route", ["project", "business", "technical", "other"])
def test_non_academic_routes_do_not_require_subject_or_teacher(tmp_path, route):
    config = make_config(tmp_path, route=route, metadata=dict(NON_ACADEMIC_META))

    result = common_validation(config)

    assert metadata_errors(result) == [], f"Route {route} must not demand academic metadata"
    assert route_errors(result) == []


@pytest.mark.parametrize("missing", ["title", "student", "date"])
def test_non_academic_routes_still_require_the_universal_metadata(tmp_path, missing):
    meta = {key: value for key, value in NON_ACADEMIC_META.items() if key != missing}
    config = make_config(tmp_path, route="project", metadata=meta)

    errors = metadata_errors(common_validation(config))

    assert errors and missing in errors[0]


@pytest.mark.parametrize(
    ("written", "expected_required"),
    [
        ("A", ("title", "subject", "teacher", "student", "date")),
        ("b", ("title", "student", "date")),
        ("  Technical  ", ("title", "student", "date")),
    ],
)
def test_route_values_are_normalised(tmp_path, written, expected_required):
    config = make_config(tmp_path, route=written, metadata=dict(ACADEMIC_META))

    assert config.required_metadata == expected_required


def test_non_academic_route_warns_when_academic_metadata_is_declared(tmp_path):
    config = make_config(tmp_path, route="project", metadata=dict(ACADEMIC_META))

    result = common_validation(config)

    assert metadata_errors(result) == []
    assert any("teacher" in w and "project" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# An unknown route fails loudly — never a silent fallback to Route A
# ---------------------------------------------------------------------------


def test_unknown_route_is_a_loud_error_and_not_an_academic_fallback(tmp_path):
    config = make_config(tmp_path, route="universitario", metadata=dict(NON_ACADEMIC_META))

    result = common_validation(config)

    assert route_errors(result), "An unknown route must be reported, not guessed"
    assert "universitario" in route_errors(result)[0]
    for value in ROUTE_REQUIRED_METADATA:
        assert value in route_errors(result)[0]
    assert metadata_errors(result) == [], "Do not fall back to the academic metadata set"


def test_unknown_route_fails_fast_when_the_config_loads(tmp_path):
    folder = tmp_path / "reports" / "informe"
    folder.mkdir(parents=True)
    (folder / "report.yml").write_text(
        "type: essay\nroute: universidad\npdf: build/report.pdf\n", encoding="utf-8"
    )

    with pytest.raises(SystemExit) as excinfo:
        load_report_config(folder)

    assert "universidad" in str(excinfo.value)
    assert "route" in str(excinfo.value)


def test_valid_route_loads_normally(tmp_path):
    folder = tmp_path / "reports" / "informe"
    folder.mkdir(parents=True)
    (folder / "report.yml").write_text(
        "type: technical_report\nroute: technical\npdf: build/report.pdf\n", encoding="utf-8"
    )

    config = load_report_config(folder)

    assert config.route == "technical"
    assert config.required_metadata == ("title", "student", "date")


def test_author_is_accepted_as_the_student_alias(tmp_path):
    config = make_config(
        tmp_path,
        route="business",
        metadata={"title": "T", "author": "Equipo", "date": "D"},
    )

    assert metadata_errors(common_validation(config)) == []
