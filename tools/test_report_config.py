"""Tests for automatic PDF publication configuration."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from output_router import subject_slug  # noqa: E402
from report_config import GLOBAL_OUTPUTS, load_report_config, targets_local_outputs  # noqa: E402


def _write_report(folder: Path, route: str, title: str) -> Path:
    folder.mkdir(parents=True)
    (folder / "report.yml").write_text(
        f"route: {route}\ntype: essay\noutput: pdf\nmetadata:\n  title: {title!r}\n",
        encoding="utf-8",
    )
    return folder


@pytest.mark.parametrize(
    ("route", "category"),
    [
        ("technical", "Tecnicos"),
        ("academic", "Academicos"),
        ("project", "Proyectos"),
        ("business", "Profesionales"),
        ("other", "Otros"),
    ],
)
def test_publication_category_is_derived_from_confirmed_route(
    tmp_path: Path, route: str, category: str
) -> None:
    config = load_report_config(_write_report(tmp_path / route, route, "Informe"))

    assert config.publication_category == category


def test_publication_slug_is_stable_ascii_from_confirmed_title(tmp_path: Path) -> None:
    config = load_report_config(
        _write_report(tmp_path / "report", "technical", "Análisis: Gestión Ñandú 2026!")
    )

    assert config.document_slug == "analisis-gestion-nandu-2026"


def test_delivery_pdf_is_not_required_or_interpreted(tmp_path: Path) -> None:
    folder = _write_report(tmp_path / "report", "technical", "Informe")
    (folder / "report.yml").write_text(
        (folder / "report.yml").read_text(encoding="utf-8") + "delivery_pdf: /tmp/ignored.pdf\n",
        encoding="utf-8",
    )

    config = load_report_config(folder)

    assert not hasattr(config, "delivery_pdf")


# ---------------------------------------------------------------------------
# Derived default output path (no `pdf:`/`docx:` declared)
# ---------------------------------------------------------------------------


def _write_academic_report(folder: Path, title: str, subject: str) -> Path:
    folder.mkdir(parents=True)
    (folder / "report.yml").write_text(
        "route: academic\ntype: essay\noutput: pdf\n"
        f"metadata:\n  title: {title!r}\n  subject: {subject!r}\n"
        "  teacher: Docente\n  student: Estudiante\n  date: '2026-01-01'\n",
        encoding="utf-8",
    )
    return folder


def test_technical_route_without_pdf_derives_under_its_route_category(tmp_path: Path) -> None:
    config = load_report_config(_write_report(tmp_path / "report", "technical", "Informe Tecnico"))

    assert config.pdf_path == GLOBAL_OUTPUTS / "tecnicos" / "informe-tecnico.pdf"
    assert not targets_local_outputs(config)


def test_technical_route_without_docx_derives_under_its_route_category(tmp_path: Path) -> None:
    config = load_report_config(_write_report(tmp_path / "report", "technical", "Informe Tecnico"))

    assert config.docx_path == GLOBAL_OUTPUTS / "tecnicos" / "informe-tecnico.docx"


def test_academic_route_without_pdf_derives_under_the_known_subject(tmp_path: Path) -> None:
    folder = _write_academic_report(tmp_path / "report", "Informe SO", "Sistemas Operativos")

    config = load_report_config(folder)

    expected_slug = subject_slug("Sistemas Operativos")
    assert expected_slug == "sistemas-operativos"
    assert config.pdf_path == GLOBAL_OUTPUTS / expected_slug / "informe-so.pdf"


def test_academic_route_without_docx_derives_under_the_known_subject(tmp_path: Path) -> None:
    folder = _write_academic_report(tmp_path / "report", "Informe SO", "Sistemas Operativos")

    config = load_report_config(folder)

    assert config.docx_path == GLOBAL_OUTPUTS / "sistemas-operativos" / "informe-so.docx"


def test_explicit_pdf_path_keeps_resolving_relative_to_the_folder(tmp_path: Path) -> None:
    folder = _write_report(tmp_path / "report", "technical", "Informe")
    (folder / "report.yml").write_text(
        (folder / "report.yml").read_text(encoding="utf-8") + "pdf: build/informe.pdf\n",
        encoding="utf-8",
    )

    config = load_report_config(folder)

    assert config.pdf_path == folder.resolve() / "build" / "informe.pdf"


def test_explicit_docx_path_keeps_resolving_relative_to_the_folder(tmp_path: Path) -> None:
    folder = _write_report(tmp_path / "report", "technical", "Informe")
    (folder / "report.yml").write_text(
        (folder / "report.yml").read_text(encoding="utf-8") + "docx: build/informe.docx\n",
        encoding="utf-8",
    )

    config = load_report_config(folder)

    assert config.docx_path == folder.resolve() / "build" / "informe.docx"
