"""Tests for automatic PDF publication configuration."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from report_config import load_report_config  # noqa: E402


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
