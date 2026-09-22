"""Strict-TDD tests for renderer-faithful connector parsing (issue #10, slice 1).

The parser must decode real ``mmdc`` SVG output: flat ``g.edgePaths`` carrying
``data-id="L_<source>_<target>_<ordinal>"``, base64 ``data-points`` route JSON
and ``marker-end`` references, with endpoint identity resolved against node
labels. Captured corpus (no mmdc binary, no network): ``mmdc-clean.svg`` is
genuine mmdc 11.14.0 output for a clean flow (A -> B, A -> C) and must stay
silent; ``github-workflow-page4.svg`` is the renderer-captured Git/GitHub
workflow defect from report page 4 (issue #10) — the red return connectors
pass through the ``Corregir y subir`` (FIX) and ``Resolver`` (RS) blocks.

Slice 2 (R2-R6) covers protected regions, crossings, minimum clearance,
source/target/direction, actionable evidence, and chart silence. Real mmdc
never emits these defects on its own layout, so every slice-2 fixture is a
synthetic SVG mirroring the DOM shape the parser above already handles
(``g.node``/``g.edgePaths``/``g.edgeLabel``/``g.cluster``/``g.cluster-label``,
plus synthetic ``g.legend``/``g.annotation`` groups); their construction is
verified against this module before being checked in.
"""
from __future__ import annotations

import re
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


# --- R2: protected regions (node text, edge text, cluster label, legend, annotation) ----


def test_connector_through_protected_regions_fails() -> None:
    """Synthetic fixture (see module docstring) — mmdc flowcharts never emit a
    defect on their own; each unrelated connector crosses one region kind."""
    issues = cg.audit_connector_geometry(FIXTURES / "mmdc-protected-bad.svg")
    assert cg.CONNECTOR_THROUGH_REGION in failure_tags(issues)
    details = " | ".join(i.detail for i in issues if i.tag == cg.CONNECTOR_THROUGH_REGION)
    for expected in (
        "node_text 'N1-text'", "edge_text 'L_EA_EB_0-label'",
        "cluster_label 'CL1'", "legend 'LEGEND1'", "annotation 'NOTE1'",
    ):
        assert expected in details, details


def test_adjacent_labels_and_clear_routes_pass() -> None:
    """A connector may touch only its own label/region; unrelated regions
    left untouched by any route stay silent."""
    assert failure_tags(cg.audit_connector_geometry(FIXTURES / "mmdc-protected-clean.svg")) == set()


# --- R3: necessary routing and crossings -------------------------------------


def test_unnecessary_connector_crossing_fails() -> None:
    issues = cg.audit_connector_geometry(FIXTURES / "mmdc-crossing-bad.svg")
    assert cg.CONNECTOR_CROSSING in failure_tags(issues)
    details = " | ".join(i.detail for i in issues if i.tag == cg.CONNECTOR_CROSSING)
    assert "L_N1_N2_0" in details and "L_N3_N4_0" in details


def test_shared_endpoint_and_touching_are_not_crossings() -> None:
    """Two edges sharing a source, plus two unrelated edges meeting at exactly
    one vertex, are neither a crossing nor a clearance defect."""
    assert failure_tags(cg.audit_connector_geometry(FIXTURES / "mmdc-touching-clean.svg")) == set()


# --- R4: minimum clearance ----------------------------------------------------


def test_minimum_clearance_to_edges_and_regions_fails() -> None:
    issues = cg.audit_connector_geometry(FIXTURES / "mmdc-clearance-bad.svg")
    assert cg.CONNECTOR_CLEARANCE in failure_tags(issues)
    details = " | ".join(i.detail for i in issues if i.tag == cg.CONNECTOR_CLEARANCE)
    assert "0.500 SVG units from edge 'L_N3_N4_0' (minimum 0.8)" in details
    assert "0.300 SVG units from node 'N5' (minimum 0.8)" in details


def test_exact_or_greater_clearance_passes() -> None:
    """Pairs separated by exactly the 0.80 SVG-unit minimum stay silent."""
    assert failure_tags(cg.audit_connector_geometry(FIXTURES / "mmdc-clearance-clean.svg")) == set()


# --- R5: endpoints and direction ----------------------------------------------


def test_source_target_and_direction_defects_fail() -> None:
    issues = cg.audit_connector_geometry(FIXTURES / "mmdc-direction-bad.svg")
    tags = failure_tags(issues)
    assert cg.CONNECTOR_DIRECTION in tags
    details = " | ".join(i.detail for i in issues if i.tag == cg.CONNECTOR_DIRECTION)
    assert "L_N1_N2_0' starts off its declared source 'N1'" in details
    assert "L_N3_N4_0' ends off its declared target 'N4'" in details
    assert "L_N5_N6_0' has no end marker" in details
    assert "L_N7_N8_0' end marker 'ghostMarker' is dangling" in details
    assert "L_N9_N10_0' end marker 'badOrient' orientation is not auto" in details


