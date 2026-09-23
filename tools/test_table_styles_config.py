"""Tests for ReportConfig's contextual table style configuration (issue #13).

Covers the report.yml/academic_format.yml properties T2 added
(`table_style_overrides`, `institution_table_style`) without a dedicated
test at the time, plus the T3 opt-in switch (`table_styles_enabled`) that
keeps every existing report's rendering unchanged by default.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from report_config import ReportConfig, load_report_config  # noqa: E402


def _write_report(folder: Path, extra: str = "") -> Path:
    folder.mkdir(parents=True)
    (folder / "report.yml").write_text(
        "type: essay\noutput: pdf\nmetadata:\n  title: Informe\n" + extra,
        encoding="utf-8",
    )
    return folder


def test_table_styles_enabled_defaults_to_false(tmp_path: Path) -> None:
    config = load_report_config(_write_report(tmp_path / "report"))
    assert config.table_styles_enabled is False


def test_table_styles_enabled_reads_explicit_opt_in(tmp_path: Path) -> None:
    config = load_report_config(
        _write_report(tmp_path / "report", "table_styles:\n  enabled: true\n")
    )
    assert config.table_styles_enabled is True


def test_table_styles_enabled_rejects_a_non_boolean_value(tmp_path: Path) -> None:
    """T1+T2 review: untested config accessor -- a coerced/truthy string
    (`strict_bool`'s own contract) must block loudly, not be silently
    interpreted as True/False."""
    config = load_report_config(
        _write_report(tmp_path / "report", 'table_styles:\n  enabled: "yes"\n')
    )
    with pytest.raises(ValueError, match="table_styles.enabled"):
        config.table_styles_enabled


def test_table_style_overrides_ignores_a_malformed_non_mapping_value(tmp_path: Path) -> None:
    """T1+T2 review: untested config accessor. Documents the current,
    deliberately permissive behavior: a malformed ``overrides:`` (not a
    mapping) is treated as absent rather than raised, matching every other
    ``dig``-backed default in this module."""
    config = load_report_config(
        _write_report(
            tmp_path / "report",
            "table_styles:\n  enabled: true\n  overrides:\n    - not-a-mapping\n",
        )
    )
    assert config.table_style_overrides == {}


def test_table_style_overrides_reads_per_table_teacher_map(tmp_path: Path) -> None:
    config = load_report_config(
        _write_report(
            tmp_path / "report",
            "table_styles:\n  enabled: true\n  overrides:\n    results-summary: TAB-MN-03\n",
        )
    )
    assert config.table_style_overrides == {"results-summary": "TAB-MN-03"}


def test_table_style_overrides_defaults_to_empty_mapping(tmp_path: Path) -> None:
    config = load_report_config(_write_report(tmp_path / "report"))
    assert config.table_style_overrides == {}


def test_institution_table_style_defaults_to_none() -> None:
    config = ReportConfig(folder=Path("."), raw={}, academic_format={})
    assert config.institution_table_style is None


def test_institution_table_style_reads_academic_format_default() -> None:
    config = ReportConfig(
        folder=Path("."), raw={}, academic_format={"tables": {"institution_override": "TAB-TC-02"}},
    )
    assert config.institution_table_style == "TAB-TC-02"


def test_institution_table_style_is_not_overridable_per_report() -> None:
    # `tables` is deliberately absent from OVERRIDABLE_SECTIONS: a report.yml
    # `tables:` block must not silently change the institutional default.
    config = ReportConfig(
        folder=Path("."),
        raw={"tables": {"institution_override": "TAB-CE-05"}},
        academic_format={"tables": {"institution_override": "TAB-TC-02"}},
    )
    assert config.institution_table_style == "TAB-TC-02"
