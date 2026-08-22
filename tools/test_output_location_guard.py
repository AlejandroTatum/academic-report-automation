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


def test_underscore_prefix_no_longer_buys_an_exemption(tmp_path):
    """The layout rule applies to scratch folders too.

    The exemption used to exist for `_example_latex_essay`, which is not
    versioned in this repository at all — and does not even need it: it writes
    its final PDF to `build/`. The example this repository DOES ship satisfies
    the rule outright, so nothing is left to exempt.
    """
    folder = write_report(
        tmp_path / "reports" / "_borrador_interno",
        "type: essay\noutput: pdf\npdf: outputs/borrador.pdf\n",
    )

    with pytest.raises(SystemExit) as excinfo:
        load_report_config(folder)

    assert LOCAL_OUTPUTS_ERROR in str(excinfo.value)


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


def test_post_build_check_flags_underscore_folders_too(tmp_path):
    folder = tmp_path / "reports" / "_borrador_interno"
    (folder / "outputs").mkdir(parents=True)
    pdf = folder / "outputs" / "borrador.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    config = ReportConfig(
        folder=folder,
        raw={
            "type": "essay",
            "pdf": "outputs/borrador.pdf",
            "metadata": {"title": "T", "subject": "S", "teacher": "D", "student": "E", "date": "F"},
        },
        academic_format={},
    )

    result = common_validation(config)

    assert any(LOCAL_OUTPUTS_ERROR in error for error in result.errors)


# ---------------------------------------------------------------------------
# One rule, one predicate: the two checks may never disagree
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("folder_name", ["informe", "_borrador_interno"])
@pytest.mark.parametrize(
    ("declared_pdf", "forbidden"),
    [("outputs/x.pdf", True), ("build/x.pdf", False), ("../../outputs/so/x.pdf", False)],
)
def test_load_guard_and_post_build_check_answer_the_same_question(
    tmp_path, folder_name, declared_pdf, forbidden
):
    """Both call sites read `targets_local_outputs`, so their verdicts match.

    They used to be spelled out separately, and the post-build check carried its
    own copy of the underscore condition — two places to keep in step, and the
    kind of drift where a report loads fine and then fails after three LuaLaTeX
    passes.
    """
    folder = tmp_path / "reports" / folder_name
    pdf = folder / declared_pdf
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF-1.4\n")
    config = ReportConfig(
        folder=folder,
        raw={
            "type": "essay",
            "pdf": declared_pdf,
            "metadata": {"title": "T", "subject": "S", "teacher": "D", "student": "E", "date": "F"},
        },
        academic_format={},
    )

    post_build_flags_it = any(
        LOCAL_OUTPUTS_ERROR in error for error in common_validation(config).errors
    )

    assert targets_local_outputs(config) is forbidden
    assert post_build_flags_it is forbidden


# ---------------------------------------------------------------------------
# The prefix keeps its OTHER meaning: scratch work is not published globally
# ---------------------------------------------------------------------------


def test_underscore_prefix_still_means_do_not_publish_a_global_copy(tmp_path):
    folder = write_report(
        tmp_path / "reports" / "_borrador_interno",
        "type: essay\noutput: pdf\npdf: ../../outputs/so/borrador.pdf\n",
    )

    assert load_report_config(folder).publish_global is False


def test_an_ordinary_folder_still_publishes_a_global_copy_by_default(tmp_path):
    folder = write_report(
        tmp_path / "reports" / "informe",
        "type: essay\noutput: pdf\npdf: ../../outputs/so/informe.pdf\n",
    )

    assert load_report_config(folder).publish_global is True


def test_publish_global_written_down_overrides_the_prefix_guess(tmp_path):
    scratch = write_report(
        tmp_path / "reports" / "_borrador_interno",
        "type: essay\noutput: pdf\npublish_global: true\n",
    )
    ordinary = write_report(
        tmp_path / "reports" / "informe",
        "type: essay\noutput: pdf\npublish_global: false\n",
    )

    assert load_report_config(scratch).publish_global is True
    assert load_report_config(ordinary).publish_global is False


@pytest.mark.parametrize("value", ["true", "false", 1, 0, None])
def test_publish_global_rejects_non_boolean_values(tmp_path, value):
    config = ReportConfig(folder=tmp_path, raw={"publish_global": value}, academic_format={})

    with pytest.raises(ValueError, match="publish_global"):
        _ = config.publish_global


@pytest.mark.parametrize(
    ("output", "validators", "message"),
    [
        ("pdf", {"common": False}, "common"),
        ("pdf", {"pdf_layout": False}, "pdf_layout"),
        ("pdf", {"common": "false"}, "common"),
        ("tex", {"common": False}, "common"),
    ],
)
def test_mandatory_validators_cannot_be_disabled_or_mistyped(tmp_path, output, validators, message):
    config = ReportConfig(
        folder=tmp_path,
        raw={"output": output, "validators": validators},
        academic_format={},
    )

    with pytest.raises(ValueError, match=message):
        _ = config.validators


def test_tex_output_can_skip_pdf_layout_only(tmp_path):
    config = ReportConfig(
        folder=tmp_path,
        raw={"output": "tex", "validators": {"pdf_layout": False}},
        academic_format={},
    )

    assert config.validators["common"] is True
    assert config.validators["pdf_layout"] is False