def test_valid_source_target_and_direction_pass() -> None:
    assert failure_tags(cg.audit_connector_geometry(FIXTURES / "mmdc-direction-clean.svg")) == set()


# --- R6: actionable evidence and chart silence --------------------------------


def test_connector_failure_evidence_is_actionable() -> None:
    """Every failure names the connector, the failure class, the affected
    counterpart, and — for clearance — the measured/required geometry."""
    issues = cg.audit_connector_geometry(FIXTURES / "mmdc-protected-bad.svg")
    region_issue = next(i for i in issues if i.tag == cg.CONNECTOR_THROUGH_REGION and "node_text" in i.detail)
    assert "L_N2_N3_0" in region_issue.detail and "node_text" in region_issue.detail and "N1-text" in region_issue.detail

    clearance_issues = cg.audit_connector_geometry(FIXTURES / "mmdc-clearance-bad.svg")
    clearance_issue = next(i for i in clearance_issues if i.tag == cg.CONNECTOR_CLEARANCE)
    assert re.search(r"L_\w+_\w+_\d+.*\d+\.\d+ SVG units from .* \(minimum 0\.8\)", clearance_issue.detail)


def test_clean_chart_without_connectors_is_silent() -> None:
    """A chart SVG with no diagram nodes/edges never trips the connector gate."""
    assert failure_tags(cg.audit_connector_geometry(FIXTURES / "mmdc-chart-clean.svg")) == set()


# --- T4: native-review hardening findings on the T1 parser --------------------


def test_edge_ids_with_underscored_node_labels_resolve() -> None:
    """A node label containing its own underscore (e.g. ``my_node``, a valid
    Mermaid id) must not hard-fail L_<source>_<target>_<ordinal> parsing."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">'
        '<g class="nodes">'
        '<g class="node" id="my-svg-flowchart-my_node-0"><rect x="0" y="0" width="10" height="10"/></g>'
        '<g class="node" id="my-svg-flowchart-your_node-1"><rect x="50" y="0" width="10" height="10"/></g>'
        "</g>"
        '<g class="edgePaths"><path data-id="L_my_node_your_node_0" d="M 10 5 L 50 5" marker-end="url(#pointEnd)"/></g>'
        "</svg>"
    )
    diagram = cg.parse_svg(svg)
    assert diagram.parse_issues == []
    assert {(e.id, e.source, e.target) for e in diagram.edges} == {("L_my_node_your_node_0", "my_node", "your_node")}


def test_sample_path_supports_relative_and_line_only_commands() -> None:
    """Relative m/l and the H/V/Z line-only commands must not corrupt the
    current point for whatever draws after them."""
    assert cg.sample_path("M 5 5 l 10 0 L 25 5") == [(5.0, 5.0), (15.0, 5.0), (25.0, 5.0)]
    assert cg.sample_path("M 0 0 H 10 V 10 Z") == [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 0.0)]


def test_circle_node_shape_is_resolved() -> None:
    """A circle-shaped node (start/end states, some flowchart shapes) must
    resolve to a bounding box, not be silently dropped as an unrecognized shape."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">'
        '<g class="nodes"><g class="node" id="my-svg-flowchart-C-0">'
        '<circle cx="50" cy="50" r="20"/></g></g></svg>'
    )
    diagram = cg.parse_svg(svg)
    assert len(diagram.nodes) == 1
    node = diagram.nodes[0]
    assert (node.x0, node.y0, node.x1, node.y1) == (30.0, 30.0, 70.0, 70.0)


def test_multi_segment_endpoint_graze_is_exempt() -> None:
    """A graze contiguous from the true source/target, spanning more than one
    polyline segment (routine for a curved departure), must total against
    CONTACT_EPS as one run -- not be checked segment-by-segment, which would
    flag the second segment as a fresh, unrelated traversal."""
    assert failure_tags(cg.audit_connector_geometry(FIXTURES / "mmdc-graze-clean.svg")) == set()


def test_multi_segment_graze_beyond_epsilon_still_fails() -> None:
    """The same contiguous-run rule must not become a loophole: a multi-segment
    graze that totals beyond CONTACT_EPS is still a traversal."""
    assert cg.CONNECTOR_THROUGH_NODE in failure_tags(cg.audit_connector_geometry(FIXTURES / "mmdc-graze-bad.svg"))
