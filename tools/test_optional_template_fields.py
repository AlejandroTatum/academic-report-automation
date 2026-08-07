"""Tests for template fields that may legitimately be absent.

A report is not required to declare every metadata field. When an optional one
is missing, the renderer substitutes an empty string — and on a cover page that
turns `{\\large {{FIELD}}}\\\\` into `{\\large }\\\\`, which is a *fatal* LaTeX
error: `! LaTeX Error: There's no line here to end.` The build dies with a
message pointing at the title page instead of at the field nobody set.

These tests work on the rendered output rather than on template source, because
the empty sized group is the actual failure mode. A template-pattern test would
also flag fields that always carry a default and can never be empty.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import build_latex_report  # noqa: E402
import report_config  # noqa: E402

# Every template key the router accepts, one per distinct template file.
TEMPLATE_KEYS = ("unl", "plain", "chamba_overleaf")

# A brace group terminated by a line break: `{...}\\`.
_SIZED_LINE = re.compile(r"\{([^{}]*)\}\s*\\\\")

# Commands that only change how following text looks. A group made of nothing
# but these typesets no box, so `\\` has no line to end and LaTeX aborts.
_STYLE_ONLY = re.compile(r"^(?:\s*\\[a-zA-Z]+)+\s*$")


def empty_sized_lines(tex: str) -> list[str]:
    r"""Return every `{...}\\` group that typesets nothing.

    `{\large }\\` and `{\bfseries }\\` are fatal. `{\large \strut}\\` is not:
    `\strut` is an invisible box with a normal line's height, so the line
    exists. That distinction is the whole point of the guard, which is why this
    cannot be a single "group of commands" pattern.

    An earlier version of this check only knew the sizing commands, passed
    happily, and the real Docker build still died on a `{\bfseries }\\` emitted
    from a different code path. Hence: match structurally, then decide.
    """
    offenders = []
    for match in _SIZED_LINE.finditer(tex):
        inner = match.group(1)
        if not inner.strip():
            offenders.append(match.group(0))
        elif _STYLE_ONLY.match(inner) and r"\strut" not in inner:
            offenders.append(match.group(0))
    return offenders


def make_config(tmp_path: Path, template: str, extra: dict | None = None):
    import yaml

    folder = tmp_path / "r"
    folder.mkdir(parents=True, exist_ok=True)
    # Deliberately minimal: only a title. Everything else is left unset so the
    # renderer has to cope with absent optional fields.
    metadata = {"title": "T"}
    metadata.update(extra or {})
    raw = {
        "type": "technical_report",
        "backend": "latex",
        "output": "pdf",
        "template": template,
        "metadata": metadata,
        "body": "body.md",
    }
    (folder / "report.yml").write_text(yaml.safe_dump(raw), encoding="utf-8")
    (folder / "body.md").write_text("# T\n\ncontent\n", encoding="utf-8")
    return report_config.ReportConfig.load(folder)


@pytest.mark.parametrize("template", TEMPLATE_KEYS)
def test_minimal_metadata_renders_no_empty_sized_line(
    tmp_path: Path, template: str,
) -> None:
    """With only a title set, no template may emit an empty sized line."""
    tex = build_latex_report.render_tex(make_config(tmp_path, template))
    hits = empty_sized_lines(tex)
    assert not hits, (
        f"template {template!r} rendered {len(hits)} empty sized line(s) with "
        f"minimal metadata; LaTeX fails on these with "
        f"'There's no line here to end.'"
    )


@pytest.mark.parametrize("template", TEMPLATE_KEYS)
@pytest.mark.parametrize("field", ["student", "teacher", "title_en"])
def test_each_optional_field_may_be_absent(
    tmp_path: Path, template: str, field: str,
) -> None:
    """Dropping any single optional field must not produce the fatal construct."""
    full = {"student": "A", "teacher": "D", "subject": "S", "title_en": "EN"}
    del full[field]
    tex = build_latex_report.render_tex(make_config(tmp_path, template, full))
    assert not empty_sized_lines(tex), (
        f"template {template!r} breaks when {field!r} is absent"
    )


# Not every template renders an English title — `unl-report.tex` deliberately
# has no such placeholder, so there is nothing there to swallow or preserve.
TEMPLATES_WITH_TITLE_EN = ("plain", "chamba_overleaf")


@pytest.mark.parametrize("template", TEMPLATES_WITH_TITLE_EN)
def test_supplied_optional_fields_still_reach_the_document(
    tmp_path: Path, template: str,
) -> None:
    """The guard must not swallow a value that was actually provided."""
    tex = build_latex_report.render_tex(
        make_config(tmp_path, template, {"title_en": "An English Title"}),
    )
    assert "An English Title" in tex
