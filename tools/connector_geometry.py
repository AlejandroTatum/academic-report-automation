#!/usr/bin/env python3
"""Renderer-faithful connector parsing and node-obstruction audit (issue #10).

Parses real ``mmdc`` SVG output into a geometry model (no mmdc binary, no
network, no pixels) and audits it deterministically. Real Mermaid CLI output:
nodes as ``<g class="node" id="my-svg-flowchart-WD-0">`` (label inside the id),
edges as flat ``<path data-id="L_<source>_<target>_<ordinal>">`` under
``g.edgePaths`` carrying the routed polyline in base64 ``data-points`` JSON
and ``marker-end`` references; markers live in ``<defs>`` with
``orient="auto"``. Endpoint identity resolves from the edge id against node
labels; wrapper ``data-source``/``data-target`` groups remain secondary
compatibility. Malformed points, ambiguous ids and unresolved endpoints are
blocking parse evidence (``CONNECTOR_PARSE``), never silent omissions.

Slice 1 audits one geometric defect: a connector traversing a node it does not
belong to (``CONNECTOR_THROUGH_NODE``). Source/target regions are exempt ONLY
at their endpoint contact point — the page-4 Git/GitHub return connectors pass
through the ``Corregir y subir`` and ``Resolver`` blocks exactly this way.
"""
from __future__ import annotations

import base64
import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from visual_pdf_auditor import FAILURE, PageIssue

# Failure tags, decided in exactly one place (auditor pattern).
CONNECTOR_THROUGH_NODE = "CONNECTOR_THROUGH_NODE"
CONNECTOR_THROUGH_REGION = "CONNECTOR_THROUGH_REGION"
CONNECTOR_CROSSING = "CONNECTOR_CROSSING"
CONNECTOR_CLEARANCE = "CONNECTOR_CLEARANCE"
CONNECTOR_DIRECTION = "CONNECTOR_DIRECTION"
CONNECTOR_PARSE = "CONNECTOR_PARSE"
# A source/target bbox may be brushed at most CONTACT_EPS SVG units beyond the
# endpoint contact point before it counts as passing through.
BEZIER_SAMPLES = 16
CONTACT_EPS = 2.0
# Endpoints resolve against their declared node's boundary within this many
# SVG units — the same tolerance an adjacent-endpoint obstruction check uses.
ENDPOINT_EPS = CONTACT_EPS
# Minimum separation, in SVG units, between unrelated connectors and between a
# connector and any protected region it does not own. The PDF stage applies
# the same rule scaled to final print size (see connector_pdf_stage.py).
MIN_CLEARANCE = 0.80
# Floating-point tolerance for the clearance boundary: a measured distance
# that floating math rounds a shade under MIN_CLEARANCE (e.g. 0.7999999999999998
# for a fixture placed at exactly 0.80) must still pass "exact or greater".
CLEARANCE_TOLERANCE = 1e-9
_POINT = r"-?\d*\.?\d+(?:[eE][-+]?\d+)?"
_PATH_RE = re.compile(rf"([MmLlCc])|({_POINT})")
_MARKER_RE = re.compile(r"url\(#([^)]+)\)")
_TRANSLATE_RE = re.compile(r"translate\(\s*([-+.\d eE]+)[ ,]+([-+.\d eE]+)\s*\)")
_EDGE_ID_RE = re.compile(r"^L_([^_]+)_([^_]+)_(\d+)$")
_NODE_ID_RE = re.compile(r"^.*-flowchart-(.+?)-\d+$")


# --- Model ---


@dataclass(frozen=True)
class Node:
    id: str
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True)
class Edge:
    id: str
    source: str
    target: str
    points: list[tuple[float, float]]
    marker_end: str  # marker id; "" when the path carries no marker-end


