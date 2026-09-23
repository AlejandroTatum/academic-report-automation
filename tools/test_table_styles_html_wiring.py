"""Tests wiring contextual table styles into build_report.py (issue #13).

build_report.py has no ReportConfig (it renders one bare Markdown file), so
there is no per-report `table_styles.enabled` flag here: a DIRECTED table
(one with a `<!-- table-style: ... -->` comment immediately before it) is
always rendered through the token mapper via automatic contextual
selection (no override machinery either, for the same reason); an
UNDIRECTED table renders exactly as before, through python-markdown's
"tables" extension -- no opt-in, no block-on-missing-directive, since
there is no config object to opt in with. Documented in
odd/tasks/contextual-table-styles.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import build_report  # noqa: E402

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


def _render(tmp_path: Path, markdown_text: str) -> str:
    md_path = tmp_path / "body.md"
    md_path.write_text(markdown_text, encoding="utf-8")
    css_path = tmp_path / "missing.css"
    return build_report.render(md_path, css_path)


def test_undirected_table_renders_through_legacy_tables_extension(tmp_path: Path) -> None:
    html = _render(tmp_path, UNDIRECTED_MD)
    assert 'data-table-style' not in html
    assert "<table>" in html  # python-markdown's own "tables" extension output


def test_directed_table_renders_through_token_mapper(tmp_path: Path) -> None:
    html = _render(tmp_path, DIRECTED_MD)
    assert 'data-table-style="TAB-CL-01"' in html
    assert "<!-- table-style:" not in html


def test_directed_table_supports_inline_markdown_in_cells(tmp_path: Path) -> None:
    markdown_text = (
        "<!-- table-style: results-summary purpose=reference -->\n"
        "| Name | Score |\n| ---- | ----- |\n| **Ana** | 9 |\n"
    )
    html = _render(tmp_path, markdown_text)
    assert "<strong>Ana</strong>" in html


def test_mixed_directed_and_undirected_tables_both_render(tmp_path: Path) -> None:
    markdown_text = DIRECTED_MD + "\n" + UNDIRECTED_MD
    html = _render(tmp_path, markdown_text)
    assert 'data-table-style="TAB-CL-01"' in html
    assert html.count("<table") == 2


def test_table_style_directive_inside_a_fenced_code_block_is_left_alone(tmp_path: Path) -> None:
    """A documentation code sample showing the directive/table syntax must
    render as literal code, never be rewritten as a real styled table
    (T4+T5 review R3-fence-unaware-html-rewrite)."""
    markdown_text = (
        "# Ejemplo\n\n"
        "```markdown\n"
        "<!-- table-style: example purpose=reference -->\n"
        "| Name | Score |\n"
        "| ---- | ----- |\n"
        "| Ana  | 9     |\n"
        "```\n"
    )
    html = build_report.apply_table_styles(markdown_text)
    assert "data-table-style" not in html
    assert "<!-- table-style: example purpose=reference -->" in html
    assert "| Name | Score |" in html


def test_undirected_body_never_loads_the_style_catalog(tmp_path: Path, monkeypatch) -> None:
    """The catalog is loaded only once a directed table is actually found,
    so an HTML build with no styled tables never depends on it (T4+T5
    review R4-unconditional-catalog-load)."""
    def _fail() -> None:
        raise AssertionError("load_catalog() must not run for a body with no directed tables")

    monkeypatch.setattr(build_report, "load_catalog", _fail)
    body = build_report.apply_table_styles(UNDIRECTED_MD)
    assert "| Name | Score |" in body  # left untouched -- no rewrite attempted


def test_invalid_table_style_is_a_reported_finding_not_a_crash(tmp_path: Path) -> None:
    """An unapproved ``[[status:...]]`` marker must surface as a warning the
    caller collects, not an uncaught ``ValueError`` crashing the whole HTML
    preview build (T4+T5 review R3/R4-html-preview-crash)."""
    markdown_text = (
        "<!-- table-style: bad-marker purpose=status meaning=status -->\n"
        "| Componente | Estado |\n"
        "| ---------- | ------ |\n"
        "| API        | [[status:mystery]] |\n"
    )
    warnings: list[str] = []
    html = build_report.apply_table_styles(markdown_text, warnings=warnings)
    assert "data-table-style" not in html
    assert "[[status:mystery]]" in html  # left untouched, not silently dropped
    assert any("bad-marker" in warning for warning in warnings)

    # And through the full render() pipeline: the banner carries the
    # warning instead of the process crashing.
    md_path = tmp_path / "body.md"
    md_path.write_text(markdown_text, encoding="utf-8")
    rendered = build_report.render(md_path, tmp_path / "missing.css")
    assert "bad-marker" in rendered
