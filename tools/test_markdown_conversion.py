"""Behaviour tests for ``markdown_to_latex()`` block and inline conversion.

Every assertion here reads the produced LaTeX string — no compile, no Docker.
The defects pinned by this module were all reproduced in rendered PDFs:

* fenced code blocks were flattened into a paragraph, losing newlines and
  indentation while their backticks survived as typographic quotes;
* ordered lists collapsed into one justified run-on paragraph;
* a trailing bibliography heading was emitted as a ``\\section`` on top of the
  title ``\\printbibliography`` prints by itself;
* long inline-code runs had no break opportunity, so they overflowed their
  table column and squeezed the interword glue of justified prose.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import build_latex_report  # noqa: E402


def _tex_for(markdown: str) -> str:
    return build_latex_report.markdown_to_latex(markdown)


# ---------------------------------------------------------------------------
# D-01 — fenced code blocks
# ---------------------------------------------------------------------------

FENCED_MD = """\
# Ejemplos

```python
from output_router import publish_global_output

destino = publish_global_output(
    pdf_path=Path("build/main.pdf"),
)
```

Texto posterior.
"""


def test_fenced_block_emits_a_verbatim_environment() -> None:
    tex = _tex_for(FENCED_MD)
    assert r"\begin{verbatim}" in tex
    assert r"\end{verbatim}" in tex


def test_fenced_block_preserves_line_breaks_and_indentation() -> None:
    tex = _tex_for(FENCED_MD)
    lines = tex.splitlines()
    start = lines.index(r"\begin{verbatim}")
    end = lines.index(r"\end{verbatim}")
    assert lines[start + 1 : end] == [
        "from output_router import publish_global_output",
        "",
        "destino = publish_global_output(",
        '    pdf_path=Path("build/main.pdf"),',
        ")",
    ]


def test_fenced_block_content_is_not_escaped_or_inline_converted() -> None:
    tex = _tex_for(FENCED_MD)
    body = tex[tex.index(r"\begin{verbatim}") : tex.index(r"\end{verbatim}")]
    # latex_escape() would have turned `_` into `\_`; convert_inline() would
    # have wrapped things in \texttt{}. Neither may touch verbatim content.
    assert r"\_" not in body
    assert r"\texttt{" not in body
    assert "publish_global_output" in body


def test_fence_markers_never_reach_the_output() -> None:
    tex = _tex_for(FENCED_MD)
    assert "```" not in tex
    assert "``\\texttt{" not in tex
    assert r"\section{Ejemplos}" in tex
    assert "Texto posterior." in tex


def test_tilde_fences_are_recognised_too() -> None:
    tex = _tex_for("~~~\nvalor = 1\n~~~\n")
    assert r"\begin{verbatim}" in tex
    assert "valor = 1" in tex
    assert "~~~" not in tex


def test_code_block_is_page_breakable_not_boxed() -> None:
    """A long block must flow onto the next page.

    ``verbatim`` breaks between its lines on its own; wrapping it in a box
    (``minipage``, ``fbox``, ``figure``) would make it atomic again — exactly
    the overflow this pins against.
    """
    tex = _tex_for(FENCED_MD)
    for atomic in (r"\begin{minipage}", r"\fbox", r"\begin{figure}", r"\parbox"):
        assert atomic not in tex


def test_code_block_font_fits_an_eighty_column_source_line() -> None:
    """``verbatim`` never wraps, so the font size decides the column budget.

    ``\\small`` stops at roughly 79 monospace columns in the A4 text block,
    which pushes a plain 80-column line into the margin (reproduced with the
    shell invocation in the technical-document fixture).
    """
    tex = _tex_for(FENCED_MD)
    scoped = tex[tex.index(r"\begingroup") : tex.index(r"\endgroup")]
    assert r"\footnotesize" in scoped


def test_unterminated_fence_does_not_swallow_the_rest_of_the_document() -> None:
    tex = _tex_for(
        "# Antes\n\n```python\nvalor = 1\n\n# Despues\n\nParrafo final.\n"
    )
    assert r"\section{Despues}" in tex
    assert "Parrafo final." in tex
    assert "```" not in tex


def test_unterminated_fence_says_so_instead_of_degrading_in_silence(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Recovering from a missing closing fence is right; doing it mutely is not.

    The block's lines are reflowed as prose, which is exactly the defect the
    fence support was added to remove — only now it happens because the author
    forgot three backticks. Whoever reads the PDF must be told where to look.
    """
    _tex_for("# Antes\n\n```python\nvalor = 1\n\n# Despues\n\nParrafo final.\n")

    message = capsys.readouterr().err
    assert "cerca" in message.lower()
    assert "3" in message  # the line the unterminated fence opened on


def test_a_closed_fence_stays_quiet(capsys: pytest.CaptureFixture[str]) -> None:
    _tex_for("```python\nvalor = 1\n```\n")

    assert capsys.readouterr().err == ""


def test_fence_closes_an_open_list() -> None:
    tex = _tex_for("- uno\n- dos\n```\ncodigo\n```\n")
    lines = tex.splitlines()
    assert lines.index(r"\end{itemize}") < lines.index(r"\begin{verbatim}")


# ---------------------------------------------------------------------------
# D-03 — ordered lists
# ---------------------------------------------------------------------------

