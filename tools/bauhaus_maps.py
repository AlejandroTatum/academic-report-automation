#!/usr/bin/env python3
"""Bauhaus técnico maps: concept maps and process maps rendered from a YAML spec.

The house style for the maps that cost the most to draw by hand
(``skills/academic-visual-builder/references/bauhaus-maps.md``): Space Grotesk only,
paper background, one ink, three meaning colours (blue, red, green) and saffron for the
core subtitle. Colour encodes a concept family (concept map) or an actor lane (process map),
never one colour per node. The author writes content only: Graphviz (``dot -Tplain``) places
concept maps and a deterministic grid places process maps.

    bauhaus_maps.py render <spec.yml> --out <figure.svg> [--png <figure.png>]

A layout wider than 860 SVG units is never shrunk: a smaller scale would print the 12.5-unit
labels below 5.5 pt (``editorial_svg.check``), so the render fails and tells the author to
split the map or shorten names and details. ``--png`` rasterises with ``rsvg-convert -z 2``
under a generated fontconfig that loads ``assets/fonts``, so the PNG looks the same on any
machine and nothing is installed system-wide.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

import yaml
from editorial_svg import SpecError, check, text as _svg_text
from PIL import ImageFont

FONT_FILE = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "SpaceGrotesk[wght].ttf"
FONT = "Space Grotesk, sans-serif"
BG, INK, MUTED, WHITE = "#F6F4EE", "#121212", "#4A4A4A", "#FFFFFF"
SAFFRON = "#F2B233"
MEANING_COLOURS = {"blue": "#2247B5", "red": "#E0452A", "green": "#0D8B6C"}
LANE_COLOURS = {**MEANING_COLOURS, "ink": INK}
LANE_DEFAULTS = ("red", "blue", "green", "ink")  # by column; saffron is for decisions only
MAX_WIDTH = 860
PAD_X = 24
DASH = "6 5"
TOOL_TIMEOUT = 60  # seconds Graphviz or rsvg-convert may take before the render gives up


def text(x, y, value, size, weight, fill, anchor="middle", style="normal", spacing=0) -> str:
    return _svg_text(x, y, value, size, weight, fill, anchor, FONT, style, spacing)


def attr(value: object) -> str:
    """``value`` made safe inside a double-quoted XML attribute."""
    return escape(str(value), {'"': "&quot;"})


# --------------------------------------------------------------------------
# measuring, colour and spec validation helpers
# --------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _face(weight: int) -> ImageFont.FreeTypeFont:
    face = ImageFont.truetype(str(FONT_FILE), 100)
    face.set_variation_by_axes([weight])
    return face


def measure(value: str, size: float, weight: int, spacing: float = 0) -> float:
    """Advance width of ``value`` in Space Grotesk, in SVG units."""
    return _face(weight).getlength(value) * size / 100 + spacing * len(value)


def mix(colour: str, amount: float, base: str = WHITE) -> str:
    """``amount`` of ``colour`` over ``base`` (0 gives the base, 1 the colour)."""
    top = [int(colour[i:i + 2], 16) for i in (1, 3, 5)]
    under = [int(base[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(b + (a - b) * amount):02X}" for a, b in zip(top, under))


def _path(parent: str, key: object) -> str:
    return f"{parent}.{key}" if parent else str(key)


def _text(parent: dict, key: str, where: str = "", required: bool = True) -> str | None:
    value = parent.get(key)
    here = _path(where, key)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise SpecError(f"'{here}' is required")
        return None
    if isinstance(value, bool):
        raise SpecError(f"'{here}' must be text; YAML reads an unquoted yes/no as true/false, so put the word in quotes")
    if not isinstance(value, (str, int, float)):
        raise SpecError(f"'{here}' must be text")
    return str(value)


def _mapping(value: object, here: str) -> dict:
    if not isinstance(value, dict):
        raise SpecError(f"'{here}' must be a mapping")
    return value


def _list(parent: dict, key: str, required: bool = True) -> list:
    value = parent.get(key)
    if value in (None, [], {}) and required:
        raise SpecError(f"'{key}' is required")
    if value is None:
        return []
    if not isinstance(value, list):
        raise SpecError(f"'{key}' must be a list")
    return value


def _choice(value: str, options, here: str) -> str:
    if value not in options:
        raise SpecError(f"'{here}' is {value!r}; use one of {sorted(options)}")
    return value


def _flag(parent: dict, key: str, here: str) -> bool:
    value = parent.get(key, False)
    if not isinstance(value, bool):
        raise SpecError(f"'{here}.{key}' must be true or false")
    return value


# --------------------------------------------------------------------------
# shared SVG pieces
# --------------------------------------------------------------------------

def _open(width: float, height: float, colours: dict[str, str]) -> list[str]:
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:g}" height="{height:g}" viewBox="0 0 {width:g} {height:g}">',
             "<defs>"]
    for name, colour in colours.items():
        parts.append(f'<marker id="tip-{name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" '
                     f'orient="auto"><path d="M1,1 L9,5 L1,9" fill="none" stroke="{colour}" stroke-width="1.8"/></marker>')
    parts += ["</defs>", f'<rect width="{width:g}" height="{height:g}" fill="{BG}"/>']
    return parts


def _header(kind_label: str, title: str, width: float) -> list[str]:
    return [text(PAD_X, 34, kind_label, 12.5, 600, MEANING_COLOURS["red"], "start", spacing=2.2),
            text(PAD_X + 172, 34, title, 13.5, 400, MUTED, "start"),
            f'<line x1="{PAD_X}" y1="46" x2="{width - PAD_X:g}" y2="46" stroke="{mix(INK, 0.25, BG)}" stroke-width="1"/>']


def _header_end(title: str) -> float:
    return PAD_X + 172 + measure(title, 13.5, 400)


class Entry:
    """One legend item: a 22-unit swatch, a bold uppercase label and an optional meaning."""

    def __init__(self, key: str, label: str, colour: str, meaning: str | None = None, swatch: str = "line"):
        self.key, self.label, self.colour, self.meaning, self.swatch = key, label, colour, meaning, swatch

    label_x = 30

    @property
    def width(self) -> float:
        end = self.label_x + measure(self.label, 12.5, 700, 1.2)
        return end + (14 + measure(self.meaning, 12.5, 400) if self.meaning else 0)


def _legend_positions(entries: list[Entry], span: float) -> list[float]:
    """Left edges of the legend items: equal columns, pushed right when an entry runs long."""
    column = span / max(len(entries), 1)
    xs: list[float] = []
    for index, entry in enumerate(entries):
        floor = xs[-1] + entries[index - 1].width + 36 if xs else PAD_X
        xs.append(max(PAD_X + index * column, floor))
    return xs


def _legend(entries: list[Entry], xs: list[float], y: float) -> list[str]:
    parts = []
    for entry, x in zip(entries, xs):
        if entry.swatch == "diamond":
            parts.append(f'<polygon data-legend="{attr(entry.key)}" points="{x + 12:g},{y - 12:g} {x + 24:g},{y - 4:g} '
                         f'{x + 12:g},{y + 4:g} {x:g},{y - 4:g}" fill="{entry.colour}"/>')
            label_colour = INK
        else:
            parts.append(f'<line data-legend="{attr(entry.key)}" x1="{x:g}" y1="{y - 4:g}" x2="{x + 22:g}" y2="{y - 4:g}" '
                         f'stroke="{entry.colour}" stroke-width="4"/>')
            label_colour = entry.colour
        parts.append(text(x + entry.label_x, y, entry.label, 12.5, 700, label_colour, "start", spacing=1.2))
        if entry.meaning:
            parts.append(text(x + entry.label_x + measure(entry.label, 12.5, 700, 1.2) + 14, y, entry.meaning,
                              12.5, 400, MUTED, "start"))
    return parts


def _legend_end(entries: list[Entry], xs: list[float]) -> float:
    return xs[-1] + entries[-1].width if entries else 0


def _guard_width(width: float) -> None:
    if width > MAX_WIDTH:
        raise SpecError(f"layout is {width:.0f} units wide, over the {MAX_WIDTH}-unit limit; the figure is never "
                        "shrunk, so split the map or shorten names and details")


def _finish(parts: list[str]) -> str:
    parts.append("</svg>")
    svg = "\n".join(parts) + "\n"
    try:
        problems = check(svg)
    except ET.ParseError as error:
        raise SpecError(f"the drawing is not well-formed XML ({error}); check the spec for control characters") from error
    if problems:
        raise SpecError(f"the figure fails the print-size check: {problems[0]}")
    return svg


# --------------------------------------------------------------------------
# concept map
# --------------------------------------------------------------------------

CORE_PAD, NODE_PAD, CORE_H, NODE_H = 56, 44, 74, 62


def _concept_model(spec: dict) -> dict:
    title = _text(spec, "title")
    if not spec.get("core"):
        raise SpecError("'core' is required")
    core_spec = _mapping(spec["core"], "core")
    core = {"id": _text(core_spec, "id", "core"), "name": _text(core_spec, "name", "core"),
            "subtitle": _text(core_spec, "subtitle", "core", required=False), "level": "core", "family": None}
    families: dict[str, dict] = {}
    used_colours: dict[str, str] = {}
    if not spec.get("families"):
        raise SpecError("'families' is required")
    for key, item in _mapping(spec["families"], "families").items():
        here = _path("families", key)
        item = _mapping(item, here)
        label = _text(item, "label", here)
        colour = _choice(_text(item, "color", here), MEANING_COLOURS, f"{here}.color")
        if colour in used_colours:
            raise SpecError(f"'{here}.color' repeats colour {colour!r}")
        used_colours[colour] = str(key)
        families[str(key)] = {"label": label, "colour": colour, "meaning": _text(item, "meaning", here, required=False)}

    concepts = [core]
    seen = {core["id"]}
    for index, item in enumerate(_list(spec, "concepts")):
        here = f"concepts[{index}]"
        item = _mapping(item, here)
        concept_id = _text(item, "id", here)
        if concept_id in seen:
            raise SpecError(f"'{here}.id' repeats id {concept_id!r}")
        seen.add(concept_id)
        name = _text(item, "name", here)
        family = _choice(_text(item, "family", here), families, f"{here}.family")
        level = _choice(_text(item, "level", here, required=False) or "leaf", ("key", "leaf"), f"{here}.level")
        concepts.append({"id": concept_id, "name": name, "detail": _text(item, "detail", here, required=False),
                         "family": family, "level": level})

    links, pairs = [], set()
    for index, item in enumerate(_list(spec, "links")):
        here = f"links[{index}]"
        item = _mapping(item, here)
        label = _text(item, "label", here)
        ends = {}
        for end in ("from", "to"):
            ends[end] = _text(item, end, here)
            if ends[end] not in seen:
                raise SpecError(f"'{here}.{end}' refers to unknown id {ends[end]!r}")
        cross = _flag(item, "cross", here)
        if ends["from"] == ends["to"]:
            raise SpecError(f"'{here}' links {ends['from']!r} to itself")
        if (ends["from"], ends["to"]) in pairs:
            raise SpecError(f"'{here}' repeats the link {ends['from']!r} -> {ends['to']!r}")
        pairs.add((ends["from"], ends["to"]))
        links.append({"from": ends["from"], "to": ends["to"], "label": label, "cross": cross})

    spine = spec.get("spine")
    if spine is not None and not isinstance(spine, list):
        raise SpecError("'spine' must be a list of ids")
    for index, concept_id in enumerate(spine or []):
        if str(concept_id) not in seen:
            raise SpecError(f"'spine[{index}]' refers to unknown id {str(concept_id)!r}")
    return {"title": title, "families": families, "concepts": concepts, "links": links,
            "spine": [str(i) for i in spine or []]}


def _box_size(concept: dict) -> tuple[float, float]:
    if concept["level"] == "core":
        sub = (concept["subtitle"] or "").upper()
        width = max(measure(concept["name"], 23, 700), measure(sub, 12.5, 600, 1.6) if sub else 0) + CORE_PAD
        return width, CORE_H if sub else 60
    detail = concept["detail"]
    width = max(measure(concept["name"], 16.5, 700), measure(detail, 14, 400) if detail else 0) + NODE_PAD
    return width, NODE_H if detail else 48


def _run_tool(tool: str, label: str, args: list[str], **options) -> subprocess.CompletedProcess:
    """Run an external tool with a timeout; a missing, unrunnable or hung tool is a SpecError naming it."""
    try:
        return subprocess.run([tool, *args], capture_output=True, timeout=TOOL_TIMEOUT, **options)
    except subprocess.TimeoutExpired as error:
        hint = "; simplify the map" if tool == "dot" else ""
        raise SpecError(f"{label} did not finish within {TOOL_TIMEOUT:g} s{hint}") from error
    except OSError as error:
        raise SpecError(f"{label} could not be run: {error}") from error


def _dot(model: dict) -> tuple[float, float, dict, dict]:
    """Run Graphviz on fixed-size boxes and fixed-size link labels; return graph size, boxes and links."""
    if shutil.which("dot") is None:
        raise SpecError("Graphviz 'dot' was not found on PATH; install graphviz")
    name = {c["id"]: f"n{i}" for i, c in enumerate(model["concepts"])}
    lines = ["digraph G {", "rankdir=TB; nodesep=0.16; ranksep=0.55; splines=spline; ordering=out;",
             'node [shape=box fixedsize=true label=""];', "edge [arrowhead=none fontsize=14];"]
    for concept in model["concepts"]:
        w, h = _box_size(concept)
        group = ' group="spine"' if concept["id"] in model["spine"] else ""
        lines.append(f"{name[concept['id']]} [width={w / 72:.3f} height={h / 72:.3f}{group}];")
    for link in model["links"]:
        cell = (f'<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="0"><TR><TD WIDTH="{round(measure(link["label"], 12.5, 500) + 14)}" '
                'HEIGHT="20"></TD></TR></TABLE>>')
        extra = " constraint=false" if link["cross"] else ""
        lines.append(f'{name[link["from"]]} -> {name[link["to"]]} [label={cell}{extra}];')
    lines.append("}")
    done = _run_tool("dot", "Graphviz 'dot'", ["-Tplain"], input="\n".join(lines), text=True)
    if done.returncode != 0:
        raise SpecError(f"Graphviz failed: {done.stderr.strip()}")
    ids = {v: k for k, v in name.items()}
    size, boxes, links = (0.0, 0.0), {}, {}
    for row in done.stdout.splitlines():
        parts = row.split()
        if parts[0] == "graph":
            size = (float(parts[2]) * 72, float(parts[3]) * 72)
        elif parts[0] == "node":
            boxes[ids[parts[1]]] = tuple(float(v) * 72 for v in parts[2:6])
        elif parts[0] == "edge":
            count = int(parts[3])
            points = [(float(parts[4 + 2 * i]) * 72, float(parts[5 + 2 * i]) * 72) for i in range(count)]
            rest = parts[4 + 2 * count:]
            # Trailing fields are "style color"; a label adds "<name> xl yl" before them.
            label = (float(rest[-4]) * 72, float(rest[-3]) * 72) if len(rest) > 2 else None
            links[(ids[parts[1]], ids[parts[2]])] = (points, label)
    return size[0], size[1], boxes, links


def _bezier(points: list[tuple[float, float]]) -> str:
    d = f"M{points[0][0]:.1f},{points[0][1]:.1f} "
    return d + " ".join("C" + " ".join(f"{points[j][0]:.1f},{points[j][1]:.1f}" for j in (i, i + 1, i + 2))
                        for i in range(1, len(points) - 2, 3))


def concept_map(spec: dict) -> str:
    model = _concept_model(spec)
    graph_w, graph_h, boxes, links = _dot(model)
    families = model["families"]
    entries = [Entry(key, item["label"], MEANING_COLOURS[item["colour"]], item["meaning"]) for key, item in families.items()]
    inner = graph_w
    xs = _legend_positions(entries, inner)
    width = max(graph_w + 2 * PAD_X, _header_end(model["title"]) + PAD_X, _legend_end(entries, xs) + PAD_X)
    _guard_width(width)
    shift = (width - graph_w - 2 * PAD_X) / 2 + PAD_X
    pad_top, pad_bottom = 76, 64
    height = graph_h + pad_top + pad_bottom

    def pt(x, y):
        return x + shift, graph_h - y + pad_top

    by_id = {c["id"]: c for c in model["concepts"]}

    def colour_of(concept_id: str) -> tuple[str, str]:
        concept = by_id[concept_id]
        if concept["level"] == "core":
            return "ink", INK
        name = families[concept["family"]]["colour"]
        return name, MEANING_COLOURS[name]

    used = {"ink": INK, **{families[c["family"]]["colour"]: MEANING_COLOURS[families[c["family"]]["colour"]]
                           for c in model["concepts"] if c["family"]}}
    out = _open(width, height, used)
    out += _header("MAPA CONCEPTUAL", model["title"], width)
    for link in model["links"]:
        points, label = links[(link["from"], link["to"])]
        name, colour = colour_of(link["from"])
        key = f"{link['from']}>{link['to']}"
        dash = f' stroke-dasharray="{DASH}"' if link["cross"] else ""
        out.append(f'<path data-link="{attr(key)}" d="{_bezier([pt(*q) for q in points])}" fill="none" stroke="{colour}" '
                   f'stroke-width="1.6"{dash} marker-end="url(#tip-{name})"/>')
        lx, ly = pt(*label)
        shade = MUTED if name == "ink" else mix(colour, 0.85, "#000000")
        out.append(text(lx, ly + 4, link["label"], 12.5, 500, shade).replace("<text ", f'<text data-label="{attr(key)}" ', 1))

    for concept in model["concepts"]:
        cx, cy, w, h = boxes[concept["id"]]
        x, y = pt(cx, cy)
        x, y = x - w / 2, y - h / 2
        mid, node_id = x + w / 2, attr(concept["id"])
        if concept["level"] == "core":
            out.append(f'<rect data-node="{node_id}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{INK}"/>')
            if concept["subtitle"]:
                out.append(text(mid, y + 36, concept["name"], 23, 700, WHITE))
                out.append(text(mid, y + 58, concept["subtitle"].upper(), 12.5, 600, SAFFRON, spacing=1.6))
            else:
                out.append(text(mid, y + 37, concept["name"], 23, 700, WHITE))
            continue
        colour = MEANING_COLOURS[families[concept["family"]]["colour"]]
        solid = concept["level"] == "key"
        stroke = "" if solid else f' stroke="{colour}" stroke-width="3"'
        out.append(f'<rect data-node="{node_id}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                   f'fill="{colour if solid else WHITE}"{stroke}/>')
        if not solid:
            out.append(f'<rect data-corner="{node_id}" x="{x:.1f}" y="{y:.1f}" width="14" height="14" fill="{colour}"/>')
        name_y = y + (27 if concept["detail"] else 30)
        out.append(text(mid, name_y, concept["name"], 16.5, 700, WHITE if solid else INK))
        if concept["detail"]:
            out.append(text(mid, y + 47, concept["detail"], 14, 400, mix(WHITE, 0.88, colour) if solid else MUTED))
    out += _legend(entries, xs, height - 26)
    return _finish(out)


# --------------------------------------------------------------------------
# process map
# --------------------------------------------------------------------------

TOP, ROW_H, BOX_H, DIAMOND_H, LANE_GAP, SIDE = 112, 92, 60, 38, 10, 15
RESERVED_LANE_IDS = {"artifact": "artifact lane", "decision": "decision legend entry"}  # ids the drawing already uses
SLOT_Y = (0, -14, 14, -24, 24)  # where connectors meet a step side, from its middle; one slot per connector
CORRIDOR_STEP = 5  # gap between two connectors that run side by side down a lane margin
LABEL_SIZE, LABEL_ABOVE, LABEL_BELOW = 12.5, 12, 1  # a label's box spans baseline - 12 .. baseline + 1


def _process_model(spec: dict) -> dict:
    title = _text(spec, "title")
    raw_lanes = _list(spec, "lanes")
    if not 2 <= len(raw_lanes) <= 3:
        raise SpecError(f"'lanes' needs 2 or 3 actor lanes, not {len(raw_lanes)}")
    lanes, lane_ids, used = [], set(), {}

    def chosen_colour(item: dict, here: str) -> str | None:
        name = _text(item, "color", here, required=False)
        if name is None:
            return None
        _choice(name, LANE_COLOURS, f"{here}.color")
        if name in used:
            raise SpecError(f"'{here}.color' repeats colour {name!r}")
        used[name] = here
        return name

    for index, item in enumerate(raw_lanes):
        here = f"lanes[{index}]"
        item = _mapping(item, here)
        lane_id = _text(item, "id", here)
        if lane_id in RESERVED_LANE_IDS:
            raise SpecError(f"'{here}.id' is {lane_id!r}, which names the {RESERVED_LANE_IDS[lane_id]}; use another id")
        if lane_id in lane_ids:
            raise SpecError(f"'{here}.id' repeats id {lane_id!r}")
        lane_ids.add(lane_id)
        label = _text(item, "label", here)
        lanes.append({"id": lane_id, "label": label, "short": _text(item, "short", here, required=False) or label,
                      "colour": chosen_colour(item, here)})
    artifact_lane = None
    if spec.get("artifact_lane"):
        item = _mapping(spec["artifact_lane"], "artifact_lane")
        label = _text(item, "label", "artifact_lane")
        artifact_lane = {"id": "artifact", "label": label,
                         "short": _text(item, "short", "artifact_lane", required=False) or label,
                         "colour": chosen_colour(item, "artifact_lane")}

    spare = iter(name for name in LANE_DEFAULTS if name not in used)  # lanes without a colour, in column order
    for lane in [*lanes, *([artifact_lane] if artifact_lane else [])]:
        lane["colour"] = lane["colour"] or next(spare)

    raw_steps = _list(spec, "steps")
    if len(raw_steps) < 2:
        raise SpecError("'steps' needs at least 2 steps")
    steps, step_ids = [], set()
    for index, item in enumerate(raw_steps):
        here = f"steps[{index}]"
        item = _mapping(item, here)
        step_id = _text(item, "id", here)
        if step_id in step_ids:
            raise SpecError(f"'{here}.id' repeats id {step_id!r}")
        step_ids.add(step_id)
        title_text = _text(item, "title", here)
        lane = _choice(_text(item, "lane", here), lane_ids, f"{here}.lane")
        decision = _flag(item, "decision", here)
        artifact = _text(item, "artifact", here, required=False)
        if artifact and decision:
            raise SpecError(f"'{here}.artifact' is not allowed on a decision")
        if artifact and artifact_lane is None:
            raise SpecError(f"'{here}.artifact' needs an 'artifact_lane'")
        steps.append({"id": step_id, "title": title_text, "lane": lane, "decision": decision, "artifact": artifact,
                      "detail": _text(item, "detail", here, required=False)})

    flow, pairs = [], set()
    for index, item in enumerate(_list(spec, "flow")):
        here = f"flow[{index}]"
        item = _mapping(item, here)
        ends = {}
        for end in ("from", "to"):
            ends[end] = _text(item, end, here)
            if ends[end] not in step_ids:
                raise SpecError(f"'{here}.{end}' refers to unknown id {ends[end]!r}")
        if ends["from"] == ends["to"]:
            raise SpecError(f"'{here}' links {ends['from']!r} to itself")
        if (ends["from"], ends["to"]) in pairs:
            raise SpecError(f"'{here}' repeats the flow {ends['from']!r} -> {ends['to']!r}")
        pairs.add((ends["from"], ends["to"]))
        flow.append({"from": ends["from"], "to": ends["to"], "label": _text(item, "label", here, required=False)})
    return {"title": title, "lanes": lanes, "artifact_lane": artifact_lane, "steps": steps, "flow": flow}


def _box_need(step: dict) -> float:
    """Narrowest box (in units) that holds the step's text, so nothing is clipped or shrunk."""
    if step["decision"]:
        return measure(step["title"], 14.5, 700) / 0.78 + 4
    detail = measure(step["detail"], 13.5, 400) if step["detail"] else 0
    return 44 + max(measure(step["title"], 15.5, 700), detail) + 14


