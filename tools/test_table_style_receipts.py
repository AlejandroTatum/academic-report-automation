"""Persist SelectionReceipt evidence into validation output (issue #13).

Closes the acceptance gap T1-T5 left open: `SelectionReceipt` (table_model.py)
was computed correctly by every backend but discarded after rendering, never
written anywhere `validate_report.py` (or a human) could read (see
odd/tasks/contextual-table-styles.md, "What remains"). Objective: "The
selected ID and rationale appear in validation evidence."

Re-resolves the exact same style each backend selected, read-only, straight
from `body.md` -- no wiring into build_latex_report.py/build_docx_report.py
is needed, since `resolve_table_style` is pure and reproducible from the
same TableStylesContext/TableContext either backend built.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from report_config import load_report_config  # noqa: E402
from validate_report import (  # noqa: E402
    ReportValidation,
    table_style_receipts_validation,
    write_quality_report,
    write_table_style_receipts,
)

DIRECTED_BODY = """\
# Resultados

<!-- table-style: results-summary purpose=reference -->
| Nombre | Puntaje |
| ------ | ------- |
| Ana    | 9       |
"""


def _write_report(folder: Path, body: str, extra: str = "") -> Path:
    folder.mkdir(parents=True)
    (folder / "report.yml").write_text(
        "type: essay\noutput: pdf\nmetadata:\n  title: Informe\n"
        "table_styles:\n  enabled: true\n" + extra,
        encoding="utf-8",
    )
    (folder / "body.md").write_text(body, encoding="utf-8")
    return folder


def test_receipts_validation_resolves_a_receipt_per_directed_table(tmp_path: Path) -> None:
    config = load_report_config(_write_report(tmp_path / "report", DIRECTED_BODY))
    receipts, result = table_style_receipts_validation(config)
    assert not result.errors
    assert len(receipts) == 1
    assert receipts[0].table_key == "results-summary"
    assert receipts[0].style_id == "TAB-CL-01"
    assert receipts[0].rationale.strip()


def test_receipts_validation_is_a_noop_when_table_styles_disabled(tmp_path: Path) -> None:
    folder = tmp_path / "report"
    folder.mkdir()
    (folder / "report.yml").write_text(
        "type: essay\noutput: pdf\nmetadata:\n  title: Informe\n", encoding="utf-8",
    )
    (folder / "body.md").write_text(DIRECTED_BODY, encoding="utf-8")
    config = load_report_config(folder)
    receipts, result = table_style_receipts_validation(config)
    assert receipts == []
    assert not result.errors


def test_receipts_validation_reports_an_invalid_override_as_an_error(tmp_path: Path) -> None:
    config = load_report_config(
        _write_report(
            tmp_path / "report", DIRECTED_BODY,
            # TAB-CC-07 requires density: high; this table is low-density --
            # context-incompatible.
            extra="  overrides:\n    results-summary: TAB-CC-07\n",
        )
    )
    receipts, result = table_style_receipts_validation(config)
    assert receipts == []
    assert any("results-summary" in error for error in result.errors)


def test_receipts_are_persisted_as_path_free_json_evidence(tmp_path: Path) -> None:
    config = load_report_config(_write_report(tmp_path / "report", DIRECTED_BODY))
    receipts, _ = table_style_receipts_validation(config)
    write_table_style_receipts(config, receipts)

    receipts_path = config.table_style_receipts_path
    assert receipts_path.exists()
    raw_text = receipts_path.read_text(encoding="utf-8")
    payload = json.loads(raw_text)
    assert payload["tables"][0]["table_key"] == "results-summary"
    assert payload["tables"][0]["style_id"] == "TAB-CL-01"
    assert payload["tables"][0]["rationale"].strip()
    assert str(tmp_path) not in raw_text
    assert "/home/" not in raw_text


def test_receipts_are_byte_stable_across_identical_runs(tmp_path: Path) -> None:
    config = load_report_config(_write_report(tmp_path / "report", DIRECTED_BODY))
    receipts, _ = table_style_receipts_validation(config)
    write_table_style_receipts(config, receipts)
    first = config.table_style_receipts_path.read_text(encoding="utf-8")
    write_table_style_receipts(config, receipts)
    second = config.table_style_receipts_path.read_text(encoding="utf-8")
    assert first == second


def test_receipt_summary_appears_in_quality_report(tmp_path: Path) -> None:
    config = load_report_config(_write_report(tmp_path / "report", DIRECTED_BODY))
    receipts, result = table_style_receipts_validation(config)
    validation = ReportValidation()
    validation.add("table_style_receipts", result)
    validation.table_style_receipts = receipts
    write_quality_report(config, validation)
    text = config.quality_report_path.read_text(encoding="utf-8")
    assert "TAB-CL-01" in text
    assert "results-summary" in text
