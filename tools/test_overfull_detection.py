"""Tests for Overfull \\hbox/\\vbox detection in the LaTeX log.

A line that overflows the right margin by more than the page margin runs off
the paper edge and its tail is clipped away — content silently lost. LaTeX
reports it in build/main.log; these tests pin that the validator reads it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from report_config import ReportConfig  # noqa: E402
from validate_report import (  # noqa: E402
    OVERFULL_CLIPPING_PT,
    OVERFULL_NOISE_PT,
    latex_log_validation,
    parse_overfull_boxes,
)

MINIMAL_TEX = (
    "\\usepackage{hyperref}\n"
    "\\Needspace{4\\baselineskip}\n"
    "\\onehalfspacing\n"
    "\\setlength{\\parindent}{0pt}\n"
)


def make_report(folder: Path, log: str) -> ReportConfig:
    build = folder / "build"
    build.mkdir(parents=True, exist_ok=True)
    (build / "main.tex").write_text(MINIMAL_TEX, encoding="utf-8")
    (build / "main.log").write_text(log, encoding="utf-8")
    return ReportConfig(folder=folder, raw={"type": "essay", "pdf": "build/report.pdf"}, academic_format={})


# ---------------------------------------------------------------------------
# parse_overfull_boxes
# ---------------------------------------------------------------------------


def test_parses_amount_and_source_lines():
    log = "Overfull \\hbox (123.87837pt too wide) in paragraph at lines 178--179\n[]\\TU/foo\n"

    boxes = parse_overfull_boxes(log)

    assert len(boxes) == 1
    assert boxes[0].kind == "hbox"
    assert boxes[0].points == pytest.approx(123.87837)
    assert boxes[0].start_line == 178
    assert boxes[0].end_line == 179


def test_parses_a_single_line_location():
    log = "Overfull \\hbox (12.5pt too wide) detected at line 42\n"

    boxes = parse_overfull_boxes(log)

    assert boxes[0].start_line == 42
    assert boxes[0].end_line == 42


def test_parses_vbox_overflow():
    log = "Overfull \\vbox (18.0pt too high) has occurred while \\output is active\n"

    boxes = parse_overfull_boxes(log)

    assert len(boxes) == 1
    assert boxes[0].kind == "vbox"
    assert boxes[0].points == pytest.approx(18.0)
    assert boxes[0].start_line is None


def test_parses_a_message_hard_wrapped_mid_sentence():
    """LaTeX wraps log lines at max_print_line; the message survives the split."""
    log = (
        "Overfull \\hbox (123.87837pt too wide) in paragraph at lines 178--\n"
        "179\n"
        "[]\\TU/TeXGyreTermes(0)/m/n/12 texto\n"
    )

    boxes = parse_overfull_boxes(log)

    assert len(boxes) == 1
    assert boxes[0].points == pytest.approx(123.87837)
    assert boxes[0].start_line == 178
    assert boxes[0].end_line == 179


def test_parses_a_message_wrapped_after_a_long_location_clause():
    log = (
        "Overfull \\hbox (9.66satisfied) \n"
        "Overfull \\hbox (123.87837pt too wide) in alignment at lines 1780--17\n"
        "99\n"
    )

    boxes = parse_overfull_boxes(log)

    assert [(box.start_line, box.end_line) for box in boxes] == [(1780, 1799)]


def test_infers_the_page_from_shipout_markers():
    log = (
        " [1\n"
        "]\n"
        " [2<../assets/fig.png>]\n"
        "Overfull \\hbox (123.87837pt too wide) in paragraph at lines 178--179\n"
        "[3]\n"
        "Overfull \\hbox (7.8595pt too wide) in paragraph at lines 200--201\n"
        "[4] (./main.aux)\n"
    )

    boxes = parse_overfull_boxes(log)

    assert [box.page for box in boxes] == [3, 4]


def test_page_is_unknown_when_the_log_has_no_shipout_markers():
    log = "Overfull \\hbox (123.87837pt too wide) in paragraph at lines 178--179\n"

    assert parse_overfull_boxes(log)[0].page is None


def test_truncated_log_never_crashes():
    log = "Overfull \\hbox (123.878"

    assert parse_overfull_boxes(log) == []


def test_empty_log_yields_nothing():
    assert parse_overfull_boxes("") == []


def test_package_version_brackets_are_not_read_as_pages():
    log = (
        "Package foo Info: loaded [2026/01/01 v1.2 something]\n"
        " [1]\n"
        "Overfull \\hbox (100.0pt too wide) in paragraph at lines 5--6\n"
    )

    assert parse_overfull_boxes(log)[0].page == 2


# ---------------------------------------------------------------------------
# latex_log_validation severity
# ---------------------------------------------------------------------------


def test_overflow_past_the_margin_is_an_error_naming_amount_and_location(tmp_path):
    config = make_report(
        tmp_path,
        " [1]\n [2]\nOverfull \\hbox (123.87837pt too wide) in paragraph at lines 178--179\n",
    )

    result = latex_log_validation(config)

    assert result.errors, "A clipping overflow must be an error"
    message = "\n".join(result.errors)
    assert "123.88" in message
    assert "178" in message and "179" in message
    assert "página 3" in message


def test_visible_but_contained_overflow_is_a_warning(tmp_path):
    config = make_report(
        tmp_path,
        "Overfull \\hbox (23.93896pt too wide) in paragraph at lines 159--159\n",
    )

    result = latex_log_validation(config)

    assert not [e for e in result.errors if "Overfull" in e or "hbox" in e]
    assert any("23.94" in w for w in result.warnings)


def test_sub_point_overflow_is_ignored_as_noise(tmp_path):
    config = make_report(
        tmp_path,
        "Overfull \\hbox (0.31883pt too wide) in paragraph at lines 12--13\n",
    )

    result = latex_log_validation(config)

    assert not any("0.31" in message for message in result.errors + result.warnings)


def test_thresholds_are_ordered():
    assert 0 < OVERFULL_NOISE_PT < OVERFULL_CLIPPING_PT


def test_missing_log_still_only_warns(tmp_path):
    build = tmp_path / "build"
    build.mkdir(parents=True)
    (build / "main.tex").write_text(MINIMAL_TEX, encoding="utf-8")
    config = ReportConfig(folder=tmp_path, raw={"type": "essay"}, academic_format={})

    result = latex_log_validation(config)

    assert result.errors == []
    assert any("log" in w.lower() for w in result.warnings)


def test_many_overfull_boxes_are_reported_but_bounded(tmp_path):
    log = "".join(
        f"Overfull \\hbox (5.{index}pt too wide) in paragraph at lines {index}--{index}\n"
        for index in range(1, 40)
    )
    config = make_report(tmp_path, log)

    result = latex_log_validation(config)

    assert len(result.warnings) <= 12, "Log noise must stay bounded"
    assert any("39" in w for w in result.warnings), "The total count must still be visible"
