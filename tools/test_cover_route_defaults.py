"""Route-derived cover defaults and their validation alignment (#23).

``document-routing.md`` says only Route A may activate academic machinery.
Before the route fix every route silently received the academic cover
expectations, and a technical PDF was failed for lacking a cover it never
agreed to.

These tests pin the derived cover defaults AND their precedence:

  1. an explicit ``cover:`` block in report.yml always wins, per key;
  2. an absent (or academic) route keeps the historical academic_format.yml
     values — legacy reports render and validate exactly as before;
  3. non-academic routes default to no institutional cover;
  4. dependent defaults stay COHERENT: explicitly requiring a cover must not
     leave the body-start page at 1 (the validator would compare page 1 with
     itself and falsely report the cover as mixed with the body) nor drop the
     logo expectation — unless that very key is explicitly overridden.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from report_config import ReportConfig  # noqa: E402
from validate_report import common_validation, pdf_layout_validation  # noqa: E402


def make_config(tmp_path: Path, raw: dict) -> ReportConfig:
    """Load a real ReportConfig (academic_format.yml included) from disk."""
    folder = tmp_path / "r"
    folder.mkdir(parents=True, exist_ok=True)
    base = {
        "type": "technical_report",
        "backend": "latex",
        "output": "pdf",
        "pdf": "build/report.pdf",
        "body": "body.md",
    }
    base.update(raw)
    (folder / "report.yml").write_text(yaml.safe_dump(base), encoding="utf-8")
    (folder / "body.md").write_text("# Propósito\n\nContenido.\n", encoding="utf-8")
    return ReportConfig.load(folder)


# ---------------------------------------------------------------------------
# Cover defaults derive from the route
# ---------------------------------------------------------------------------


def test_absent_route_keeps_the_academic_cover_defaults(tmp_path):
    config = make_config(tmp_path, {})
    assert config.cover_value("required") is True
    assert config.cover_value("logo_required") is True
    assert config.cover_value("body_starts_on_page") == 2


@pytest.mark.parametrize("route", ["project", "business", "technical", "other"])
def test_non_academic_routes_default_to_no_institutional_cover(tmp_path, route):
    config = make_config(tmp_path, {"route": route})
    assert config.cover_value("required") is False
    assert config.cover_value("logo_required") is False
    assert config.cover_value("body_starts_on_page") == 1


def test_explicit_cover_block_beats_the_route_default(tmp_path):
    config = make_config(tmp_path, {"route": "technical", "cover": {"required": True}})
    assert config.cover_value("required") is True


def test_explicit_cover_keys_win_even_over_required_dependence(tmp_path):
    """A user who explicitly sets a dependent key keeps their exact value."""
    config = make_config(
        tmp_path,
        {
            "route": "technical",
            "cover": {"required": True, "body_starts_on_page": 3, "logo_required": False},
        },
    )
    assert config.cover_value("required") is True
    assert config.cover_value("body_starts_on_page") == 3
    assert config.cover_value("logo_required") is False


def test_academic_route_can_explicitly_drop_the_cover(tmp_path):
    config = make_config(tmp_path, {"route": "academic", "cover": {"required": False}})
    assert config.cover_value("required") is False


def test_cover_keys_outside_the_route_table_still_come_from_academic_format(tmp_path):
    config = make_config(tmp_path, {"route": "technical"})
    assert config.cover_value("full_first_page") is True


def test_partial_cover_override_does_not_shadow_sibling_keys(tmp_path):
    config = make_config(tmp_path, {"route": "technical", "cover": {"logo_required": True}})
    assert config.cover_value("logo_required") is True
    assert config.cover_value("required") is False
    assert config.cover_value("body_starts_on_page") == 1


# ---------------------------------------------------------------------------
# Dependent defaults stay coherent when a cover is explicitly required (#23 fix 2)
# ---------------------------------------------------------------------------


def test_explicit_required_cover_on_technical_route_upgrades_dependent_defaults(tmp_path):
    """Requiring a cover must not leave body page at 1 (self-comparison)."""
    config = make_config(tmp_path, {"route": "technical", "cover": {"required": True}})
    assert config.cover_value("required") is True
    assert config.cover_value("body_starts_on_page") == 2
    assert config.cover_value("logo_required") is True


def test_explicit_required_cover_on_project_route_upgrades_dependent_defaults(tmp_path):
    config = make_config(tmp_path, {"route": "project", "cover": {"required": True}})
    assert config.cover_value("body_starts_on_page") == 2
    assert config.cover_value("logo_required") is True


def test_cover_not_required_keeps_the_plain_dependent_defaults(tmp_path):
    config = make_config(tmp_path, {"route": "technical", "cover": {"required": False}})
    assert config.cover_value("body_starts_on_page") == 1
    assert config.cover_value("logo_required") is False


# ---------------------------------------------------------------------------
# Validation aligns with the derived cover defaults
# ---------------------------------------------------------------------------


def test_technical_route_without_cover_does_not_fail_cover_validation(tmp_path):
    """A plain technical PDF must not be failed for lacking an academic cover.

    The PDF bytes are a stub: pdftotext/pdfinfo degrade to empty output, which
    is exactly the state that used to trip the academic cover requirements.
    """
    folder = tmp_path / "r"
    config = make_config(folder, {"route": "technical"})
    config.pdf_path.parent.mkdir(parents=True, exist_ok=True)
    config.pdf_path.write_bytes(b"%PDF-1.4\n")
    result = common_validation(config)
    assert not any("portada es obligatoria" in e for e in result.errors)
    layout = pdf_layout_validation(config)
    assert not any("logo UNL" in e for e in layout.errors)
    assert not any("portada parece mezclada" in e for e in layout.errors)


def test_technical_route_with_cover_does_not_false_warn_on_unnumbered_heading(tmp_path, monkeypatch):
    """Non-academic routes use unnumbered, non-academic headings by contract.

    The body-start heuristic used to require an academic Spanish marker
    (`introducción`, `desarrollo`, `ejercicio`, ...) on the body page; a
    technical route whose body opens with e.g. "Arquitectura" never matches
    one, so it always warned even though the body demonstrably starts there.
    """
    folder = tmp_path / "r"
    config = make_config(
        folder,
        {"route": "technical", "cover": {"required": True, "body_starts_on_page": 2}},
    )
    config.pdf_path.parent.mkdir(parents=True, exist_ok=True)
    config.pdf_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "validate_report.pdf_text_pages",
        lambda path: ["Portada\n", "Arquitectura\n\nContenido técnico.\n"],
    )
    monkeypatch.setattr("validate_report.pdfinfo", lambda path: {"Pages": "2"})

    result = pdf_layout_validation(config)

    assert not any("inicio claro del cuerpo" in w for w in result.warnings)


def test_academic_route_still_demands_the_cover(tmp_path):
    folder = tmp_path / "r"
    config = make_config(folder, {})
    config.pdf_path.parent.mkdir(parents=True, exist_ok=True)
    config.pdf_path.write_bytes(b"%PDF-1.4\n")
    result = common_validation(config)
    assert any("portada es obligatoria" in e for e in result.errors), (
        "an academic PDF without pages must still fail the cover requirement"
    )
