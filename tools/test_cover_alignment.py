"""Tests for the alignment of the institutional cover.

The UNL cover is a centred stack: university, faculty, career, title, then the
AUTOR / DOCENTE / place / date block, all on the page's vertical centre axis.
The framed box carrying subject, activity type and parallel sat inside a
`flushright` group, so it hung off to the right and lined up with nothing on
the page. On a rendered A4 cover it is one of the first things a reader sees.

These tests pin the alignment, and equally pin what must *not* change: the
frame, the left-aligned text inside it, and the tuned vertical rhythm that
`cover_field()` exists to protect.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import build_latex_report  # noqa: E402

UNL_TEMPLATE = ROOT / "templates" / "unl-report.tex"


@pytest.fixture(scope="module")
def unl() -> str:
    return UNL_TEMPLATE.read_text(encoding="utf-8")


#: An unescaped `%` and everything after it on the line.
_LATEX_COMMENT = re.compile(r"(?<!\\)%.*")


def strip_comments(tex: str) -> str:
    """Drop LaTeX comments so prose about the layout is never read as layout."""
    return "\n".join(_LATEX_COMMENT.sub("", line) for line in tex.splitlines())


@pytest.fixture(scope="module")
def titlepage(unl: str) -> str:
    match = re.search(
        r"\\begin\{titlepage\}(.*?)\\end\{titlepage\}", unl, re.DOTALL
    )
    assert match, "unl-report.tex must still build a titlepage"
    return strip_comments(match.group(1))


def enclosing_alignment(tex: str, position: int) -> str | None:
    """Return the innermost alignment environment still open at `position`."""
    stack: list[str] = []
    pattern = re.compile(r"\\(begin|end)\{(center|flushright|flushleft)\}")
    for match in pattern.finditer(tex[:position]):
        if match.group(1) == "begin":
            stack.append(match.group(2))
        elif stack:
            stack.pop()
    return stack[-1] if stack else None


# ---------------------------------------------------------------------------
# The defect
# ---------------------------------------------------------------------------


def test_cover_metadata_box_is_not_pushed_to_the_right(titlepage: str) -> None:
    r"""A `flushright` group around the framed box was the misalignment."""
    assert r"\begin{flushright}" not in titlepage, (
        "the cover metadata box must not be right-aligned: it lines up with "
        "neither the centre axis nor the right margin"
    )


def test_cover_metadata_box_sits_on_the_centre_axis(titlepage: str) -> None:
    """Everything else on the cover is centred; the box must be too."""
    box = re.search(r"\\fbox\{.*?\\end\{minipage\}\s*\}", titlepage, re.DOTALL)
    assert box, "the cover must still frame the subject/activity/parallel block"
    enclosing = enclosing_alignment(titlepage, box.start())
    assert enclosing in (None, "center"), (
        "the framed box must inherit the titlepage's \\centering or sit in a "
        f"center group, not in {enclosing!r}"
    )


# ---------------------------------------------------------------------------
# What the fix must preserve
# ---------------------------------------------------------------------------


def test_the_frame_is_kept(titlepage: str) -> None:
    assert r"\fbox{" in titlepage, "the cover metadata box keeps its frame"
    assert r"\setlength{\fboxsep}{8pt}" in titlepage, "frame padding is unchanged"


def test_text_inside_the_box_stays_left_aligned(titlepage: str) -> None:
    r"""A `minipage` is left-aligned by default; nothing may re-centre it."""
    box = re.search(
        r"\\fbox\{(.*?)\\end\{minipage\}", titlepage, re.DOTALL
    )
    assert box, "the framed minipage must survive"
    inner = box.group(1)
    assert r"\centering" not in inner, (
        "the text inside the box is intentionally left-aligned"
    )
    assert r"\begin{minipage}{0.48\textwidth}" in inner, "box width is unchanged"


@pytest.mark.parametrize(
    "gap", [r"\\[0.48cm]", r"\\[1.35cm]", r"\\[0.9cm]", r"\\[1.35em]"]
)
def test_cover_vertical_rhythm_is_untouched(titlepage: str, gap: str) -> None:
    """The cover spacing is deliberately tuned; the fix must not retune it."""
    assert gap in titlepage, f"cover spacing {gap} must be preserved"


def test_the_box_keeps_its_place_in_the_stack(titlepage: str) -> None:
    """Title, then the framed box, then AUTOR — the order does not change."""
    title = titlepage.index("{{TITLE}}")
    box = titlepage.index(r"\fbox{")
    author = titlepage.index("AUTOR:")
    assert title < box < author


def test_empty_field_protection_still_applies() -> None:
    """`cover_field()` guards the sized groups the rhythm depends on."""
    assert build_latex_report.cover_field(None) != ""
    assert build_latex_report.cover_field("") != ""
