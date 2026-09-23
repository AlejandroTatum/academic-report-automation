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
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from visual_pdf_auditor import FAILURE, INFO, PageIssue

# Failure tags, decided in exactly one place (auditor pattern).
CONNECTOR_THROUGH_NODE = "CONNECTOR_THROUGH_NODE"
CONNECTOR_THROUGH_REGION = "CONNECTOR_THROUGH_REGION"
CONNECTOR_CROSSING = "CONNECTOR_CROSSING"
CONNECTOR_CLEARANCE = "CONNECTOR_CLEARANCE"
CONNECTOR_DIRECTION = "CONNECTOR_DIRECTION"
CONNECTOR_PARSE = "CONNECTOR_PARSE"
# INFO-level, never a FAILURE: the direction/marker check ran against the
# pre-#43 strict rule because no ``.mmd`` source was found next to the SVG to
# say which links are intentionally undirected (see direction_issues()).
CONNECTOR_DIRECTION_NO_SOURCE = "CONNECTOR_DIRECTION_NO_SOURCE"
# A geometry exception (malformed XML, corrupted path/point data, or any
# other defect the parser cannot recover from) turned into a finding instead
# of an uncaught crash. See run_geometry_audit() (#43 T2).
CONNECTOR_AUDIT_ERROR = "CONNECTOR_AUDIT_ERROR"
# Cubic-bezier flattening resolution for sample_path()'s fallback d-attribute
# sampling (node/region shapes given as a path, not a rect/polygon/circle).
BEZIER_SAMPLES = 16
# A source/target bbox may be brushed at most CONTACT_EPS SVG units, measured
# as the total contiguous run from the true endpoint (which may span several
# polyline segments), before it counts as passing through rather than grazing.
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
_PATH_RE = re.compile(rf"([MmLlCcHhVvZz])|({_POINT})")
_MARKER_RE = re.compile(r"url\(#([^)]+)\)")
_TRANSLATE_RE = re.compile(r"translate\(\s*([-+.\d eE]+)[ ,]+([-+.\d eE]+)\s*\)")
# Lenient envelope only: source/target may themselves contain underscores, so
# the middle group is split against known node labels in parse_flat_edge(),
# not here.
_EDGE_ID_RE = re.compile(r"^L_(.+)_(\d+)$")
_NODE_ID_RE = re.compile(r"^.*-flowchart-(.+?)-\d+$")
_VIEWBOX_RE = re.compile(rf"^({_POINT})\s+({_POINT})\s+({_POINT})\s+({_POINT})$")


# --- Model ---


@dataclass(frozen=True)
class Node:
    """A diagram node's identity and bounding box.

    ``id`` holds the resolved diagram-visible label (``node_label()``
    already strips the ``<svg-id>-flowchart-...-<ordinal>`` wrapper) — the
    same value ``Edge.source``/``Edge.target`` and ``ProtectedRegion.owner_id``
    key against — not the raw SVG element id/attribute.
    """

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
    # The SVG's own viewBox, (x0, y0, x1, y1) -- the outer limit an
    # alternative route may occupy when proving a crossing necessary (#43
    # T3). ``None`` when the SVG carries no viewBox (route search then stays
    # unbounded: more room to find a route, never less -- the safe
    # direction, see _has_alternative_route()).
    bounds: tuple[float, float, float, float] | None = None


# --- SVG parsing into the model ---


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def node_label(node_id: str) -> str:
    """'my-svg-flowchart-WD-0' -> 'WD'; plain ids pass through unchanged."""
    match = _NODE_ID_RE.match(node_id)
    return match.group(1) if match else node_id