@dataclass(frozen=True)
class ProtectedRegion:
    """A non-node area a connector must not traverse.

    ``kind`` is one of ``node_text``, ``edge_text``, ``cluster_label``,
    ``legend`` or ``annotation``. ``owner_id`` names the node/edge this region
    belongs to (empty for cluster/legend/annotation regions, which no
    connector owns); it is the only adjacency a connector may claim.
    """

    id: str
    kind: str
    x0: float
    y0: float
    x1: float
    y1: float
    owner_id: str


@dataclass
class Diagram:
    nodes: list[Node]
    edges: list[Edge]
    markers: dict[str, str]  # marker id -> orient value
    regions: list[ProtectedRegion]
    parse_issues: list[PageIssue]


# --- SVG parsing into the model ---


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def node_label(node_id: str) -> str:
    """'my-svg-flowchart-WD-0' -> 'WD'; plain ids pass through unchanged."""
    match = _NODE_ID_RE.match(node_id)
    return match.group(1) if match else node_id


def sample_path(d: str, steps: int = BEZIER_SAMPLES) -> list[tuple[float, float]]:
    """Flatten an SVG path ``d`` (absolute M/L/C) to a polyline."""
    tokens = _PATH_RE.findall(d)
    points: list[tuple[float, float]] = []
    cx = cy = 0.0
    i = 0
    cmd = "M"
    while i < len(tokens):
        if tokens[i][0]:
            cmd = tokens[i][0]
            i += 1
            continue
        numbers: list[float] = []
        while i < len(tokens) and not tokens[i][0]:
            numbers.append(float(tokens[i][1]))
            i += 1
        if cmd.upper() in ("M", "L"):
            for j in range(0, len(numbers), 2):
                cx, cy = numbers[j], numbers[j + 1]
                points.append((cx, cy))
        elif cmd.upper() == "C":
            for j in range(0, len(numbers), 6):
                x1, y1, x2, y2, x, y = numbers[j:j + 6]
                _cubic(cx, cy, x1, y1, x2, y2, x, y, points, steps)
                cx, cy = x, y
    return points


def _cubic(p0x, p0y, p1x, p1y, p2x, p2y, p3x, p3y, out, steps) -> None:
    for k in range(1, steps + 1):
        t = k / steps
        u = 1.0 - t
        out.append((u ** 3 * p0x + 3 * u * u * t * p1x + 3 * u * t * t * p2x + t ** 3 * p3x,
                    u ** 3 * p0y + 3 * u * u * t * p1y + 3 * u * t * t * p2y + t ** 3 * p3y))


def _translate(el: ET.Element) -> tuple[float, float]:
    match = _TRANSLATE_RE.search(el.attrib.get("transform", ""))
    return (float(match.group(1)), float(match.group(2))) if match else (0.0, 0.0)


def _shape_bbox(el: ET.Element) -> tuple[float, float, float, float] | None:
    """Bounding box of the first shape inside a node group, in user units."""
    for child in el.iter():
        name = local(child.tag)
        if name == "rect":
            x = float(child.attrib.get("x", 0.0))
            y = float(child.attrib.get("y", 0.0))
            bbox = (x, y, x + float(child.attrib.get("width", 0.0)), y + float(child.attrib.get("height", 0.0)))
        elif name == "polygon":
            coords = [float(v) for v in re.split(r"[ ,]+", child.attrib.get("points", "").strip()) if v]
            if not coords:
                continue
            bbox = (min(coords[0::2]), min(coords[1::2]), max(coords[0::2]), max(coords[1::2]))
        elif name == "path" and "d" in child.attrib:
            pts = sample_path(child.attrib["d"])
            if not pts:
                continue
            bbox = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))
        else:
            continue
        dx, dy = _translate(child)
        return (bbox[0] + dx, bbox[1] + dy, bbox[2] + dx, bbox[3] + dy)
    return None


