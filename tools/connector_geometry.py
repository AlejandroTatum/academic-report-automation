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
CONNECTOR_PARSE = "CONNECTOR_PARSE"
# A source/target bbox may be brushed at most CONTACT_EPS SVG units beyond the
# endpoint contact point before it counts as passing through.
BEZIER_SAMPLES = 16
CONTACT_EPS = 2.0
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


@dataclass
class Diagram:
    nodes: list[Node]
    edges: list[Edge]
    markers: dict[str, str]  # marker id -> orient value
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


def parse_svg(text: str) -> Diagram:
    root = ET.fromstring(text)
    nodes: list[Node] = []
    edges: list[Edge] = []
    markers: dict[str, str] = {}
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
    return Diagram(nodes=nodes, edges=edges, markers=markers, parse_issues=issues)


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


def _edge_traverses_node(points, node, edge) -> bool:
    """Does the edge polyline enter the node bbox beyond endpoint contact?

    Adjacent source/target regions are exempt ONLY at the endpoint contact
    point: the first (resp. last) segment may touch the bbox for at most
    ``CONTACT_EPS`` SVG units; every other penetration is a traversal.
    """
    start_exempt = node.id == edge.source
    end_exempt = node.id == edge.target
    last = len(points) - 1
    for i in range(last):
        a, b = points[i], points[i + 1]
        interval = _clip_interval(a, b, (node.x0, node.y0, node.x1, node.y1))
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


def through_node_issues(diagram: Diagram) -> list[PageIssue]:
    issues: list[PageIssue] = []
    for edge in diagram.edges:
        for node in diagram.nodes:
            if _edge_traverses_node(edge.points, node, edge):
                issues.append(PageIssue(FAILURE, CONNECTOR_THROUGH_NODE, f"edge '{edge.id}' passes through node '{node.id}'"))
    return issues


def audit_diagram(diagram: Diagram) -> list[PageIssue]:
    return list(diagram.parse_issues) + through_node_issues(diagram)


def audit_connector_geometry(svg: Path) -> list[PageIssue]:
    """Audit a rendered Mermaid SVG file for connector defects."""
    return audit_diagram(parse_svg(svg.read_text(encoding="utf-8")))