def process_map(spec: dict) -> str:
    model = _process_model(spec)
    columns = [*model["lanes"], *([model["artifact_lane"]] if model["artifact_lane"] else [])]
    n = len(columns)
    box_need = max(_box_need(s) for s in model["steps"])
    corridor_slots, corridors = _corridor_plan(model)
    margin = max(SIDE, CORRIDOR_STEP * (corridors + 1))  # room beside the boxes for every concurrent corridor
    lane_need = max([box_need + 2 * margin, *(measure(c["label"], 12.5, 700, 1.4) + 24 for c in columns)])
    art_widths = [14 + measure(s["artifact"], 13.5, 500) + 16 + 14 for s in model["steps"] if s["artifact"]]
    if art_widths:
        lane_need = max(lane_need, max(art_widths) + 50)
    _guard_width(2 * PAD_X + n * lane_need + (n - 1) * LANE_GAP)

    entries = [Entry(c["id"], c["short"], LANE_COLOURS[c["colour"]]) for c in columns]
    if any(s["decision"] for s in model["steps"]):
        entries.append(Entry("decision", "DECISIÓN", SAFFRON, swatch="diamond"))
    xs = _legend_positions(entries, MAX_WIDTH - 2 * PAD_X)
    _guard_width(max(_legend_end(entries, xs) + PAD_X, _header_end(model["title"]) + PAD_X))

    width = MAX_WIDTH
    lane_w = (width - 2 * PAD_X - (n - 1) * LANE_GAP) / n
    box_w = max(min(lane_w - 2 * margin, 260), box_need)
    lane_x = {c["id"]: PAD_X + i * (lane_w + LANE_GAP) for i, c in enumerate(columns)}
    height = TOP + 24 + len(model["steps"]) * ROW_H + 56
    by_lane = {c["id"]: c for c in columns}
    used = {"ink": INK, **{c["colour"]: LANE_COLOURS[c["colour"]] for c in columns}}
    out = _open(width, height, used)
    out += _header("MAPA DE PROCESO", model["title"], width)
    for c in columns:
        colour, x = LANE_COLOURS[c["colour"]], lane_x[c["id"]]
        out.append(f'<rect data-lane-header="{attr(c["id"])}" x="{x:.1f}" y="{TOP - 44}" width="{lane_w:.1f}" height="34" fill="{colour}"/>')
        out.append(text(x + lane_w / 2, TOP - 22, c["label"], 12.5, 700, WHITE, spacing=1.4))
        out.append(f'<rect data-lane="{attr(c["id"])}" x="{x:.1f}" y="{TOP - 10}" width="{lane_w:.1f}" height="{height - TOP - 40}" '
                   f'fill="{mix(colour, 0.05, BG)}"/>')

    nodes, number, obstacles, art_lines = {}, 0, [], []
    for row, step in enumerate(model["steps"]):
        lane = by_lane[step["lane"]]
        colour = LANE_COLOURS[lane["colour"]]
        cx, top = lane_x[lane["id"]] + lane_w / 2, TOP + 24 + row * ROW_H
        cy = top + BOX_H / 2
        half_w = box_w / 2 - 2 if step["decision"] else box_w / 2
        nodes[step["id"]] = {"row": row, "lane": lane["id"], "cx": cx, "cy": cy, "hw": half_w,
                             "hh": DIAMOND_H if step["decision"] else BOX_H / 2, "decision": step["decision"],
                             "artifact": bool(step["artifact"])}
        sid = attr(step["id"])
        if step["decision"]:
            out.append(f'<polygon data-node="{sid}" points="{cx:.1f},{cy - DIAMOND_H:.1f} {cx + half_w:.1f},{cy:.1f} '
                       f'{cx:.1f},{cy + DIAMOND_H:.1f} {cx - half_w:.1f},{cy:.1f}" fill="{SAFFRON}"/>')
            out.append(text(cx, cy + 5, step["title"], 14.5, 700, INK))
            continue
        number += 1
        x = cx - box_w / 2
        out.append(f'<rect data-node="{sid}" x="{x:.1f}" y="{top:.1f}" width="{box_w:.1f}" height="{BOX_H}" fill="{WHITE}" '
                   f'stroke="{colour}" stroke-width="3"/>')
        out.append(f'<rect data-corner="{sid}" x="{x:.1f}" y="{top:.1f}" width="30" height="30" fill="{colour}"/>')
        out.append(text(x + 15, top + 21, number, 15, 700, WHITE).replace("<text ", f'<text data-number="{sid}" ', 1))
        out.append(text(x + 44, top + 25, step["title"], 15.5, 700, INK, "start"))
        if step["detail"]:
            out.append(text(x + 44, top + 46, step["detail"], 13.5, 400, MUTED, "start"))
        if step["artifact"]:
            art = model["artifact_lane"]
            art_colour = LANE_COLOURS[art["colour"]]
            ax, aw, fold = lane_x["artifact"] + 25, lane_w - 50, 16
            obstacles.append((ax - 2, cy - 21, ax + aw + 2, cy + 21))
            art_lines.append([(x + box_w + 2, cy), (ax, cy)])
            out.append(f'<line data-edge="artifact:{sid}" x1="{x + box_w + 2:.1f}" y1="{cy:.1f}" x2="{ax:.1f}" y2="{cy:.1f}" '
                       f'stroke="{art_colour}" stroke-width="1.6" stroke-dasharray="4 4" marker-end="url(#tip-{art["colour"]})"/>')
            out.append(f'<path data-artifact="{sid}" d="M{ax:.1f},{cy - 19:.1f} H{ax + aw - fold:.1f} L{ax + aw:.1f},{cy - 19 + fold:.1f} '
                       f'V{cy + 19:.1f} H{ax:.1f} Z" fill="{WHITE}" stroke="{art_colour}" stroke-width="2.4"/>')
            out.append(f'<path data-fold="{sid}" d="M{ax + aw - fold:.1f},{cy - 19:.1f} V{cy - 19 + fold:.1f} H{ax + aw:.1f}" '
                       f'fill="{art_colour}" stroke="{art_colour}" stroke-width="2.4"/>')
            out.append(text(ax + 14, cy + 5, step["artifact"], 13.5, 500, INK, "start"))

    routes = _plan_routes(model, nodes, lane_x, lane_w, margin, corridor_slots, corridors)
    obstacles += [(n["cx"] - n["hw"] - 2, n["cy"] - n["hh"] - 2, n["cx"] + n["hw"] + 2, n["cy"] + n["hh"] + 2)
                  for n in nodes.values()]
    spots = _place_labels(model, routes, obstacles, art_lines)
    for index, (link, route) in enumerate(zip(model["flow"], routes)):
        d = f"M{route[0][0]:.1f},{route[0][1]:.1f}" + "".join(
            f" H{x:.1f}" if abs(y - route[i][1]) < 1e-6 else f" V{y:.1f}" for i, (x, y) in enumerate(route[1:]))
        key = attr(f"{link['from']}>{link['to']}")
        out.append(f'<path data-edge="{key}" d="{d}" fill="none" stroke="{INK}" stroke-width="1.8" marker-end="url(#tip-ink)"/>')
        if index in spots:
            x, y = spots[index]
            out.append(text(x, y, link["label"].upper(), LABEL_SIZE, 700, INK, "start", spacing=1.2)
                       .replace("<text ", f'<text data-label="{key}" ', 1))
    out += _legend(entries, xs, height - 22)
    return _finish(out)