def sample_path(d: str, steps: int = BEZIER_SAMPLES) -> list[tuple[float, float]]:
    """Flatten an SVG path ``d`` to a polyline.

    Handles M/L/C in both absolute and relative (lowercase) form, plus the
    line-only H/V and the Z close-path command. A command outside this set
    is skipped rather than left to silently corrupt the current point for
    whatever draws after it (real mmdc emits only absolute M/L/C, but shape
    libraries feeding a node's own ``path`` bbox routinely use the rest).
    """
    tokens = _PATH_RE.findall(d)
    points: list[tuple[float, float]] = []
    cx = cy = 0.0
    start_x = start_y = 0.0
    i = 0
    cmd = "M"
    while i < len(tokens):
        if tokens[i][0]:
            cmd = tokens[i][0]
            i += 1
            if cmd.upper() == "Z":
                cx, cy = start_x, start_y
                points.append((cx, cy))
            continue
        numbers: list[float] = []
        while i < len(tokens) and not tokens[i][0]:
            numbers.append(float(tokens[i][1]))
            i += 1
        relative = cmd.islower()
        upper = cmd.upper()
        if upper in ("M", "L"):
            for j in range(0, len(numbers), 2):
                nx, ny = numbers[j], numbers[j + 1]
                cx, cy = (cx + nx, cy + ny) if relative else (nx, ny)
                points.append((cx, cy))
                if upper == "M" and j == 0:
                    start_x, start_y = cx, cy
        elif upper == "H":
            for value in numbers:
                cx = cx + value if relative else value
                points.append((cx, cy))
        elif upper == "V":
            for value in numbers:
                cy = cy + value if relative else value
                points.append((cx, cy))
        elif upper == "C":
            for j in range(0, len(numbers), 6):
                x1, y1, x2, y2, x, y = numbers[j:j + 6]
                if relative:
                    x1, y1, x2, y2, x, y = cx + x1, cy + y1, cx + x2, cy + y2, cx + x, cy + y
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
        elif name == "circle":
            cx = float(child.attrib.get("cx", 0.0))
            cy = float(child.attrib.get("cy", 0.0))
            r = float(child.attrib.get("r", 0.0))
            bbox = (cx - r, cy - r, cx + r, cy + r)
        elif name == "ellipse":
            cx = float(child.attrib.get("cx", 0.0))
            cy = float(child.attrib.get("cy", 0.0))
            rx = float(child.attrib.get("rx", 0.0))
            ry = float(child.attrib.get("ry", 0.0))
            bbox = (cx - rx, cy - ry, cx + rx, cy + ry)
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


