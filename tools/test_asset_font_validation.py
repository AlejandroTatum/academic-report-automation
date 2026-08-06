"""Tests for asset/font constants and validation in the LaTeX pipeline.

Covers existence checks for logo/background assets and canonical font config.
No LaTeX/PDF compilation — all tests are fast and deterministic.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

# Make tools/ importable
TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from build_latex_report import (
    ASSETS_DIR,
    BACKGROUND_FILENAME,
    EXPECTED_ASSETS,
    KNOWN_EXTRA_ASSETS,
    LOGO_FILENAME,
    PLAIN_LOGO_FILENAME,
    validate_assets_exist,
)
from report_config import ROOT as AUTO_ROOT
from validate_report import asset_validation, ReportConfig


# ---------------------------------------------------------------------------
# Asset constant tests
# ---------------------------------------------------------------------------


class TestAssetConstants:
    """Asset filenames are the single source of truth — verify they match disk."""

    def test_logo_constant_matches_disk(self) -> None:
        """LOGO_FILENAME must exist under ASSETS_DIR."""
        path = ASSETS_DIR / LOGO_FILENAME
        assert path.exists(), f"Logo file not found: {path}"

    def test_background_constant_matches_disk(self) -> None:
        """BACKGROUND_FILENAME must exist under ASSETS_DIR."""
        path = ASSETS_DIR / BACKGROUND_FILENAME
        assert path.exists(), f"Background file not found: {path}"

    def test_expected_assets_all_exist(self) -> None:
        """Every entry in EXPECTED_ASSETS must be present on disk."""
        for filename, _description in EXPECTED_ASSETS:
            path = ASSETS_DIR / filename
            assert path.exists(), f"Expected asset missing: {path}"
            assert path.stat().st_size >= 1_000, (
                f"Asset too small (likely corrupt or placeholder): {path} "
                f"({path.stat().st_size} bytes)"
            )

    def test_no_extra_top_level_pngs(self) -> None:
        """Flag if an unknown .png appears in assets/ that isn't EXPECTED or KNOWN_EXTRA.

        This is a warning-gate: if someone adds a new asset without updating
        EXPECTED_ASSETS or KNOWN_EXTRA_ASSETS, this test fails.
        """
        if not ASSETS_DIR.exists():
            pytest.skip("ASSETS_DIR does not exist on this machine")
        expected_names = {name for name, _desc in EXPECTED_ASSETS}
        known = expected_names | KNOWN_EXTRA_ASSETS
        top_level_pngs = {p.name for p in ASSETS_DIR.iterdir() if p.suffix == ".png" and p.parent == ASSETS_DIR}

        # generated/ subfolder contains auto-generated visuals not covered here
        extra = top_level_pngs - known
        assert not extra, (
            f"Unknown PNG(s) in {ASSETS_DIR} not tracked in EXPECTED_ASSETS or KNOWN_EXTRA_ASSETS: {extra}"
        )


# ---------------------------------------------------------------------------
# Font configuration consistency tests
# ---------------------------------------------------------------------------


class TestFontConfig:
    """Verify font references are consistent across config sources."""

    CANONICAL_FONT = "Times New Roman"
    FALLBACK_SERIF = "Liberation Serif"
    FALLBACK_TEX_LATEX = "TeX Gyre Termes"

    def test_academic_format_yml_has_times_first(self) -> None:
        """The YAML font_preference must list Times New Roman first."""
        import yaml

        path = AUTO_ROOT / "templates" / "academic_format.yml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        prefs = data.get("body_text", {}).get("font_preference", [])
        assert prefs, "font_preference list is empty or missing"
        assert prefs[0] == self.CANONICAL_FONT, (
            f"Canonical font must be '{self.CANONICAL_FONT}', got '{prefs[0]}'"
        )

    def test_latex_template_uses_times_fallback_chain(self) -> None:
        """The .tex template must reference Times New Roman + TeX Gyre Termes fallback."""
        path = AUTO_ROOT / "templates" / "unl-report.tex"
        tex = path.read_text(encoding="utf-8")

        assert self.CANONICAL_FONT in tex, (
            f"{path.name} must reference '{self.CANONICAL_FONT}'"
        )
        assert self.FALLBACK_TEX_LATEX in tex, (
            f"{path.name} must reference '{self.FALLBACK_TEX_LATEX}' as fallback"
        )
        assert self.FALLBACK_SERIF not in tex, (
            f"{path.name} should NOT reference '{self.FALLBACK_SERIF}' directly"
        )

    def test_chamba_template_uses_times_fallback_chain(self) -> None:
        """The chamba-overleaf template must also use Times + TeX Gyre Termes."""
        path = AUTO_ROOT / "templates" / "chamba-overleaf.tex"
        if not path.exists():
            pytest.skip("chamba-overleaf.tex not present")
        tex = path.read_text(encoding="utf-8")

        assert self.CANONICAL_FONT in tex, (
            f"{path.name} must reference '{self.CANONICAL_FONT}'"
        )
        assert self.FALLBACK_TEX_LATEX in tex, (
            f"{path.name} must reference '{self.FALLBACK_TEX_LATEX}' as fallback"
        )


# ---------------------------------------------------------------------------
# validate_assets_exist (build_latex_report) tests
# ---------------------------------------------------------------------------


class TestValidateAssetsExist:
    """Exercise validate_assets_exist() with real and patched ASSETS_DIR."""

    def test_real_assets_pass(self) -> None:
        """With real assets present, validate_assets_exist returns empty list."""
        errors = validate_assets_exist()
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_missing_asset_reports_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When an asset file is missing, validate_assets_exist reports it."""
        with tempfile.TemporaryDirectory() as tmp:
            fake_assets = Path(tmp)
            # Create only one of the three expected assets (> 1000 bytes to pass size check)
            content = "x" * 2000
            (fake_assets / LOGO_FILENAME).write_text(content, encoding="utf-8")
            monkeypatch.setattr("build_latex_report.ASSETS_DIR", fake_assets)
            errors = validate_assets_exist()
            # Two missing: BACKGROUND_FILENAME + PLAIN_LOGO_FILENAME
            assert len(errors) == 2
            assert BACKGROUND_FILENAME in errors[0] or BACKGROUND_FILENAME in errors[1]

    def test_empty_asset_reports_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An asset smaller than 1000 bytes should generate a warning-level error."""
        with tempfile.TemporaryDirectory() as tmp:
            fake_assets = Path(tmp)
            # Create all three expected assets as tiny files
            (fake_assets / LOGO_FILENAME).write_text("x", encoding="utf-8")
            (fake_assets / BACKGROUND_FILENAME).write_text("y", encoding="utf-8")
            (fake_assets / PLAIN_LOGO_FILENAME).write_text("z", encoding="utf-8")
            monkeypatch.setattr("build_latex_report.ASSETS_DIR", fake_assets)
            errors = validate_assets_exist()
            assert len(errors) == 3  # all three are suspiciously small
            assert all("sospechosamente pequeño" in e for e in errors)


# ---------------------------------------------------------------------------
# asset_validation (validate_report) tests
# ---------------------------------------------------------------------------


class TestValidateReportAssetValidation:
    """Exercise asset_validation() from validate_report.py."""

    def test_real_assets_pass(self) -> None:
        """With real assets present, asset_validation returns no errors."""
        config = ReportConfig(folder=Path("/tmp/fake"), raw={"type": "essay"})
        result = asset_validation(config)
        assert result.errors == [], f"Expected no errors, got: {result.errors}"

    def test_missing_asset_reports_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When an asset is missing, asset_validation reports it."""
        import build_latex_report as blr

        with tempfile.TemporaryDirectory() as tmp:
            fake_assets = Path(tmp)
            # Create only one of three expected assets (> 1000 bytes to pass size check)
            (fake_assets / LOGO_FILENAME).write_text("x" * 2000, encoding="utf-8")
            monkeypatch.setattr(blr, "ASSETS_DIR", fake_assets)

            config = ReportConfig(folder=Path("/tmp/fake"), raw={"type": "essay"})
            result = asset_validation(config)
            # Two missing: BACKGROUND_FILENAME + PLAIN_LOGO_FILENAME
            assert len(result.errors) == 2
            assert BACKGROUND_FILENAME in " ".join(result.errors)

    def test_non_latex_backend_still_validates_assets(self) -> None:
        """asset_validation() itself is backend-agnostic (checks system assets). Pipeline gates it to latex backend."""
        config = ReportConfig(folder=Path("/tmp/fake"), raw={"type": "visual"})
        result = asset_validation(config)
        # Uses real ASSETS_DIR — should pass
        assert result.errors == [], f"Expected no errors, got: {result.errors}"