def _corridor_plan(model: dict) -> tuple[dict, int]:
    """Give every row-skipping and back edge its own corridor, and count the corridors a lane side needs.

    A skip edge runs down the left margin of its source lane; a back edge runs up the right margin of
    the rightmost lane of its two steps. Edges whose rows overlap on the same lane side take different
    slots (greedy interval colouring), so no two corridors share a line.
    """
    row = {s["id"]: i for i, s in enumerate(model["steps"])}
    lane_of = {s["id"]: s["lane"] for s in model["steps"]}
    order = {lane["id"]: i for i, lane in enumerate(model["lanes"])}
    wanted: dict[tuple[str, str], list[tuple[int, int, int]]] = {}
    for index, link in enumerate(model["flow"]):
        ra, rb = row[link["from"]], row[link["to"]]
        if rb == ra + 1:
            continue
        if rb > ra:
            wanted.setdefault((lane_of[link["from"]], "left"), []).append((ra, rb, index))
        else:
            lane = max(lane_of[link["from"]], lane_of[link["to"]], key=order.get)
            wanted.setdefault((lane, "right"), []).append((rb, ra, index))
    slots, widest = {}, 0
    for key, items in wanted.items():
        last_rows: list[int] = []  # last row each slot is busy until
        for first, last, index in sorted(items):
            for slot, busy_until in enumerate(last_rows):
                if busy_until < first:
                    last_rows[slot] = last
                    break
            else:
                slot = len(last_rows)
                last_rows.append(last)
            slots[index] = (key, slot)
        widest = max(widest, len(last_rows))
    return slots, widest