ORDERED_MD = """\
# Procedimientos

1. Compilar el PDF en `build/`.
2. Resolver la materia desde `metadata.subject`.
3. Copiar a `outputs/` si corresponde.
"""


def test_ordered_list_emits_enumerate_with_one_item_per_entry() -> None:
    tex = _tex_for(ORDERED_MD)
    assert r"\begin{enumerate}" in tex
    assert r"\end{enumerate}" in tex
    assert tex.count(r"\item ") == 3
    assert "Compilar el PDF en" in tex


def test_ordered_list_does_not_collapse_into_a_paragraph() -> None:
    tex = _tex_for(ORDERED_MD)
    assert "1. Compilar" not in tex
    assert "2. Resolver" not in tex


def test_parenthesis_style_ordered_list_is_supported() -> None:
    tex = _tex_for("1) Uno\n2) Dos\n")
    assert r"\begin{enumerate}" in tex
    assert tex.count(r"\item ") == 2


def test_ordered_list_closes_when_a_heading_interrupts_it() -> None:
    tex = _tex_for("1. Uno\n2. Dos\n# Siguiente\n")
    lines = tex.splitlines()
    assert lines.index(r"\end{enumerate}") < lines.index(r"\section{Siguiente}")


def test_switching_list_kind_closes_the_previous_environment() -> None:
    tex = _tex_for("- vinieta\n1. numerado\n")
    lines = tex.splitlines()
    assert lines.index(r"\begin{itemize}") < lines.index(r"\end{itemize}")
    assert lines.index(r"\end{itemize}") < lines.index(r"\begin{enumerate}")
    assert lines.index(r"\begin{enumerate}") < lines.index(r"\end{enumerate}")


def test_ordered_list_closes_before_a_table() -> None:
    tex = _tex_for("1. Uno\n| A | B |\n| --- | --- |\n| 1 | 2 |\n")
    lines = tex.splitlines()
    assert r"\end{enumerate}" in lines
    assert lines.index(r"\end{enumerate}") < lines.index(r"\Needspace{4\baselineskip}")


def test_bullet_lists_still_work() -> None:
    tex = _tex_for("- uno\n- dos\n")
    assert r"\begin{itemize}" in tex
    assert r"\end{itemize}" in tex
    assert tex.count(r"\item ") == 2


# ---------------------------------------------------------------------------
# D-07 — trailing bibliography heading
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "title",
    ["Bibliografía", "Bibliografia", "Referencias", "References", "Bibliography", "BIBLIOGRAFÍA"],
)
def test_empty_trailing_bibliography_heading_is_suppressed(title: str) -> None:
    tex = _tex_for(f"# Contenido\n\nTexto.\n\n# {title}\n")
    assert rf"\section{{{title}}}" not in tex
    assert title not in tex
    assert r"\section{Contenido}" in tex


def test_bibliography_heading_with_prose_under_it_is_kept() -> None:
    tex = _tex_for("# Referencias\n\nSe listan a continuacion.\n")
    assert r"\section{Referencias}" in tex


def test_non_bibliography_trailing_heading_is_kept() -> None:
    tex = _tex_for("# Contenido\n\nTexto.\n\n# Anexos\n")
    assert r"\section{Anexos}" in tex


def test_bibliography_heading_followed_by_another_section_is_kept() -> None:
    tex = _tex_for("# Referencias\n\n# Anexos\n\nTexto.\n")
    assert r"\section{Referencias}" in tex
    assert r"\section{Anexos}" in tex


# ---------------------------------------------------------------------------
# D-11 / D-23 — inline code needs break opportunities
# ---------------------------------------------------------------------------


def test_inline_code_gets_break_opportunities_inside_a_table_cell() -> None:
    """A long \\texttt{} run used to cross the vertical rule of its column.

    ``\\allowbreak`` after each path/identifier separator lets the X column
    wrap the run inside its own cell instead of overflowing into the next one.
    """
    tex = _tex_for(
        "| Funcion | Entrada | Salida | Error |\n"
        "| --- | --- | --- | --- |\n"
        "| `resolve_content_root(env)` | dict | Path | Nunca lanza |\n"
    )
    cell = next(line for line in tex.splitlines() if "resolve" in line)
    assert r"\texttt{" in cell
    assert r"\allowbreak{}" in cell
    assert cell.count(r"\allowbreak{}") >= 2


def test_inline_code_in_justified_prose_can_break() -> None:
    latex = build_latex_report.convert_inline(
        "La cobertura vive en `tools/test_content_root.py` y en otro modulo."
    )
    assert r"\texttt{" in latex
    assert r"\allowbreak{}" in latex
    # The interword spaces around the code run must survive untouched.
    assert latex.startswith("La cobertura vive en ")
    assert "} y en otro modulo." in latex


def test_inline_code_still_escapes_latex_specials() -> None:
    latex = build_latex_report.convert_inline("valor `a_b & c%` final")
    assert r"\_" in latex
    assert r"\&" in latex
    assert r"\%" in latex


def test_inline_code_has_no_trailing_break_opportunity() -> None:
    latex = build_latex_report.convert_inline("ruta `build/`")
    assert not latex.endswith(r"\allowbreak{}}")