def parse_node(el: ET.Element) -> Node | None:
    node_id = el.attrib.get("data-id") or el.attrib.get("id")
    bbox = _shape_bbox(el)
    if not node_id or bbox is None:
        return None
    dx, dy = _translate(el)
    return Node(node_label(node_id), bbox[0] + dx, bbox[1] + dy, bbox[2] + dx, bbox[3] + dy)


def _edge_from_attrs(edge_id, source, target, path_el) -> tuple[Edge | None, str]:
    """Build an Edge from a path element, decoding data-points (or d)."""
    d = path_el.attrib.get("d", "")
    encoded = path_el.attrib.get("data-points", "")
    points: list[tuple[float, float]] | None = None
    if encoded:
        try:
            payload = json.loads(base64.b64decode(encoded))
            points = [(float(p["x"]), float(p["y"])) for p in payload]
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None, "malformed data-points"
    if points is None and d:
        points = sample_path(d)
    if not points or len(points) < 2:
        return None, "no measurable points"
    marker = _MARKER_RE.search(path_el.attrib.get("marker-end", ""))
    return Edge(edge_id, source, target, points, marker.group(1) if marker else ""), ""


def parse_flat_edge(el: ET.Element) -> tuple[Edge | None, str]:
    """Parse a real mmdc flat edge path (data-id + data-points + marker-end)."""
    data_id = el.attrib.get("data-id", "")
    match = _EDGE_ID_RE.match(data_id)
    if not match:
        return None, f"edge id '{data_id}' is not L_<source>_<target>_<ordinal>"
    return _edge_from_attrs(data_id, match.group(1), match.group(2), el)


def parse_edge_wrapper(el: ET.Element, index: int) -> tuple[Edge | None, str]:
    source = el.attrib.get("data-source", "")
    target = el.attrib.get("data-target", "")
    if not source or not target:
        return None, "wrapper edge lacks data-source/data-target"
    path_el = next((c for c in el.iter() if local(c.tag) == "path" and "d" in c.attrib), None)
    if path_el is None:
        return None, "no path found"
    edge_id = el.attrib.get("data-id") or el.attrib.get("id") or f"e{index}"
    return _edge_from_attrs(edge_id, source, target, path_el)


def _accumulate_bbox(el: ET.Element) -> tuple[float, float, float, float] | None:
    """DFS from *el* to its first ``foreignObject``, summing nested translates.

    Mermaid renders every label (node, edge, cluster) as a chain of translated
    ``<g>`` wrappers around a ``foreignObject`` sized to the text. Only
    ``translate()`` is ever emitted by mmdc, the same assumption ``_translate``
    above already makes.
    """
    dx0, dy0 = _translate(el)
    for child in el:
        if local(child.tag) == "foreignObject":
            width = float(child.attrib.get("width", 0.0))
            height = float(child.attrib.get("height", 0.0))
            if width <= 0 or height <= 0:
                continue
            cdx, cdy = _translate(child)
            return (dx0 + cdx, dy0 + cdy, dx0 + cdx + width, dy0 + cdy + height)
        nested = _accumulate_bbox(child)
        if nested is not None:
            nx0, ny0, nx1, ny1 = nested
            return (nx0 + dx0, ny0 + dy0, nx1 + dx0, ny1 + dy0)
    return None


def _label_child(el: ET.Element) -> ET.Element | None:
    return next((c for c in el if local(c.tag) == "g" and "label" in c.attrib.get("class", "").split()), None)


def _node_text_regions(el: ET.Element, node: Node | None) -> list[ProtectedRegion]:
    label_el = _label_child(el)
    if label_el is None:
        return []
    bbox = _accumulate_bbox(label_el)
    if bbox is None:
        return []
    ndx, ndy = _translate(el)
    owner = node.id if node is not None else node_label(el.attrib.get("data-id") or el.attrib.get("id", ""))
    return [ProtectedRegion(f"{owner}-text", "node_text", bbox[0] + ndx, bbox[1] + ndy, bbox[2] + ndx, bbox[3] + ndy, owner)]


