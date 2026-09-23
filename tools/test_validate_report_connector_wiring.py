"""Strict-TDD integration tests for validate_report.py's final-size connector
gate wiring (issue #10, native-review hardening).

``connector_final_size_validation`` itself was only ever exercised through
``connector_pdf_stage.audit_svg_at_final_size`` directly (``tools/
test_connector_pdf_stage.py``); the glue in ``validate_report.py`` --
resolving Markdown figure references to a build-directory SVG, resolving the
active LaTeX template, and turning connector findings into
``ValidationResult`` entries -- had no test of its own, at any commit.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import validate_report  # noqa: E402
from report_config import ReportConfig  # noqa: E402

FIXTURES = TOOLS / "fixtures" / "connector_geometry"
CLEAN_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"></svg>'


def make_config(tmp_path: Path, body: str) -> ReportConfig:
    import yaml

    folder = tmp_path / "r"
    folder.mkdir(parents=True, exist_ok=True)
    raw = {
        "type": "technical_report",
        "backend": "latex",
        "output": "pdf",
        "template": "plain",
        "metadata": {"title": "T", "subject": "S", "teacher": "D", "student": "A"},
        "body": "body.md",
    }
    (folder / "report.yml").write_text(yaml.safe_dump(raw), encoding="utf-8")
    (folder / "body.md").write_text(body, encoding="utf-8")
    (folder / "build").mkdir(parents=True, exist_ok=True)
    return ReportConfig.load(folder)


def test_clean_diagram_is_audited_and_reports_nothing(tmp_path: Path) -> None:
    config = make_config(tmp_path, "![Diagrama.](diagram.svg)\n")
    (config.tex_path.parent / "diagram.svg").write_text(CLEAN_SVG, encoding="utf-8")

    result = validate_report.connector_final_size_validation(config)
    assert result.errors == []
    assert result.warnings == []


def test_final_size_defect_is_reported_through_the_wiring(tmp_path: Path) -> None:
    """A known final-size-only defect (clears the isolated 0.80 SVG-unit
    minimum but not the final print scale) must surface through the exact
    same wiring a real ``validate_report.py`` run uses, not just through a
    direct call to ``connector_pdf_stage``."""
    config = make_config(tmp_path, "![Diagrama.](diagram.svg)\n")
    svg_text = (FIXTURES / "mmdc-final-clearance-bad.svg").read_text(encoding="utf-8")
    (config.tex_path.parent / "diagram.svg").write_text(svg_text, encoding="utf-8")

    result = validate_report.connector_final_size_validation(config)
    assert any("[tamaño final]" in error and "CONNECTOR_CLEARANCE" in error and "diagram.svg" in error for error in result.errors)


def test_unresolved_figure_reference_is_reported_not_silently_skipped(tmp_path: Path) -> None:
    """A figure reference that resolves to no file at all must not let the
    gate pass having audited zero figures in silence."""
    config = make_config(tmp_path, "![Diagrama.](missing.png)\n")

    result = validate_report.connector_final_size_validation(config)
    assert result.errors == []
    assert any("missing.png" in warning for warning in result.warnings)


def test_figure_without_matching_svg_is_reported_not_silently_skipped(tmp_path: Path) -> None:
    """A resolvable figure with no same-stem SVG sibling must still be named,
    not dropped from the audit without a trace."""
    config = make_config(tmp_path, "![Diagrama.](diagram.png)\n")
    (config.tex_path.parent / "diagram.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    result = validate_report.connector_final_size_validation(config)
    assert result.errors == []
    assert any("diagram.svg" in warning or "diagram.png" in warning for warning in result.warnings)


def test_malformed_svg_becomes_a_reported_error_not_a_crash(tmp_path: Path) -> None:
    """A parse error auditing one figure must become a finding, never let an
    uncaught exception abort the whole validation run."""
    config = make_config(tmp_path, "![Diagrama.](diagram.svg)\n")
    (config.tex_path.parent / "diagram.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><g class="node" id="A">',
        encoding="utf-8",
    )

    result = validate_report.connector_final_size_validation(config)
    assert any("diagram.svg" in error for error in result.errors)


def test_indexerror_becomes_a_reported_error_not_a_crash(tmp_path: Path) -> None:
    """Same guard, a different exception class (#43 T2): the previous guard
    caught only (OSError, ValueError, ET.ParseError) and let an IndexError
    from corrupted path/point data escape uncaught -- and it differed from
    visual_builder.py's own guard, which caught a different tuple again."""
    config = make_config(tmp_path, "![Diagrama.](diagram.svg)\n")
    (config.tex_path.parent / "diagram.svg").write_text(
        (FIXTURES / "mmdc-malformed-indexerror.svg").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = validate_report.connector_final_size_validation(config)
    assert any("diagram.svg" in error for error in result.errors)
