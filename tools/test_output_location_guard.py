"""Tests for the early guard against finals written to reports/<work>/outputs/.

The builder used to compile three LuaLaTeX passes, copy the PDF and announce
success — only for the validator to reject the very file it had just produced.
The layout rule is knowable from report.yml alone, so it is checked when the
configuration loads, before any compilation. The post-build check stays as
defence in depth.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from report_config import (  # noqa: E402
    LOCAL_OUTPUTS_ERROR,
    ReportConfig,
    load_report_config,
    targets_local_outputs,
)
from validate_report import common_validation  # noqa: E402

ACADEMIC_META = (
    "metadata:\n"
    "  title: T\n"
    "  subject: S\n"
    "  teacher: D\n"
    "  student: E\n"
    "  date: F\n"
)


def write_report(folder: Path, body: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "report.yml").write_text(body + ACADEMIC_META, encoding="utf-8")
    (folder / "body.md").write_text("# Titulo\n\nTexto.\n", encoding="utf-8")
    return folder


# ---------------------------------------------------------------------------
# Fail fast at configuration load time
# ---------------------------------------------------------------------------


def test_explicit_local_outputs_pdf_fails_before_any_compilation(tmp_path):
    folder = write_report(
        tmp_path / "reports" / "c1_academic_unl",
        "type: essay\noutput: pdf\npdf: outputs/c1_academic_unl.pdf\n",
    )

    with pytest.raises(SystemExit) as excinfo:
        load_report_config(folder)

    message = str(excinfo.value)
    assert LOCAL_OUTPUTS_ERROR in message
    assert "c1_academic_unl.pdf" in message


def test_underscore_prefixed_example_keeps_its_exemption(tmp_path):
    folder = write_report(
        tmp_path / "reports" / "_example_latex_essay",
        "type: essay\noutput: pdf\npdf: outputs/example.pdf\n",
    )

    config = load_report_config(folder)

    assert config.pdf_path == folder.resolve() / "outputs" / "example.pdf"


def test_global_outputs_path_loads_without_complaint(tmp_path):
    folder = write_report(
        tmp_path / "reports" / "informe",
        "type: essay\noutput: pdf\npdf: ../../outputs/sistemas-operativos/informe.pdf\n",
    )

    config = load_report_config(folder)

    assert config.pdf_path.name == "informe.pdf"


def test_default_pdf_path_still_loads(tmp_path):
    """No declared final path: nothing for the user to fix yet, so no fail-fast."""
    folder = write_report(tmp_path / "reports" / "informe", "type: essay\noutput: pdf\n")

    config = load_report_config(folder)

    assert config.pdf_path == folder.resolve() / "outputs" / "report.pdf"


def test_docx_output_is_not_caught_by_the_pdf_rule(tmp_path):
    folder = write_report(
        tmp_path / "reports" / "informe",
        "type: docx\noutput: docx\npdf: outputs/informe.pdf\n",
    )

    assert load_report_config(folder).output_format == "docx"


def test_targets_local_outputs_is_explicit_about_the_rule(tmp_path):
    folder = tmp_path / "reports" / "informe"
    folder.mkdir(parents=True)
    inside = ReportConfig(folder=folder, raw={"pdf": "outputs/x.pdf"}, academic_format={})
    outside = ReportConfig(folder=folder, raw={"pdf": "build/x.pdf"}, academic_format={})

    assert targets_local_outputs(inside)
    assert not targets_local_outputs(outside)


# ---------------------------------------------------------------------------
# Defence in depth: the post-build check is still there
# ---------------------------------------------------------------------------


def test_post_build_check_still_reports_the_same_guidance(tmp_path):
    folder = tmp_path / "reports" / "informe"
    (folder / "outputs").mkdir(parents=True)
    pdf = folder / "outputs" / "informe.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    config = ReportConfig(
        folder=folder,
        raw={
            "type": "essay",
            "pdf": "outputs/informe.pdf",
            "metadata": {"title": "T", "subject": "S", "teacher": "D", "student": "E", "date": "F"},
        },
        academic_format={},
    )

    result = common_validation(config)

    assert any(LOCAL_OUTPUTS_ERROR in error for error in result.errors)


def test_post_build_check_keeps_the_underscore_exemption(tmp_path):
    folder = tmp_path / "reports" / "_example_latex_essay"
    (folder / "outputs").mkdir(parents=True)
    pdf = folder / "outputs" / "example.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    config = ReportConfig(
        folder=folder,
        raw={
            "type": "essay",
            "pdf": "outputs/example.pdf",
            "metadata": {"title": "T", "subject": "S", "teacher": "D", "student": "E", "date": "F"},
        },
        academic_format={},
    )

    result = common_validation(config)

    assert not any(LOCAL_OUTPUTS_ERROR in error for error in result.errors)