def _cluster_label_regions(el: ET.Element) -> list[ProtectedRegion]:
    cluster_id = el.attrib.get("id", "")
    cdx, cdy = _translate(el)
    regions: list[ProtectedRegion] = []
    for child in el:
        if local(child.tag) == "g" and "cluster-label" in child.attrib.get("class", "").split():
            bbox = _accumulate_bbox(child)
            if bbox is not None:
                regions.append(
                    ProtectedRegion(cluster_id, "cluster_label", bbox[0] + cdx, bbox[1] + cdy, bbox[2] + cdx, bbox[3] + cdy, cluster_id)
                )
    return regions


def _edge_text_regions(el: ET.Element) -> list[ProtectedRegion]:
    edx, edy = _translate(el)
    regions: list[ProtectedRegion] = []
    for child in el:
        if local(child.tag) == "g" and "label" in child.attrib.get("class", "").split():
            owner = child.attrib.get("data-id", "")
            bbox = _accumulate_bbox(child)
            if bbox is not None and owner:
                regions.append(
                    ProtectedRegion(f"{owner}-label", "edge_text", bbox[0] + edx, bbox[1] + edy, bbox[2] + edx, bbox[3] + edy, owner)
                )
    return regions


def _synthetic_region(el: ET.Element) -> ProtectedRegion | None:
    """Legend/annotation regions: not emitted by real mmdc flowcharts, but a
    synthetic ``<g class="legend"|"annotation" data-id="...">`` carrying a
    direct ``rect``/``polygon``/``path`` child is honoured the same way."""
    classes = el.attrib.get("class", "").split()
    kind = "legend" if "legend" in classes else "annotation"
    bbox = _shape_bbox(el)
    if bbox is None:
        return None
    dx, dy = _translate(el)
    region_id = el.attrib.get("data-id") or el.attrib.get("id") or kind
    return ProtectedRegion(region_id, kind, bbox[0] + dx, bbox[1] + dy, bbox[2] + dx, bbox[3] + dy, "")


def parse_svg(text: str) -> Diagram:
    root = ET.fromstring(text)
    nodes: list[Node] = []
    edges: list[Edge] = []
    markers: dict[str, str] = {}
    regions: list[ProtectedRegion] = []
    issues: list[PageIssue] = []
    for el in root.iter():
        name = local(el.tag)
        classes = el.attrib.get("class", "").split()
        if name == "marker" and el.attrib.get("id"):
            markers[el.attrib["id"]] = el.attrib.get("orient", "")
        elif name == "g" and "node" in classes:
            node = parse_node(el)
            if node is not None:
                nodes.append(node)
            regions.extend(_node_text_regions(el, node))
        elif name == "g" and "cluster" in classes:
            regions.extend(_cluster_label_regions(el))
        elif name == "g" and "edgeLabel" in classes:
            regions.extend(_edge_text_regions(el))
        elif name == "g" and ("legend" in classes or "annotation" in classes):
            region = _synthetic_region(el)
            if region is not None:
                regions.append(region)
        elif (name == "path" and "data-id" in el.attrib) or (name == "g" and "edgePath" in classes):
            edge, issue = (
                parse_flat_edge(el) if "data-id" in el.attrib else parse_edge_wrapper(el, len(edges))
            )
            if edge is None:
                issues.append(PageIssue(FAILURE, CONNECTOR_PARSE, f"edge '{el.attrib.get('data-id', 'wrapper')}': {issue}"))
            else:
                edges.append(edge)
    label_index = {}
    for node in nodes:
        label_index.setdefault(node.id, []).append(node)
    for edge in edges:
        for attr in ("source", "target"):
            token = getattr(edge, attr)
            if token and len(label_index.get(token, [])) != 1:
                issues.append(PageIssue(FAILURE, CONNECTOR_PARSE, f"edge '{edge.id}' {attr} '{token}' is ambiguous or unresolved"))
    return Diagram(nodes=nodes, edges=edges, markers=markers, regions=regions, parse_issues=issues)