def _plan_routes(model: dict, nodes: dict, lane_x: dict, lane_w: float, margin: float, corridor_slots: dict,
                 corridors: int) -> list[list[tuple[float, float]]]:
    """Orthogonal connector from each flow's source step to its target step, as lists of vertices.

    One step per row means a row holds no other node, so the only obstacles are the vertical runs:
    those stay in the gap between rows (adjacent rows) or in a lane margin (rows skipped, or a back
    edge to an earlier row). Connectors that meet the same side of a step use different slots, and
    the slot in the middle of a side stays free for the dashed connector to the step's artifact.
    """
    tip = 2  # the arrow stops this far from the border of the step
    order = {lane["id"]: i for i, lane in enumerate(model["lanes"])}
    attached: dict[tuple[str, str], list[int]] = {}
    sides: dict[int, tuple[str, str]] = {}
    for index, link in enumerate(model["flow"]):
        a, b = nodes[link["from"]], nodes[link["to"]]
        if b["row"] == a["row"] + 1:
            continue
        if b["row"] > a["row"]:
            sides[index] = ("left", "left" if order[b["lane"]] >= order[a["lane"]] else "right")
        else:
            sides[index] = ("right", "right")
        attached.setdefault((link["from"], sides[index][0]), []).append(index)
        attached.setdefault((link["to"], sides[index][1]), []).append(index)
    slot_y = {}
    for (step_id, side), indexes in attached.items():
        free = SLOT_Y[1:] if side == "right" and nodes[step_id]["artifact"] else SLOT_Y
        if len(indexes) > len(free):
            raise SpecError(f"step {step_id!r} has {len(indexes)} connectors on its {side} side and only {len(free)} fit "
                            "apart; split the map or route some flows through another step")
        for slot, index in zip(free, indexes):
            slot_y[(index, step_id)] = slot

    def border(node: dict, side: str, dy: float) -> float:
        reach = node["hw"] * (1 - abs(dy) / node["hh"]) if node["decision"] else node["hw"]
        return node["cx"] + (reach if side == "right" else -reach)

    routes = []
    for index, link in enumerate(model["flow"]):
        a, b = nodes[link["from"]], nodes[link["to"]]
        if index not in sides:
            y0, y1 = a["cy"] + a["hh"], b["cy"] - b["hh"]
            if a["cx"] == b["cx"]:
                routes.append([(a["cx"], y0), (b["cx"], y1 - tip)])
            else:
                mid = (y0 + y1) / 2
                routes.append([(a["cx"], y0), (a["cx"], mid), (b["cx"], mid), (b["cx"], y1 - tip)])
            continue
        (lane_id, side), slot = corridor_slots[index]
        gap = margin * (slot + 1) / (corridors + 1)
        run = lane_x[lane_id] + gap if side == "left" else lane_x[lane_id] + lane_w - gap
        a_side, b_side = sides[index]
        ya, yb = a["cy"] + slot_y[(index, link["from"])], b["cy"] + slot_y[(index, link["to"])]
        entry = border(b, b_side, yb - b["cy"]) + (tip if b_side == "right" else -tip)
        routes.append([(border(a, a_side, ya - a["cy"]), ya), (run, ya), (run, yb), (entry, yb)])
    return routes


