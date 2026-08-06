"""Tests for metadata validation in visual_builder and validate_report.

Covers the unified `section`/`intended_section` and `title` requirements
without rendering images or PDFs. Uses temp file fixtures.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest
import yaml

# Make the tools/ directory importable so sibling modules can be loaded.
# Existing scripts use absolute imports like `from report_config import ...`,
# which work only when tools/ is on sys.path.
TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from report_config import ReportConfig, load_report_config, DEFAULT_FORMAT  # noqa: E402
from validate_report import common_validation, pdf_layout_validation, visual_validation  # noqa: E402
from validate_ieee_refs import ValidationResult  # noqa: E402
from visual_builder import metadata_errors  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers: create minimal fixtures
# ---------------------------------------------------------------------------


def make_figures_yml(folder: Path, figures: list[dict]) -> Path:
    path = folder / "figures.yml"
    path.write_text(yaml.dump({"figures": figures}), encoding="utf-8")
    return path


def touch_svg(folder: Path, name: str) -> Path:
    """Create a minimal valid SVG that passes size checks."""
    path = folder / name
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" '
        'viewBox="0 0 800 600"><rect width="800" height="600" fill="white"/>'
        "</svg>",
        encoding="utf-8",
    )
    return path


def make_report_yml(folder: Path) -> Path:
    data = {
        "type": "visual",
        "metadata": {
            "title": "Test",
            "subject": "TS",
            "teacher": "T",
            "student": "S",
            "date": "2025-01-01",
        },
    }
    path = folder / "report.yml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_visual_folder():
    """Create a temp folder for visual test fixtures."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def full_valid_setup(temp_visual_folder):
    """Folder with a valid report.yml + figures.yml + actual SVG file."""
    folder = temp_visual_folder
    make_report_yml(folder)
    svg = touch_svg(folder, "diagram.svg")
    make_figures_yml(folder, [
        {
            "file": svg.name,
            "title": "Test diagram",
            "caption": "A test caption",
            "source": "Lecture notes",
            "renderer": "Mermaid",
            "section": "Introduction",
        },
    ])
    return folder


# ---------------------------------------------------------------------------
# visual_builder.metadata_errors tests
# ---------------------------------------------------------------------------