# --- Geometry primitives and checks (each a FAILURE, classified here) ---


def _clip_interval(a, b, bbox):
    """Liang-Barsky: parametric t-range of segment a->b inside an AABB."""
    x0, y0, x1, y1 = bbox
    dx, dy = b[0] - a[0], b[1] - a[1]
    p = (-dx, dx, -dy, dy)
    q = (a[0] - x0, x1 - a[0], a[1] - y0, y1 - a[1])
    t0, t1 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if pi == 0.0:
            if qi < 0:
                return None
        else:
            t = qi / pi
            if pi < 0:
                if t > t1:
                    return None
                t0 = max(t0, t)
            else:
                if t < t0:
                    return None
                t1 = min(t1, t)
    return (t0, t1)


def _edge_traverses_bbox(points, bbox, start_exempt: bool, end_exempt: bool) -> bool:
    """Does the edge polyline enter *bbox* beyond endpoint contact?

    Adjacent source/target regions are exempt ONLY at the endpoint contact
    point: the first (resp. last) segment may touch the bbox for at most
    ``CONTACT_EPS`` SVG units; every other penetration is a traversal.
    """
    last = len(points) - 1
    for i in range(last):
        a, b = points[i], points[i + 1]
        interval = _clip_interval(a, b, bbox)
        if interval is None:
            continue
        t0, t1 = interval
        inside = (t1 - t0) * math.hypot(b[0] - a[0], b[1] - a[1])
        if i == 0 and start_exempt and inside <= CONTACT_EPS:
            continue
        if i == last - 1 and end_exempt and inside <= CONTACT_EPS:
            continue
        return True
    return False


def obstruction_issues(diagram: Diagram) -> tuple[list[PageIssue], set[tuple[str, str]]]:
    """Connector-through-node and connector-through-region failures.

    Returns the issues alongside the ``(edge_id, node_or_region_id)`` pairs
    already flagged, so ``clearance_issues`` never restates the same pair as a
    (weaker) clearance defect — obstruction takes precedence over clearance.
    """
    issues: list[PageIssue] = []
    pairs: set[tuple[str, str]] = set()
    for edge in diagram.edges:
        for node in diagram.nodes:
            bbox = (node.x0, node.y0, node.x1, node.y1)
            if _edge_traverses_bbox(edge.points, bbox, node.id == edge.source, node.id == edge.target):
                issues.append(PageIssue(FAILURE, CONNECTOR_THROUGH_NODE, f"edge '{edge.id}' passes through node '{node.id}'"))
                pairs.add((edge.id, node.id))
        for region in diagram.regions:
            if region.kind == "node_text":
                start_exempt, end_exempt = region.owner_id == edge.source, region.owner_id == edge.target
            elif region.kind == "edge_text":
                if region.owner_id == edge.id:
                    continue  # a connector is not "through" its own label
                start_exempt = end_exempt = False
            else:
                start_exempt = end_exempt = False
            bbox = (region.x0, region.y0, region.x1, region.y1)
            if _edge_traverses_bbox(edge.points, bbox, start_exempt, end_exempt):
                issues.append(PageIssue(FAILURE, CONNECTOR_THROUGH_REGION, f"edge '{edge.id}' passes through {region.kind} '{region.id}'"))
                pairs.add((edge.id, region.id))
    return issues, pairs


def _orient(o, a, b) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _on_segment(p, a, b) -> bool:
    return (
        min(a[0], b[0]) - 1e-9 <= p[0] <= max(a[0], b[0]) + 1e-9
        and min(a[1], b[1]) - 1e-9 <= p[1] <= max(a[1], b[1]) + 1e-9
    )