def _place_labels(model: dict, routes: list, boxes: list, lines: list) -> dict[int, tuple[float, float]]:
    """Left x and baseline for every branch label, in flow order.

    A label sits beside its own connector, nearest the source first, on the first spot where its box
    touches no connector, arrow tip, step, document or earlier label. No spot is an error, never an overlap.
    """
    segments = [seg for route in routes for seg in zip(route, route[1:])] + [tuple(line) for line in lines]
    tips = [(x - 9, y - 9, x + 9, y + 9) for x, y in [route[-1] for route in routes] + [line[-1] for line in lines]]
    taken = [*boxes, *tips]
    spots: dict[int, tuple[float, float]] = {}
    for index, (link, route) in enumerate(zip(model["flow"], routes)):
        if not link["label"]:
            continue
        width = measure(link["label"].upper(), LABEL_SIZE, 700, 1.2)
        for left, baseline in _spots(route, width):
            rect = (left, baseline - LABEL_ABOVE, left + width, baseline + LABEL_BELOW)
            if _free(rect, segments, taken):
                spots[index] = (left, baseline)
                taken.append(rect)
                break
        else:
            raise SpecError(f"'flow[{index}].label' has no free spot beside its connector; shorten it or move the steps")
    return spots


def _spots(route: list, width: float):
    """Candidate label origins beside each segment of ``route``, nearest to the segment's start first."""
    for (x0, y0), (x1, y1) in zip(route, route[1:]):
        if abs(y0 - y1) < 1e-6:  # horizontal: above the line, then below it
            direction, span = (1 if x1 > x0 else -1), abs(x1 - x0)
            for along in range(8, int(span - width - 4) + 1, 6):
                left = x0 + along if direction > 0 else x0 - along - width
                yield left, y0 - 6
                yield left, y0 + 7 + LABEL_ABOVE
        else:  # vertical: right of the line, then left of it
            direction, span = (1 if y1 > y0 else -1), abs(y1 - y0)
            for side in (1, -1):
                for along in range(12, int(span - 6) + 1, 6):
                    yield (x0 + 7 if side > 0 else x0 - 7 - width), y0 + direction * along + 6


