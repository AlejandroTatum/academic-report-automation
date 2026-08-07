"""Tests for figure detection in the LaTeX renderer.

`{{HAS_FIGURES}}` and `{{LIST_OF_FIGURES}}` decide whether the rendered
document gets a list of figures. Detection has to run against the Markdown
source, because that is where the `![caption](path)` syntax exists. Once the
body has been converted the images are already `\\includegraphics` commands
and the Markdown pattern can never match again.

These tests pin the observable behaviour:
  1. A body containing a Markdown image produces a list of figures.
  2. A body with no images does not.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import build_latex_report  # noqa: E402
import report_config  # noqa: E402

BODY_WITH_FIGURE = """# Section

Some prose before the figure.

![A flow diagram. Source: own elaboration.](../assets/flow.png)

Some prose after the figure.
"""

BODY_WITHOUT_FIGURE = """# Section

Only prose here, no images at all.
"""


# Every template must honour figure detection. `unl-report.tex` originally
# exposed no {{LIST_OF_FIGURES}} placeholder at all, so an academic report with
# figures silently got no figure index — and the placeholder test only checked
# the plain template, so nothing caught it.
TEMPLATE_KEYS = ("unl", "plain", "chamba_overleaf")


def make_config(
    tmp_path: Path, body: str, template: str = "plain",
) -> "report_config.ReportConfig":
    import yaml

    folder = tmp_path / "r"
    folder.mkdir(parents=True, exist_ok=True)
    raw = {
        "type": "technical_report",
        "backend": "latex",
        "output": "pdf",
        "template": template,
        "metadata": {"title": "T", "subject": "S", "teacher": "D", "student": "A"},
        "body": "body.md",
    }
    (folder / "report.yml").write_text(yaml.safe_dump(raw), encoding="utf-8")
    (folder / "body.md").write_text(body, encoding="utf-8")
    return report_config.ReportConfig.load(folder)


@pytest.mark.parametrize("template", TEMPLATE_KEYS)
def test_markdown_image_produces_a_list_of_figures(
    tmp_path: Path, template: str,
) -> None:
    config = make_config(tmp_path, BODY_WITH_FIGURE, template)
    rendered = build_latex_report.render_tex(config)
    assert r"\listoffigures" in rendered


@pytest.mark.parametrize("template", TEMPLATE_KEYS)
def test_body_without_images_has_no_list_of_figures(
    tmp_path: Path, template: str,
) -> None:
    config = make_config(tmp_path, BODY_WITHOUT_FIGURE, template)
    rendered = build_latex_report.render_tex(config)
    assert r"\listoffigures" not in rendered


@pytest.mark.parametrize("template", TEMPLATE_KEYS)
def test_template_exposes_the_figure_list_placeholder(template: str) -> None:
    r"""Every template must have somewhere to put the list.

    Only `{{LIST_OF_FIGURES}}` is required. The renderer already substitutes an
    empty string when the body has no images, so a bare placeholder is
    self-gating; the extra `{{HAS_FIGURES}}` flag that `plain-report.tex` uses
    is one valid implementation, not a contract.
    """
    path = build_latex_report.resolve_template(template)
    tex = path.read_text(encoding="utf-8")
    assert "{{LIST_OF_FIGURES}}" in tex, f"{path.name} exposes no figure list"


@pytest.mark.parametrize("template", TEMPLATE_KEYS)
def test_template_localizes_the_figure_list_title(template: str) -> None:
    r"""The documents are written in Spanish; the index heading must match.

    Without `\renewcommand{\listfigurename}{...}`, `\listoffigures` prints the
    LaTeX default "List of Figures" in the middle of a Spanish report.
    """
    path = build_latex_report.resolve_template(template)
    tex = path.read_text(encoding="utf-8")
    assert r"\renewcommand{\listfigurename}" in tex, (
        f"{path.name} emits a figure list but never localizes its title"
    )
