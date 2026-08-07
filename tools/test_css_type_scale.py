"""Tests for the typographic scale of the HTML stylesheet.

`templates/ensayo_unl.css` drives the HTML/print deliverable produced by
`tools/build_report.py`. It used to declare a 12 pt body with `h1` and `h2`
both at 11 pt: every heading was *smaller* than the text it introduced, and
`h1` and `h2` were indistinguishable from each other. Rendered in a browser,
sections read as slightly-smaller bold text instead of titles — there was no
hierarchy at all.

These tests pin the ordering invariant so the scale cannot silently collapse
again, and keep it anchored to `templates/academic_format.yml`, which declares
the 12 pt body as the format contract.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent

CSS_PATH = ROOT / "templates" / "ensayo_unl.css"
FORMAT_PATH = ROOT / "templates" / "academic_format.yml"

# Headings, largest first. The stylesheet must define every one of them.
HEADING_SELECTORS = ("h1", "h2", "h3", "h4")

# Font stacks academic_format.yml declares. The scale fix must not touch them.
CANONICAL_SERIF = ("Times New Roman", "Liberation Serif")
CANONICAL_FALLBACKS = ("TeX Gyre Termes", "TeX Gyre Heros")


@pytest.fixture(scope="module")
def css() -> str:
    return CSS_PATH.read_text(encoding="utf-8")


def rule_body(css: str, selector: str) -> str:
    """Return the declaration block of a top-level rule, or "" when absent.

    Selectors are matched at the start of a line so that `h1` does not also
    match the `h1, h2, h3` grouping or a descendant selector further in.
    """
    pattern = re.compile(
        r"^" + re.escape(selector) + r"\s*\{([^{}]*)\}",
        re.MULTILINE,
    )
    match = pattern.search(css)
    return match.group(1) if match else ""


def font_size_pt(css: str, selector: str) -> float | None:
    """Return the `font-size` of a top-level rule in points, or None."""
    match = re.search(r"font-size\s*:\s*([\d.]+)pt", rule_body(css, selector))
    return float(match.group(1)) if match else None


# ---------------------------------------------------------------------------
# The scale exists at all
# ---------------------------------------------------------------------------


def test_stylesheet_exists() -> None:
    assert CSS_PATH.is_file(), "templates/ensayo_unl.css must exist"


def test_body_size_matches_the_format_contract(css: str) -> None:
    """academic_format.yml owns the body size; the stylesheet must agree."""
    declared = yaml.safe_load(FORMAT_PATH.read_text(encoding="utf-8"))
    expected = float(declared["body_text"]["size_pt"])
    assert font_size_pt(css, "html, body") == expected, (
        "the stylesheet body size must match academic_format.yml body_text.size_pt"
    )


@pytest.mark.parametrize("selector", HEADING_SELECTORS)
def test_every_heading_level_declares_a_size(css: str, selector: str) -> None:
    assert font_size_pt(css, selector) is not None, (
        f"{selector} must declare an explicit font-size so the scale is readable "
        "from the stylesheet instead of inherited from the browser default"
    )


# ---------------------------------------------------------------------------
# The ordering invariant — this is the regression guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("selector", HEADING_SELECTORS)
def test_every_heading_is_larger_than_the_body(css: str, selector: str) -> None:
    """A heading smaller than its own body text is the defect being fixed."""
    body = font_size_pt(css, "html, body")
    heading = font_size_pt(css, selector)
    assert heading is not None and body is not None
    assert heading > body, (
        f"{selector} is {heading}pt but the body is {body}pt: a heading must "
        "never be smaller than or equal to the text it introduces"
    )


def test_heading_sizes_decrease_strictly_with_depth(css: str) -> None:
    """h1 > h2 > h3 > h4. Equal sizes are what erased the hierarchy before."""
    sizes = [font_size_pt(css, selector) for selector in HEADING_SELECTORS]
    assert all(size is not None for size in sizes)
    for shallower, deeper, size_a, size_b in zip(
        HEADING_SELECTORS, HEADING_SELECTORS[1:], sizes, sizes[1:]
    ):
        assert size_a > size_b, (
            f"{shallower} ({size_a}pt) must outrank {deeper} ({size_b}pt)"
        )


def test_report_title_is_not_outranked_by_a_section_heading(css: str) -> None:
    """The document title must not read as smaller than the sections under it."""
    title = font_size_pt(css, ".report-title")
    h1 = font_size_pt(css, "h1")
    assert title is not None and h1 is not None
    assert title >= h1, (
        f".report-title ({title}pt) must be at least as large as h1 ({h1}pt)"
    )


def test_scale_stays_sober_for_print(css: str) -> None:
    """An academic print deliverable, not a marketing page.

    The largest heading stays within a restrained ratio of the body so the
    fix cannot drift into web-sized display type.
    """
    body = font_size_pt(css, "html, body")
    h1 = font_size_pt(css, "h1")
    assert body is not None and h1 is not None
    assert h1 / body <= 1.5, (
        f"h1 is {h1 / body:.2f}x the body size; keep the print scale restrained"
    )


# ---------------------------------------------------------------------------
# The scale fix must not disturb the declared font stacks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("family", CANONICAL_SERIF)
def test_declared_font_families_are_preserved(css: str, family: str) -> None:
    assert family in css, (
        f"academic_format.yml declares {family!r}; the type scale must not "
        "change the font families"
    )


@pytest.mark.parametrize("selector", HEADING_SELECTORS)
def test_headings_declare_no_font_family_of_their_own(css: str, selector: str) -> None:
    """Headings inherit the declared stack instead of introducing a new one."""
    body = rule_body(css, selector)
    assert "font-family" not in body or "var(--serif)" in body or "var(--sans)" in body, (
        f"{selector} must reuse the declared font variables, not a new stack"
    )