def _segments_cross_strict(a1, b1, a2, b2) -> bool:
    """Interior crossing only — excludes shared endpoints, collinear contact
    and vertex-only touch (spec: those MUST NOT count as a crossing)."""
    d1, d2 = _orient(a2, b2, a1), _orient(a2, b2, b1)
    d3, d4 = _orient(a1, b1, a2), _orient(a1, b1, b2)
    return (d1 > 0) != (d2 > 0) and d1 != 0 and d2 != 0 and (d3 > 0) != (d4 > 0) and d3 != 0 and d4 != 0


def _segments_intersect(a1, b1, a2, b2) -> bool:
    """Any shared point at all: strict crossing, touching, or collinear overlap."""
    if _segments_cross_strict(a1, b1, a2, b2):
        return True
    d1, d2 = _orient(a2, b2, a1), _orient(a2, b2, b1)
    d3, d4 = _orient(a1, b1, a2), _orient(a1, b1, b2)
    if d1 == 0 and _on_segment(a1, a2, b2):
        return True
    if d2 == 0 and _on_segment(b1, a2, b2):
        return True
    if d3 == 0 and _on_segment(a2, a1, b1):
        return True
    if d4 == 0 and _on_segment(b2, a1, b1):
        return True
    return False


def _edges_touch_or_cross(e1: Edge, e2: Edge) -> bool:
    return any(
        _segments_intersect(a1, b1, a2, b2)
        for a1, b1 in zip(e1.points, e1.points[1:])
        for a2, b2 in zip(e2.points, e2.points[1:])
    )


def crossing_issues(diagram: Diagram) -> list[PageIssue]:
    issues: list[PageIssue] = []
    edges = diagram.edges
    for i, e1 in enumerate(edges):
        for e2 in edges[i + 1:]:
            crossed = any(
                _segments_cross_strict(a1, b1, a2, b2)
                for a1, b1 in zip(e1.points, e1.points[1:])
                for a2, b2 in zip(e2.points, e2.points[1:])
            )
            if crossed:
                issues.append(PageIssue(FAILURE, CONNECTOR_CROSSING, f"edge '{e1.id}' crosses edge '{e2.id}'"))
    return issues


def _point_segment_dist(p, a, b) -> float:
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def _segment_dist(a1, b1, a2, b2) -> float:
    if _segments_intersect(a1, b1, a2, b2):
        return 0.0
    return min(
        _point_segment_dist(a1, a2, b2), _point_segment_dist(b1, a2, b2),
        _point_segment_dist(a2, a1, b1), _point_segment_dist(b2, a1, b1),
    )


def _segment_bbox_dist(a, b, bbox) -> float:
    if _clip_interval(a, b, bbox) is not None:
        return 0.0
    x0, y0, x1, y1 = bbox
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    edges = list(zip(corners, corners[1:] + corners[:1]))
    return min(_segment_dist(a, b, c1, c2) for c1, c2 in edges)


def pairwise_clearances(diagram: Diagram, obstructed_pairs: set[tuple[str, str]]):
    """Yield ``(edge_id, counterpart_kind, counterpart_id, distance_svg)`` for
    every unrelated edge/edge, edge/region and edge/node pair, skipping any
    pair obstruction/crossing already flagged or that is a legitimate
    adjacency. Shared by the isolated (``clearance_issues``) and final-print
    (``connector_pdf_stage.py``) stages so the pair selection can never drift
    between them — only the threshold each applies differs."""
    edges = diagram.edges
    for i, e1 in enumerate(edges):
        for e2 in edges[i + 1:]:
            if _edges_touch_or_cross(e1, e2):
                continue
            dist = min(
                _segment_dist(a1, b1, a2, b2)
                for a1, b1 in zip(e1.points, e1.points[1:])
                for a2, b2 in zip(e2.points, e2.points[1:])
            )
            yield e1.id, "edge", e2.id, dist
        for region in diagram.regions:
            if (e1.id, region.id) in obstructed_pairs:
                continue
            if region.kind == "node_text" and region.owner_id in (e1.source, e1.target):
                continue
            if region.kind == "edge_text" and region.owner_id == e1.id:
                continue
            bbox = (region.x0, region.y0, region.x1, region.y1)
            dist = min(_segment_bbox_dist(a, b, bbox) for a, b in zip(e1.points, e1.points[1:]))
            yield e1.id, region.kind, region.id, dist
    for node in diagram.nodes:
        bbox = (node.x0, node.y0, node.x1, node.y1)
        for edge in edges:
            if node.id in (edge.source, edge.target) or (edge.id, node.id) in obstructed_pairs:
                continue
            dist = min(_segment_bbox_dist(a, b, bbox) for a, b in zip(edge.points, edge.points[1:]))
            yield edge.id, "node", node.id, dist