class TestVisualBuilderMetadataErrors:
    """Exercise `metadata_errors` from visual_builder.py."""

    def test_valid_entry_passes(self, full_valid_setup):
        errors = metadata_errors(full_valid_setup)
        assert errors == []

    def test_missing_title_is_error(self, temp_visual_folder):
        folder = temp_visual_folder
        make_report_yml(folder)
        touch_svg(folder, "fig.svg")
        make_figures_yml(folder, [
            {
                "file": "fig.svg",
                "caption": "No title",
                "source": "X",
                "renderer": "Mermaid",
                "section": "Intro",
            },
        ])
        errors = metadata_errors(folder)
        assert any("sin title" in e.lower() for e in errors)

    def test_missing_section_and_intended_section_is_error(self, temp_visual_folder):
        folder = temp_visual_folder
        make_report_yml(folder)
        touch_svg(folder, "fig.svg")
        make_figures_yml(folder, [
            {
                "file": "fig.svg",
                "title": "No section",
                "caption": "Missing section",
                "source": "X",
                "renderer": "Mermaid",
            },
        ])
        errors = metadata_errors(folder)
        assert any("sin section" in e.lower() for e in errors)

    def test_intended_section_works_as_alias(self, temp_visual_folder):
        folder = temp_visual_folder
        make_report_yml(folder)
        touch_svg(folder, "fig.svg")
        make_figures_yml(folder, [
            {
                "file": "fig.svg",
                "title": "Legacy entry",
                "caption": "Uses intended_section",
                "source": "X",
                "renderer": "Mermaid",
                "intended_section": "Legacy section",
            },
        ])
        errors = metadata_errors(folder)
        assert errors == []

    def test_both_section_and_intended_section_pass(self, temp_visual_folder):
        folder = temp_visual_folder
        make_report_yml(folder)
        touch_svg(folder, "fig.svg")
        make_figures_yml(folder, [
            {
                "file": "fig.svg",
                "title": "Both fields",
                "caption": "Has both section fields",
                "source": "X",
                "renderer": "Mermaid",
                "section": "Canonical",
                "intended_section": "Alias",
            },
        ])
        errors = metadata_errors(folder)
        assert errors == []

    def test_multiple_figures_report_multiple_errors(self, temp_visual_folder):
        folder = temp_visual_folder
        make_report_yml(folder)
        touch_svg(folder, "a.svg")
        touch_svg(folder, "b.svg")
        make_figures_yml(folder, [
            {
                "file": "a.svg",
                "caption": "No title no section",
                "source": "X",
                "renderer": "Mermaid",
            },
            {
                "file": "b.svg",
                "title": "Second",
                "caption": "No section",
                "source": "X",
                "renderer": "Mermaid",
            },
        ])
        errors = metadata_errors(folder)
        assert any("Figura 1" in e for e in errors)
        assert any("Figura 2" in e for e in errors)
        assert any("sin title" in e.lower() for e in errors)
        assert any("sin section" in e.lower() for e in errors)

    def test_missing_figures_yml(self, temp_visual_folder):
        errors = metadata_errors(temp_visual_folder)
        assert any("falta" in e.lower() for e in errors)

    def test_null_file_reports_missing_file_no_crash(self, temp_visual_folder):
        """file: null must report 'sin file' and never crash in metadata_errors."""
        folder = temp_visual_folder
        make_report_yml(folder)
        make_figures_yml(folder, [
            {
                "file": None,
                "title": "Null file test",
                "caption": "Has file set to null",
                "source": "X",
                "renderer": "Mermaid",
                "section": "Intro",
            },
        ])
        errors = metadata_errors(folder)
        assert any("sin file" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# validate_report.visual_validation tests
# ---------------------------------------------------------------------------


class TestValidateReportVisualValidation:
    """Exercise `visual_validation` from validate_report.py."""

    def _errors(self, folder: Path) -> list[str]:
        config = ReportConfig(folder=folder, raw={"type": "visual"})
        result = visual_validation(config)
        return result.errors

    def test_valid_entry_passes(self, full_valid_setup):
        errors = self._errors(full_valid_setup)
        assert errors == []

    def test_missing_title_is_error(self, temp_visual_folder):
        folder = temp_visual_folder
        make_report_yml(folder)
        touch_svg(folder, "fig.svg")
        make_figures_yml(folder, [
            {
                "file": "fig.svg",
                "caption": "No title",
                "source": "X",
                "renderer": "Mermaid",
                "section": "Intro",
            },
        ])
        errors = self._errors(folder)
        assert any("sin title" in e.lower() for e in errors)

    def test_missing_section_and_intended_section_is_error(self, temp_visual_folder):
        folder = temp_visual_folder
        make_report_yml(folder)
        touch_svg(folder, "fig.svg")
        make_figures_yml(folder, [
            {
                "file": "fig.svg",
                "title": "No section",
                "caption": "Missing section",
                "source": "X",
                "renderer": "Mermaid",
            },
        ])
        errors = self._errors(folder)
        assert any("sin section" in e.lower() for e in errors)

    def test_intended_section_works_as_alias(self, temp_visual_folder):
        folder = temp_visual_folder
        make_report_yml(folder)
        touch_svg(folder, "fig.svg")
        make_figures_yml(folder, [
            {
                "file": "fig.svg",
                "title": "Legacy entry",
                "caption": "Uses intended_section",
                "source": "X",
                "renderer": "Mermaid",
                "intended_section": "Legacy section",
            },
        ])
        errors = self._errors(folder)
        assert errors == []

    def test_missing_figures_yml_is_warning_not_error(self, temp_visual_folder):
        folder = temp_visual_folder
        make_report_yml(folder)
        errors = self._errors(folder)
        assert errors == []  # missing figures.yml generates a warning, not an error

    def test_null_file_is_validation_error_not_crash(self, temp_visual_folder):
        """file: null must produce a validation error, never a crash."""
        folder = temp_visual_folder
        make_report_yml(folder)
        make_figures_yml(folder, [
            {
                "file": None,
                "title": "Null file test",
                "caption": "Has file set to null",
                "source": "X",
                "renderer": "Mermaid",
                "section": "Intro",
            },
        ])
        errors = self._errors(folder)
        assert any("sin file" in e.lower() for e in errors)
        # Also verify no traceback happens: if we reached here, no crash.


# ---------------------------------------------------------------------------
# Fixtures for common_validation tests (need real dirs for outputs/ checks)
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_report_folder():
    """Create a minimal report folder with an outputs/ dir for common_validation."""
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        (folder / "outputs").mkdir(parents=True, exist_ok=True)
        yield folder


# ---------------------------------------------------------------------------
# common_validation tests for academic_format.yml enforcement
# ---------------------------------------------------------------------------


class TestCommonValidationAcademicFormat:
    """Exercise common_validation's academic_format.yml policy reading.

    These tests verify that fields annotated [ENFORCED] in academic_format.yml
    are actually read and trigger errors when violated.

    Covers:
      - cover.required: PDF with < 2 pages triggers error
      - conclusions.banned_openers: config list is used, not just defaults
    """

    # -- cover.required enforcement ------------------------------------------

    def test_cover_required_single_page_pdf_triggers_error(
        self, monkeypatch, temp_report_folder,
    ) -> None:
        """When cover.required=True and PDF has only 1 page, error is reported."""
        import validate_report as vr

        monkeypatch.setattr(vr, "pdf_text_pages", lambda _p: ["only page"])

        # Create a fake PDF so config.pdf_path.exists() returns True
        pdf_path = temp_report_folder / "outputs" / "report.pdf"
        pdf_path.write_text("fake pdf content", encoding="utf-8")
        config = ReportConfig(
            folder=temp_report_folder,
            raw={"type": "essay", "pdf": str(pdf_path)},
            academic_format={
                "cover": {"required": True},
                "conclusions": {"banned_openers": []},
            },
        )

        result = common_validation(config)
        assert any("portada" in e.lower() and "menos de 2" in e.lower() for e in result.errors), (
            f"Expected cover error for single-page PDF, got: {result.errors}"
        )

    def test_cover_required_not_required_skips_check(
        self, monkeypatch, temp_report_folder,
    ) -> None:
        """When cover.required is explicitly False, no cover error for 1-page PDF."""
        import validate_report as vr

        monkeypatch.setattr(vr, "pdf_text_pages", lambda _p: ["only page"])

        pdf_path = temp_report_folder / "outputs" / "report.pdf"
        pdf_path.write_text("fake pdf content", encoding="utf-8")
        config = ReportConfig(
            folder=temp_report_folder,
            raw={"type": "essay", "pdf": str(pdf_path)},
            academic_format={
                "cover": {"required": False},
                "conclusions": {"banned_openers": []},
            },
        )

        result = common_validation(config)
        cover_errors = [e for e in result.errors if "portada" in e.lower()]
        assert not cover_errors, f"Expected no cover errors when cover.required=False, got: {cover_errors}"

    def test_cover_required_two_page_pdf_passes(
        self, monkeypatch, temp_report_folder,
    ) -> None:
        """When cover.required=True and PDF has 2+ pages, no cover error."""
        import validate_report as vr

        monkeypatch.setattr(vr, "pdf_text_pages", lambda _p: ["page 1 cover", "page 2 body"])

        pdf_path = temp_report_folder / "outputs" / "report.pdf"
        pdf_path.write_text("fake pdf content", encoding="utf-8")
        config = ReportConfig(
            folder=temp_report_folder,
            raw={"type": "essay", "pdf": str(pdf_path)},
            academic_format={
                "cover": {"required": True},
                "conclusions": {"banned_openers": []},
            },
        )

        result = common_validation(config)
        cover_errors = [e for e in result.errors if "portada" in e.lower()]
        assert not cover_errors, f"Expected no cover errors for 2-page PDF, got: {cover_errors}"

    # -- conclusions.banned_openers enforcement -------------------------------

    def test_banned_openers_reads_from_config(
        self, monkeypatch, temp_report_folder,
    ) -> None:
        """banned_openers list is read from academic_format, not hardcoded.
        With no PDF, banned_openers check is skipped — verify result is a clean ValidationResult.
        """
        config = ReportConfig(
            folder=temp_report_folder,
            raw={"type": "essay"},
            academic_format={
                "conclusions": {"banned_openers": ["Custom banned"]},
                "cover": {"required": False},
            },
        )

        result = common_validation(config)
        assert isinstance(result, ValidationResult)
        # No PDF exists, so banned_openers cannot be checked — no errors about banned terms
        assert not any("banned" in e.lower() for e in result.errors), (
            f"Did not expect banned-opener errors without a PDF: {result.errors}"
        )
        assert not any("custom banned" in e.lower() for e in result.errors), (
            f"Custom banned opener leaked without PDF to scan: {result.errors}"
        )

    def test_banned_openers_flag_found_text(
        self, monkeypatch, temp_report_folder,
    ) -> None:
        """When PDF text contains a banned opener, error is flagged."""
        import validate_report as vr

        monkeypatch.setattr(vr, "pdf_text_pages", lambda _p: ["page with Se concluye in it"])

        pdf_path = temp_report_folder / "outputs" / "report.pdf"
        pdf_path.write_text("fake pdf content", encoding="utf-8")
        config = ReportConfig(
            folder=temp_report_folder,
            raw={"type": "essay", "pdf": str(pdf_path)},
            academic_format={
                "conclusions": {"banned_openers": ["Se concluye"]},
                "cover": {"required": False},
            },
        )

        result = common_validation(config)
        assert any("Se concluye" in e for e in result.errors), (
            f"Expected banned opener error, got: {result.errors}"
        )

    # -- academic_format default path survives YAML changes ------------------

    def test_academic_format_default_loads_valid_keys(self) -> None:
        """The real academic_format.yml loads and has expected enforced keys."""
        import yaml

        path = DEFAULT_FORMAT
        data = yaml.safe_load(path.read_text(encoding="utf-8"))

        # Enforced keys must exist (regression guard)
        assert "conclusions" in data
        assert "banned_openers" in data.get("conclusions", {})
        assert "cover" in data
        assert "logo_required" in data.get("cover", {})
        assert "required" in data.get("cover", {})
