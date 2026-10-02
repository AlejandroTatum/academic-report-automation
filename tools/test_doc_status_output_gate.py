"""``output:`` gate, effective source minimum and unfinished intake (task 9.2)."""
from __future__ import annotations

from pathlib import Path

import doc_status
from conftest import (
    _approval,
    _body,
    _choose_format,
    _config,
    _final_review,
    _pdf,
    _published,
    _report,
    _rubric,
    _sources_bib,
    _validation,
)

SLUG = "informe-de-laboratorio"


def _format_phase(folder: Path, root: Path | None = None) -> doc_status.PhaseState:
    return doc_status._phase_format(folder, _config(folder), root)


def _legacy_folder(folder: Path) -> Path:
    """Format chosen, no ``output:`` recorded (reports from before task 9.1)."""
    _report(folder)
    _choose_format(folder, "aa", output=None)
    return folder


def test_new_run_without_output_still_asks_for_it(tmp_path: Path) -> None:
    phase = _format_phase(_legacy_folder(tmp_path / "wf"))

    assert phase.state == doc_status.PENDING and phase.detail.endswith("output")


def test_generated_pdf_alone_does_not_waive_the_output_answer(tmp_path: Path) -> None:
    folder = _legacy_folder(tmp_path / "wf")
    _pdf(folder)

    assert _format_phase(folder).state == doc_status.PENDING


def test_legacy_validated_pdf_without_output_is_not_pulled_back_to_format(tmp_path: Path) -> None:
    folder = _legacy_folder(tmp_path / "wf")
    pdf = _pdf(folder)
    _validation(folder, pdf=pdf)

    phase = _format_phase(folder)

    assert phase.state == doc_status.DONE and "pdf" in phase.detail.lower()


def test_legacy_delivered_pdf_without_output_is_not_pulled_back_to_format(tmp_path: Path) -> None:
    folder = _legacy_folder(tmp_path / "wf")
    pdf = _pdf(folder)
    root = tmp_path / "Documents"
    _published(root, category="Academicos/fisica", slug=SLUG, source=pdf)

    assert _format_phase(folder, root).state == doc_status.DONE


def test_explicit_output_wins_over_the_legacy_rule(tmp_path: Path) -> None:
    folder = _legacy_folder(tmp_path / "wf")
    pdf = _pdf(folder)
    _validation(folder, pdf=pdf)
    (folder / "report.yml").write_text(
        (folder / "report.yml").read_text(encoding="utf-8") + "output: docx\n", encoding="utf-8"
    )

    assert _format_phase(folder).state == doc_status.DONE


def test_invalid_output_value_is_blocked_and_named(tmp_path: Path) -> None:
    folder = _legacy_folder(tmp_path / "wf")
    (folder / "report.yml").write_text(
        (folder / "report.yml").read_text(encoding="utf-8") + "output: odt\n", encoding="utf-8"
    )

    phase = _format_phase(folder)

    assert phase.state == doc_status.BLOCKED
    assert "odt" in phase.detail and phase.blocked_reason == "unknown_output"


def test_valid_output_values_stay_done(tmp_path: Path) -> None:
    for value in ("pdf", "DOCX"):
        folder = tmp_path / value
        _report(folder)
        _choose_format(folder, "aa", output=value)
        assert _format_phase(folder).state == doc_status.DONE


def test_research_guidance_states_the_effective_minimum(tmp_path: Path) -> None:
    default = tmp_path / "default"
    _report(default)
    custom = tmp_path / "custom"
    _report(custom)
    (custom / "report.yml").write_text(
        (custom / "report.yml").read_text(encoding="utf-8") + "min_sources: 2\n", encoding="utf-8"
    )

    assert "at least 5 " in doc_status._guidance("research", default)
    assert "at least 2 " in doc_status._guidance("research", custom)
    assert "at least 5" not in doc_status._guidance("research", custom)


def test_research_gate_message_prints_the_effective_number(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder)
    (folder / "report.yml").write_text(
        (folder / "report.yml").read_text(encoding="utf-8") + "min_sources: 2\n", encoding="utf-8"
    )
    _sources_bib(folder, count=1)

    phase = doc_status._phase_research(folder, _config(folder), None)

    assert phase.state == doc_status.PENDING and "1/2" in phase.detail


def test_folder_without_report_yml_is_an_unfinished_intake(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _sources_bib(folder)
    _rubric(folder)
    _body(folder)

    status = doc_status.derive(folder)

    assert status.next_token == "intake"
    assert next(p for p in status.phases if p.name == "intake").detail == "report.yml missing"


def _finished_folder(tmp_path: Path) -> tuple[Path, Path, Path]:
    folder = tmp_path / "wf"
    _report(folder)
    pdf = _pdf(folder)
    root = tmp_path / "Documents"
    return folder, pdf, root


def test_delivered_needs_a_current_final_review_and_a_published_version(tmp_path: Path) -> None:
    folder, pdf, root = _finished_folder(tmp_path)
    config = _config(folder)
    _published(root, category="Academicos/fisica", slug=SLUG, source=pdf)

    # A published version without a current final-review.yml is not delivered.
    assert doc_status._phase_review(folder, config, root).state == doc_status.PENDING
    assert doc_status._phase_deliver(folder, config, root).state == doc_status.DONE

    # A current final-review.yml without a published version is not delivered either.
    other = tmp_path / "other"
    _report(other)
    _pdf(other)
    _final_review(other, pdf=other / "final" / "report.pdf")
    assert doc_status._phase_review(other, _config(other), root).state == doc_status.DONE
    assert doc_status._phase_deliver(other, _config(other), tmp_path / "empty").state == doc_status.PENDING

    # Both conditions together.
    _final_review(folder, pdf=pdf)
    assert doc_status._phase_review(folder, config, root).state == doc_status.DONE
