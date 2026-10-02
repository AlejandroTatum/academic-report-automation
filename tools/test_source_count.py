"""Unit tests for ``tools/source_count.py`` (new-report-flow T2).

The research phase gate: every document needs at least ``MIN_ACADEMIC_SOURCES``
eligible book-or-paper BibTeX entries in its own ``.bib`` file. These tests pin
the eligibility vocabulary, the parser's tolerance for ``@comment``/``@string``/
``@preamble`` and entry-type case, and the folder-level predicate (missing or
unreadable file, exactly 4 vs 5 entries, ``bibliography:``/``bib:`` overrides).
"""
from __future__ import annotations

from pathlib import Path

import pytest

import source_count
from report_config import ReportConfig


def _config(folder: Path, raw: dict[str, object] | None = None) -> ReportConfig:
    return ReportConfig(folder=folder, raw=raw or {})


def test_min_academic_sources_is_five() -> None:
    assert source_count.MIN_ACADEMIC_SOURCES == 5


def test_eligible_entry_types_exclude_web_only_types() -> None:
    assert "book" in source_count.ELIGIBLE_ENTRY_TYPES
    assert "article" in source_count.ELIGIBLE_ENTRY_TYPES
    assert "misc" not in source_count.ELIGIBLE_ENTRY_TYPES
    assert "online" not in source_count.ELIGIBLE_ENTRY_TYPES


def test_eligible_entry_keys_filter_types_case_and_bibtex_directives() -> None:
    """Eligible types match case-insensitively; @misc/@online and the
    @comment/@string/@preamble directives never count."""
    text = "\n".join(
        [
            "@book{knuth1984, author={Knuth}, title={TeX}, year={1984}}",
            "@ARTICLE{ieee2020, author={IEEE}, title={Std}, year={2020}}",
            "@InProceedings{conf2021, author={Doe}, title={Paper}, year={2021}}",
            "@misc{web1, howpublished={url}}",
            "@online{web2, url={https://example.com}}",
            "@comment{notes about sources, not entries}",
            "@string{venue = {Some Venue}}",
            "@preamble{\\newcommand{\\x}{y}}",
        ]
    )

    keys = source_count.eligible_entry_keys(text)

    assert keys == ("knuth1984", "ieee2020", "conf2021")


def test_eligible_entry_keys_dedupe_a_repeated_key() -> None:
    text = "@book{dup, title={A}}\n@article{dup, title={B}}\n@book{other, title={C}}"

    keys = source_count.eligible_entry_keys(text)

    assert keys == ("dup", "other")


def test_source_gate_missing_file_is_reported(tmp_path: Path) -> None:
    folder = tmp_path / "wf"

    result = source_count.source_gate(folder, _config(folder))

    assert result.count == 0
    assert result.keys == ()
    assert result.ok is False
    assert "sources.bib" in result.reason


def test_source_gate_unreadable_file_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "wf"
    folder.mkdir()
    (folder / "sources.bib").write_text("@book{a, title={A}}\n", encoding="utf-8")
    original = Path.read_text

    def denied(self: Path, *args: object, **kwargs: object) -> str:
        if self.name == "sources.bib":
            raise PermissionError("denied")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", denied)
    result = source_count.source_gate(folder, _config(folder))

    assert result.count == 0
    assert result.ok is False
    assert "unreadable" in result.reason


