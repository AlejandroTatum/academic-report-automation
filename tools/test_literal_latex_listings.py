"""#81: the literal-LaTeX check exempts text that comes from code listings.

An Octave/MATLAB listing may legitimately contain ``\\pi`` (TeX markup in a plot
title). Only body prose and math may trigger "COMANDOS LATEX RENDERIZADOS COMO
TEXTO LITERAL"; a command escaped outside code is still a defect.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import validate_report as vr
from report_config import ReportConfig

LITERAL_ERROR = "COMANDOS LATEX RENDERIZADOS COMO TEXTO LITERAL"
LISTING = "title('4.2: errores en cos(\\pi/3)')"


def _validate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str, pdf_body_text: str) -> list[str]:
    (tmp_path / "body.md").write_text(body, encoding="utf-8")
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_text("fake pdf content", encoding="utf-8")
    monkeypatch.setattr(vr, "pdf_text_pages", lambda _p: ["cover", pdf_body_text])
    config = ReportConfig(
        folder=tmp_path,
        raw={"type": "essay", "pdf": str(pdf_path)},
        academic_format={"cover": {"required": True}, "conclusions": {"banned_openers": []}},
    )
    return [error for error in vr.common_validation(config).errors if LITERAL_ERROR in error]


def test_pi_inside_a_fenced_listing_is_not_a_literal_latex_error(tmp_path, monkeypatch) -> None:
    body = f"# Resultados\n\n```octave\n{LISTING}\n{LISTING}\n```\n"
    pdf_text = f"Resultados\n{LISTING}\n{LISTING}\n"

    assert _validate(tmp_path, monkeypatch, body, pdf_text) == []


def test_pi_inside_an_inline_code_span_is_not_a_literal_latex_error(tmp_path, monkeypatch) -> None:
    body = "La orden `title('cos(\\pi/3)')` rotula la gráfica.\n"
    pdf_text = "La orden title('cos(\\pi/3)') rotula la gráfica.\n"

    assert _validate(tmp_path, monkeypatch, body, pdf_text) == []


def test_pi_escaped_in_prose_is_still_a_literal_latex_error(tmp_path, monkeypatch) -> None:
    body = "El ángulo vale \\pi/3 radianes.\n"
    pdf_text = "El ángulo vale \\pi/3 radianes.\n"

    errors = _validate(tmp_path, monkeypatch, body, pdf_text)

    assert len(errors) == 1
    assert "\\pi (1 vez/veces)" in errors[0]


def test_a_listing_missing_from_the_pdf_does_not_hide_a_prose_defect(tmp_path, monkeypatch) -> None:
    body = f"El ángulo vale \\pi/3.\n\n```octave\n{LISTING}\n```\n"
    pdf_text = "El ángulo vale \\pi/3.\n"

    errors = _validate(tmp_path, monkeypatch, body, pdf_text)

    assert len(errors) == 1
    assert "\\pi (1 vez/veces)" in errors[0]


def test_a_wrapped_numbered_listing_line_is_still_exempt(tmp_path, monkeypatch) -> None:
    line = "title('4.2: errores en cos(\\pi/3) con una línea larga que el listado parte')"
    body = f"# Resultados\n\n```octave\n{line}\n```\n"
    pdf_text = (
        "Resultados\n"
        "1 title('4.2: errores en cos(\\pi/3) con una línea larga que el\n"
        "↪→\n"
        "listado parte')\n"
    )

    assert _validate(tmp_path, monkeypatch, body, pdf_text) == []


def test_an_aligned_comment_extracted_as_its_own_column_is_still_exempt(tmp_path, monkeypatch) -> None:
    body = "```octave\nx = cos(\\pi/3);     % \\pi en radianes\ny = 1;\n```\n"
    pdf_text = "1 x = cos(\\pi/3);\n2 y = 1;\n% \\pi en radianes\n"

    assert _validate(tmp_path, monkeypatch, body, pdf_text) == []


def test_a_longer_closing_fence_still_closes_the_listing(tmp_path, monkeypatch) -> None:
    body = f"# Resultados\n\n```octave\n{LISTING}\n`````\n"
    pdf_text = f"Resultados\n1 {LISTING}\n"

    assert _validate(tmp_path, monkeypatch, body, pdf_text) == []


def test_only_the_occurrences_beyond_the_listings_are_reported(tmp_path, monkeypatch) -> None:
    body = f"El ángulo vale \\pi/3.\n\n```octave\n{LISTING}\n```\n"
    pdf_text = f"El ángulo vale \\pi/3.\n{LISTING}\n"

    errors = _validate(tmp_path, monkeypatch, body, pdf_text)

    assert len(errors) == 1
    assert "\\pi (1 vez/veces)" in errors[0]
