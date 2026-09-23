"""Tests for the table-style directive migration checker (issue #13).

Reports, per Markdown file under a directory, which tables carry a valid
directive, which are undirected (candidates for migration), and which
carry a malformed directive (a real error, not just a migration note) --
matching design's "Slice 1 includes a migration tool/check that reports
tables lacking directives; no legacy generic fallback."
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from check_table_contexts import scan_directory  # noqa: E402

DIRECTED = """\
<!-- table-style: results-summary purpose=reference -->
| A | B |
| --- | --- |
| 1 | 2 |
"""

UNDIRECTED = """\
| A | B |
| --- | --- |
| 1 | 2 |
"""

MALFORMED = """\
<!-- table-style: broken -->
| A | B |
| --- | --- |
| 1 | 2 |
"""


def test_scan_directory_reports_directed_and_undirected_tables(tmp_path: Path) -> None:
    (tmp_path / "directed.md").write_text(DIRECTED, encoding="utf-8")
    (tmp_path / "undirected.md").write_text(UNDIRECTED, encoding="utf-8")

    report = scan_directory(tmp_path)

    assert report.directed == [("directed.md", "results-summary")]
    assert report.undirected == [("undirected.md", 1)]
    assert report.errors == []
    assert report.ok is True


def test_scan_directory_reports_malformed_directive_as_error(tmp_path: Path) -> None:
    (tmp_path / "broken.md").write_text(MALFORMED, encoding="utf-8")

    report = scan_directory(tmp_path)

    assert len(report.errors) == 1
    assert "broken.md" in report.errors[0]
    assert "purpose" in report.errors[0]
    assert report.ok is False


def test_scan_directory_is_recursive_and_only_reads_markdown(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.md").write_text(DIRECTED, encoding="utf-8")
    (tmp_path / "ignore.txt").write_text(UNDIRECTED, encoding="utf-8")

    report = scan_directory(tmp_path)

    assert report.directed == [("sub/nested.md", "results-summary")]
