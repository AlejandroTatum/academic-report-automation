"""Tests for the cover/body boundary check on documents that have no cover.

``pdf_layout_validation()`` enforced the UNL shell's "body starts on page 2"
rule unconditionally, so a report that had already declared
``cover: {required: false}`` was still measured against a cover it does not
have. Two consequences, both reproduced on real builds:

* the body markers are academic Spanish (``introducción``, ``tema``,
  ``antecedentes``, ``desarrollo``, ``ejercicio``), so a business report opening
  on "Resumen ejecutivo" or a technical document opening on "Propósito" could
  never match one — the warning was guaranteed, on every build, forever;
* worse in the other direction, a coverless document whose first section IS one
  of those words has its real body on page 1, and the check calls that "portada
  mezclada con el cuerpo" — an ERROR, for correct output.

A gate nobody can satisfy teaches people to skip reading warnings, which is
exactly what a gate exists to prevent.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import validate_report  # noqa: E402
from report_config import load_report_config  # noqa: E402

A4_PAGE_SIZE = "595.276 x 841.89 pts (A4)"


def _report(tmp_path: Path, *, cover_required: bool, route: str = "technical") -> Path:
    folder = tmp_path / "informe"
    folder.mkdir()
    cover_block = "" if cover_required else "cover:\n  required: false\n  logo_required: false\n"
    (folder / "report.yml").write_text(
        f"route: {route}\n"
        "type: technical_report\n"
        "backend: latex\n"
        "output: pdf\n"
        f"{cover_block}"
        "pdf: build/main.pdf\n"
        "metadata:\n"
        '  title: "Contrato del router"\n'
        '  student: "Plataforma"\n'
        '  date: "7 de agosto de 2026"\n',
        encoding="utf-8",
    )
    (folder / "body.md").write_text("# Propósito\n\nTexto.\n", encoding="utf-8")
    build = folder / "build"
    build.mkdir()
    (build / "main.pdf").write_bytes(b"%PDF-1.5\n")
    return folder


@pytest.fixture
def stub_pdf_tools(monkeypatch: pytest.MonkeyPatch):
    """Feed the validator fixed page text and a clean A4 pdfinfo."""

    def apply(pages: list[str]) -> None:
        monkeypatch.setattr(validate_report, "pdf_text_pages", lambda _pdf: pages)
        monkeypatch.setattr(
            validate_report,
            "pdfinfo",
            lambda _pdf: {"Pages": str(len(pages)), "Page size": A4_PAGE_SIZE},
        )
        monkeypatch.setattr(
            validate_report,
            "run",
            lambda cmd: type("P", (), {"stdout": "image 1 0 0", "returncode": 0})(),
        )

    return apply


def test_coverless_report_is_not_asked_for_a_body_on_page_two(
    tmp_path: Path, stub_pdf_tools
) -> None:
    """A document with no cover starts its body on page 1, by definition."""
    folder = _report(tmp_path, cover_required=False)
    stub_pdf_tools(["Propósito\nTexto del contrato.", "Errores\nMás texto."])

    result = validate_report.pdf_layout_validation(load_report_config(folder))

    assert not any("inicio claro del cuerpo" in w for w in result.warnings), result.warnings


def test_coverless_report_whose_body_opens_on_desarrollo_is_not_an_error(
    tmp_path: Path, stub_pdf_tools
) -> None:
    """Page 1 holding 'Desarrollo' is the body, not a cover bleeding into it."""
    folder = _report(tmp_path, cover_required=False)
    stub_pdf_tools(["Desarrollo\nTexto del desarrollo.", "Conclusiones\nCierre."])

    result = validate_report.pdf_layout_validation(load_report_config(folder))

    assert not any("portada parece mezclada" in e for e in result.errors), result.errors


def test_report_with_a_cover_still_gets_the_boundary_checks(
    tmp_path: Path, stub_pdf_tools
) -> None:
    """Route A must not lose the UNL shell rule this fix carves an exception in."""
    folder = _report(tmp_path, cover_required=True, route="academic")
    stub_pdf_tools(["Universidad Nacional de Loja\nPortada", "Sin marcador de cuerpo."])

    result = validate_report.pdf_layout_validation(load_report_config(folder))

    assert any("inicio claro del cuerpo" in w for w in result.warnings), result.warnings


def test_report_with_a_cover_still_rejects_body_bleeding_onto_page_one(
    tmp_path: Path, stub_pdf_tools
) -> None:
    folder = _report(tmp_path, cover_required=True, route="academic")
    stub_pdf_tools(["Universidad Nacional de Loja\nAntecedentes del trabajo", "Tema\nCuerpo."])

    result = validate_report.pdf_layout_validation(load_report_config(folder))

    assert any("portada parece mezclada" in e for e in result.errors), result.errors


def test_orphan_heading_detection_survives_for_coverless_reports(
    tmp_path: Path, stub_pdf_tools
) -> None:
    """Only the cover/body boundary is exempted — other layout checks stay on."""
    folder = _report(tmp_path, cover_required=False)
    stub_pdf_tools(["Texto corriente.\nProcedimientos", "Contenido de la sección."])

    result = validate_report.pdf_layout_validation(load_report_config(folder))

    assert any("huérfano" in e for e in result.errors), result.errors
