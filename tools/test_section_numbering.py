"""Tests for the per-report academic section numbering switch.

`skills/academic-report-builder/references/document-routing.md` lists
"academic section numbering" among the things Route B (project documentation)
MUST NOT auto-include, and Routes C and D forbid academic furniture too. The
plain template numbered sections unconditionally, so a technical document came
out as `1. Propósito`, `2. Alcance`, ... `11. Referencias` with no way to turn
it off.

`section_numbering:` in report.yml now controls it. With the key absent the default is
ROUTE-derived (#23): numbered for the academic route (every existing
route-omitted report), unnumbered for Routes B–D, which the routing contract
forbids from auto-including academic numbering. An explicit key overrides the
route default in either direction.
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

PLAIN_TEMPLATE = ROOT / "templates" / "plain-report.tex"
UNL_TEMPLATE = ROOT / "templates" / "unl-report.tex"
TEMPLATES = (PLAIN_TEMPLATE, UNL_TEMPLATE)

PLACEHOLDER = "{{SECTION_NUMBERING}}"


def make_config(tmp_path: Path, raw: dict) -> "report_config.ReportConfig":
    """Build a minimal on-disk report and load it, mirroring test_plain_template."""
    folder = tmp_path / "r"
    folder.mkdir(parents=True, exist_ok=True)
    base = {
        "type": "technical_report",
        "backend": "latex",
        "output": "pdf",
        "template": "plain",
        "metadata": {"title": "T", "subject": "S", "teacher": "D", "student": "A"},
        "body": "body.md",
    }
    base.update(raw)
    (folder / "report.yml").write_text(yaml.safe_dump(base), encoding="utf-8")
    (folder / "body.md").write_text("# Propósito\n\ncontent\n", encoding="utf-8")
    return report_config.ReportConfig.load(folder)


# ---------------------------------------------------------------------------
# The templates expose the switch
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: p.name)
def test_template_exposes_the_numbering_placeholder(template: Path) -> None:
    """Both templates carry the same mechanism, so neither is a special case."""
    assert PLACEHOLDER in template.read_text(encoding="utf-8"), (
        f"{template.name} must expose {PLACEHOLDER}"
    )


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: p.name)
def test_template_suppresses_only_the_printed_label(template: Path) -> None:
    r"""`secnumdepth` is the mechanism, not `\section*`.

    Starring the headings would drop them from the table of contents and from
    the hyperref anchor tree. Lowering `secnumdepth` removes only the printed
    number: `\@sect` still calls `\addcontentsline` and hyperref still places
    its anchor.
    """
    tex = template.read_text(encoding="utf-8")
    assert "secnumdepth" in tex, (
        f"{template.name} must switch numbering through secnumdepth"
    )


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: p.name)
def test_heading_spacing_machinery_is_untouched(template: Path) -> None:
    """The numbering switch must not disturb the tuned heading layout."""
    tex = template.read_text(encoding="utf-8")
    assert r"\titlespacing*{\section}{0pt}{18pt}{10pt}" in tex
    assert r"\titlespacing*{\subsection}{0pt}{14pt}{7pt}" in tex
    assert r"\titlespacing*{\subsubsection}{0pt}{10pt}{5pt}" in tex
    assert r"\Needspace" in tex, "the orphan-heading guard must survive"


# ---------------------------------------------------------------------------
# Value parsing
# ---------------------------------------------------------------------------


def test_absent_key_means_numbered_on_the_academic_route() -> None:
    """The default for route-omitted reports stays the historical behaviour."""
    assert build_latex_report.section_numbering_enabled({}) is True
    assert build_latex_report.section_numbering_enabled({"route": "academic"}) is True


@pytest.mark.parametrize("value", [True, "true", "True", "yes", "on", "si", "sí"])
def test_truthy_values_keep_numbering(value: object) -> None:
    assert build_latex_report.section_numbering_enabled(
        {build_latex_report.SECTION_NUMBERING_KEY: value}
    ) is True


@pytest.mark.parametrize("value", [False, "false", "False", "no", "off"])
def test_falsy_values_disable_numbering(value: object) -> None:
    assert build_latex_report.section_numbering_enabled(
        {build_latex_report.SECTION_NUMBERING_KEY: value}
    ) is False


def test_unrecognised_value_fails_loudly() -> None:
    """A typo must not quietly pick a side and change the document's look."""
    with pytest.raises(SystemExit) as excinfo:
        build_latex_report.section_numbering_enabled(
            {build_latex_report.SECTION_NUMBERING_KEY: "maybe"}
        )
    message = str(excinfo.value)
    assert "maybe" in message
    assert build_latex_report.SECTION_NUMBERING_KEY in message


def test_route_moves_the_default_and_explicit_choice_wins() -> None:
    """Routes B–D forbid auto-included academic numbering (#23).

    The absent key now derives from the route; an explicit key overrides the
    route default in either direction.
    """
    key = build_latex_report.SECTION_NUMBERING_KEY
    for route in ("project", "business", "technical", "other"):
        assert build_latex_report.section_numbering_enabled({"route": route}) is False
        assert build_latex_report.section_numbering_enabled({"route": route, key: True}) is True
    assert build_latex_report.section_numbering_enabled({"route": "academic", key: False}) is False


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_rendered_tex_is_numbered_by_default(tmp_path: Path) -> None:
    tex = build_latex_report.render_tex(make_config(tmp_path, {}))
    assert PLACEHOLDER not in tex, "the placeholder must be substituted"
    assert r"\newcommand{\reportsectionnumbering}{true}" in tex


def test_rendered_tex_drops_numbers_when_switched_off(tmp_path: Path) -> None:
    config = make_config(tmp_path, {build_latex_report.SECTION_NUMBERING_KEY: False})
    tex = build_latex_report.render_tex(config)
    assert r"\newcommand{\reportsectionnumbering}{false}" in tex


def test_switching_numbering_off_changes_nothing_else(tmp_path: Path) -> None:
    """The only difference between the two renders is the switch itself."""
    numbered = build_latex_report.render_tex(make_config(tmp_path / "on", {}))
    unnumbered = build_latex_report.render_tex(
        make_config(tmp_path / "off", {build_latex_report.SECTION_NUMBERING_KEY: False})
    )
    assert numbered.replace(
        r"\newcommand{\reportsectionnumbering}{true}",
        r"\newcommand{\reportsectionnumbering}{false}",
    ) == unnumbered


def test_academic_template_still_defaults_to_numbered(tmp_path: Path) -> None:
    """Route A legitimately wants numbering; its default must not move."""
    config = make_config(tmp_path, {"template": "unl"})
    tex = build_latex_report.render_tex(config)
    assert r"\newcommand{\reportsectionnumbering}{true}" in tex