def _free(rect: tuple, segments: list, boxes: list) -> bool:
    x0, y0, x1, y1 = rect
    reach = 2.5  # half a connector stroke plus a hair of air
    for (ax, ay), (bx, by) in segments:
        if min(ax, bx) - reach < x1 and max(ax, bx) + reach > x0 and min(ay, by) - reach < y1 and max(ay, by) + reach > y0:
            return False
    return not any(bx0 < x1 and x0 < bx1 and by0 < y1 and y0 < by1 for bx0, by0, bx1, by1 in boxes)


# --------------------------------------------------------------------------
# rendering, PNG and CLI
# --------------------------------------------------------------------------

LAYOUTS = {"concept_map": concept_map, "process_map": process_map}


def render(spec: dict) -> str:
    kind = spec.get("kind")
    if kind in (None, ""):
        raise SpecError(f"'kind' is required; use one of {sorted(LAYOUTS)}")
    if not isinstance(kind, str):
        raise SpecError(f"'kind' must be text; use one of {sorted(LAYOUTS)}")
    if kind not in LAYOUTS:
        raise SpecError(f"unknown kind {kind!r}; use one of {sorted(LAYOUTS)}")
    return LAYOUTS[kind](spec)


def write_fontconfig(directory: Path) -> Path:
    """A fontconfig file that adds the repo's font folder to the system fonts."""
    conf = directory / "fonts.conf"
    conf.write_text('<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
                    f"<fontconfig><dir>{escape(str(FONT_FILE.parent))}</dir>"
                    '<include ignore_missing="yes">/etc/fonts/fonts.conf</include>'
                    f'<cachedir>{escape(str(directory / "cache"))}</cachedir></fontconfig>\n', encoding="utf-8")
    return conf


