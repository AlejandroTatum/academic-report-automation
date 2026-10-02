"""``min_sources: 0`` lets a non-academic document ship without a bibliography."""
from __future__ import annotations

from pathlib import Path

import pytest

import build_latex_report
import content_check
import doc_status
import source_count
from conftest import _body, _report, _rubric
from report_config import ReportConfig, load_report_config


def _config(folder: Path, route: str | None, **extra: object) -> ReportConfig:
    raw: dict[str, object] = {"min_sources": 0, **extra}
    if route is not None:
        raw["route"] = route
    return ReportConfig(folder=folder, raw=raw)


def _business_folder(folder: Path) -> Path:
    _report(folder, route="business")
    with (folder / "report.yml").open("a", encoding="utf-8") as handle:
        handle.write("min_sources: 0\n")
    _rubric(folder)
    _body(folder, "# Contrato\n\nTexto sin citas.\n")
    return folder


@pytest.mark.parametrize("route", ["business", "project", "technical", "other"])
def test_zero_minimum_is_accepted_outside_academic(tmp_path: Path, route: str) -> None:
    assert _config(tmp_path, route).min_sources == 0
    assert source_count.effective_min_sources(_config(tmp_path, route)) == 0


@pytest.mark.parametrize("route", ["academic", "a", None])
def test_zero_minimum_is_rejected_on_academic_with_a_clear_error(tmp_path: Path, route: str | None) -> None:
    with pytest.raises(ValueError, match=r"min_sources.*academic"):
        _config(tmp_path, route).min_sources


def test_load_report_config_rejects_zero_on_academic(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder, route="academic")
    with (folder / "report.yml").open("a", encoding="utf-8") as handle:
        handle.write("min_sources: 0\n")
    with pytest.raises(SystemExit, match="academic"):
        load_report_config(folder)


def test_non_academic_still_rejects_negative_values(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="min_sources"):
        ReportConfig(folder=tmp_path, raw={"route": "business", "min_sources": -1}).min_sources


def test_source_gate_is_ok_without_a_bib(tmp_path: Path) -> None:
    result = source_count.source_gate(tmp_path, _config(tmp_path, "business"))
    assert result.ok and result.count == 0


def test_research_phase_is_done_without_sources_bib(tmp_path: Path) -> None:
    folder = _business_folder(tmp_path / "wf")
    config = load_report_config(folder)

    phase = doc_status._phase_research(folder, config, None)

    assert phase.state == doc_status.DONE


def test_research_guidance_does_not_ask_for_sources(tmp_path: Path) -> None:
    folder = _business_folder(tmp_path / "wf")

    text = doc_status._guidance("research", folder, load_report_config(folder))

    assert "at least 0" not in text and "sources.bib" not in text


def test_body_check_passes_with_no_citations_and_no_bib(tmp_path: Path) -> None:
    folder = _business_folder(tmp_path / "wf")

    results = {c["check"]: c for c in content_check.body_check_results(folder)}

    assert results["eligible_sources_cited"]["ok"] is True
    assert results["citations_resolve"]["ok"] is True
    assert content_check.main([str(folder), "--body-check"]) == 0


def test_build_emits_no_bibliography_section_without_bib(tmp_path: Path) -> None:
    folder = _business_folder(tmp_path / "wf")

    tex = build_latex_report.render_tex(ReportConfig.load(folder))

    assert r"\printbibliography" not in tex