def parse_flat_edge(el: ET.Element, known_labels: set[str]) -> tuple[Edge | None, str]:
    """Parse a real mmdc flat edge path (data-id + data-points + marker-end).

    ``data-id`` is ``L_<source>_<target>_<ordinal>``, but source and target
    are the diagram's own node labels and may themselves legitimately contain
    underscores (a valid Mermaid id) — a single fixed split point is not
    always correct. Every split of the ``source_target`` middle whose two
    halves both resolve to a *known* node label is tried: a unique such split
    wins, more than one is a genuine ambiguity, and none falls back to the
    original leftmost two-run split so the "ambiguous or unresolved" pass
    still reports whatever it could not identify (an actually-missing node,
    for instance) exactly as before.
    """
    data_id = el.attrib.get("data-id", "")
    match = _EDGE_ID_RE.match(data_id)
    if not match:
        return None, f"edge id '{data_id}' is not L_<source>_<target>_<ordinal>"
    parts = match.group(1).split("_")
    if len(parts) < 2:
        return None, f"edge id '{data_id}' is not L_<source>_<target>_<ordinal>"
    resolved = [
        (source, target)
        for i in range(1, len(parts))
        for source, target in [("_".join(parts[:i]), "_".join(parts[i:]))]
        if source in known_labels and target in known_labels
    ]
    if len(resolved) == 1:
        source, target = resolved[0]
    elif len(resolved) > 1:
        return None, f"edge id '{data_id}' splits ambiguously across known node labels: {resolved}"
    else:
        # No split resolved against a known label: fall back to the leftmost
        # split so the later "ambiguous or unresolved" pass still names
        # exactly what it could not identify (e.g. a genuinely missing node).
        source, target = parts[0], "_".join(parts[1:])
    return _edge_from_attrs(data_id, source, target, el)


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
                # owner_id "" per ProtectedRegion's own contract: no connector
                # owns a cluster label, so it claims no endpoint adjacency.
                regions.append(
                    ProtectedRegion(cluster_id, "cluster_label", bbox[0] + cdx, bbox[1] + cdy, bbox[2] + cdx, bbox[3] + cdy, "")
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

    # First pass: nodes and markers only. A flat edge id may legitimately
    # contain underscores in its own source/target labels, which can only be
    # disambiguated against the full known-label set — and real mmdc emits
    # g.edgePaths BEFORE g.nodes in document order, so a single combined pass
    # cannot have that set ready when it reaches the edges.
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
    known_labels = {node.id for node in nodes}

    for el in root.iter():
        name = local(el.tag)
        classes = el.attrib.get("class", "").split()
        if name == "g" and "cluster" in classes:
            regions.extend(_cluster_label_regions(el))
        elif name == "g" and "edgeLabel" in classes:
            regions.extend(_edge_text_regions(el))
        elif name == "g" and ("legend" in classes or "annotation" in classes):
            region = _synthetic_region(el)
            if region is not None:
                regions.append(region)
        elif (name == "path" and "data-id" in el.attrib) or (name == "g" and "edgePath" in classes):
            edge, issue = (
                parse_flat_edge(el, known_labels) if "data-id" in el.attrib else parse_edge_wrapper(el, len(edges))
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
    bounds = None
    view_box = _VIEWBOX_RE.match(root.attrib.get("viewBox", "").strip())
    if view_box:
        x0, y0, w, h = (float(v) for v in view_box.groups())
        bounds = (x0, y0, x0 + w, y0 + h)
    return Diagram(nodes=nodes, edges=edges, markers=markers, regions=regions, parse_issues=issues, bounds=bounds)


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

    Adjacent source/target regions are exempt ONLY at the endpoint contact:
    the run of segments CONTIGUOUS with the true start (resp. end) may touch
    the bbox for at most ``CONTACT_EPS`` SVG units in total; every other
    penetration is a traversal. The run — not a single fixed segment index —
    is what is measured: a curved departure routinely grazes its own source
    across more than one polyline segment before fully leaving it, and
    checking segment 0 (resp. the last one) in isolation would flag the
    second segment of that same graze as an unrelated traversal.
    """
    last = len(points) - 1
    inside = [0.0] * last
    for i in range(last):
        a, b = points[i], points[i + 1]
        interval = _clip_interval(a, b, bbox)
        if interval is not None:
            t0, t1 = interval
            inside[i] = (t1 - t0) * math.hypot(b[0] - a[0], b[1] - a[1])

    exempt_prefix = 0
    if start_exempt:
        run = 0.0
        for value in inside:
            if value <= 0:
                break
            run += value
        if run <= CONTACT_EPS:
            exempt_prefix = next((i for i, v in enumerate(inside) if v <= 0), last)

    exempt_suffix = 0
    if end_exempt:
        run = 0.0
        for value in reversed(inside):
            if value <= 0:
                break
            run += value
        if run <= CONTACT_EPS:
            exempt_suffix = next((i for i, v in enumerate(reversed(inside)) if v <= 0), last)

    for i, value in enumerate(inside):
        if value <= 0:
            continue
        if i < exempt_prefix or i >= last - exempt_suffix:
            continue
        return True
    return False


def _node_text_endpoint_exemption(region: ProtectedRegion, edge: Edge) -> tuple[bool, bool]:
    """(start_exempt, end_exempt): whether a ``node_text`` region is owned by
    *edge*'s source and/or target, and therefore a legitimate adjacency only
    at that endpoint's graze."""
    return region.owner_id == edge.source, region.owner_id == edge.target


def _is_own_edge_label(region: ProtectedRegion, edge: Edge) -> bool:
    """The single place ownership of an ``edge_text`` label is decided: a
    connector is never "through" or too close to its own label. Used by both
    obstruction and clearance so the rule cannot drift between the two."""
    return region.kind == "edge_text" and region.owner_id == edge.id


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
            if _is_own_edge_label(region, edge):
                continue  # a connector is not "through" its own label
            if region.kind == "node_text":
                start_exempt, end_exempt = _node_text_endpoint_exemption(region, edge)
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


def _collinear_overlap_length(a1, b1, a2, b2) -> float:
    """Length of the collinear overlap between two segments, 0 when they are
    not collinear or only touch at a single point (a shared endpoint or a
    T-touch is zero-length and stays exempt; a genuine overlapping run is
    not — two connectors routed on top of each other for a stretch are as
    much a routing defect as a strict crossing)."""
    if _orient(a1, b1, a2) != 0 or _orient(a1, b1, b2) != 0:
        return 0.0
    dx, dy = b1[0] - a1[0], b1[1] - a1[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return 0.0
    ux, uy = dx / length, dy / length

    def proj(p) -> float:
        return (p[0] - a1[0]) * ux + (p[1] - a1[1]) * uy

    lo2, hi2 = sorted((proj(a2), proj(b2)))
    return max(0.0, min(length, hi2) - max(0.0, lo2))


def _polyline_passes_through_vertex(points, seg_a, seg_b) -> bool:
    """True when an INTERIOR vertex of *points* (never its true start/end —
    a legitimate shared-endpoint touch) sits exactly on segment
    (seg_a, seg_b) with its neighbours on strictly opposite sides.

    Per-segment-pair strict crossing alone cannot see this: the crossing
    point coincides with a polyline vertex, so each adjacent segment pair on
    its own only ever reports an endpoint-only touch, never a strict
    interior crossing — even though the whole polyline demonstrably passes
    from one side of the other edge to the other, transversally.
    """
    for i in range(1, len(points) - 1):
        v = points[i]
        if _orient(seg_a, seg_b, v) != 0 or not _on_segment(v, seg_a, seg_b):
            continue
        prev_side, next_side = _orient(seg_a, seg_b, points[i - 1]), _orient(seg_a, seg_b, points[i + 1])
        if prev_side != 0 and next_side != 0 and (prev_side > 0) != (next_side > 0):
            return True
    return False


def _edges_cross(e1: Edge, e2: Edge) -> bool:
    """A genuine crossing: a strict interior segment cross, a nonzero-length
    collinear overlap, or a transversal pass-through landing exactly on the
    other polyline's vertex (see ``_polyline_passes_through_vertex``)."""
    for a1, b1 in zip(e1.points, e1.points[1:]):
        for a2, b2 in zip(e2.points, e2.points[1:]):
            if _segments_cross_strict(a1, b1, a2, b2):
                return True
            if _collinear_overlap_length(a1, b1, a2, b2) > CLEARANCE_TOLERANCE:
                return True
    return any(
        _polyline_passes_through_vertex(e1.points, a2, b2) for a2, b2 in zip(e2.points, e2.points[1:])
    ) or any(
        _polyline_passes_through_vertex(e2.points, a1, b1) for a1, b1 in zip(e1.points, e1.points[1:])
    )


# --- Necessary-crossing exemption (#43 T3) -------------------------------------
#
# 2026-09-23 decision: conservative. A crossing is exempt ONLY when the gate
# PROVES no alternative route exists for one of the two edges -- an
# obstacle-aware visibility check, within the diagram's own bounds, showing
# every possible route from that edge's own source to its own target must
# cross the other edge as currently drawn. When the proof is inconclusive
# (state budget exceeded, no bounds to reason within) or a route IS found,
# the crossing still fails -- the pre-#43 always-fail behaviour, which this
# only narrows, never widens past what is actually proven.

# Hard cap on visibility-graph vertices (2 endpoints + 4 per obstacle): keeps
# the O(V^2) all-pairs visibility check bounded on real diagrams carrying
# many nodes/regions. Past this, the proof is inconclusive by construction --
# the crossing keeps failing, the same safe default as having no proof at all.
MAX_VISIBILITY_VERTICES = 60


def _obstacles_for_edge(diagram: Diagram, edge: Edge) -> list[tuple[float, float, float, float]]:
    """Bounding boxes an alternative route for *edge* must not cross: every
    node it does not itself terminate at, and every protected region it does
    not own -- the same adjacency rule obstruction_issues() already applies."""
    boxes = [(n.x0, n.y0, n.x1, n.y1) for n in diagram.nodes if n.id != edge.source and n.id != edge.target]
    boxes.extend(
        (r.x0, r.y0, r.x1, r.y1)
        for r in diagram.regions
        if r.owner_id != edge.id and not _is_own_edge_label(r, edge)
    )
    return boxes


def _segment_crosses_bbox_interior(a, b, bbox) -> bool:
    """True only when segment a-b passes through *bbox*'s OPEN interior --
    merely touching its boundary or a corner is a legitimate way to route
    around it, not a block."""
    x0, y0, x1, y1 = bbox
    inset = 1e-6
    ix0, iy0, ix1, iy1 = x0 + inset, y0 + inset, x1 - inset, y1 - inset
    if ix1 <= ix0 or iy1 <= iy0:
        return False
    return _clip_interval(a, b, (ix0, iy0, ix1, iy1)) is not None


def _point_within_bounds(p, bounds) -> bool:
    x0, y0, x1, y1 = bounds
    eps = 1e-6
    return x0 - eps <= p[0] <= x1 + eps and y0 - eps <= p[1] <= y1 + eps


def _has_alternative_route(
    start: tuple[float, float],
    end: tuple[float, float],
    obstacles: list[tuple[float, float, float, float]],
    blocker: Edge,
    bounds: tuple[float, float, float, float] | None,
) -> bool | None:
    """Whether *start* can reach *end* by a route of straight segments that
    stays within *bounds*, never crosses an obstacle's interior, and never
    crosses *blocker*'s own polyline -- a standard corner visibility graph
    over ``{start, end} + every obstacle corner``: the shortest route around
    axis-aligned rectangles always bends only at their corners, so this
    construction is exact, not a heuristic.

    Returns ``None`` (inconclusive) once the vertex budget is exceeded; the
    caller must then treat the crossing as NOT proven necessary, never as
    proven exempt.
    """
    if bounds is not None:
        # *start*/*end* are the edge's own required endpoints, not part of
        # the alternative route being searched for -- a declared viewBox
        # that happens not to enclose one of them (a stray node placed
        # outside it) must never trap the search into a false "no route
        # exists" just because the endpoint itself sits outside bounds.
        x0, y0, x1, y1 = bounds
        xs, ys = (start[0], end[0]), (start[1], end[1])
        bounds = (min(x0, *xs), min(y0, *ys), max(x1, *xs), max(y1, *ys))
    corners = [
        (x, y)
        for x0, y0, x1, y1 in obstacles
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
        if bounds is None or _point_within_bounds((x, y), bounds)
    ]
    vertices = [start, end, *corners]
    if len(vertices) > MAX_VISIBILITY_VERTICES:
        return None

    def blocked(a, b) -> bool:
        if bounds is not None and not (_point_within_bounds(a, bounds) and _point_within_bounds(b, bounds)):
            return True
        if any(_segment_crosses_bbox_interior(a, b, box) for box in obstacles):
            return True
        # Unlike an obstacle box (which has an interior/exterior, so merely
        # touching its boundary while staying outside is a legitimate way to
        # route around it), *blocker* is a zero-width curve: any shared
        # point at all -- including a single tangent touch -- is contact a
        # route claiming to "avoid" it cannot have. Strict-crossing-only
        # here would let a route flip sides by grazing exactly one point of
        # *blocker*, which is not a real alternative route.
        return any(_segments_intersect(a, b, p1, p2) for p1, p2 in zip(blocker.points, blocker.points[1:]))

    adjacency: list[list[int]] = [[] for _ in vertices]
    for i in range(len(vertices)):
        for j in range(i + 1, len(vertices)):
            if not blocked(vertices[i], vertices[j]):
                adjacency[i].append(j)
                adjacency[j].append(i)

    seen, frontier = {0}, [0]
    while frontier:
        current = frontier.pop()
        if current == 1:
            return True
        for neighbour in adjacency[current]:
            if neighbour not in seen:
                seen.add(neighbour)
                frontier.append(neighbour)
    return False


def _crossing_is_provably_necessary(diagram: Diagram, e1: Edge, e2: Edge) -> bool:
    """True only when the gate can PROVE neither edge has an alternative
    route around the other. Checking just one edge's total routing freedom
    against the other's fixed, as-rendered path is sufficient proof per the
    accepted decision ("every route for one of the edges must cross the
    other"); an inconclusive check never grants the exemption."""
    for edge, blocker in ((e1, e2), (e2, e1)):
        obstacles = _obstacles_for_edge(diagram, edge)
        if _has_alternative_route(edge.points[0], edge.points[-1], obstacles, blocker, diagram.bounds) is False:
            return True
    return False


def crossing_issues(diagram: Diagram) -> list[PageIssue]:
    """Every genuine crossing between unrelated connectors fails, except one
    the gate can prove is unavoidable (see the module note above and
    ``_crossing_is_provably_necessary`` -- #43 T3, conservative: an
    inconclusive proof still fails, exactly like the pre-#43 rule)."""
    issues: list[PageIssue] = []
    edges = diagram.edges
    for i, e1 in enumerate(edges):
        for e2 in edges[i + 1:]:
            if _edges_cross(e1, e2) and not _crossing_is_provably_necessary(diagram, e1, e2):
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
            if region.kind == "node_text" and any(_node_text_endpoint_exemption(region, e1)):
                continue
            if _is_own_edge_label(region, e1):
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


# --- Declared link direction, from the .mmd source (#43 T1) -------------------
#
# 2026-09-23 decision (supersedes the August "every connector MUST use a
# defined end marker" rule): an undirected Mermaid link (open ---, dotted
# -.-, thick ===, with or without a |label| or inline ' text ' segment) is
# valid and skips direction/marker checks. A link carrying any arrowhead
# (-->, -.->,  ==>, <-->, --o, --x, ...) is unchanged -- still checked in
# full. The source is the sole authority on intent; there is no SVG-only
# signal to tell "renderer correctly omitted the marker" from "marker
# generation broke", so a missing source keeps the old strict rule and says
# so (CONNECTOR_DIRECTION_NO_SOURCE, informational).
_LINK_ID = r"[A-Za-z0-9_][\w-]*"
# A node's shape delimiter on either side of a link (e.g. "A[Label]",
# "B((Label))"); only skipped past, never parsed for its own content.
_LINK_SHAPE = (
    r"(?:@\{[^}]*\}|\[\[[^\]]*\]\]|\(\([^)]*\)\)|\{\{[^}]*\}\}|\[\([^)]*\)\]"
    r"|>[^\]]*\]|\[[^\]]*\]|\([^)]*\)|\{[^}]*\})?"
)
# The connector itself: an optional leading '<' (bidirectional/reversed
# arrowhead), a run of >=2 line characters (-/./=), an optional inline label
# (|...| or free text before the closing run), the closing run, an optional
# trailing arrowhead ('>' or a circle/cross terminator 'o'/'x'), and an
# optional |label| placed AFTER the arrow (Mermaid's "-->|label|" form).
_LINK_ARROW = (
    r"(?P<lhead><)?(?P<lpunct>[-=.]{2,})"
    r"(?:\s*\|[^|]*\||\s+[^-=.\n]+?(?=\s*[-=.]{2,}))?"
    r"\s*(?P<rpunct>[-=.]{0,})(?P<rhead>[>ox])?"
    r"(?:\s*\|[^|]*\|)?"
)
_LINK_RE = re.compile(rf"(?P<src>{_LINK_ID}){_LINK_SHAPE}\s*{_LINK_ARROW}\s*(?P<tgt>{_LINK_ID})")
# Lines that never carry a link, skipped so their punctuation cannot be
# mistaken for one (subgraph/style/class declarations use similar symbols).
_LINK_SKIP_LINE_RE = re.compile(
    r"^\s*(subgraph\b|end\b|classDef\b|class\b|style\b|click\b|linkStyle\b|direction\b|flowchart\b|graph\b|%%)",
    re.IGNORECASE,
)
_LINK_COMMENT_RE = re.compile(r"%%.*$")


def parse_link_directions(text: str) -> dict[tuple[str, str], list[bool]]:
    """Declared link directedness per ``(source, target)`` pair, in
    declaration order, from Mermaid flowchart/graph source text.

    ``True`` means the link carries an arrowhead (checked in full); ``False``
    means a bare open/dotted/thick link (direction/marker checks skipped).
    Known gap: chained (``A --> B --> C``) and fan-out (``A --> B & C``)
    links only resolve their first hop -- the rest are simply absent from
    the returned map, and ``direction_issues()`` already treats an edge with
    no matching entry as directed, the same safe default a missing source
    file gets.
    """
    directions: dict[tuple[str, str], list[bool]] = {}
    for raw_line in text.splitlines():
        line = _LINK_COMMENT_RE.sub("", raw_line)
        if _LINK_SKIP_LINE_RE.match(line):
            continue
        for match in _LINK_RE.finditer(line):
            key = (match.group("src"), match.group("tgt"))
            directed = bool(match.group("lhead") or match.group("rhead"))
            directions.setdefault(key, []).append(directed)
    return directions


def _edge_ordinal(edge_id: str) -> int:
    match = _EDGE_ID_RE.match(edge_id)
    return int(match.group(2)) if match else 0


def _match_declared_directions(
    edges: list[Edge], link_directions: dict[tuple[str, str], list[bool]]
) -> dict[str, bool]:
    """Map each edge id to whether the source declared it directed.

    mmdc does not number repeated links between the same pair sequentially
    from the SVG's ``_<ordinal>`` suffix alone (a second ``A--F`` link is
    ``L_A_F_2``, not ``L_A_F_1``) -- but it always keeps them in ascending,
    declaration-preserving order. Matching therefore goes by each edge's
    position within its own (source, target) group, not by the raw ordinal
    value: sort the group by ordinal, zip it against the source's
    declaration-ordered list for that same pair. An edge past the end of its
    pair's declared list (parse gap, e.g. a chained link) defaults to
    directed -- the safe, stricter choice.
    """
    groups: dict[tuple[str, str], list[Edge]] = {}
    for edge in edges:
        groups.setdefault((edge.source, edge.target), []).append(edge)
    result: dict[str, bool] = {}
    for key, group in groups.items():
        declared = link_directions.get(key, [])
        for position, edge in enumerate(sorted(group, key=lambda e: _edge_ordinal(e.id))):
            result[edge.id] = declared[position] if position < len(declared) else True
    return result


def _source_path_for(svg_path: Path) -> Path:
    """The sibling ``.mmd``: same directory, same stem."""
    return svg_path.with_suffix(".mmd")


def _mirrored_specs_path(svg_path: Path) -> Path | None:
    """The ``.mmd`` under the mirrored ``visuals/specs/`` tree, for a
    rendered asset stored under ``assets/generated/`` (the canonical
    asset-class layout, see visual-workflow.md's "Asset classes" section):
    same relative subpath and stem, only the leading ``assets/generated``
    path-segment pair replaced by ``visuals/specs``. ``None`` when
    *svg_path* does not sit under an ``assets/generated`` prefix at all --
    derived purely from the path, no config or flag.
    """
    parts = svg_path.parts
    for i in range(len(parts) - 1):
        if parts[i] == "assets" and parts[i + 1] == "generated":
            mirrored = (*parts[:i], "visuals", "specs", *parts[i + 2:])
            return Path(*mirrored).with_suffix(".mmd")
    return None


def _source_candidates(svg_path: Path) -> list[Path]:
    """Every place *svg_path*'s ``.mmd`` source could legitimately live, in
    lookup order: the cheaper sibling first, then the mirrored specs tree
    real pipeline runs actually use (renders and specs live in parallel
    directory trees, never siblings there -- see
    ``_mirrored_specs_path``)."""
    candidates = [_source_path_for(svg_path)]
    mirrored = _mirrored_specs_path(svg_path)
    if mirrored is not None:
        candidates.append(mirrored)
    return candidates


def load_link_directions(svg_path: Path) -> dict[tuple[str, str], list[bool]] | None:
    """Declared link directions from *svg_path*'s ``.mmd`` source (see
    ``_source_candidates``), or ``None`` when none of the candidate
    locations exist."""
    for source in _source_candidates(svg_path):
        if source.exists():
            return parse_link_directions(source.read_text(encoding="utf-8"))
    return None


def direction_issues(
    diagram: Diagram, link_directions: dict[tuple[str, str], list[bool]] | None = None
) -> list[PageIssue]:
    """Source/target endpoint containment and end-marker validity.

    *link_directions* (see ``parse_link_directions``) is ``None`` when no
    ``.mmd`` source was found: every edge is checked in full, the pre-#43
    strict rule. When it is provided, an edge the source declared undirected
    skips the endpoint-containment and end-marker checks entirely -- a
    legitimately undirected connector renders with no end marker at all, and
    the source is the only authority that can tell that apart from a broken
    one (see the module-level note above ``_LINK_RE``).
    """
    issues: list[PageIssue] = []
    by_id = {node.id: node for node in diagram.nodes}
    directed_by_edge = _match_declared_directions(diagram.edges, link_directions) if link_directions is not None else {}
    for edge in diagram.edges:
        if link_directions is not None and not directed_by_edge.get(edge.id, True):
            continue
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


def audit_diagram(
    diagram: Diagram, link_directions: dict[tuple[str, str], list[bool]] | None = None
) -> list[PageIssue]:
    obstruction, obstructed_pairs = obstruction_issues(diagram)
    return (
        list(diagram.parse_issues)
        + obstruction
        + crossing_issues(diagram)
        + clearance_issues(diagram, obstructed_pairs)
        + direction_issues(diagram, link_directions)
    )


def audit_connector_geometry(svg: Path) -> list[PageIssue]:
    """Audit a rendered Mermaid SVG file for connector defects."""
    link_directions = load_link_directions(svg)
    issues = audit_diagram(parse_svg(svg.read_text(encoding="utf-8")), link_directions)
    if link_directions is None:
        issues.append(
            PageIssue(
                INFO, CONNECTOR_DIRECTION_NO_SOURCE,
                f"'{svg.name}': no '.mmd' source found (sibling or mirrored visuals/specs tree); direction/marker check ran in strict mode",
            )
        )
    return issues


def run_geometry_audit(figure_name: str, audit: Callable[[], list[PageIssue]]) -> list[PageIssue]:
    """Run *audit* (a zero-argument connector-geometry audit call) and turn
    ANY exception it raises into one ``CONNECTOR_AUDIT_ERROR`` finding naming
    *figure_name*, instead of letting it escape uncaught (#43 T2).

    Both audit entry points -- ``visual_builder.py``'s isolated ``validate``
    command and ``validate_report.py``'s final-size stage -- call this same
    helper, so they can no longer diverge on which exceptions are "safe" to
    catch. Deliberately broad (``except Exception``, not a narrow tuple): a
    malformed-geometry crash is exactly what this guard exists to convert
    into a reported finding, whatever shape it takes -- an XML parse error,
    a decoding failure, or an arithmetic ``IndexError``/``ValueError`` deep
    in path-sampling on corrupted point data, none of which are ever a
    reason to abort an entire validation run over one bad file.
    """
    try:
        return audit()
    except Exception as exc:  # noqa: BLE001 - see docstring: deliberately broad
        return [PageIssue(FAILURE, CONNECTOR_AUDIT_ERROR, f"'{figure_name}': {type(exc).__name__}: {exc}")]
