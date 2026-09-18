"""Route-derived rendering defaults (#23).

``document-routing.md`` says only Route A may activate academic machinery.
Before this fix every route silently received the academic defaults: the UNL
institutional template, a required academic cover, an UNL logo check,
numbered academic headings and a body that must start on page 2 — so a
technical document came out wearing the UNL shell and its validation failed
against academic expectations it never agreed to.

These tests pin the derived defaults AND their precedence:

  1. explicit report.yml keys always win (template, cover, section_numbering);
  2. an absent route keeps the historical academic defaults (legacy reports);
  3. non-academic routes derive a plain, non-institutional document by default,
     with no academic preliminary pages (no forced list of figures);
  4. nothing rewrites report.yml — derivation happens at resolution time only.
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
from report_config import ReportConfig  # noqa: E402

UNL_TEMPLATE = ROOT / "templates" / "unl-report.tex"
PLAIN_TEMPLATE = ROOT / "templates" / "plain-report.tex"

ACADEMIC_META = {
    "title": "Planificación de CPU",
    "subject": "Sistemas Operativos",
    "teacher": "Ing. Hernán Torres",
    "student": "Alejandro Padilla",
    "date": "7 de agosto de 2026",
}
NON_ACADEMIC_META = {
    "title": "Guía técnica del pipeline",
    "author": "Equipo de plataforma",
    "date": "7 de agosto de 2026",
}


def make_config(tmp_path: Path, raw: dict) -> ReportConfig:
    """Load a real ReportConfig (academic_format.yml included) from disk."""
    folder = tmp_path / "r"
    folder.mkdir(parents=True, exist_ok=True)
    base = {
        "type": "technical_report",
        "backend": "latex",
        "output": "pdf",
        "pdf": "build/report.pdf",
        "body": "body.md",
    }
    base.update(raw)
    (folder / "report.yml").write_text(yaml.safe_dump(base), encoding="utf-8")
    (folder / "body.md").write_text("# Propósito\n\nContenido.\n", encoding="utf-8")
    return ReportConfig.load(folder)


def rendered_template_name(config: ReportConfig) -> str:
    """The template render_tex() would use, without rendering."""
    return build_latex_report.resolve_template(
        build_latex_report.template_key_for(config)
    ).name


# ---------------------------------------------------------------------------
# Template defaults derive from the route
# ---------------------------------------------------------------------------


def test_absent_route_and_template_keep_the_academic_default(tmp_path):
    assert rendered_template_name(make_config(tmp_path, {})) == UNL_TEMPLATE.name


@pytest.mark.parametrize("route", ["project", "business", "technical", "other"])
@pytest.mark.parametrize("letter", ["b", "c", "d", "e"])
def test_non_academic_routes_default_to_the_plain_template(tmp_path, route, letter):
    assert rendered_template_name(make_config(tmp_path, {"route": route})) == PLAIN_TEMPLATE.name
    assert rendered_template_name(make_config(tmp_path, {"route": letter})) == PLAIN_TEMPLATE.name


def test_explicit_template_beats_the_route_default(tmp_path):
    """A technical report asking for the UNL shell explicitly gets it."""
    config = make_config(tmp_path, {"route": "technical", "template": "unl"})
    assert rendered_template_name(config) == UNL_TEMPLATE.name


def test_academic_route_can_explicitly_choose_plain(tmp_path):
    config = make_config(tmp_path, {"route": "academic", "template": "plain"})
    assert rendered_template_name(config) == PLAIN_TEMPLATE.name


def test_unknown_template_key_still_fails_loudly_on_any_route(tmp_path):
    config = make_config(tmp_path, {"route": "technical", "template": "plian"})
    with pytest.raises(SystemExit) as excinfo:
        build_latex_report.resolve_template(build_latex_report.template_key_for(config))
    assert "plian" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Front matter / preliminary pages derive from the route (#23 fix 1)
# ---------------------------------------------------------------------------


def test_technical_route_with_figures_gets_no_academic_prelim_pages(tmp_path):
    """A technical report never auto-receives an academic list of figures.

    The routing contract forbids academic prelim machinery on Routes B-D;
    figures themselves still render, only the academic LIST_OF_FIGURES page
    must stay empty.
    """
    tex = build_latex_report.render_tex(
        make_render_config(tmp_path, {"route": "technical"}, True)
    )
    assert r"\includegraphics" in tex
    assert r"\listoffigures" not in tex
    assert r"\newpage\listoffigures" not in tex


def test_project_route_with_figures_gets_no_academic_prelim_pages(tmp_path):
    tex = build_latex_report.render_tex(
        make_render_config(tmp_path, {"route": "project"}, True)
    )
    assert r"\includegraphics" in tex
    assert r"\listoffigures" not in tex


def test_explicit_template_unl_does_not_reinstate_the_prelim_page(tmp_path):
    """Template choice is typographic; the route owns academic prelim pages."""
    tex = build_latex_report.render_tex(
        make_render_config(tmp_path, {"route": "technical", "template": "unl"}, True)
    )
    assert "titlepage" in tex
    assert r"\listoffigures" not in tex


def test_academic_route_with_figures_keeps_the_list_of_figures(tmp_path):
    tex = build_latex_report.render_tex(make_render_config(tmp_path, {"route": "academic"}, True))
    assert r"\listoffigures" in tex


def test_route_omitted_report_with_figures_keeps_legacy_list_of_figures(tmp_path):
    """Every report written before `route:` existed keeps its prelim page."""
    config = make_render_config(tmp_path, {"template": "plain"}, True)
    assert config.route == "academic"
    tex = build_latex_report.render_tex(config)
    assert r"\listoffigures" in tex


# ---------------------------------------------------------------------------
# Section numbering defaults derive from the route
# ---------------------------------------------------------------------------


def test_absent_route_and_key_still_number_sections():
    assert build_latex_report.section_numbering_enabled({}) is True


@pytest.mark.parametrize("route", ["project", "business", "technical", "other"])
def test_non_academic_routes_default_to_unnumbered_sections(route):
    assert build_latex_report.section_numbering_enabled({"route": route}) is False


def test_explicit_section_numbering_beats_the_route_default():
    key = build_latex_report.SECTION_NUMBERING_KEY
    assert build_latex_report.section_numbering_enabled({"route": "technical", key: True}) is True
    assert build_latex_report.section_numbering_enabled({"route": "academic", key: False}) is False


# ---------------------------------------------------------------------------
# Rendered TeX matrix: route x override x figures
# ---------------------------------------------------------------------------


def write_body(folder: Path, with_figure: bool) -> None:
    figure = "\n\n![Un diagrama](assets/generated/diagrama.png)\n" if with_figure else ""
    (folder / "body.md").write_text("# Propósito\n\nContenido." + figure, encoding="utf-8")


def make_render_config(tmp_path: Path, raw: dict, with_figure: bool) -> ReportConfig:
    config = make_config(tmp_path, raw)
    write_body(config.folder, with_figure)
    return config


def test_technical_render_has_no_academic_shell_without_figures(tmp_path):
    tex = build_latex_report.render_tex(make_render_config(tmp_path, {"route": "technical"}, False))
    assert "titlepage" not in tex
    assert r"\listoffigures" not in tex
    assert r"\newcommand{\reportsectionnumbering}{false}" in tex
    assert "DOCENTE" not in tex and "Facultad de la Energ" not in tex.split("% Universidad")[0]


def test_technical_render_with_figures_keeps_figures_but_no_academic_shell(tmp_path):
    tex = build_latex_report.render_tex(make_render_config(tmp_path, {"route": "technical"}, True))
    assert r"\includegraphics" in tex
    assert "titlepage" not in tex


def test_academic_render_unchanged_no_figures(tmp_path):
    tex = build_latex_report.render_tex(make_render_config(tmp_path, {}, False))
    assert "titlepage" in tex
    assert r"\listoffigures" not in tex
    assert r"\newcommand{\reportsectionnumbering}{true}" in tex


def test_technical_explicit_unl_template_renders_the_shell(tmp_path):
    tex = build_latex_report.render_tex(
        make_render_config(tmp_path, {"route": "technical", "template": "unl"}, False)
    )
    assert "titlepage" in tex
    assert r"\newcommand{\reportsectionnumbering}{false}" in tex, (
        "the explicit template choice must not re-enable academic numbering"
    )


def test_technical_explicit_numbering_true_renumbers(tmp_path):
    tex = build_latex_report.render_tex(
        make_render_config(
            tmp_path, {"route": "technical", build_latex_report.SECTION_NUMBERING_KEY: True}, False
        )
    )
    assert r"\newcommand{\reportsectionnumbering}{true}" in tex


def test_render_never_rewrites_report_yml(tmp_path):
    """Derivation happens at resolution time; the written YAML stays as authored."""
    make_render_config(tmp_path, {"route": "technical"}, False)
    folder = tmp_path / "r"
    before = (folder / "report.yml").read_text(encoding="utf-8")
    build_latex_report.render_tex(ReportConfig.load(folder))
    assert (folder / "report.yml").read_text(encoding="utf-8") == before
    assert "template" not in yaml.safe_load(before)
