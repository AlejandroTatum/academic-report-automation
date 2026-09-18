"""Citation-driven bibliography emission (#26).

Defect (Cata Club run): ``\\printbibliography`` was emitted unconditionally in
the plain and UNL templates, gated only on the *file presence* of a ``.bib``.
Two visible failures followed:

1. A report with a ``.bib`` file but no ``[@...]`` citations still printed the
   template's "Referencias"/"Bibliografía" heading over an empty list.
2. A body whose own Markdown carried a "## Referencias" heading duplicated the
   title once the template heading printed too.

Contract under test: the *actual citations in the body* (not file presence)
decide whether the bibliography is printed. When it is not printed, no
bibliography-named heading is manufactured by the template either. Citation
syntax (``[@key]`` → ``\\cite{key}``) is preserved.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import build_latex_report  # noqa: E402
import report_config  # noqa: E402

CITED_BODY = """\
# Introduccion

La paginacion de demanda se describe en la literatura [@silberschatz2018].

# Desarrollo

Mas detalle en [@tanenbaum2015].
"""

BIB_FILE = """\
@book{silberschatz2018,
  author = {Silberschatz, Abraham},
  title = {Operating System Concepts},
  year = {2018},
}
@book{tanenbaum2015,
  author = {Tanenbaum, Andrew S.},
  title = {Modern Operating Systems},
  year = {2015},
}
"""


def make_config(tmp_path: Path, body: str, template: str = "plain") -> report_config.ReportConfig:
    folder = tmp_path / "r"
    folder.mkdir(parents=True, exist_ok=True)
    raw = {
        "type": "technical_report",
        "backend": "latex",
        "output": "pdf",
        "template": template,
        "metadata": {"title": "T", "subject": "S"},
        "body": "body.md",
        "bibliography": "sources.bib",
    }
    (folder / "report.yml").write_text(yaml.safe_dump(raw), encoding="utf-8")
    (folder / "body.md").write_text(body, encoding="utf-8")
    (folder / "sources.bib").write_text(BIB_FILE, encoding="utf-8")
    return report_config.ReportConfig.load(folder)


@pytest.fixture(scope="module")
def cited_tex_plain(tmp_path_factory: pytest.TempPathFactory) -> str:
    config = make_config(tmp_path_factory.mktemp("bib-cited"), CITED_BODY)
    return build_latex_report.render_tex(config)


@pytest.fixture(scope="module")
def uncited_tex_plain(tmp_path_factory: pytest.TempPathFactory) -> str:
    body = CITED_BODY.replace(" [@silberschatz2018]", "").replace(" [@tanenbaum2015]", "")
    config = make_config(tmp_path_factory.mktemp("bib-uncited"), body)
    return build_latex_report.render_tex(config)


# ---------------------------------------------------------------------------
# Citations decide the emission — not file presence
# ---------------------------------------------------------------------------


def test_citations_with_bib_file_print_the_bibliography_once(cited_tex_plain: str) -> None:
    assert cited_tex_plain.count(r"\printbibliography") == 1


def test_citation_keys_reach_the_bibliography_intact(cited_tex_plain: str) -> None:
    assert r"\cite{silberschatz2018}" in cited_tex_plain
    assert r"\cite{tanenbaum2015}" in cited_tex_plain


def test_bib_file_without_citations_prints_no_bibliography(uncited_tex_plain: str) -> None:
    """The .bib file alone must not manufacture an empty Referencias heading."""
    assert r"\printbibliography" not in uncited_tex_plain


def test_citations_without_bib_file_print_no_bibliography(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """No .bib file -> nothing to print; the citation markers stay in the text."""
    config = make_config(tmp_path_factory.mktemp("bib-nofile"), CITED_BODY)
    (config.folder / "sources.bib").unlink()
    tex = build_latex_report.render_tex(config)
    assert r"\printbibliography" not in tex


# ---------------------------------------------------------------------------
# No duplicate bibliography titles
# ---------------------------------------------------------------------------


def test_bibliography_heading_is_not_duplicated_when_printing(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Citations + a trailing '## Referencias' heading -> exactly one title."""
    body = CITED_BODY + "\n## Referencias\n"
    config = make_config(tmp_path_factory.mktemp("bib-dup"), body)
    tex = build_latex_report.render_tex(config)
    assert tex.count(r"\printbibliography") == 1
    assert r"\section{Referencias}" not in tex
    assert r"\subsection{Referencias}" not in tex


def test_cited_body_with_populated_references_section_prints_one_title(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """A '## Referencias' heading with prose under it must not become a second
    bibliography title when the citation-driven bibliography also prints."""
    body = CITED_BODY + "\n## Referencias\n\nNotas sobre las fuentes consultadas.\n"
    config = make_config(tmp_path_factory.mktemp("bib-pop"), body)
    tex = build_latex_report.render_tex(config)
    assert tex.count(r"\printbibliography") == 1
    assert r"\section{Referencias}" not in tex
    assert "Notas sobre las fuentes consultadas." in tex


def test_uncited_trailing_references_heading_stays_suppressed(
    uncited_tex_plain: str,
) -> None:
    """No citations and a trailing empty '## Referencias' -> no heading at all
    (the pre-existing trailing-empty suppression must survive the rework)."""
    assert r"\section{Referencias}" not in uncited_tex_plain


def test_uncited_references_section_with_content_keeps_its_heading(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Without citations the Markdown '## Referencias' section is ordinary
    content: the heading (and whatever the author wrote under it) renders."""
    body = "Texto sin citas.\n\n## Referencias\n\nFuentes consultadas manualmente.\n"
    config = make_config(tmp_path_factory.mktemp("bib-manual"), body)
    tex = build_latex_report.render_tex(config)
    assert r"\printbibliography" not in tex
    assert r"\subsection{Referencias}" in tex
    assert "Fuentes consultadas manualmente." in tex


# ---------------------------------------------------------------------------
# Citation detection uses rendered-body semantics, not raw Markdown (#26)
# ---------------------------------------------------------------------------


def test_fenced_code_examples_do_not_trigger_the_bibliography(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """A fenced/inline literal `[@key]` example renders no \\cite, so the
    bibliography must not print over an empty reference list."""
    body = (
        "Ejemplo de sintaxis:\n\n"
        "```text\nCite asi: [@silberschatz2018].\n```\n\n"
        "Inline: `[@tanenbaum2015]` es un ejemplo literal.\n"
    )
    config = make_config(tmp_path_factory.mktemp("bib-fenced"), body)
    tex = build_latex_report.render_tex(config)
    assert r"\printbibliography" not in tex
    assert r"\cite{silberschatz2018}" not in tex
    assert r"\cite{tanenbaum2015}" not in tex


def test_real_citation_next_to_fenced_example_still_prints(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    body = (
        "Los procesos planifican tareas [@silberschatz2018].\n\n"
        "```text\nCite asi: [@tanenbaum2015].\n```\n"
    )
    config = make_config(tmp_path_factory.mktemp("bib-mixed"), body)
    tex = build_latex_report.render_tex(config)
    assert tex.count(r"\printbibliography") == 1
    assert r"\cite{silberschatz2018}" in tex
    assert r"\cite{tanenbaum2015}" not in tex
