"""Markdown table-style directive parser (issue #13, authoring convention).

Approved 2026-09-22 (see odd/tasks/contextual-table-styles.md, "Decision gap
found while scoping T3") to resolve two tokens `tools/table_styles.py`
cannot derive from plain Markdown alone:

* `TAB-CE-05` (`row_rhythm: column_emphasis`) needs to know which column is
  the protagonist -- declared as `emphasis_column: <0-indexed int>`.
* `TAB-TC-02` / `TAB-ES-06` (`indicators: symbol_color`) need to know which
  cells carry a status meaning -- declared inline as `[[status:<value>]]`,
  stripped and mapped to a catalog-approved symbol+color+label at render
  time (`tools/table_styles.py::Catalog.status_indicators`).

Directive line (an HTML comment, invisible to any Markdown renderer),
immediately before its table (blank lines in between are allowed)::

    <!-- table-style: <key> purpose=<p> [meaning=..] [emphasis=..]
         [color_policy=..] [accessibility_needs=..] [emphasis_column=<n>] -->

A table with no such directive is "undirected": `table_key`/`context` are
``None``. That is not an error here -- a caller that opted into contextual
table styles decides whether an undirected table blocks its build (see
`tools/check_table_contexts.py`). A *malformed* present directive (missing
`purpose`, an out-of-range `emphasis_column`, an unrecognised attribute)
raises `TableDirectiveError` immediately: no silent fallback, matching every
other blocking rule in this feature.

Structural facts (`columns`, `rows`, `length`, `pagination`, `density`) are
always derived from the table itself, never declared -- the directive only
carries facts a parser cannot infer (purpose, semantic meaning/emphasis,
color policy, accessibility needs, the emphasis column).
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from table_styles import TableContext

DIRECTIVE_RE = re.compile(r"^<!--\s*table-style:\s*(?P<key>[A-Za-z0-9_-]+)(?P<attrs>.*?)-->\s*$")
ATTR_RE = re.compile(r"(?P<name>[a-z_]+)=(?P<value>\S+)")
STATUS_MARKER_RE = re.compile(r"\[\[status:(?P<value>[A-Za-z0-9_-]+)\]\]")

# Attribute name -> ("bool" | "int" | one of these string enums).
_ATTR_ENUMS: dict[str, tuple[str, ...] | None] = {
    "purpose": ("reference", "comparison", "status", "evidence", "dense"),
    "meaning": ("none", "comparison", "status"),
    "emphasis": ("none", "column"),
    "color_policy": ("color", "grayscale"),
    "accessibility_needs": None,  # bool
    "emphasis_column": None,  # int
}

_LENGTH_ROW_THRESHOLD = 6
_LENGTH_CELL_CHAR_THRESHOLD = 40
_MULTIPAGE_ROW_THRESHOLD = 25
_LOW_DENSITY_MAX_COLUMNS = 3
_MEDIUM_DENSITY_MAX_COLUMNS = 5


class TableDirectiveError(ValueError):
    """A present table-style directive is malformed: block, never guess."""


@dataclass(frozen=True)
class TableBlock:
    """One Markdown table: its raw cells, plus a directive-derived context.

    `table_key`/`context` are ``None`` for an undirected table (no
    preceding `<!-- table-style: ... -->` comment).
    """

    table_key: str | None
    context: TableContext | None
    header: list[str]
    rows: list[list[str]]
    line: int  # 1-indexed source line of the header row


def _split_row(row: str) -> list[str]:
    stripped = row.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def _is_separator(row: str) -> bool:
    cells = _split_row(row)
    return bool(cells) and all(re.match(r"^:?-{3,}:?$", cell) for cell in cells)


def _parse_attrs(key: str, attrs_text: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    remainder = attrs_text
    for match in ATTR_RE.finditer(attrs_text):
        name = match.group("name")
        if name not in _ATTR_ENUMS:
            raise TableDirectiveError(f"table-style '{key}': unknown attribute {name!r}")
        attrs[name] = match.group("value")
        remainder = remainder.replace(match.group(0), "", 1)
    if remainder.strip():
        raise TableDirectiveError(f"table-style '{key}': unrecognised directive text {remainder.strip()!r}")
    return attrs


def _derive_context(key: str, attrs: dict[str, str], header: list[str], rows: list[list[str]]) -> TableContext:
    if "purpose" not in attrs:
        raise TableDirectiveError(f"table-style '{key}': missing required attribute 'purpose'")

    for name, value in attrs.items():
        enum = _ATTR_ENUMS[name]
        if enum is not None and value not in enum:
            raise TableDirectiveError(
                f"table-style '{key}': {name}={value!r} is not one of {enum}"
            )

    columns = len(header)
    row_count = len(rows)
    all_cells = [cell for row in ([header] + rows) for cell in row]
    length = "long" if row_count > _LENGTH_ROW_THRESHOLD or any(
        len(cell) > _LENGTH_CELL_CHAR_THRESHOLD for cell in all_cells
    ) else "short"
    pagination = "multipage" if row_count > _MULTIPAGE_ROW_THRESHOLD else "single"
    if columns <= _LOW_DENSITY_MAX_COLUMNS:
        density = "low"
    elif columns <= _MEDIUM_DENSITY_MAX_COLUMNS:
        density = "medium"
    else:
        density = "high"

    accessibility_needs = False
    if "accessibility_needs" in attrs:
        raw = attrs["accessibility_needs"].strip().lower()
        if raw not in ("true", "false"):
            raise TableDirectiveError(
                f"table-style '{key}': accessibility_needs={attrs['accessibility_needs']!r} must be true/false"
            )
        accessibility_needs = raw == "true"

    emphasis_column: int | None = None
    if "emphasis_column" in attrs:
        raw = attrs["emphasis_column"]
        if not raw.lstrip("-").isdigit():
            raise TableDirectiveError(f"table-style '{key}': emphasis_column={raw!r} must be an integer")
        emphasis_column = int(raw)
        if not (0 <= emphasis_column < columns):
            raise TableDirectiveError(
                f"table-style '{key}': emphasis_column={emphasis_column} is out of range "
                f"for a {columns}-column table (valid range 0..{columns - 1})"
            )

    return TableContext(
        purpose=attrs["purpose"],
        length=length,
        density=density,
        columns=columns,
        rows=row_count,
        pagination=pagination,
        emphasis=attrs.get("emphasis", "none"),
        meaning=attrs.get("meaning", "none"),
        color_policy=attrs.get("color_policy", "color"),
        accessibility_needs=accessibility_needs,
        emphasis_column=emphasis_column,
    )


def context_for_table(
    lines: list[str], table_start_index: int, header: list[str], rows: list[list[str]],
) -> tuple[str | None, TableContext | None]:
    """Find the directive immediately preceding ``lines[table_start_index]``.

    Backward-scans over blank lines only; any other intervening content
    means the table is undirected. Exposed separately from
    ``parse_table_blocks`` so a renderer that already extracts a table's
    raw rows via its own Markdown scan (``build_latex_report.py``'s
    ``markdown_to_latex``, for instance) does not need to re-implement
    table detection just to look up its directive.
    """
    idx = table_start_index - 1
    while idx >= 0 and not lines[idx].strip():
        idx -= 1
    if idx < 0:
        return None, None
    match = DIRECTIVE_RE.match(lines[idx].strip())
    if not match:
        return None, None
    key = match.group("key")
    attrs = _parse_attrs(key, match.group("attrs"))
    context = _derive_context(key, attrs, header, rows)
    return key, context


def parse_table_blocks(markdown: str) -> list[TableBlock]:
    """Find every Markdown table in ``markdown``, directed or not.

    Raises ``TableDirectiveError`` immediately for a malformed *present*
    directive. An absent directive is not an error -- the returned block
    simply carries ``table_key=None, context=None``.
    """
    lines = markdown.splitlines()
    blocks: list[TableBlock] = []

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        if not stripped:
            i += 1
            continue

        if DIRECTIVE_RE.match(stripped):
            # Attached to its table (if any) below, via context_for_table's
            # own backward scan -- nothing to do at the directive line itself.
            i += 1
            continue

        if "|" in stripped and i + 1 < len(lines) and _is_separator(lines[i + 1]):
            table_start = i
            header = _split_row(stripped)
            header_line = i + 1
            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and "|" in lines[i].strip() and lines[i].strip():
                rows.append(_split_row(lines[i]))
                i += 1

            key, context = context_for_table(lines, table_start, header, rows)
            blocks.append(TableBlock(table_key=key, context=context, header=header, rows=rows, line=header_line))
            continue

        i += 1

    return blocks


def strip_status_markers(text: str) -> tuple[str, list[str]]:
    """Remove every `[[status:<value>]]` marker from ``text``.

    Returns the cleaned text and the ordered list of raw marker values
    (not yet validated against the catalog -- callers check membership in
    ``Catalog.status_indicators`` and block on an unknown value).
    """
    markers = [match.group("value") for match in STATUS_MARKER_RE.finditer(text)]
    clean = STATUS_MARKER_RE.sub("", text)
    clean = re.sub(r"\s{2,}", " ", clean).strip()
    return clean, markers