def rasterize(svg: str) -> bytes:
    """The PNG at twice the SVG size, drawn with the repo font through a generated fontconfig."""
    with tempfile.TemporaryDirectory(prefix="bauhaus-maps-") as scratch:
        scratch_dir = Path(scratch)
        env = dict(os.environ, FONTCONFIG_FILE=str(write_fontconfig(scratch_dir)))
        done = _run_tool("rsvg-convert", "rsvg-convert", ["-z", "2", "-o", str(scratch_dir / "fig.png")],
                         input=svg.encode("utf-8"), env=env)
        if done.returncode != 0:
            raise SpecError(f"rsvg-convert failed: {done.stderr.decode('utf-8', 'replace').strip()}")
        return (scratch_dir / "fig.png").read_bytes()


def publish(files: list[tuple[Path, bytes]]) -> None:
    """Write every file or none: each goes to a temporary file beside its destination, then all move into place."""
    for path, _ in files:
        if path.is_dir():
            raise SpecError(f"cannot write {path}: it is a directory")
    staged: list[tuple[Path, Path]] = []
    placed: list[Path] = []
    try:
        for path, data in files:
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False)
            staged.append((Path(handle.name), path))
            with handle:
                handle.write(data)
        for temporary, path in staged:
            fresh = not path.exists()
            os.replace(temporary, path)
            if fresh:
                placed.append(path)
    except OSError as error:
        for path in placed:
            path.unlink(missing_ok=True)
        raise SpecError(f"cannot write the output: {error}") from error
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def load_spec(path: Path) -> dict:
    try:
        spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise SpecError(f"cannot read the spec: {error}") from error
    except yaml.YAMLError as error:
        raise SpecError(f"the spec is not valid YAML: {error}") from error
    if spec is None:
        return {}
    if not isinstance(spec, dict):
        raise SpecError("the spec must be a YAML mapping")
    return spec


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Bauhaus técnico concept and process maps from a YAML spec.")
    sub = parser.add_subparsers(dest="command", required=True)
    render_cmd = sub.add_parser("render", help="render a concept_map or process_map spec to SVG (and PNG)")
    render_cmd.add_argument("spec", type=Path)
    render_cmd.add_argument("--out", type=Path, required=True)
    render_cmd.add_argument("--png", type=Path, help="also rasterise at 2x with the repo font")
    args = parser.parse_args(argv)
    try:
        if args.png and shutil.which("rsvg-convert") is None:
            raise SpecError("rsvg-convert was not found on PATH; install librsvg to use --png")
        svg = render(load_spec(args.spec))
        files = [(args.out, svg.encode("utf-8"))]
        if args.png:
            files.append((args.png, rasterize(svg)))
        publish(files)
    except (SpecError, OSError) as error:
        print(f"bauhaus_maps: {error}", file=sys.stderr)
        return 2
    print(f"rendered {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
