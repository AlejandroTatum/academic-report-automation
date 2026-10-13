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


@pytest.fixture(autouse=True)
def _never_publish_outside_tmp(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Leak-proof by construction: a build here can only publish into a scratch dir.

    The repo-root conftest.py already pins REPORT_CONTENT_ROOT to a per-session
    temp dir. This adds the monkeypatch ``test_content_root.py`` uses, so a
    test that forgets ``publish_global: false`` (or a module that bound the
    root before the pin) still copies its PDF under tmp, never into the real
    ``outputs/<materia>/``.
    """
    import importlib

    sandbox = tmp_path_factory.mktemp("global-outputs")
    for name in ("output_router", "report_config", "build_latex_report", "validate_report"):
        module = importlib.import_module(name)
        if hasattr(module, "GLOBAL_OUTPUTS"):
            monkeypatch.setattr(module, "GLOBAL_OUTPUTS", sandbox)
    return sandbox


A4_PAGE_SIZE = "595.276 x 841.89 pts (A4)"


def _report(
    tmp_path: Path,
    *,
    cover_required: bool,
    route: str = "technical",
    subject: str = "",
    title: str = "Contrato del router",
) -> Path:
    folder = tmp_path / "informe"
    folder.mkdir()
    cover_block = "" if cover_required else "cover:\n  required: false\n  logo_required: false\n"
    subject_line = f'  subject: "{subject}"\n' if subject else ""
    (folder / "report.yml").write_text(
        f"route: {route}\n"
        "type: technical_report\n"
        "backend: latex\n"
        "output: pdf\n"
        f"{cover_block}"
        "pdf: build/main.pdf\n"
        "metadata:\n"
        f'  title: "{title}"\n'
        f"{subject_line}"
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


def test_cover_naming_a_subject_that_contains_a_body_marker_is_not_mixed(
    tmp_path: Path, stub_pdf_tools
) -> None:
    """The subject 'Desarrollo Basado en Plataformas' belongs on the cover."""
    folder = _report(
        tmp_path,
        cover_required=True,
        route="academic",
        subject="Desarrollo Basado en Plataformas",
        title="Descripción de actores del sistema",
    )
    stub_pdf_tools(
        [
            "Universidad Nacional de Loja\nDescripción de actores\ndel sistema\n"
            "Desarrollo Basado en Plataformas.\nInforme académico.",
            "1. Introducción\nCuerpo.",
        ]
    )

    result = validate_report.pdf_layout_validation(load_report_config(folder))

    assert not any("portada parece mezclada" in e for e in result.errors), result.errors


def test_cover_metadata_written_with_alias_keys_is_also_exempt(
    tmp_path: Path, stub_pdf_tools
) -> None:
    """#72.3: `asignatura`/`titulo` resolve like `subject`/`title`."""
    folder = _report(tmp_path, cover_required=True, route="academic", subject="Desarrollo Basado en Plataformas")
    report = folder / "report.yml"
    report.write_text(
        report.read_text(encoding="utf-8").replace("  subject:", "  asignatura:").replace("  title:", "  titulo:"),
        encoding="utf-8",
    )
    stub_pdf_tools(
        ["Universidad Nacional de Loja\nContrato del router\nDesarrollo Basado en Plataformas", "1. Introducción\nCuerpo."]
    )

    result = validate_report.pdf_layout_validation(load_report_config(folder))

    assert not any("portada parece mezclada" in e for e in result.errors), result.errors


def test_cover_title_hyphenated_across_lines_is_exempt(tmp_path: Path, stub_pdf_tools) -> None:
    """#72.3: the PDF text may break a long title word with a hyphen."""
    folder = _report(
        tmp_path, cover_required=True, route="academic", title="Antecedentes y desarrollo del proyecto"
    )
    stub_pdf_tools(["Universidad Nacional de Loja\nAntecedentes y desarrollo del pro-\nyecto", "1. Introducción\nCuerpo."])

    result = validate_report.pdf_layout_validation(load_report_config(folder))

    assert not any("portada parece mezclada" in e for e in result.errors), result.errors


def test_cover_metadata_is_removed_only_as_whole_words(tmp_path: Path, stub_pdf_tools) -> None:
    """#72.3: removing subject 'Sub' must not cut 'Subdesarrollo' into a marker."""
    folder = _report(tmp_path, cover_required=True, route="academic", subject="Sub")
    stub_pdf_tools(["Universidad Nacional de Loja\nSub\nSubdesarrollo regional", "1. Introducción\nCuerpo."])

    result = validate_report.pdf_layout_validation(load_report_config(folder))

    assert not any("portada parece mezclada" in e for e in result.errors), result.errors


def test_cover_with_a_subject_still_rejects_body_markers_outside_the_metadata(
    tmp_path: Path, stub_pdf_tools
) -> None:
    folder = _report(
        tmp_path,
        cover_required=True,
        route="academic",
        subject="Desarrollo Basado en Plataformas",
    )
    stub_pdf_tools(
        [
            "Universidad Nacional de Loja\nDesarrollo Basado en Plataformas\n"
            "Antecedentes del trabajo",
            "Tema\nCuerpo.",
        ]
    )

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


def _ape_report(tmp_path: Path) -> Path:
    folder = _report(tmp_path, cover_required=True, route="academic")
    report = folder / "report.yml"
    report.write_text(report.read_text(encoding="utf-8") + "format: ape\n", encoding="utf-8")
    (folder / "body.md").write_text(
        "# Procedimiento\n\n| Integrante | Tarea |\n|---|---|\n| Ana | Redacción del informe |\n",
        encoding="utf-8",
    )
    return folder


def test_ape_identification_page_is_not_a_cover_mixed_with_the_body(
    tmp_path: Path, stub_pdf_tools
) -> None:
    """APE has no cover: page 1 is the identification table, whose unit name may hold 'Introducción'."""
    folder = _ape_report(tmp_path)
    stub_pdf_tools(["Datos de Identificación\nUnidad\n1 – Introducción al Networking", "Objetivo\nTexto."])

    result = validate_report.pdf_layout_validation(load_report_config(folder))

    assert not any("portada parece mezclada" in e for e in result.errors), result.errors


def test_table_cell_closing_a_page_is_not_an_orphan_heading(
    tmp_path: Path, stub_pdf_tools
) -> None:
    folder = _ape_report(tmp_path)
    stub_pdf_tools(["Tabla 1.\nAna\nRedacción del informe", "Resultados\nTexto."])

    result = validate_report.pdf_layout_validation(load_report_config(folder))

    assert not any("huérfano" in e for e in result.errors), result.errors


# ---------------------------------------------------------------------------
# Coverless by format (aa-acd-templates S8)
# ---------------------------------------------------------------------------
#
# `ape`, `aa` and `acd` render with no cover page, so a report of those formats
# is not asked for one: `cover: {required: false}` in report.yml is no longer
# needed. The default is resolved in ReportConfig.cover_value, the single place
# every cover rule reads, and an explicit `cover:` block in report.yml still
# wins, per key.

COVERLESS_FORMATS = ("ape", "aa", "acd")


def _format_report(tmp_path: Path, fmt: str, cover: dict | None = None, route: str = "academic") -> Path:
    folder = tmp_path / f"informe-{fmt}"
    folder.mkdir()
    cover_block = ""
    if cover is not None:
        cover_block = "cover:\n" + "".join(f"  {key}: {str(value).lower()}\n" for key, value in cover.items())
    (folder / "report.yml").write_text(
        f"route: {route}\n"
        f"format: {fmt}\n"
        "type: technical_report\n"
        "backend: latex\n"
        "output: pdf\n"
        f"{cover_block}"
        "pdf: build/main.pdf\n"
        "metadata:\n"
        '  title: "Planificación de procesos"\n'
        '  subject: "Sistemas Operativos"\n'
        '  student: "Camila Jaramillo"\n'
        '  teacher: "Ing. Luis Cueva"\n'
        '  date: "9 de octubre de 2026"\n',
        encoding="utf-8",
    )
    (folder / "body.md").write_text("# Introducción\n\nTexto.\n", encoding="utf-8")
    build = folder / "build"
    build.mkdir()
    (build / "main.pdf").write_bytes(b"%PDF-1.5\n")
    return folder


@pytest.mark.parametrize("fmt", COVERLESS_FORMATS)
def test_format_without_a_cover_key_resolves_to_no_cover(tmp_path: Path, fmt: str) -> None:
    config = load_report_config(_format_report(tmp_path, fmt))
    assert config.cover_value("required", default=True) is False
    assert config.cover_value("body_starts_on_page", default=2) == 1


@pytest.mark.parametrize("fmt", COVERLESS_FORMATS)
def test_format_default_keeps_the_logo_check(tmp_path: Path, fmt: str) -> None:
    """These templates print the faculty logo, so the embedded-image check still applies."""
    config = load_report_config(_format_report(tmp_path, fmt))
    assert config.cover_value("logo_required", default=True) is True


@pytest.mark.parametrize("fmt", COVERLESS_FORMATS)
def test_format_without_a_cover_key_accepts_a_body_that_opens_on_page_one(
    tmp_path: Path, stub_pdf_tools, fmt: str
) -> None:
    """A one-page report whose page 1 holds 'Introducción' is the body, not a mixed cover."""
    folder = _format_report(tmp_path, fmt)
    stub_pdf_tools(["Datos de identificación\nIntroducción\nTexto del informe.", "Desarrollo\nMás texto."])

    result = validate_report.pdf_layout_validation(load_report_config(folder))

    assert not any("portada" in e.lower() for e in result.errors), result.errors
    assert not any("inicio claro del cuerpo" in w for w in result.warnings), result.warnings


@pytest.mark.parametrize("fmt", COVERLESS_FORMATS)
def test_format_without_a_cover_key_is_not_failed_for_a_one_page_pdf(tmp_path: Path, fmt: str) -> None:
    """common_validation demanded 2+ pages for the cover these formats do not have."""
    config = load_report_config(_format_report(tmp_path, fmt))

    result = validate_report.common_validation(config)

    assert not any("portada es obligatoria" in e for e in result.errors), result.errors


@pytest.mark.parametrize("fmt", COVERLESS_FORMATS)
def test_format_with_explicit_cover_required_true_still_gets_the_cover_checks(
    tmp_path: Path, fmt: str
) -> None:
    """An explicit report.yml setting wins over the format default."""
    config = load_report_config(_format_report(tmp_path, fmt, cover={"required": True}))
    assert config.cover_value("required", default=False) is True
    assert config.cover_value("body_starts_on_page", default=1) == 2, "a required cover starts the body on page 2"

    result = validate_report.common_validation(config)

    assert any("portada es obligatoria" in e for e in result.errors), result.errors


@pytest.mark.parametrize("fmt", ("aa", "acd"))
def test_aa_and_acd_with_explicit_cover_required_true_reject_a_mixed_cover(
    tmp_path: Path, stub_pdf_tools, fmt: str
) -> None:
    folder = _format_report(tmp_path, fmt, cover={"required": True})
    stub_pdf_tools(["Universidad Nacional de Loja\nAntecedentes del trabajo", "Tema\nCuerpo."])

    result = validate_report.pdf_layout_validation(load_report_config(folder))

    assert any("portada parece mezclada" in e for e in result.errors), result.errors


@pytest.mark.parametrize("fmt", COVERLESS_FORMATS)
def test_format_with_explicit_cover_required_false_stays_coverless(
    tmp_path: Path, stub_pdf_tools, fmt: str
) -> None:
    """The `required: false` every existing APE report carries keeps validating."""
    folder = _format_report(tmp_path, fmt, cover={"required": False})
    config = load_report_config(folder)
    assert config.cover_value("required", default=True) is False
    stub_pdf_tools(["Introducción\nTexto del informe."])

    result = validate_report.pdf_layout_validation(config)

    assert not any("portada" in e.lower() for e in result.errors), result.errors


@pytest.mark.parametrize("fmt", COVERLESS_FORMATS)
def test_partial_cover_block_does_not_shadow_the_format_default(tmp_path: Path, fmt: str) -> None:
    config = load_report_config(_format_report(tmp_path, fmt, cover={"logo_required": False}))
    assert config.cover_value("logo_required", default=True) is False
    assert config.cover_value("required", default=True) is False


@pytest.mark.parametrize("route", ["technical", "project"])
def test_format_default_and_route_default_agree_on_non_academic_routes(tmp_path: Path, route: str) -> None:
    config = load_report_config(_format_report(tmp_path, "aa", route=route))
    assert config.cover_value("required", default=True) is False
    assert config.cover_value("logo_required", default=True) is False, "the route default still applies"


@pytest.mark.parametrize("fmt", ["libre", None])
def test_other_formats_keep_the_academic_cover_default(tmp_path: Path, fmt: str | None) -> None:
    folder = _format_report(tmp_path, fmt or "libre")
    if fmt is None:
        report = folder / "report.yml"
        report.write_text(report.read_text(encoding="utf-8").replace("format: libre\n", ""), encoding="utf-8")
    config = load_report_config(folder)
    assert config.cover_value("required", default=True) is True
    assert config.cover_value("body_starts_on_page", default=2) == 2
