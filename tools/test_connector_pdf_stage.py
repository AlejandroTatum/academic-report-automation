"""Strict-TDD tests for the final-print-size connector audit (issue #10, slice 3).

Scope note (see connector_pdf_stage.py's module docstring): this pipeline
records no per-figure placement receipt (final page number, exact PDF box,
PDF hash) anywhere, and there is no cheap, stdlib-only way to recover one
post-compile. This stage instead recomputes the same closed-form print-scale
formula ``build_latex_report.py`` already applies at ``\\includegraphics``
time, against the active template's own geometry, and audits connector
clearance in that final PDF-point space. ``mmdc-final-clearance-bad.svg`` and
``mmdc-final-clearance-clean.svg`` are synthetic (see
``test_connector_geometry.py``'s module docstring for why); both keep the same
isolated 0.80/6.0-SVG-unit gap, spread across a realistically wide (900-unit)
canvas so the print-scale shrink actually changes the final-stage verdict.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import connector_geometry as cg  # noqa: E402
import connector_pdf_stage as cps  # noqa: E402
from visual_pdf_auditor import FAILURE  # noqa: E402

FIXTURES = TOOLS / "fixtures" / "connector_geometry"
TEMPLATE = (TOOLS.parent / "templates" / "unl-report.tex").read_text(encoding="utf-8")


def failure_tags(issues) -> set[str]:
    return {i.tag for i in issues if i.level == FAILURE}


def test_isolated_pass_final_pdf_defect_blocks_visual_pass() -> None:
    """A connector pair that clears the isolated 0.80 SVG-unit minimum can
    still fail once the diagram is shrunk to its actual print size."""
    svg = FIXTURES / "mmdc-final-clearance-bad.svg"
    isolated = cg.audit_connector_geometry(svg)
    assert failure_tags(isolated) == set(), "fixture must pass the isolated stage"

    issues = cps.audit_svg_at_final_size(svg, TEMPLATE)
    assert cg.CONNECTOR_CLEARANCE in failure_tags(issues)
    details = " | ".join(i.detail for i in issues if i.tag == cg.CONNECTOR_CLEARANCE)
    assert "at final print size (minimum 2.0pt)" in details


def test_known_github_workflow_defect_regression() -> None:
    """The renderer-captured Git/GitHub page-4 defect (issue #10) must still
    fail at final print size — obstruction is scale-invariant, so isolated
    enforcement is never a substitute for the independent final-stage run."""
    svg = FIXTURES / "github-workflow-page4.svg"
    issues = cps.audit_svg_at_final_size(svg, TEMPLATE)
    assert cg.CONNECTOR_THROUGH_NODE in failure_tags(issues)
    details = " | ".join(i.detail for i in issues if i.tag == cg.CONNECTOR_THROUGH_NODE)
    assert "passes through node 'RS'" in details and "L_RS_CONF_0" in details
    assert "passes through node 'FIX'" in details and "L_FIX_PR_0" in details


def test_clean_isolated_and_final_pdf_can_pass_connector_gate() -> None:
    """A comfortably-clear diagram passes both stages — the final-size rule
    is not a stricter blanket threshold, only a scale-aware one."""
    svg = FIXTURES / "mmdc-final-clearance-clean.svg"
    assert failure_tags(cg.audit_connector_geometry(svg)) == set()
    assert failure_tags(cps.audit_svg_at_final_size(svg, TEMPLATE)) == set()


# --- T1 (#43): undirected links stay exempt at final print size too -----------


def test_undirected_link_declared_in_source_skips_direction_check_at_final_size() -> None:
    """The same ``.mmd``-declared undirected link stays exempt when the
    diagram is re-audited at final print scale, not just in isolation."""
    svg = FIXTURES / "mmdc-undirected-clean.svg"
    issues = cps.audit_svg_at_final_size(svg, TEMPLATE)
    assert cg.CONNECTOR_DIRECTION not in failure_tags(issues)


def test_no_sibling_source_reports_strict_mode_informational_finding_at_final_size() -> None:
    """A figure with no ``.mmd`` next to it keeps reporting the strict-mode
    fallback at final print size too, not just in the isolated precheck."""
    issues = cps.audit_svg_at_final_size(FIXTURES / "mmdc-direction-clean.svg", TEMPLATE)
    info = [i for i in issues if i.tag == cg.CONNECTOR_DIRECTION_NO_SOURCE]
    assert len(info) == 1
    assert "mmdc-direction-clean.svg" in info[0].detail
