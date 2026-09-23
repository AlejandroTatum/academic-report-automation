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

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import connector_geometry as cg  # noqa: E402
from visual_pdf_auditor import FAILURE, INFO  # noqa: E402

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


# --- T5: native-review hardening findings on phases 2-3 ------------------------


def test_transversal_crossing_through_a_shared_vertex_is_detected() -> None:
    """A polyline whose crossing point coincides exactly with the OTHER
    edge's vertex must not escape detection: per-segment-pair strict
    crossing alone only ever sees two endpoint-only touches there, one per
    side of the vertex, and neither alone qualifies as a strict crossing."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="260" height="100" viewBox="0 0 260 100">'
        '<defs><marker id="pointEnd" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z"/></marker></defs>'
        '<g class="node" id="my-svg-flowchart-N1-0"><rect x="150" y="0" width="10" height="10"/></g>'
        '<g class="node" id="my-svg-flowchart-N2-0"><rect x="220" y="0" width="10" height="10"/></g>'
        '<g class="node" id="my-svg-flowchart-N3-0"><rect x="190" y="-40" width="10" height="10"/></g>'
        '<g class="node" id="my-svg-flowchart-N4-0"><rect x="190" y="40" width="10" height="10"/></g>'
        '<g class="edgePaths"><path data-id="L_N1_N2_0" d="M 160 5 L 220 5" marker-end="url(#pointEnd)"/></g>'
        '<g class="edgePaths"><path data-id="L_N3_N4_0" d="M 195 -30 L 195 5 L 195 40" marker-end="url(#pointEnd)"/></g>'
        "</svg>"
    )
    issues = cg.audit_diagram(cg.parse_svg(svg))
    tags = failure_tags(issues)
    assert cg.CONNECTOR_CROSSING in tags
    details = " | ".join(i.detail for i in issues if i.tag == cg.CONNECTOR_CROSSING)
    assert "L_N1_N2_0" in details and "L_N3_N4_0" in details


def test_collinear_overlapping_segments_are_detected_as_crossing() -> None:
    """Two unrelated connectors routed along the same line for an
    overlapping stretch are a routing defect (indistinguishable overlapping
    lines), not a silent touch -- strict crossing alone excludes every
    collinear case, including a genuine nonzero-length overlap."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="150" height="60" viewBox="0 0 150 60">'
        '<defs><marker id="pointEnd" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z"/></marker></defs>'
        '<g class="node" id="my-svg-flowchart-N1-0"><rect x="0" y="4" width="10" height="1"/></g>'
        '<g class="node" id="my-svg-flowchart-N2-0"><rect x="140" y="5" width="10" height="1"/></g>'
        '<g class="node" id="my-svg-flowchart-N3-0"><rect x="40" y="54" width="10" height="1"/></g>'
        '<g class="node" id="my-svg-flowchart-N4-0"><rect x="100" y="54" width="10" height="1"/></g>'
        '<g class="edgePaths"><path data-id="L_N1_N2_0" d="M 5 5 L 5 30 L 145 30 L 145 5" marker-end="url(#pointEnd)"/></g>'
        '<g class="edgePaths"><path data-id="L_N3_N4_0" d="M 45 55 L 45 30 L 105 30 L 105 55" marker-end="url(#pointEnd)"/></g>'
        "</svg>"
    )
    issues = cg.audit_diagram(cg.parse_svg(svg))
    tags = failure_tags(issues)
    assert cg.CONNECTOR_CROSSING in tags
    details = " | ".join(i.detail for i in issues if i.tag == cg.CONNECTOR_CROSSING)
    assert "L_N1_N2_0" in details and "L_N3_N4_0" in details


