"""Tests for the non-institutional (plain) LaTeX template.

The pipeline historically assumed every deliverable was a UNL university
assignment. Project documentation needs the same rendering quality without
the institutional cover, logo and academic header/footer.

These tests pin three things:
  1. `template: plain` resolves to the plain template.
  2. An unknown template key fails loudly instead of silently rendering UNL.
  3. Cover requirements can be relaxed per report, without changing the
     global defaults that academic reports rely on.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import build_latex_report  # noqa: E402
import report_config  # noqa: E402

PLAIN_TEMPLATE = ROOT / "templates" / "plain-report.tex"
UNL_TEMPLATE = ROOT / "templates" / "unl-report.tex"

# Placeholders every template must expose for the renderer to fill.
REQUIRED_PLACEHOLDERS = (
    "{{TITLE}}",
    "{{BODY}}",
    "{{BIB_FILE}}",
    "{{HAS_BIB}}",
    "{{HAS_FIGURES}}",
    "{{LIST_OF_FIGURES}}",
    "{{FRONT_MATTER}}",
    "{{AI_DECLARATION}}",
    "{{AFTER_BIBLIOGRAPHY}}",
)

# Strings validate_report.py:298-301 greps for in the generated .tex.
REQUIRED_PACKAGES = ("hyperref", "Needspace", "onehalfspacing", "parindent")


# ---------------------------------------------------------------------------
# The template itself
# ---------------------------------------------------------------------------


def test_plain_template_exists() -> None:
    assert PLAIN_TEMPLATE.is_file(), "templates/plain-report.tex must exist"


@pytest.fixture(scope="module")
def plain() -> str:
    return PLAIN_TEMPLATE.read_text(encoding="utf-8")


@pytest.mark.parametrize("placeholder", REQUIRED_PLACEHOLDERS)
def test_plain_template_exposes_placeholder(plain: str, placeholder: str) -> None:
    assert placeholder in plain, f"plain template must expose {placeholder}"


@pytest.mark.parametrize("package", REQUIRED_PACKAGES)
def test_plain_template_satisfies_latex_validator(plain: str, package: str) -> None:
    assert package in plain, (
        f"validate_report.py greps the generated .tex for {package!r}"
    )


def test_plain_template_has_no_institutional_cover(plain: str) -> None:
    assert "titlepage" not in plain, "the plain template must not render a cover page"
    assert "BackgroundPic" not in plain, "no full-bleed institutional background"
    assert "{{BACKGROUND_PATH}}" not in plain, "no institutional background asset"


def test_plain_template_has_no_academic_header_or_footer(plain: str) -> None:
    assert "fancyhdr" not in plain, "no academic running header"
    assert "Educamos para Transformar" not in plain
    assert "HE-CIS-2022" not in plain


def test_plain_template_carries_no_hardcoded_institution(plain: str) -> None:
    for literal in (
        "Universidad Nacional de Loja",
        "Carrera de Computación",
        "Facultad de la Energía",
        "DOCENTE",
        "Paralelo",
    ):
        assert literal not in plain, (
            f"plain template must not hardcode {literal!r}"
        )


def test_unl_template_is_untouched() -> None:
    """The academic route must keep working exactly as before."""
    unl = UNL_TEMPLATE.read_text(encoding="utf-8")
    assert "titlepage" in unl
    assert "fancyhdr" in unl
    assert "Educamos para Transformar" in unl


# ---------------------------------------------------------------------------
# Template resolution
# ---------------------------------------------------------------------------


def test_plain_alias_resolves_to_plain_template() -> None:
    assert "plain" in build_latex_report.TEMPLATE_ALIASES
    assert build_latex_report.TEMPLATE_ALIASES["plain"] == PLAIN_TEMPLATE


@pytest.mark.parametrize("alias", ["default", "unl", "unl_report"])
def test_academic_aliases_still_resolve_to_unl(alias: str) -> None:
    assert build_latex_report.TEMPLATE_ALIASES[alias] == UNL_TEMPLATE


def test_unknown_template_key_fails_loudly() -> None:
    """A typo must not silently render the institutional shell.

    This was a real defect: `TEMPLATE_ALIASES.get(key, DEFAULT_TEMPLATE)` meant
    `template: plian` produced a full UNL document with no warning at all.
    """
    with pytest.raises(SystemExit) as excinfo:
        build_latex_report.resolve_template("definitely-not-a-template")
    message = str(excinfo.value)
    assert "definitely-not-a-template" in message
    assert "plain" in message, "the error must list the valid keys"


def test_absent_template_key_still_defaults_to_unl() -> None:
    """Omitting `template:` keeps the historical academic behavior."""
    assert build_latex_report.resolve_template(None) == UNL_TEMPLATE
    assert build_latex_report.resolve_template("") == UNL_TEMPLATE
    assert build_latex_report.resolve_template("default") == UNL_TEMPLATE


# ---------------------------------------------------------------------------
# Per-report cover overrides
# ---------------------------------------------------------------------------


def make_config(tmp_path: Path, raw: dict) -> "report_config.ReportConfig":
    import yaml

    folder = tmp_path / "r"
    folder.mkdir(parents=True, exist_ok=True)
    base = {
        "type": "technical_report",
        "backend": "latex",
        "output": "pdf",
        "metadata": {"title": "T", "subject": "S", "teacher": "D", "student": "A"},
        "body": "body.md",
    }
    base.update(raw)
    (folder / "report.yml").write_text(yaml.safe_dump(base), encoding="utf-8")
    (folder / "body.md").write_text("# T\n\ncontent\n", encoding="utf-8")
    return report_config.ReportConfig.load(folder)


def test_cover_required_defaults_to_true(tmp_path: Path) -> None:
    config = make_config(tmp_path, {})
    assert config.academic_value("cover", "required", default=True) is True


def test_report_can_opt_out_of_the_cover(tmp_path: Path) -> None:
    config = make_config(tmp_path, {"cover": {"required": False}})
    assert config.academic_value("cover", "required", default=True) is False


def test_report_can_opt_out_of_the_logo(tmp_path: Path) -> None:
    config = make_config(tmp_path, {"cover": {"logo_required": False}})
    assert config.academic_value("cover", "logo_required", default=True) is False


def test_override_is_scoped_to_that_report(tmp_path: Path) -> None:
    """One report opting out must not change the global default."""
    opted_out = make_config(tmp_path / "a", {"cover": {"required": False}})
    assert opted_out.academic_value("cover", "required", default=True) is False

    untouched = make_config(tmp_path / "b", {})
    assert untouched.academic_value("cover", "required", default=True) is True


def test_unrelated_academic_values_are_not_shadowed(tmp_path: Path) -> None:
    """A partial cover override must not hide the rest of the cover block."""
    config = make_config(tmp_path, {"cover": {"required": False}})
    assert config.academic_value("cover", "body_starts_on_page", default=None) == 2


@pytest.mark.parametrize("section", ["validators", "figures", "page", "body_text"])
def test_non_overridable_sections_cannot_be_shadowed(
    tmp_path: Path, section: str
) -> None:
    """Only `cover` is overridable per report.

    Top-level report.yml keys share a namespace with academic_format.yml
    sections and several already collide: 31 reports carry `validators:`.
    A report must not be able to shadow a globally owned rule by accident.
    """
    config = make_config(tmp_path, {section: {"required": "hijacked"}})
    assert config.academic_value(section, "required", default="untouched") != "hijacked"


def test_cover_override_requires_a_mapping(tmp_path: Path) -> None:
    """A malformed, non-mapping `cover:` falls back instead of exploding."""
    config = make_config(tmp_path, {"cover": ["not", "a", "mapping"]})
    assert config.academic_value("cover", "required", default=True) is True
