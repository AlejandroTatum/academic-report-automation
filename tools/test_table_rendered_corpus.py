"""R10/R11 rendered-corpus evidence, via the HTML/WeasyPrint preview backend.

Spec scenarios:
  R10 `test_issue_13_rendered_context_corpus`
  R11 `test_issue_13_multipage_headers_and_captions`

Renders `tests/fixtures/table_styles/corpus/six-contexts.md` (the six named
context classes from `test_issue_13_context_matrix_is_deterministic`: short,
long, comparison, status, dense, multipage) to an actual PDF via
`tools/build_report.py --pdf` (WeasyPrint), then inspects the rendered
artifact with `pdfinfo`/`pdftotext` -- not source-only assertions.

Manually verified once by rasterizing every page to PNG and reading them
(recorded in odd/tasks/contextual-table-styles.md, T5 evidence): headers
repeat correctly on every continuation page, zebra banding and column
emphasis survive the page break, long cells wrap without clipping, and
status indicators show symbol + color + label together. This file turns
that one-off visual check into an automated, re-runnable structural proxy
for it (page count, per-page header text, no page devoid of table content)
-- it does NOT replace human/contact-sheet visual inspection, which is
what the design's closure contract (`odd/tasks/contextual-table-styles.md`
Acceptance) reserves `VISUAL_PASS` for.

Skips (not fails) when WeasyPrint or poppler-utils (`pdfinfo`/`pdftotext`)
are unavailable, matching this repository's convention for optional
external tools (e.g. the LaTeX backend's own Docker fallback check).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import build_report  # noqa: E402

CORPUS = TOOLS.parent / "tests" / "fixtures" / "table_styles" / "corpus" / "six-contexts.md"
MULTIPAGE_FIXTURE = TOOLS.parent / "tests" / "fixtures" / "table_styles" / "corpus" / "multipage.md"
CSS = TOOLS.parent / "templates" / "ensayo_unl.css"

try:
    import weasyprint  # noqa: F401
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False

HAS_POPPLER = shutil.which("pdfinfo") is not None and shutil.which("pdftotext") is not None

requires_pdf_tooling = pytest.mark.skipif(
    not (HAS_WEASYPRINT and HAS_POPPLER),
    reason="WeasyPrint and/or poppler-utils (pdfinfo/pdftotext) unavailable",
)


def _page_count(pdf_path: Path) -> int:
    output = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True, check=True).stdout
    for line in output.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise AssertionError(f"pdfinfo produced no 'Pages:' line for {pdf_path}")


def _page_text(pdf_path: Path, page: int) -> str:
    return subprocess.run(
        ["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(pdf_path), "-"],
        capture_output=True, text=True, check=True,
    ).stdout


@requires_pdf_tooling
def test_issue_13_rendered_context_corpus(tmp_path: Path) -> None:
    pdf_path = tmp_path / "six-contexts.pdf"
    html = build_report.render(CORPUS, CSS, out_dir=tmp_path)
    (tmp_path / "six-contexts.html").write_text(html, encoding="utf-8")

    from weasyprint import HTML

    HTML(string=html, base_url=str(tmp_path)).write_pdf(str(pdf_path))
    assert pdf_path.exists()

    pages = _page_count(pdf_path)
    assert pages >= 3  # short+long+comparison / status+dense+multipage-start / continuation ...

    full_text = "\n".join(_page_text(pdf_path, page) for page in range(1, pages + 1))
    # Every context section heading survived rendering, legible and present.
    for heading in ("Corto", "Largo", "Comparaci", "Estado", "Denso", "Multip"):
        assert heading in full_text
    # Long cell text wrapped rather than being silently dropped or clipped.
    assert "Item-08" in full_text
    # Status indicators: symbol-adjacent label text is real, extractable
    # PDF text -- never a color-only signal (contrast is verified
    # separately, by computation, in tools/test_table_accessibility.py).
    assert "OK" in full_text and "Falla" in full_text and "Alerta" in full_text


@requires_pdf_tooling
def test_issue_13_multipage_headers_and_captions(tmp_path: Path) -> None:
    pdf_path = tmp_path / "multipage.pdf"
    html = build_report.render(MULTIPAGE_FIXTURE, CSS, out_dir=tmp_path)

    from weasyprint import HTML

    HTML(string=html, base_url=str(tmp_path)).write_pdf(str(pdf_path))
    pages = _page_count(pdf_path)
    assert pages >= 2  # 40 rows must not fit (or be truncated onto) one page

    header_hits = sum(1 for page in range(1, pages + 1) if "Código" in _page_text(pdf_path, page))
    assert header_hits == pages, (
        f"table header repeated on {header_hits}/{pages} pages -- "
        "every continuation page must show it, not just the first"
    )

    # No row is lost across the break: every item number appears exactly
    # once across the whole document.
    full_text = "\n".join(_page_text(pdf_path, page) for page in range(1, pages + 1))
    for i in range(1, 41):
        assert full_text.count(f"Item-{i:02d}") == 1, f"Item-{i:02d} missing or duplicated across the page break"