def test_cluster_label_region_has_no_owner_id() -> None:
    """``ProtectedRegion``'s own documented contract: ``owner_id`` is empty
    for cluster/legend/annotation regions, which no connector owns. A
    cluster's own id is bookkeeping only, never a legitimate adjacency."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">'
        '<g class="cluster" id="my-svg-cluster-A">'
        '<g class="cluster-label" transform="translate(5,5)">'
        '<foreignObject width="20" height="10"></foreignObject>'
        "</g></g></svg>"
    )
    diagram = cg.parse_svg(svg)
    assert len(diagram.regions) == 1
    assert diagram.regions[0].owner_id == ""


# --- T1 (#43): undirected links declared in the .mmd source -------------------


def test_parse_link_directions_classifies_declared_link_types() -> None:
    """Only a bare open/dotted/thick link -- with or without a label -- is
    undirected; anything carrying an arrowhead (>, <, o, x) stays directed,
    regardless of an inline label or free-text segment."""
    text = (
        "flowchart LR\n"
        "  A[A] --- B[B]\n"
        "  A -.- C[C]\n"
        "  A === D[D]\n"
        "  A --> E[E]\n"
        "  A -->|label| F[F]\n"
        "  A -- text --- G[G]\n"
        "  A -. text .-> H[H]\n"
    )
    directions = cg.parse_link_directions(text)
    assert directions[("A", "B")] == [False]
    assert directions[("A", "C")] == [False]
    assert directions[("A", "D")] == [False]
    assert directions[("A", "E")] == [True]
    assert directions[("A", "F")] == [True]
    assert directions[("A", "G")] == [False]
    assert directions[("A", "H")] == [True]


def test_undirected_link_declared_in_source_skips_direction_check() -> None:
    """A real mmdc capture of ``A --- B`` (no end marker at all) must not
    fail direction when its ``.mmd`` sibling declares it undirected; the
    ``A --> C`` arrow in the same diagram keeps the full check."""
    svg = FIXTURES / "mmdc-undirected-clean.svg"
    issues = cg.audit_connector_geometry(svg)
    assert cg.CONNECTOR_DIRECTION not in failure_tags(issues)


def test_undirected_link_without_source_falls_back_to_strict() -> None:
    """The same ``A --- B`` shape, audited without its ``.mmd`` sibling
    present, still fails under the pre-#43 strict rule -- and the fallback
    itself is reported as an informational finding naming the figure."""
    svg = FIXTURES / "mmdc-undirected-clean.svg"
    text = svg.read_text(encoding="utf-8")
    diagram = cg.parse_svg(text)
    issues = cg.audit_diagram(diagram, link_directions=None)
    assert cg.CONNECTOR_DIRECTION in failure_tags(issues)


def test_no_sibling_source_reports_strict_mode_informational_finding() -> None:
    """A figure with no ``.mmd`` next to it keeps the strict direction rule
    and says so, instead of silently behaving differently from a sourced
    figure with no way to tell the two apart."""
    issues = cg.audit_connector_geometry(FIXTURES / "mmdc-direction-clean.svg")
    info = [i for i in issues if i.tag == cg.CONNECTOR_DIRECTION_NO_SOURCE]
    assert len(info) == 1
    assert info[0].level == INFO
    assert "mmdc-direction-clean.svg" in info[0].detail


def test_mirrored_specs_tree_source_is_found_when_no_sibling_exists(tmp_path) -> None:
    """The real pipeline renders under ``assets/generated/<materia>/<tarea>/``
    and keeps specs under ``visuals/specs/<materia>/<tarea>/`` -- not
    siblings. Without this mirror, the #43 T1 decision never applies to a
    real run: the lookup must also try the mirrored specs path, same
    relative subpath and stem, before falling back to strict."""
    svg_dir = tmp_path / "assets" / "generated" / "materia" / "tarea"
    svg_dir.mkdir(parents=True)
    spec_dir = tmp_path / "visuals" / "specs" / "materia" / "tarea"
    spec_dir.mkdir(parents=True)
    svg_path = svg_dir / "diagram.svg"
    svg_path.write_text((FIXTURES / "mmdc-undirected-clean.svg").read_text(encoding="utf-8"), encoding="utf-8")
    (spec_dir / "diagram.mmd").write_text(
        (FIXTURES / "mmdc-undirected-clean.mmd").read_text(encoding="utf-8"), encoding="utf-8"
    )

    issues = cg.audit_connector_geometry(svg_path)
    assert cg.CONNECTOR_DIRECTION not in failure_tags(issues)
    assert cg.CONNECTOR_DIRECTION_NO_SOURCE not in {i.tag for i in issues}


def test_sibling_source_takes_priority_over_the_mirrored_specs_tree(tmp_path) -> None:
    """When both exist, the sibling ``.mmd`` (cheaper, no path surgery)
    wins -- the mirrored specs tree is a fallback, not a replacement."""
    svg_dir = tmp_path / "assets" / "generated" / "materia" / "tarea"
    svg_dir.mkdir(parents=True)
    spec_dir = tmp_path / "visuals" / "specs" / "materia" / "tarea"
    spec_dir.mkdir(parents=True)
    svg_path = svg_dir / "diagram.svg"
    svg_path.write_text((FIXTURES / "mmdc-undirected-clean.svg").read_text(encoding="utf-8"), encoding="utf-8")
    # Sibling declares everything directed (no undirected links at all);
    # the mirrored spec (if wrongly preferred) would exempt L_A_B_0.
    (svg_dir / "diagram.mmd").write_text("flowchart LR\n  A --> B\n  A --> C\n", encoding="utf-8")
    (spec_dir / "diagram.mmd").write_text(
        (FIXTURES / "mmdc-undirected-clean.mmd").read_text(encoding="utf-8"), encoding="utf-8"
    )

    issues = cg.audit_connector_geometry(svg_path)
    assert cg.CONNECTOR_DIRECTION in failure_tags(issues)


def test_multiple_links_between_same_pair_match_by_ordinal() -> None:
    """Two links between the same nodes -- one arrowed, one open -- must map
    onto the right SVG edge each, not both-or-neither: mmdc assigns the
    second link's ordinal out of declaration order (``_0`` then ``_2``, not
    ``_1``), so matching has to go by each pair's own relative position, not
    the raw ordinal value."""
    svg = FIXTURES / "mmdc-undirected-multi.svg"
    issues = cg.audit_connector_geometry(svg)
    direction_issues = [i for i in issues if i.tag == cg.CONNECTOR_DIRECTION]
    # L_A_F_0 (the declared arrow) must still be checked and pass; L_A_F_2
    # (the declared open link) must be exempt from the missing-marker rule.
    assert not any("L_A_F_2" in i.detail for i in direction_issues)


# --- T2 (#43): one shared guard for any geometry exception ---------------------


def test_malformed_path_data_raises_indexerror_uncaught() -> None:
    """Documents the underlying defect ``run_geometry_audit`` exists to
    guard against: an odd count of coordinate numbers in a path's ``d``
    (routine corruption, not a contrived input) crashes the parser itself
    with an ``IndexError``, not a ``PageIssue``."""
    with pytest.raises(IndexError):
        cg.audit_connector_geometry(FIXTURES / "mmdc-malformed-indexerror.svg")


def test_run_geometry_audit_converts_indexerror_into_a_finding() -> None:
    """The shared guard turns that same crash into one reported finding
    naming the figure, instead of propagating it."""
    svg = FIXTURES / "mmdc-malformed-indexerror.svg"
    issues = cg.run_geometry_audit(svg.name, lambda: cg.audit_connector_geometry(svg))
    assert failure_tags(issues) == {cg.CONNECTOR_AUDIT_ERROR}
    assert svg.name in issues[0].detail
    assert "IndexError" in issues[0].detail


def test_run_geometry_audit_passes_through_a_clean_result() -> None:
    """No exception, no guard finding -- the underlying audit's own result
    passes through unchanged."""
    svg = FIXTURES / "mmdc-clean.svg"
    assert cg.run_geometry_audit(svg.name, lambda: cg.audit_connector_geometry(svg)) == cg.audit_connector_geometry(svg)


# --- T3 (#43): necessary-crossing exemption, conservative ---------------------


def test_k3_3_style_forced_crossing_is_exempt() -> None:
    """Two diagonal connectors between four corner nodes sealed to the
    diagram's own viewBox: N1/N4's corner regions have no way to reach each
    other other than through the diagonal L_N2_N3 occupies, corner to
    corner -- an obstacle-aware visibility check proves it, so the crossing
    is exempt (#43 T3), unlike every other crossing in this suite."""
    issues = cg.audit_connector_geometry(FIXTURES / "mmdc-crossing-necessary.svg")
    assert cg.CONNECTOR_CROSSING not in failure_tags(issues)


def test_avoidable_crossing_still_fails_despite_open_space() -> None:
    """The same diagonal-crossing shape, given generous open margin around
    it, has an obvious way around -- the gate must find it and keep failing
    the crossing, not just exempt every diagonal pair on sight."""
    issues = cg.audit_connector_geometry(FIXTURES / "mmdc-crossing-avoidable.svg")
    assert cg.CONNECTOR_CROSSING in failure_tags(issues)


def test_existing_crossing_fixtures_stay_unexempt() -> None:
    """The pre-#43 always-fail fixtures must not become collateral
    exemptions: an open, unsealed crossing (a real route around exists, or
    the proof is otherwise inconclusive) still fails, exactly as before."""
    assert cg.CONNECTOR_CROSSING in failure_tags(cg.audit_connector_geometry(FIXTURES / "mmdc-crossing-bad.svg"))


def test_inconclusive_proof_keeps_failing_past_the_vertex_budget() -> None:
    """When the obstacle count would blow up the visibility-graph state
    past MAX_VISIBILITY_VERTICES, the proof is inconclusive -- and an
    inconclusive proof must never grant the exemption, the same safe
    default as finding an actual route."""
    edge = cg.Edge("L_A_B_0", "A", "B", [(0.0, 0.0), (100.0, 100.0)], "pointEnd")
    other = cg.Edge("L_C_D_0", "C", "D", [(0.0, 100.0), (100.0, 0.0)], "pointEnd")
    # 20 obstacle nodes (80 corners) plus the two endpoints comfortably
    # exceeds MAX_VISIBILITY_VERTICES.
    obstacles = [cg.Node(f"N{i}", float(i), float(i), float(i) + 1, float(i) + 1) for i in range(20)]
    diagram = cg.Diagram(
        nodes=[cg.Node("A", -1, -1, 0, 0), cg.Node("B", 100, 100, 101, 101), *obstacles],
        edges=[edge, other],
        markers={"pointEnd": "auto"},
        regions=[],
        parse_issues=[],
        bounds=(-10.0, -10.0, 110.0, 110.0),
    )
    assert cg._has_alternative_route(edge.points[0], edge.points[-1], [(n.x0, n.y0, n.x1, n.y1) for n in obstacles], other, diagram.bounds) is None
    assert cg._crossing_is_provably_necessary(diagram, edge, other) is False


# --- Native review hardening (#43, post-delivery) ------------------------------


def test_alternative_route_around_blockers_tip_is_found() -> None:
    """R3-visibility-graph-omits-blocker-vertices: with zero other
    obstacles, a detour around EITHER end of the blocking connector
    trivially exists in the open plane -- the visibility graph must
    include the blocker's own vertices as candidate waypoints, or it has
    nothing to route around its tip with and wrongly concludes "no
    alternative route" (a false, fail-open exemption)."""
    e1 = cg.Edge("L_A_B_0", "A", "B", [(10.0, 10.0), (90.0, 90.0)], "pointEnd")
    e2 = cg.Edge("L_C_D_0", "C", "D", [(40.0, 60.0), (60.0, 40.0)], "pointEnd")
    diagram = cg.Diagram(
        nodes=[cg.Node("A", 5.0, 5.0, 15.0, 15.0), cg.Node("B", 85.0, 85.0, 95.0, 95.0)],
        edges=[e1, e2],
        markers={"pointEnd": "auto"},
        regions=[],
        parse_issues=[],
        bounds=(0.0, 0.0, 100.0, 100.0),
    )
    assert cg._crossing_is_provably_necessary(diagram, e1, e2) is False
    assert cg.CONNECTOR_CROSSING in failure_tags(cg.crossing_issues(diagram))


def test_no_declared_bounds_is_inconclusive_not_a_false_exemption() -> None:
    """R2-no-bounds-inconclusive-contradiction: the module's own docstring
    says "no bounds to reason within" is one of the inconclusive cases, but
    an undeclared viewBox used to fall through to an effectively unbounded
    search instead of actually returning the documented inconclusive
    result -- silently granting an exemption the decision never proves
    (the #43 T3 rule only reasons "within the diagram's own bounds")."""
    e1 = cg.Edge("L_A_B_0", "A", "B", [(10.0, 10.0), (90.0, 90.0)], "pointEnd")
    e2 = cg.Edge("L_C_D_0", "C", "D", [(40.0, 60.0), (60.0, 40.0)], "pointEnd")
    assert cg._has_alternative_route(e1.points[0], e1.points[-1], [], e2, None) is None
    diagram = cg.Diagram(
        nodes=[cg.Node("A", 5.0, 5.0, 15.0, 15.0), cg.Node("B", 85.0, 85.0, 95.0, 95.0)],
        edges=[e1, e2],
        markers={"pointEnd": "auto"},
        regions=[],
        parse_issues=[],
        bounds=None,
    )
    assert cg._crossing_is_provably_necessary(diagram, e1, e2) is False


def test_link_regex_does_not_mistake_ox_prefixed_target_for_a_terminator() -> None:
    """R3-link-regex-o-x-node-prefix: a target id that merely STARTS with
    'o' or 'x' (``ox``, ``xray``) must parse as that whole id, not as a
    circle/cross line terminator swallowing the id's first letter."""
    directions = cg.parse_link_directions("flowchart LR\n  A --- ox\n  A --> xray\n")
    assert ("A", "ox") in directions
    assert directions[("A", "ox")] == [False]
    assert ("A", "xray") in directions
    assert directions[("A", "xray")] == [True]


def test_unreadable_mmd_source_falls_back_to_strict_mode(tmp_path) -> None:
    """R4-mmd-read-failure-masks-geometry-audit: an unreadable/undecodable
    ``.mmd`` (not merely a missing one) must not raise past
    ``load_link_directions`` and abort or mask the whole geometry audit --
    it must fall back to strict mode with the same informational finding a
    genuinely missing source gets."""
    svg_path = tmp_path / "diagram.svg"
    svg_path.write_text(
        (FIXTURES / "mmdc-undirected-clean.svg").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "diagram.mmd").write_bytes(b"\xff\xfe\x00not valid utf-8")

    assert cg.load_link_directions(svg_path) is None
    issues = cg.audit_connector_geometry(svg_path)
    assert cg.CONNECTOR_AUDIT_ERROR not in failure_tags(issues)
    assert cg.CONNECTOR_DIRECTION in failure_tags(issues)  # strict fallback: L_A_B_0 has no end marker
    info = [i for i in issues if i.tag == cg.CONNECTOR_DIRECTION_NO_SOURCE]
    assert len(info) == 1
