"""Doc-asserts for the README Markdown compatibility note (issue #7).

The note must name every backend that consumes Markdown — LaTeX, DOCX and HTML
— and document what a ``---`` line does in each. Issue #7 was filed because the
DOCX backend was missing from the note even though ``build_docx_report.py``
already turns ``^-{3,}$`` into a page break.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"


def _compatibility_note() -> str:
    """Return the body of the README's Markdown compatibility note section."""
    lines = README.read_text(encoding="utf-8").splitlines()
    starts = [
        index
        for index, line in enumerate(lines)
        if line.startswith("### Markdown compatibility note")
    ]
    assert starts, "README must keep a Markdown compatibility note section"
    start = starts[0]
    ends = [
        index
        for index in range(start + 1, len(lines))
        if lines[index].startswith("## ")
    ]
    end = ends[0] if ends else len(lines)
    return "\n".join(lines[start + 1 : end])


def _bullet_text(note: str, marker: str) -> str:
    """Return one markdown bullet as a single line, joined across wraps."""
    lines = note.splitlines()
    start = next(index for index, line in enumerate(lines) if marker in line)
    parts = [lines[start]]
    for line in lines[start + 1 :]:
        if line.lstrip().startswith("- ") or not line.strip():
            break
        parts.append(line)
    return " ".join(parts)


def test_readme_names_three_markdown_consumers() -> None:
    """LaTeX, DOCX and HTML must all appear as Markdown consumers in the note."""
    note = _compatibility_note()
    for backend in ("LaTeX", "DOCX", "HTML"):
        assert backend in note, (
            f"the compatibility note must name {backend} as a Markdown consumer"
        )


def test_readme_documents_docx_page_break_claim() -> None:
    """The DOCX bullet must say a --- line becomes a page break."""
    note = _compatibility_note()
    docx_bullet = _bullet_text(note, "build_docx_report.py")
    assert "page break" in docx_bullet, (
        "the DOCX bullet must document that `---` triggers a page break"
    )


def test_readme_keeps_latex_and_html_consumer_claims() -> None:
    """The existing LaTeX and HTML claims must stay documented."""
    note = _compatibility_note()
    latex_bullet = _bullet_text(note, "build_latex_report.py")
    html_bullet = _bullet_text(note, "build_report.py")
    assert "page break" in latex_bullet, "the LaTeX bullet must keep its page break"
    assert "front-matter" in html_bullet, "the HTML bullet must keep its front-matter"
