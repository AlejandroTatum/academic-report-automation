"""Strict-TDD tests for renderer-faithful connector parsing (issue #10, slice 1).

The parser must decode real ``mmdc`` SVG output: flat ``g.edgePaths`` carrying
``data-id="L_<source>_<target>_<ordinal>"``, base64 ``data-points`` route JSON
and ``marker-end`` references, with endpoint identity resolved against node
labels. Captured corpus (no mmdc binary, no network): ``mmdc-clean.svg`` is
genuine mmdc 11.14.0 output for a clean flow (A -> B, A -> C) and must stay
silent; ``github-workflow-page4.svg`` is the renderer-captured Git/GitHub
workflow defect from report page 4 (issue #10) — the red return connectors
pass through the ``Corregir y subir`` (FIX) and ``Resolver`` (RS) blocks.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import connector_geometry as cg  # noqa: E402
from visual_pdf_auditor import FAILURE  # noqa: E402

FIXTURES = TOOLS / "fixtures" / "connector_geometry"


def failure_tags(issues: list[cg.PageIssue]) -> set[str]:
    return {i.tag for i in issues if i.level == FAILURE}


# --- R1: real mmdc captures are parsed faithfully ---------------------------
def test_real_mmdc_flat_edges_are_parsed() -> None:
    flow = cg.parse_svg((FIXTURES / "github-workflow-page4.svg").read_text(encoding="utf-8"))
    assert flow.parse_issues == []
    assert {(e.id, e.source, e.target) for e in flow.edges} == {
        ("L_WD_STG_0", "WD", "STG"), ("L_STG_CM_0", "STG", "CM"), ("L_PR_REV_0", "PR", "REV"),
        ("L_REV_CONF_0", "REV", "CONF"), ("L_CONF_MG_0", "CONF", "MG"), ("L_MG_MAIN_0", "MG", "MAIN"),
        ("L_CM_PR_0", "CM", "PR"), ("L_MAIN_WD_0", "MAIN", "WD"), ("L_REV_FIX_0", "REV", "FIX"),
        ("L_FIX_PR_0", "FIX", "PR"), ("L_CONF_RS_0", "CONF", "RS"), ("L_RS_CONF_0", "RS", "CONF"),
    }
    assert all(len(e.points) >= 2 for e in flow.edges)
    assert all(e.marker_end == "my-svg_flowchart-v2-pointEnd" for e in flow.edges)
    assert flow.markers["my-svg_flowchart-v2-pointEnd"] == "auto"
    clean = cg.parse_svg((FIXTURES / "mmdc-clean.svg").read_text(encoding="utf-8"))
    assert clean.parse_issues == []
    assert {n.id for n in clean.nodes} == {"A", "B", "C"}
    assert {(e.id, e.source, e.target) for e in clean.edges} == {
        ("L_A_B_0", "A", "B"), ("L_A_C_0", "A", "C"),
    }


def test_real_mmdc_clean_capture_is_silent() -> None:
    """The clean real capture produces no connector failure."""
    assert failure_tags(cg.audit_connector_geometry(FIXTURES / "mmdc-clean.svg")) == set()


# --- Known-defect regression: page-4 return connectors through blocks -------
# The PR1 runtime harness requires github-workflow-page4.svg to fail validation.


def test_real_mmdc_known_defect_return_connector_fails() -> None:
    """The page-4 return connectors pass through FIX/RS blocks and must fail."""
    issues = cg.audit_connector_geometry(FIXTURES / "github-workflow-page4.svg")
    assert cg.CONNECTOR_THROUGH_NODE in failure_tags(issues)
    details = " | ".join(i.detail for i in issues)
    assert "passes through node 'RS'" in details and "L_RS_CONF_0" in details
    assert "passes through node 'FIX'" in details and "L_FIX_PR_0" in details


# --- parse evidence triangulation: malformed identity/endpoints block -------


def test_malformed_flat_edge_id_is_blocking_parse_evidence() -> None:
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">'
           '<g class="edgePaths"><path data-id="not-an-edge-id" d="M 0 0 L 10 10"/></g></svg>')
    diagram = cg.parse_svg(svg)
    assert any(i.tag == cg.CONNECTOR_PARSE and "not-an-edge-id" in i.detail for i in diagram.parse_issues)


def test_unresolved_edge_endpoint_is_blocking_parse_evidence() -> None:
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">'
           '<g class="nodes"><g class="node" id="A"><rect x="0" y="0" width="10" height="10"/></g></g>'
           '<g class="edgePaths"><path data-id="L_A_GHOST_0" d="M 10 5 L 50 5"/></g></svg>')
    diagram = cg.parse_svg(svg)
    assert any(i.tag == cg.CONNECTOR_PARSE and "GHOST" in i.detail for i in diagram.parse_issues)
