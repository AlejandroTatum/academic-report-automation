"""Template-level bibliography rendering contract (#26).

The UNL (academic) and plain templates used to hardcode
``\\printbibliography[title={...}]``, so both printed their bibliography title
even when the body cited nothing — an empty heading. The renderer now owns the
emission decision and fills a ``{{PRINT_BIBLIOGRAPHY}}`` placeholder. These
tests pin that both default templates agree on the placeholder contract and
that neither carries a hardcoded, always-on bibliography print anymore.
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

TEMPLATES = ROOT / "templates"

CITED_BODY = "Los procesos [@silberschatz2018] planifican tareas.\n"
UNCITED_BODY = "Los procesos planifican tareas.\n"

# Heading wording each template owns; the renderer only decides *whether* it
# prints (#26).
BIBLIOGRAPHY_TITLES = {
    "unl-report": "Bibliografía",
    "plain-report": "Referencias",
}

BIB_FILE = """\
@book{silberschatz2018,
  author = {Silberschatz, Abraham},
  title = {Operating System Concepts},
  year = {2018},
}
"""


def make_config(folder: Path, body: str, template: str) -> report_config.ReportConfig:
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


# ---------------------------------------------------------------------------
# Template contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("template_name", ["unl-report.tex", "plain-report.tex"])
def test_template_delegates_bibliography_print_to_the_renderer(template_name: str) -> None:
    text = (TEMPLATES / template_name).read_text(encoding="utf-8")
    assert "{{PRINT_BIBLIOGRAPHY}}" in text, (
        f"{template_name} must let the renderer decide the bibliography print (#26)"
    )
    assert r"\printbibliography[" not in text, (
        f"{template_name} must not hardcode an always-on bibliography print"
    )


@pytest.mark.parametrize("template_name", ["unl-report.tex", "plain-report.tex"])
def test_template_keeps_its_own_bibliography_title(template_name: str) -> None:
    """The academic shell keeps 'Bibliografía'; plain keeps 'Referencias'."""
    assert BIBLIOGRAPHY_TITLES[template_name.replace(".tex", "")]


def test_bibliography_titles_cover_the_fillable_templates() -> None:
    for key in ("default", "unl", "plain"):
        assert key in build_latex_report.BIBLIOGRAPHY_TITLES



# ---------------------------------------------------------------------------
# Both templates agree on citation-driven emission
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("template", ["unl", "plain"])
def test_cited_body_prints_bibliography_on_both_templates(
    tmp_path_factory: pytest.TempPathFactory, template: str
) -> None:
    config = make_config(tmp_path_factory.mktemp(f"cited-{template}"), CITED_BODY, template)
    tex = build_latex_report.render_tex(config)
    assert tex.count(r"\printbibliography") == 1
    assert "{{PRINT_BIBLIOGRAPHY}}" not in tex, "renderer must fill the placeholder"


@pytest.mark.parametrize("template", ["unl", "plain"])
def test_uncited_body_prints_no_bibliography_on_both_templates(
    tmp_path_factory: pytest.TempPathFactory, template: str
) -> None:
    config = make_config(tmp_path_factory.mktemp(f"uncited-{template}"), UNCITED_BODY, template)
    tex = build_latex_report.render_tex(config)
    assert r"\printbibliography" not in tex


@pytest.mark.parametrize("template", ["unl", "plain"])
def test_each_template_prints_its_own_title(
    tmp_path_factory: pytest.TempPathFactory, template: str
) -> None:
    config = make_config(tmp_path_factory.mktemp(f"title-{template}"), CITED_BODY, template)
    tex = build_latex_report.render_tex(config)
    if template == "unl":
        assert r"\printbibliography[title={Bibliografía}]" in tex
    else:
        assert r"\printbibliography[title={Referencias}]" in tex


# ---------------------------------------------------------------------------
# Template parity: every supported template delegates the print (#26)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "template_name,title",
    [
        ("unl-report.tex", "Bibliograf\u00eda"),
        ("plain-report.tex", "Referencias"),
        ("chamba-overleaf.tex", "Referencias bibliogr\u00e1ficas"),
    ],
)
def test_every_supported_template_delegates_the_bibliography_print(
    template_name: str, title: str
) -> None:
    text = (TEMPLATES / template_name).read_text(encoding="utf-8")
    assert "{{PRINT_BIBLIOGRAPHY}}" in text, (
        f"{template_name} must let the renderer decide the bibliography print (#26)"
    )
    assert r"\printbibliography[" not in text, (
        f"{template_name} must not hardcode an always-on bibliography print"
    )
    assert build_latex_report.BIBLIOGRAPHY_TITLES[
        template_name.replace(".tex", "").replace("-", "_")
    ] == title


@pytest.mark.parametrize("template", ["unl", "plain", "chamba_overleaf"])
def test_citation_driven_emission_agrees_across_all_templates(
    tmp_path_factory: pytest.TempPathFactory, template: str
) -> None:
    config = make_config(tmp_path_factory.mktemp(f"parity-{template}"), CITED_BODY, template)
    tex = build_latex_report.render_tex(config)
    assert tex.count(r"\printbibliography") == 1
    assert "{{PRINT_BIBLIOGRAPHY}}" not in tex


@pytest.mark.parametrize("template", ["unl", "plain", "chamba_overleaf"])
def test_uncited_bodies_print_no_bibliography_on_any_template(
    tmp_path_factory: pytest.TempPathFactory, template: str
) -> None:
    config = make_config(tmp_path_factory.mktemp(f"parity0-{template}"), UNCITED_BODY, template)
    tex = build_latex_report.render_tex(config)
    assert r"\printbibliography" not in tex
