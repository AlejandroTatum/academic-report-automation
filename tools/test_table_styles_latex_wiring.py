"""Tests wiring contextual table styles into build_latex_report.py (issue #13).

`table_styles_enabled` (default False) must leave the LEGACY generic
renderer byte-for-byte unchanged for every report that has not opted in
(zero regression risk). Only a report that opts in activates
directive-driven per-table selection -- and, once opted in, every table
must carry a directive; there is no silent fallback to the generic style.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import build_latex_report  # noqa: E402
from table_model import TableStylesContext  # noqa: E402
from table_styles import load_catalog  # noqa: E402

CATALOG = load_catalog()

DIRECTED_MD = """\
# Resultados

<!-- table-style: results-summary purpose=reference -->
| Name | Score |
| ---- | ----- |
| Ana  | 9     |
| Luis | 7     |
"""

UNDIRECTED_MD = """\
# Resultados

| Name | Score |
| ---- | ----- |
| Ana  | 9     |
"""


def _styles_context(**overrides: object) -> TableStylesContext:
    fields: dict[str, object] = {
        "catalog": CATALOG,
        "teacher_overrides": {},
        "institution_override": None,
    }
    fields.update(overrides)
    return TableStylesContext(**fields)  # type: ignore[arg-type]


def test_table_styles_disabled_by_default_uses_legacy_render_table() -> None:
    tex = build_latex_report.markdown_to_latex(DIRECTED_MD)
    assert r"\rowcolor[gray]{0.92}" in tex  # legacy generic header shading
    assert "% table-style:" not in tex


def test_table_styles_enabled_renders_selected_style() -> None:
    tex = build_latex_report.markdown_to_latex(DIRECTED_MD, table_styles=_styles_context())
    assert "% table-style: TAB-CL-01" in tex


def test_table_styles_enabled_applies_teacher_override() -> None:
    styles = _styles_context(teacher_overrides={"results-summary": "TAB-MN-03"})
    tex = build_latex_report.markdown_to_latex(DIRECTED_MD, table_styles=styles)
    assert "% table-style: TAB-MN-03" in tex


def test_table_styles_enabled_blocks_on_missing_directive() -> None:
    with pytest.raises(SystemExit, match="table-style"):
        build_latex_report.markdown_to_latex(UNDIRECTED_MD, table_styles=_styles_context())


def test_directive_comment_never_renders_as_visible_text() -> None:
    # The directive is an inert HTML comment (issue #13): it must not leak
    # into the PDF as escaped paragraph text, enabled or not.
    tex = build_latex_report.markdown_to_latex(DIRECTED_MD, table_styles=_styles_context())
    assert "table-style" not in tex.replace("% table-style:", "")
    tex_disabled = build_latex_report.markdown_to_latex(DIRECTED_MD)
    assert "<!--" not in tex_disabled