def test_source_gate_non_utf8_file_is_reported_not_raised(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    folder.mkdir()
    (folder / "sources.bib").write_bytes(
        "@book{a, author={Muñoz}, title={A}}\n".encode("latin-1")
    )
    result = source_count.source_gate(folder, _config(folder))

    assert result.count == 0
    assert result.ok is False
    assert "UTF-8" in result.reason


def test_source_gate_four_eligible_entries_is_short(tmp_path: Path) -> None:
    """TRIANGULATE: 4 eligible entries plus 2 web-only ones still fail the gate."""
    folder = tmp_path / "wf"
    folder.mkdir()
    entries = "\n".join(
        [
            "@book{b1, title={A}}",
            "@article{b2, title={B}}",
            "@inproceedings{b3, title={C}}",
            "@phdthesis{b4, title={D}}",
            "@misc{web1, howpublished={url}}",
            "@online{web2, url={https://example.com}}",
        ]
    )
    (folder / "sources.bib").write_text(entries + "\n", encoding="utf-8")

    result = source_count.source_gate(folder, _config(folder))

    assert result.count == 4
    assert result.keys == ("b1", "b2", "b3", "b4")
    assert result.ok is False
    assert "sources.bib has 4/5 book or paper sources" == result.reason


def test_source_gate_five_eligible_entries_is_ok(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    folder.mkdir()
    entries = "\n".join(
        f"@book{{key{i}, title={{T{i}}}}}" for i in range(1, 6)
    )
    (folder / "sources.bib").write_text(entries + "\n", encoding="utf-8")

    result = source_count.source_gate(folder, _config(folder))

    assert result.count == 5
    assert result.ok is True
    assert result.keys == tuple(f"key{i}" for i in range(1, 6))


def test_source_gate_honors_bibliography_override(tmp_path: Path) -> None:
    """TRIANGULATE: a `bibliography:` override moves both the read and the name."""
    folder = tmp_path / "wf"
    folder.mkdir()
    entries = "\n".join(f"@book{{key{i}, title={{T{i}}}}}" for i in range(1, 6))
    (folder / "refs.bib").write_text(entries + "\n", encoding="utf-8")
    (folder / "sources.bib").write_text("@misc{decoy, howpublished={x}}\n", encoding="utf-8")

    result = source_count.source_gate(folder, _config(folder, {"bibliography": "refs.bib"}))

    assert result.ok is True
    assert "refs.bib" in result.reason

    missing = source_count.source_gate(folder, _config(folder, {"bib": "absent.bib"}))

    assert missing.ok is False
    assert "absent.bib" in missing.reason


def _bib_with(folder: Path, count: int) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "sources.bib").write_text(
        "\n".join(f"@book{{k{i}, title={{T{i}}}}}" for i in range(count)) + "\n",
        encoding="utf-8",
    )


def test_min_sources_override_lowers_the_gate(tmp_path: Path) -> None:
    _bib_with(tmp_path, 1)

    result = source_count.source_gate(tmp_path, _config(tmp_path, {"min_sources": 1}))

    assert result.ok is True
    assert result.reason == "sources.bib has 1/1 book or paper sources"


def test_min_sources_override_can_raise_the_gate(tmp_path: Path) -> None:
    _bib_with(tmp_path, 5)

    result = source_count.source_gate(tmp_path, _config(tmp_path, {"min_sources": 7}))

    assert result.ok is False
    assert result.reason == "sources.bib has 5/7 book or paper sources"


def test_absent_min_sources_keeps_default_five(tmp_path: Path) -> None:
    _bib_with(tmp_path, 4)

    result = source_count.source_gate(tmp_path, _config(tmp_path))

    assert result.ok is False
    assert result.reason == "sources.bib has 4/5 book or paper sources"
    assert source_count.effective_min_sources(_config(tmp_path)) == 5


@pytest.mark.parametrize("bad", [0, -1, "3", 2.5, True, None, [1]])
def test_invalid_min_sources_fails_closed(tmp_path: Path, bad: object) -> None:
    _bib_with(tmp_path, 9)
    config = _config(tmp_path, {"min_sources": bad})

    with pytest.raises(ValueError, match="min_sources"):
        source_count.effective_min_sources(config)
    result = source_count.source_gate(tmp_path, config)
    assert result.ok is False
    assert "min_sources" in result.reason


def test_business_route_defaults_min_sources_to_zero(tmp_path: Path) -> None:
    config = _config(tmp_path, {"route": "business"})

    assert source_count.effective_min_sources(config) == 0
    assert source_count.source_gate(tmp_path, config).ok is True


def test_explicit_min_sources_wins_on_business_route(tmp_path: Path) -> None:
    assert source_count.effective_min_sources(_config(tmp_path, {"route": "business", "min_sources": 3})) == 3


@pytest.mark.parametrize("route", [None, "academic", "technical", "project"])
def test_other_routes_keep_the_academic_default(tmp_path: Path, route: str | None) -> None:
    raw = {} if route is None else {"route": route}

    assert source_count.effective_min_sources(_config(tmp_path, raw)) == 5