def clearance_issues(diagram: Diagram, obstructed_pairs: set[tuple[str, str]]) -> list[PageIssue]:
    """Minimum-separation failures against the isolated 0.80 SVG-unit rule."""
    issues: list[PageIssue] = []
    for edge_id, kind, other_id, dist in pairwise_clearances(diagram, obstructed_pairs):
        if dist < MIN_CLEARANCE - CLEARANCE_TOLERANCE:
            issues.append(
                PageIssue(FAILURE, CONNECTOR_CLEARANCE, f"edge '{edge_id}' is {dist:.3f} SVG units from {kind} '{other_id}' (minimum {MIN_CLEARANCE})")
            )
    return issues


def _point_near_bbox(p, bbox, eps=ENDPOINT_EPS) -> bool:
    x, y = p
    x0, y0, x1, y1 = bbox
    return x0 - eps <= x <= x1 + eps and y0 - eps <= y <= y1 + eps


def direction_issues(diagram: Diagram) -> list[PageIssue]:
    """Source/target endpoint containment and end-marker validity."""
    issues: list[PageIssue] = []
    by_id = {node.id: node for node in diagram.nodes}
    for edge in diagram.edges:
        src, tgt = by_id.get(edge.source), by_id.get(edge.target)
        if src is not None and not _point_near_bbox(edge.points[0], (src.x0, src.y0, src.x1, src.y1)):
            issues.append(PageIssue(FAILURE, CONNECTOR_DIRECTION, f"edge '{edge.id}' starts off its declared source '{edge.source}'"))
        if tgt is not None and not _point_near_bbox(edge.points[-1], (tgt.x0, tgt.y0, tgt.x1, tgt.y1)):
            issues.append(PageIssue(FAILURE, CONNECTOR_DIRECTION, f"edge '{edge.id}' ends off its declared target '{edge.target}'"))
        if not edge.marker_end:
            issues.append(PageIssue(FAILURE, CONNECTOR_DIRECTION, f"edge '{edge.id}' has no end marker"))
        elif edge.marker_end not in diagram.markers:
            issues.append(PageIssue(FAILURE, CONNECTOR_DIRECTION, f"edge '{edge.id}' end marker '{edge.marker_end}' is dangling"))
        elif diagram.markers[edge.marker_end] != "auto":
            issues.append(PageIssue(FAILURE, CONNECTOR_DIRECTION, f"edge '{edge.id}' end marker '{edge.marker_end}' orientation is not auto"))
    return issues


def audit_diagram(diagram: Diagram) -> list[PageIssue]:
    obstruction, obstructed_pairs = obstruction_issues(diagram)
    return (
        list(diagram.parse_issues)
        + obstruction
        + crossing_issues(diagram)
        + clearance_issues(diagram, obstructed_pairs)
        + direction_issues(diagram)
    )


def audit_connector_geometry(svg: Path) -> list[PageIssue]:
    """Audit a rendered Mermaid SVG file for connector defects."""
    return audit_diagram(parse_svg(svg.read_text(encoding="utf-8")))
