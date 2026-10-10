#!/usr/bin/env python3
"""Bauhaus técnico maps: concept maps rendered from a YAML spec with automatic layout.

The house style for the maps that cost the most to draw by hand
(``skills/academic-visual-builder/references/bauhaus-maps.md``): Space Grotesk only,
paper background, one ink, three meaning colours (blue, red, green) and saffron for the
core subtitle. Colour encodes a concept family, never one colour per node. The author
writes content only; Graphviz (``dot -Tplain``) places the nodes and the tool draws them.

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
MAX_WIDTH = 860
PAD_X = 24
DASH = "6 5"


def text(x, y, value, size, weight, fill, anchor="middle", style="normal", spacing=0) -> str:
    return _svg_text(x, y, value, size, weight, fill, anchor, FONT, style, spacing)


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
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
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
            parts.append(f'<polygon data-legend="{entry.key}" points="{x + 12:g},{y - 12:g} {x + 24:g},{y - 4:g} '
                         f'{x + 12:g},{y + 4:g} {x:g},{y - 4:g}" fill="{entry.colour}"/>')
            label_colour = INK
        else:
            parts.append(f'<line data-legend="{entry.key}" x1="{x:g}" y1="{y - 4:g}" x2="{x + 22:g}" y2="{y - 4:g}" '
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
    problems = check(svg)
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
    done = subprocess.run(["dot", "-Tplain"], input="\n".join(lines), capture_output=True, text=True)
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
        out.append(f'<path data-link="{escape(key)}" d="{_bezier([pt(*q) for q in points])}" fill="none" stroke="{colour}" '
                   f'stroke-width="1.6"{dash} marker-end="url(#tip-{name})"/>')
        lx, ly = pt(*label)
        shade = MUTED if name == "ink" else mix(colour, 0.85, "#000000")
        out.append(text(lx, ly + 4, link["label"], 12.5, 500, shade).replace("<text ", f'<text data-label="{escape(key)}" ', 1))

    for concept in model["concepts"]:
        cx, cy, w, h = boxes[concept["id"]]
        x, y = pt(cx, cy)
        x, y = x - w / 2, y - h / 2
        mid, node_id = x + w / 2, escape(concept["id"])
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
# rendering, PNG and CLI
# --------------------------------------------------------------------------

LAYOUTS = {"concept_map": concept_map}


def render(spec: dict) -> str:
    kind = spec.get("kind")
    if kind in (None, ""):
        raise SpecError(f"'kind' is required; use one of {sorted(LAYOUTS)}")
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


def rasterize(svg: str, png: Path) -> None:
    """Write ``png`` at twice the SVG size, using the repo font through a generated fontconfig."""
    with tempfile.TemporaryDirectory(prefix="bauhaus-maps-") as scratch:
        scratch_dir = Path(scratch)
        env = dict(os.environ, FONTCONFIG_FILE=str(write_fontconfig(scratch_dir)))
        done = subprocess.run(["rsvg-convert", "-z", "2", "-o", str(scratch_dir / "fig.png")], input=svg.encode("utf-8"),
                              capture_output=True, env=env)
        if done.returncode != 0:
            raise SpecError(f"rsvg-convert failed: {done.stderr.decode('utf-8', 'replace').strip()}")
        png.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(scratch_dir / "fig.png"), png)


def load_spec(path: Path) -> dict:
    try:
        spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise SpecError(f"cannot read the spec: {error}") from error
    except yaml.YAMLError as error:
        raise SpecError(f"the spec is not valid YAML: {error}") from error
    if spec is None:
        return {}
    if not isinstance(spec, dict):
        raise SpecError("the spec must be a YAML mapping")
    return spec


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Bauhaus técnico concept maps from a YAML spec.")
    sub = parser.add_subparsers(dest="command", required=True)
    render_cmd = sub.add_parser("render", help="render a concept_map spec to SVG (and PNG)")
    render_cmd.add_argument("spec", type=Path)
    render_cmd.add_argument("--out", type=Path, required=True)
    render_cmd.add_argument("--png", type=Path, help="also rasterise at 2x with the repo font")
    args = parser.parse_args(argv)
    try:
        if args.png and shutil.which("rsvg-convert") is None:
            raise SpecError("rsvg-convert was not found on PATH; install librsvg to use --png")
        svg = render(load_spec(args.spec))
        if args.png:
            rasterize(svg, args.png)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(svg, encoding="utf-8")
    except (SpecError, OSError) as error:
        print(f"bauhaus_maps: {error}", file=sys.stderr)
        return 2
    print(f"rendered {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
