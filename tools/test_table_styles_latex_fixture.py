"""End-to-end T3 harness: the real build_latex_report.py pipeline, --tex-only.

Mirrors the harness command from odd/tasks/contextual-table-styles.md:
    .venv/bin/python tools/build_latex_report.py \\
        tests/fixtures/table_styles/sample-reports/latex --tex-only

(Named ``sample-reports/``, not ``reports/``, because ``.gitignore`` has an
unanchored ``reports/`` rule for the private content tree that would
otherwise swallow this fixture -- see odd/tasks/contextual-table-styles.md.)

The fixture is copied into ``tmp_path`` before building -- the source
fixture under tests/fixtures/ is never written to, and the real content
root is never touched (conftest.py already sandboxes it).
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import build_latex_report  # noqa: E402

FIXTURE = TOOLS.parent / "tests" / "fixtures" / "table_styles" / "sample-reports" / "latex"
GOLDEN = TOOLS.parent / "tests" / "fixtures" / "table_styles" / "golden" / "latex" / "results-summary.tex"


def _build_tex_only(tmp_path: Path) -> str:
    folder = tmp_path / "latex-fixture"
    shutil.copytree(FIXTURE, folder)
    config = build_latex_report.build(folder, compile_pdf=False)
    return config.tex_path.read_text(encoding="utf-8")


def test_fixture_report_renders_all_three_selected_styles(tmp_path: Path) -> None:
    tex = _build_tex_only(tmp_path)

    assert "% table-style: TAB-CL-01" in tex  # results-summary: plain reference table
    assert "% table-style: TAB-CE-05" in tex  # method-comparison: column emphasis
    assert "% table-style: TAB-ES-06" in tex  # status-matrix: status indicators

    # Status markers never leak into the PDF as raw authoring syntax, and
    # never rely on color alone (symbol + accessible label both present).
    assert "[[status:" not in tex
    assert "✓" in tex and "OK" in tex
    assert "✗" in tex and "Falla" in tex


def test_fixture_results_summary_table_matches_golden_fragment(tmp_path: Path) -> None:
    tex = _build_tex_only(tmp_path)
    start = tex.index("% table-style: TAB-CL-01")
    end = tex.index("% table-style: TAB-CE-05")
    fragment = tex[start:end].strip() + "\n"

    golden = GOLDEN.read_text(encoding="utf-8")
    assert fragment == golden
