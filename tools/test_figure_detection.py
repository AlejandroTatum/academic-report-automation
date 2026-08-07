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


def make_config(tmp_path: Path, body: str) -> "report_config.ReportConfig":
    import yaml

    folder = tmp_path / "r"
    folder.mkdir(parents=True, exist_ok=True)
    raw = {
        "type": "technical_report",
        "backend": "latex",
        "output": "pdf",
        # The plain template is the one that exposes {{LIST_OF_FIGURES}}, so it
        # is where the effect of figure detection is observable end to end.
        "template": "plain",
        "metadata": {"title": "T", "subject": "S", "teacher": "D", "student": "A"},
        "body": "body.md",
    }
    (folder / "report.yml").write_text(yaml.safe_dump(raw), encoding="utf-8")
    (folder / "body.md").write_text(body, encoding="utf-8")
    return report_config.ReportConfig.load(folder)


def test_markdown_image_produces_a_list_of_figures(tmp_path: Path) -> None:
    config = make_config(tmp_path, BODY_WITH_FIGURE)
    rendered = build_latex_report.render_tex(config)
    assert r"\listoffigures" in rendered


def test_body_without_images_has_no_list_of_figures(tmp_path: Path) -> None:
    config = make_config(tmp_path, BODY_WITHOUT_FIGURE)
    rendered = build_latex_report.render_tex(config)
    assert r"\listoffigures" not in rendered
