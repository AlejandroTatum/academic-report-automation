"""Tests for the Markdown table-style directive/marker authoring convention.

Authoring convention approved 2026-09-22 (see
odd/tasks/contextual-table-styles.md, "Decision gap found while scoping T3"):

    <!-- table-style: <key> purpose=<p> [meaning=..] [emphasis=..]
         [color_policy=..] [accessibility_needs=..] [emphasis_column=<n>] -->
    | header | ... |
    | ------ | --- |
    | cell [[status:ok]] | ... |

A table with no preceding directive is "undirected" (table_key=None,
context=None) -- not an error by itself; callers that opted into contextual
table styles decide whether that blocks a build. A directive with a missing
`purpose`, an out-of-range `emphasis_column`, or a malformed attribute
raises `TableDirectiveError` immediately: no silent fallback.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from table_directives import (  # noqa: E402
    STATUS_MARKER_RE,
    TableDirectiveError,
    context_for_table,
    parse_table_blocks,
    strip_status_markers,
)

DIRECTED_DOC = """\
Intro paragraph.

<!-- table-style: results-summary purpose=reference -->
| Name | Score |
| ---- | ----- |
| Ana  | 9     |
| Luis | 7     |

More text.
"""

UNDIRECTED_DOC = """\
| Name | Score |
| ---- | ----- |
| Ana  | 9     |
"""

FULL_ATTRS_DOC = """\
<!-- table-style: status-matrix purpose=status meaning=status emphasis=column color_policy=grayscale accessibility_needs=true emphasis_column=1 -->
| Item | Status |
| ---- | ------ |
| A    | [[status:ok]] |
| B    | [[status:fail]] |
"""

MISSING_PURPOSE_DOC = """\
<!-- table-style: broken -->
| A | B |
| --- | --- |
| 1 | 2 |
"""

OUT_OF_RANGE_COLUMN_DOC = """\
<!-- table-style: broken purpose=reference emphasis_column=5 -->
| A | B |
| --- | --- |
| 1 | 2 |
"""


def test_undirected_table_has_no_key_or_context() -> None:
    blocks = parse_table_blocks(UNDIRECTED_DOC)
    assert len(blocks) == 1
    assert blocks[0].table_key is None
    assert blocks[0].context is None
    assert blocks[0].header == ["Name", "Score"]


def test_directed_table_derives_structure_and_carries_declared_fields() -> None:
    blocks = parse_table_blocks(DIRECTED_DOC)
    assert len(blocks) == 1
    block = blocks[0]
    assert block.table_key == "results-summary"
    assert block.context is not None
    assert block.context.purpose == "reference"
    assert block.context.columns == 2
    assert block.context.rows == 2
    assert block.context.length == "short"
    assert block.context.emphasis_column is None


def test_full_attribute_set_and_status_markers_parse() -> None:
    blocks = parse_table_blocks(FULL_ATTRS_DOC)
    block = blocks[0]
    assert block.table_key == "status-matrix"
    assert block.context.meaning == "status"
    assert block.context.emphasis == "column"
    assert block.context.color_policy == "grayscale"
    assert block.context.accessibility_needs is True
    assert block.context.emphasis_column == 1
    # Status markers are preserved verbatim in cell text for the renderer to
    # strip per backend -- the parser only validates structure here.
    assert "[[status:ok]]" in block.rows[0][1]
    assert "[[status:fail]]" in block.rows[1][1]


def test_missing_purpose_blocks() -> None:
    with pytest.raises(TableDirectiveError, match="purpose"):
        parse_table_blocks(MISSING_PURPOSE_DOC)


def test_out_of_range_emphasis_column_blocks() -> None:
    with pytest.raises(TableDirectiveError, match="emphasis_column"):
        parse_table_blocks(OUT_OF_RANGE_COLUMN_DOC)


def test_strip_status_markers_extracts_values_and_placeholders() -> None:
    clean, markers = strip_status_markers("Result [[status:ok]] confirmed")
    assert markers == ["ok"]
    assert "[[status:ok]]" not in clean
    assert STATUS_MARKER_RE.search(clean) is None


def test_strip_status_markers_handles_multiple_markers_in_order() -> None:
    clean, markers = strip_status_markers("[[status:ok]] then [[status:fail]]")
    assert markers == ["ok", "fail"]


def test_context_for_table_finds_preceding_directive() -> None:
    lines = DIRECTED_DOC.splitlines()
    # Header row "| Name | Score |" is line index 4 (0-indexed) in DIRECTED_DOC.
    table_start = next(idx for idx, line in enumerate(lines) if line.startswith("| Name"))
    key, context = context_for_table(lines, table_start, ["Name", "Score"], [["Ana", "9"], ["Luis", "7"]])
    assert key == "results-summary"
    assert context.purpose == "reference"


def test_context_for_table_returns_none_when_undirected() -> None:
    lines = UNDIRECTED_DOC.splitlines()
    table_start = 0
    key, context = context_for_table(lines, table_start, ["Name", "Score"], [["Ana", "9"]])
    assert key is None
    assert context is None
