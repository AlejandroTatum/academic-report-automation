"""Tests for page-breakable table emission in ``render_table()``.

Body tables used to be wrapped in ``\\begin{table}[H]`` + ``\\centering``,
forcing LaTeX to push the *whole* table to the next page whenever it did not
fit in the remaining space — the mechanism behind stranded headings. These
tests assert the `.tex` string output directly (no compile, no Docker):
tables must now emit as a breakable ``xltabular``/``longtable`` inside an
explicit ``\\begingroup``/``\\endgroup`` group, with header-row repetition
via ``\\endhead``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import build_latex_report  # noqa: E402

TEMPLATES = TOOLS.parent / "templates"

MANY_COLUMNS_MD = """\
| Codigo | Descripcion | Modulo | Prioridad |
| --- | --- | --- | --- |
| RF-M01-01 | Login de usuario | Auth | Alta |
| RF-M01-02 | Logout de usuario | Auth | Media |
| RF-M02-01 | Listar reportes | Reportes | Alta |
"""

TWO_COLUMNS_MD = """\
| Termino | Definicion |
| --- | --- |
| API | Interfaz de programacion |
| DTO | Objeto de transferencia de datos |
"""


def _tex_for(markdown: str) -> str:
    return build_latex_report.markdown_to_latex(markdown)


# ---------------------------------------------------------------------------
# Breakable environment per column-count branch
# ---------------------------------------------------------------------------


def test_more_than_two_columns_emits_xltabular() -> None:
    tex = _tex_for(MANY_COLUMNS_MD)
    assert r"\begin{xltabular}{\textwidth}{" in tex
    assert r"\begin{table}[H]" not in tex
    # `\centering` still legitimately appears per-column inside the colspec
    # (`>{\centering\arraybackslash}X`) — only the float-centering directive
    # on its own line must be gone.
    assert r"\centering" not in tex.splitlines()
    assert r"\begin{tabularx}" not in tex


def test_two_or_fewer_columns_emits_longtable() -> None:
    tex = _tex_for(TWO_COLUMNS_MD)
    assert r"\begin{longtable}{| c | c |}" in tex
    assert r"\begin{table}[H]" not in tex
    assert r"\centering" not in tex.splitlines()


# ---------------------------------------------------------------------------
# Needspace reduction — both branches
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("markdown", [MANY_COLUMNS_MD, TWO_COLUMNS_MD])
def test_needspace_shrunk_to_four_baselines(markdown: str) -> None:
    tex = _tex_for(markdown)
    assert r"\Needspace{4\baselineskip}" in tex
    assert "15\\baselineskip" not in tex


# ---------------------------------------------------------------------------
# \endhead placement and absence of unsupported longtable markers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("markdown", [MANY_COLUMNS_MD, TWO_COLUMNS_MD])
def test_exactly_one_endhead_after_header_hline_before_data_row(markdown: str) -> None:
    tex = _tex_for(markdown)
    assert tex.count(r"\endhead") == 1

    lines = tex.splitlines()
    endhead_idx = next(i for i, line in enumerate(lines) if line.strip() == r"\endhead")

    # The header row's SECOND \hline (top rule, header row, closing rule)
    # must immediately precede \endhead.
    assert lines[endhead_idx - 1].strip() == r"\hline"
    hline_count_before = sum(1 for line in lines[: endhead_idx] if line.strip() == r"\hline")
    assert hline_count_before == 2, "endhead must follow the header row's SECOND \\hline"

    # The first data row must come right after \endhead.
    first_data_row = lines[endhead_idx + 1]
    assert first_data_row.strip().endswith(r"\\")
    assert r"\textbf{" not in first_data_row, "the row after \\endhead must be data, not the header"


@pytest.mark.parametrize("markdown", [MANY_COLUMNS_MD, TWO_COLUMNS_MD])
def test_no_endfirsthead_or_endfoot(markdown: str) -> None:
    tex = _tex_for(markdown)
    assert r"\endfirsthead" not in tex
    assert r"\endfoot" not in tex


# ---------------------------------------------------------------------------
# Explicit group wraps the font-size/spacing declarations and the table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "markdown,env,font",
    [
        (MANY_COLUMNS_MD, "xltabular", r"\footnotesize"),
        (TWO_COLUMNS_MD, "longtable", r"\small"),
    ],
)
def test_begingroup_endgroup_wrap_font_and_table(markdown: str, env: str, font: str) -> None:
    tex = _tex_for(markdown)
    begingroup_idx = tex.index(r"\begingroup")
    endgroup_idx = tex.index(r"\endgroup")
    assert begingroup_idx < endgroup_idx, "\\begingroup must precede \\endgroup"

    scoped = tex[begingroup_idx:endgroup_idx]
    assert font in scoped
    assert r"\renewcommand{\arraystretch}" in scoped
    assert r"\setlength{\tabcolsep}" in scoped
    assert rf"\begin{{{env}}}" in scoped
    assert rf"\end{{{env}}}" in scoped

    assert tex.count(r"\begingroup") == 1
    assert tex.count(r"\endgroup") == 1


# ---------------------------------------------------------------------------
# Template package declaration
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "template_name",
    ["unl-report.tex", "plain-report.tex", "chamba-overleaf.tex"],
)
def test_template_declares_xltabular_after_tabularx(template_name: str) -> None:
    text = (TEMPLATES / template_name).read_text(encoding="utf-8")
    assert r"\usepackage{xltabular}" in text

    tabularx_idx = text.index(r"\usepackage{tabularx}")
    xltabular_idx = text.index(r"\usepackage{xltabular}")
    assert xltabular_idx > tabularx_idx, (
        f"{template_name}: xltabular must be declared after tabularx"
    )
