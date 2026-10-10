"""Bauhaus técnico maps: fonts, concept maps and process maps rendered from a YAML spec.

Every test drives the public interface: the ``render`` CLI (exit code, stderr, files on disk)
and the SVG it writes (colours, fonts, text, geometry).
"""
from __future__ import annotations

import copy
import hashlib
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import editorial_svg
import pytest
import yaml

TOOL = Path(__file__).resolve().parent / "bauhaus_maps.py"
FONTS = Path(__file__).resolve().parents[1] / "assets" / "fonts"
needs_dot = pytest.mark.skipif(shutil.which("dot") is None, reason="Graphviz dot is not installed")
needs_rsvg = pytest.mark.skipif(shutil.which("rsvg-convert") is None, reason="rsvg-convert is not installed")

BG, INK, MUTED = "#F6F4EE", "#121212", "#4A4A4A"
BLUE, RED, GREEN, SAFFRON = "#2247B5", "#E0452A", "#0D8B6C", "#F2B233"
# Link phrases are the family colour at 85 % over black, for contrast on the paper background.
SHADE = {BLUE: "#1D3C9A", RED: "#BE3B24", GREEN: "#0B765C"}
WHITE = "#FFFFFF"
SIZE_LIMIT = 860

CONCEPT_SPEC = {
    "kind": "concept_map",
    "title": "Spec-Driven Development en el proyecto de prácticas",
    "core": {"id": "sdd", "name": "Spec-Driven Development", "subtitle": "desarrollo guiado por especificaciones"},
    "families": {
        "que": {"label": "QUÉ", "color": "blue", "meaning": "problema y requisitos"},
        "reglas": {"label": "REGLAS", "color": "red", "meaning": "principios del proyecto"},
        "como": {"label": "CÓMO", "color": "green", "meaning": "solución técnica"},
    },
    "concepts": [
        {"id": "spec", "name": "Especificación", "detail": "spec.md: qué y por qué", "family": "que", "level": "key"},
        {"id": "const", "name": "Constitución", "detail": "principios del proyecto", "family": "reglas", "level": "key"},
        {"id": "problema", "name": "Problema", "detail": "lo que se quiere cambiar", "family": "que"},
        {"id": "req", "name": "Requisitos", "detail": "verificables", "family": "que"},
        {"id": "clar", "name": "Clarificación", "detail": "hasta 5 preguntas", "family": "que"},
        {"id": "plan", "name": "Plan técnico", "detail": "stack y datos", "family": "como"},
        {"id": "tareas", "name": "Tareas", "detail": "unidades verificables", "family": "como"},
        {"id": "codigo", "name": "Código", "detail": "se genera o se verifica", "family": "como"},
    ],
    "links": [
        {"from": "sdd", "to": "spec", "label": "toma como artefacto principal"},
        {"from": "sdd", "to": "const", "label": "se rige por"},
        {"from": "spec", "to": "problema", "label": "se escribe en el dominio del"},
        {"from": "spec", "to": "req", "label": "reúne"},
        {"from": "spec", "to": "plan", "label": "se traduce en"},
        {"from": "spec", "to": "clar", "label": "se depura con"},
        {"from": "const", "to": "plan", "label": "evalúa", "cross": True},
        {"from": "plan", "to": "tareas", "label": "se parte en"},
        {"from": "tareas", "to": "req", "label": "son rastreables a", "cross": True},
        {"from": "tareas", "to": "codigo", "label": "guían el"},
    ],
    "spine": ["sdd", "spec", "plan", "tareas", "codigo"],
}

PROCESS_SPEC = {
    "kind": "process_map",
    "title": "Flujo SDD con GitHub Spec Kit",
    "lanes": [
        {"id": "equipo", "label": "EQUIPO DE DESARROLLO", "short": "EQUIPO"},
        {"id": "ia", "label": "ASISTENTE CON SPEC KIT", "short": "ASISTENTE"},
    ],
    "artifact_lane": {"label": "ARTEFACTO"},
    "steps": [
        {"id": "s1", "lane": "equipo", "title": "Fijar principios", "detail": "/constitution", "artifact": "constitution.md"},
        {"id": "s2", "lane": "ia", "title": "Especificar", "detail": "/specify: qué y por qué", "artifact": "spec.md"},
        {"id": "d1", "lane": "equipo", "title": "¿Quedan ambigüedades?", "decision": True},
        {"id": "s3", "lane": "ia", "title": "Preguntar y registrar", "detail": "/clarify: hasta 5 preguntas",
         "artifact": "spec.md actualizado"},
        {"id": "s4", "lane": "ia", "title": "Diseñar la solución", "detail": "/plan: stack y datos",
         "artifact": "plan.md · data-model.md"},
        {"id": "s5", "lane": "ia", "title": "Partir en tareas", "detail": "/tasks", "artifact": "tasks.md"},
        {"id": "s6", "lane": "equipo", "title": "Implementar y verificar", "detail": "contra la especificación"},
    ],
    "flow": [
        {"from": "s1", "to": "s2"}, {"from": "s2", "to": "d1"},
        {"from": "d1", "to": "s3", "label": "sí"}, {"from": "s3", "to": "d1"},
        {"from": "d1", "to": "s4", "label": "no"},
        {"from": "s4", "to": "s5"}, {"from": "s5", "to": "s6"},
    ],
}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def run_cli(*args: object, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True, env=env)


def write_spec(tmp_path: Path, spec: dict) -> Path:
    path = tmp_path / "spec.yml"
    path.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def render(tmp_path: Path, spec: dict, *extra: object) -> tuple[subprocess.CompletedProcess, Path]:
    out = tmp_path / "fig.svg"
    return run_cli("render", write_spec(tmp_path, spec), "--out", out, *extra), out


def svg_root(tmp_path: Path, spec: dict) -> ET.Element:
    result, out = render(tmp_path, spec)
    assert result.returncode == 0, result.stderr
    return ET.fromstring(out.read_text(encoding="utf-8"))


def tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def find(root: ET.Element, name: str, **attrs: str) -> list[ET.Element]:
    return [e for e in root.iter() if tag(e) == name and all(e.get(k.replace("_", "-")) == v for k, v in attrs.items())]


def texts(root: ET.Element) -> list[ET.Element]:
    return find(root, "text")


def text_of(root: ET.Element, value: str) -> ET.Element:
    found = [e for e in texts(root) if "".join(e.itertext()) == value]
    assert found, f"no text {value!r}"
    return found[0]


def box(element: ET.Element) -> tuple[float, float, float, float]:
    """x0, y0, x1, y1 of a rect or an axis-aligned polygon."""
    if tag(element) == "rect":
        x, y, w, h = (float(element.get(k)) for k in ("x", "y", "width", "height"))
        return x, y, x + w, y + h
    points = [tuple(map(float, p.split(","))) for p in element.get("points").split()]
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def node_box(root: ET.Element, node_id: str) -> tuple[float, float, float, float]:
    found = find(root, "rect", data_node=node_id) + find(root, "polygon", data_node=node_id)
    assert len(found) == 1, node_id
    return box(found[0])


def path_points(d: str) -> list[tuple[float, float]]:
    """Vertices of a path made of absolute M/L/H/V commands (straight, orthogonal connectors)."""
    points: list[tuple[float, float]] = []
    for command, args in re.findall(r"([MLHV])([^MLHV]*)", d):
        numbers = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", args)]
        if command in "ML":
            points.append((numbers[0], numbers[1]))
        elif command == "H":
            points.append((numbers[0], points[-1][1]))
        else:
            points.append((points[-1][0], numbers[0]))
    return points


def crosses_box(points: list[tuple[float, float]], rect: tuple[float, float, float, float]) -> bool:
    """True when an axis-aligned segment of the polyline enters the open interior of ``rect``."""
    x0, y0, x1, y1 = rect
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        sx0, sx1, sy0, sy1 = min(ax, bx), max(ax, bx), min(ay, by), max(ay, by)
        if sx1 > x0 + 1e-6 and sx0 < x1 - 1e-6 and sy1 > y0 + 1e-6 and sy0 < y1 - 1e-6:
            return True
    return False


def canvas_width(root: ET.Element) -> float:
    return float(root.get("width"))


# --------------------------------------------------------------------------
# T1 · shipped fonts
# --------------------------------------------------------------------------

def test_space_grotesk_ships_in_the_repo_with_its_licence() -> None:
    font = FONTS / "SpaceGrotesk[wght].ttf"
    assert font.is_file() and font.stat().st_size > 10_000
    assert "SIL OPEN FONT LICENSE" in (FONTS / "OFL.txt").read_text(encoding="utf-8").upper()


@needs_rsvg
def test_png_fontconfig_loads_only_the_repo_font_folder(tmp_path: Path) -> None:
    import bauhaus_maps

    conf = bauhaus_maps.write_fontconfig(tmp_path)
    assert f"<dir>{FONTS}</dir>" in conf.read_text(encoding="utf-8")
    if shutil.which("fc-match"):
        match = subprocess.run(["fc-match", "Space Grotesk:weight=bold", "family"], capture_output=True, text=True,
                               env={"FONTCONFIG_FILE": str(conf), "PATH": "/usr/bin:/bin"})
        assert "Space Grotesk" in match.stdout


# --------------------------------------------------------------------------
# T1 · concept map: style tokens
# --------------------------------------------------------------------------

@needs_dot
def test_concept_map_renders_a_valid_svg_and_reports_it(tmp_path: Path) -> None:
    result, out = render(tmp_path, CONCEPT_SPEC)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"rendered {out}"
    root = ET.fromstring(out.read_text(encoding="utf-8"))
    assert tag(root) == "svg"


@needs_dot
def test_concept_map_uses_only_space_grotesk_in_four_weights(tmp_path: Path) -> None:
    root = svg_root(tmp_path, CONCEPT_SPEC)
    assert {t.get("font-family") for t in texts(root)} == {"Space Grotesk, sans-serif"}
    assert {t.get("font-weight") for t in texts(root)} <= {"400", "500", "600", "700"}
    assert find(root, "rect", width=root.get("width"), fill=BG), "paper background"


@needs_dot
def test_concept_map_header_has_red_kind_label_muted_title_and_hairline(tmp_path: Path) -> None:
    root = svg_root(tmp_path, CONCEPT_SPEC)
    kind = text_of(root, "MAPA CONCEPTUAL")
    assert kind.get("fill") == RED and kind.get("letter-spacing") == "2.2"
    title = text_of(root, CONCEPT_SPEC["title"])
    assert title.get("fill") == MUTED and float(title.get("x")) > float(kind.get("x"))
    assert title.get("y") == kind.get("y")
    rules = [e for e in find(root, "line") if e.get("data-legend") is None and e.get("y1") == e.get("y2")]
    assert any(float(e.get("y1")) > float(kind.get("y")) for e in rules), "hairline below the header"


@needs_dot
def test_core_concept_is_a_solid_ink_box_with_white_title_and_saffron_subtitle(tmp_path: Path) -> None:
    root = svg_root(tmp_path, CONCEPT_SPEC)
    (core,) = find(root, "rect", data_node="sdd")
    assert core.get("fill") == INK
    title = text_of(root, "Spec-Driven Development")
    assert title.get("fill") == WHITE and title.get("font-weight") == "700"
    sub = text_of(root, "DESARROLLO GUIADO POR ESPECIFICACIONES")
    assert sub.get("fill") == SAFFRON


@needs_dot
def test_key_concepts_are_solid_family_colour_with_white_text(tmp_path: Path) -> None:
    root = svg_root(tmp_path, CONCEPT_SPEC)
    for node_id, colour, name in (("spec", BLUE, "Especificación"), ("const", RED, "Constitución")):
        (rect,) = find(root, "rect", data_node=node_id)
        assert rect.get("fill") == colour
        assert text_of(root, name).get("fill") == WHITE


@needs_dot
def test_leaves_are_white_with_a_family_border_and_a_corner_square(tmp_path: Path) -> None:
    root = svg_root(tmp_path, CONCEPT_SPEC)
    for node_id, colour in (("problema", BLUE), ("plan", GREEN), ("codigo", GREEN)):
        (rect,) = find(root, "rect", data_node=node_id)
        assert (rect.get("fill"), rect.get("stroke"), rect.get("stroke-width")) == (WHITE, colour, "3")
        (corner,) = find(root, "rect", data_corner=node_id)
        assert (corner.get("width"), corner.get("height"), corner.get("fill")) == ("14", "14", colour)
        assert (corner.get("x"), corner.get("y")) == (rect.get("x"), rect.get("y"))


@needs_dot
def test_colour_encodes_the_family_never_one_colour_per_node(tmp_path: Path) -> None:
    root = svg_root(tmp_path, CONCEPT_SPEC)
    fills = {find(root, "rect", data_node=n)[0].get("stroke") or find(root, "rect", data_node=n)[0].get("fill")
             for n in ("spec", "problema", "req", "clar")}
    assert fills == {BLUE}
    colours = {e.get(a) for e in root.iter() for a in ("fill", "stroke")}
    assert {BLUE, RED, GREEN, SAFFRON, INK} <= colours


@needs_dot
def test_every_link_carries_its_phrase_coloured_by_the_source_family(tmp_path: Path) -> None:
    root = svg_root(tmp_path, CONCEPT_SPEC)
    for link in CONCEPT_SPEC["links"]:
        label = find(root, "text", data_label=f"{link['from']}>{link['to']}")
        assert len(label) == 1 and "".join(label[0].itertext()) == link["label"], link
    family = {c["id"]: c["family"] for c in CONCEPT_SPEC["concepts"]}
    colour = {"que": BLUE, "reglas": RED, "como": GREEN}
    assert find(root, "text", data_label="spec>req")[0].get("fill") == SHADE[BLUE]
    assert find(root, "text", data_label="const>plan")[0].get("fill") == SHADE[colour[family["const"]]]
    assert find(root, "text", data_label="plan>tareas")[0].get("fill") == SHADE[GREEN]
    assert find(root, "text", data_label="sdd>spec")[0].get("fill") == MUTED


@needs_dot
def test_cross_links_are_dashed_and_other_links_are_solid(tmp_path: Path) -> None:
    root = svg_root(tmp_path, CONCEPT_SPEC)
    cross = {f"{l['from']}>{l['to']}" for l in CONCEPT_SPEC["links"] if l.get("cross")}
    paths = {p.get("data-link"): p for p in find(root, "path") if p.get("data-link")}
    assert set(paths) == {f"{l['from']}>{l['to']}" for l in CONCEPT_SPEC["links"]}
    for name, path in paths.items():
        assert (path.get("stroke-dasharray") == "6 5") == (name in cross), name


@needs_dot
def test_legend_has_a_coloured_line_a_bold_uppercase_label_and_its_meaning(tmp_path: Path) -> None:
    root = svg_root(tmp_path, CONCEPT_SPEC)
    for family, colour in (("que", BLUE), ("reglas", RED), ("como", GREEN)):
        (line,) = find(root, "line", data_legend=family)
        assert line.get("stroke") == colour and line.get("stroke-width") == "4"
        assert abs(float(line.get("x2")) - float(line.get("x1")) - 22) < 1e-6
    label = text_of(root, "QUÉ")
    assert label.get("font-weight") == "700" and label.get("fill") == BLUE
    assert text_of(root, "problema y requisitos").get("fill") == MUTED
    assert not [e for e in find(root, "rect") if e.get("data-legend")], "no chip grid"
    foot = max(float(e.get("y1")) for e in find(root, "line", data_legend="que"))
    assert foot > max(box(r)[3] for r in find(root, "rect") if r.get("data-node")), "legend sits at the foot"


# --------------------------------------------------------------------------
# T1 · concept map: layout
# --------------------------------------------------------------------------

@needs_dot
def test_cross_links_do_not_shape_the_ranks(tmp_path: Path) -> None:
    spec = copy.deepcopy(CONCEPT_SPEC)
    root = svg_root(tmp_path, spec)
    # tareas -> req and const -> plan are cross-links: req stays level with its siblings
    # and plan stays one rank below spec, as if the dashed links were absent.
    assert node_box(root, "req")[1] == node_box(root, "problema")[1]
    assert node_box(root, "plan")[1] == node_box(root, "problema")[1]
    assert node_box(root, "tareas")[1] > node_box(root, "plan")[3]


@needs_dot
def test_spine_is_a_straight_central_axis(tmp_path: Path) -> None:
    def spread(root: ET.Element) -> float:
        centres = [(node_box(root, n)[0] + node_box(root, n)[2]) / 2 for n in CONCEPT_SPEC["spine"]]
        return max(centres) - min(centres)

    assert spread(svg_root(tmp_path, CONCEPT_SPEC)) < 0.3  # one vertical axis (rounding only)
    assert spread(svg_root(tmp_path, _without(CONCEPT_SPEC, "spine"))) > 20


@needs_dot
def test_sibling_order_follows_the_spec(tmp_path: Path) -> None:
    spec = copy.deepcopy(CONCEPT_SPEC)
    root = svg_root(tmp_path, spec)
    order = sorted(("problema", "req", "plan", "clar"), key=lambda n: node_box(root, n)[0])
    assert order == ["problema", "req", "plan", "clar"]  # the order of the spec's links from 'spec'
    spec["links"][2], spec["links"][3] = spec["links"][3], spec["links"][2]
    flipped = svg_root(tmp_path, spec)
    assert node_box(flipped, "req")[0] < node_box(flipped, "problema")[0]


@needs_dot
def test_titles_are_centred_in_their_boxes_and_the_canvas_stays_within_the_limit(tmp_path: Path) -> None:
    root = svg_root(tmp_path, CONCEPT_SPEC)
    for concept in CONCEPT_SPEC["concepts"]:
        x0, _, x1, _ = node_box(root, concept["id"])
        centre = (x0 + x1) / 2
        assert abs(float(text_of(root, concept["name"]).get("x")) - centre) < 1.0
    assert 0 < canvas_width(ET.fromstring(Path(tmp_path / "fig.svg").read_text(encoding="utf-8"))) <= SIZE_LIMIT


# --------------------------------------------------------------------------
# T1 · legibility and width
# --------------------------------------------------------------------------

@needs_dot
def test_rendered_concept_map_passes_the_print_size_check(tmp_path: Path) -> None:
    result, out = render(tmp_path, CONCEPT_SPEC)
    assert result.returncode == 0
    svg = out.read_text(encoding="utf-8")
    assert editorial_svg.check(svg) == []
    assert min(size for size, _ in editorial_svg.printed_sizes(svg)) >= 5.5


@needs_dot
def test_a_layout_wider_than_860_units_fails_instead_of_shrinking(tmp_path: Path) -> None:
    spec = copy.deepcopy(CONCEPT_SPEC)
    spec["concepts"] = [
        {"id": f"c{i}", "name": f"Concepto largo número {i}", "detail": "con un detalle bastante extenso",
         "family": "que"} for i in range(8)]
    spec["links"] = [{"from": "sdd", "to": f"c{i}", "label": "incluye"} for i in range(8)]
    spec.pop("spine")
    result, out = render(tmp_path, spec)
    assert result.returncode == 2
    assert re.fullmatch(
        r"bauhaus_maps: layout is \d+ units wide, over the 860-unit limit; the figure is never shrunk, "
        r"so split the map or shorten names and details\n", result.stderr), result.stderr
    assert not out.exists()


# --------------------------------------------------------------------------
# T1 · malformed specs: SpecError names the field, exit 2, no file
# --------------------------------------------------------------------------

def _without(spec: dict, *path: object) -> dict:
    spec = copy.deepcopy(spec)
    target = spec
    for key in path[:-1]:
        target = target[key]
    del target[path[-1]]
    return spec


def _with(spec: dict, value: object, *path: object) -> dict:
    spec = copy.deepcopy(spec)
    target = spec
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return spec


CONCEPT_CASES = [
    (_without(CONCEPT_SPEC, "title"), "'title' is required"),
    (_without(CONCEPT_SPEC, "core"), "'core' is required"),
    (_without(CONCEPT_SPEC, "core", "name"), "'core.name' is required"),
    (_without(CONCEPT_SPEC, "concepts"), "'concepts' is required"),
    (_without(CONCEPT_SPEC, "families"), "'families' is required"),
    (_without(CONCEPT_SPEC, "links"), "'links' is required"),
    (_without(CONCEPT_SPEC, "concepts", 0, "name"), "'concepts[0].name' is required"),
    (_without(CONCEPT_SPEC, "concepts", 2, "family"), "'concepts[2].family' is required"),
    (_with(CONCEPT_SPEC, "nope", "concepts", 0, "family"), "'concepts[0].family' is 'nope'; use one of ['como', 'que', 'reglas']"),
    (_with(CONCEPT_SPEC, "huge", "concepts", 0, "level"), "'concepts[0].level' is 'huge'; use one of ['key', 'leaf']"),
    (_with(CONCEPT_SPEC, "spec", "concepts", 1, "id"), "'concepts[1].id' repeats id 'spec'"),
    (_with(CONCEPT_SPEC, "sdd", "concepts", 0, "id"), "'concepts[0].id' repeats id 'sdd'"),
    (_with(CONCEPT_SPEC, "saffron", "families", "que", "color"),
     "'families.que.color' is 'saffron'; use one of ['blue', 'green', 'red']"),
    (_with(CONCEPT_SPEC, "blue", "families", "reglas", "color"), "'families.reglas.color' repeats colour 'blue'"),
    (_without(CONCEPT_SPEC, "families", "que", "label"), "'families.que.label' is required"),
    (_with(CONCEPT_SPEC, "zzz", "links", 0, "to"), "'links[0].to' refers to unknown id 'zzz'"),
    (_with(CONCEPT_SPEC, "zzz", "links", 3, "from"), "'links[3].from' refers to unknown id 'zzz'"),
    (_without(CONCEPT_SPEC, "links", 0, "label"), "'links[0].label' is required"),
    (_with(CONCEPT_SPEC, "yes please", "links", 6, "cross"), "'links[6].cross' must be true or false"),
    (_with(CONCEPT_SPEC, "spec", "links", 1, "to"), "'links[1]' repeats the link 'sdd' -> 'spec'"),
    (_with(CONCEPT_SPEC, "sdd", "links", 1, "to"), "'links[1]' links 'sdd' to itself"),
    (_with(CONCEPT_SPEC, ["sdd", "nope"], "spine"), "'spine[1]' refers to unknown id 'nope'"),
    (_with(CONCEPT_SPEC, "sdd", "spine"), "'spine' must be a list of ids"),
    ({**CONCEPT_SPEC, "kind": "actor_map"},
     "unknown kind 'actor_map'; use one of ['concept_map', 'process_map']"),
    (_without(CONCEPT_SPEC, "kind"), "'kind' is required; use one of ['concept_map', 'process_map']"),
]


@pytest.mark.parametrize(("spec", "message"), CONCEPT_CASES, ids=[m for _, m in CONCEPT_CASES])
def test_malformed_concept_specs_fail_naming_the_field_and_write_nothing(tmp_path: Path, spec: dict, message: str) -> None:
    result, out = render(tmp_path, spec, "--png", tmp_path / "fig.png")
    assert result.returncode == 2
    assert result.stderr == f"bauhaus_maps: {message}\n"
    assert result.stdout == ""
    assert not out.exists() and not (tmp_path / "fig.png").exists()


def test_a_spec_that_is_not_a_yaml_mapping_is_rejected(tmp_path: Path) -> None:
    spec = tmp_path / "spec.yml"
    spec.write_text("- just\n- a list\n", encoding="utf-8")
    out = tmp_path / "fig.svg"
    result = run_cli("render", spec, "--out", out)
    assert (result.returncode, result.stderr) == (2, "bauhaus_maps: the spec must be a YAML mapping\n")
    assert not out.exists()


def test_invalid_yaml_and_missing_spec_file_exit_2_without_output(tmp_path: Path) -> None:
    broken = tmp_path / "broken.yml"
    broken.write_text("kind: [unclosed\n", encoding="utf-8")
    out = tmp_path / "fig.svg"
    for spec in (broken, tmp_path / "absent.yml"):
        result = run_cli("render", spec, "--out", out)
        assert result.returncode == 2 and result.stderr.startswith("bauhaus_maps: ")
        assert not out.exists()


@pytest.mark.skipif(shutil.which("dot") is None, reason="needs a real dot to prove the lookup")
def test_missing_graphviz_is_reported_and_writes_nothing(tmp_path: Path) -> None:
    out = tmp_path / "fig.svg"
    result = run_cli("render", write_spec(tmp_path, CONCEPT_SPEC), "--out", out, env={"PATH": str(tmp_path)})
    assert result.returncode == 2
    assert result.stderr == "bauhaus_maps: Graphviz 'dot' was not found on PATH; install graphviz\n"
    assert not out.exists()


# --------------------------------------------------------------------------
# T1 · PNG
# --------------------------------------------------------------------------

@needs_dot
@needs_rsvg
def test_png_output_is_written_at_twice_the_svg_size(tmp_path: Path) -> None:
    png = tmp_path / "fig.png"
    result, out = render(tmp_path, CONCEPT_SPEC, "--png", png)
    assert result.returncode == 0, result.stderr
    data = png.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    root = ET.fromstring(out.read_text(encoding="utf-8"))
    assert (width, height) == (round(float(root.get("width")) * 2), round(float(root.get("height")) * 2))


@needs_dot
def test_png_without_rsvg_convert_fails_cleanly_and_writes_nothing(tmp_path: Path) -> None:
    out = tmp_path / "fig.svg"
    png = tmp_path / "fig.png"
    dot_dir = tmp_path / "bin"
    dot_dir.mkdir()
    (dot_dir / "dot").symlink_to(shutil.which("dot"))
    result = run_cli("render", write_spec(tmp_path, CONCEPT_SPEC), "--out", out, "--png", png,
                     env={"PATH": str(dot_dir), "HOME": str(tmp_path)})
    assert result.returncode == 2
    assert result.stderr == "bauhaus_maps: rsvg-convert was not found on PATH; install librsvg to use --png\n"
    assert not out.exists() and not png.exists()


# --------------------------------------------------------------------------
# T2 · process map
# --------------------------------------------------------------------------

LANE_TINT = {RED: "#F5EBE4", BLUE: "#EBEBEB", GREEN: "#EAEFE8"}  # 5 % of the lane colour over the paper


def artifact_box(root: ET.Element, step_id: str) -> tuple[float, float, float, float]:
    (shape,) = find(root, "path", data_artifact=step_id)
    xs, ys = zip(*path_points(shape.get("d")))
    return min(xs), min(ys), max(xs), max(ys)


def all_boxes(root: ET.Element) -> dict[str, tuple[float, float, float, float]]:
    boxes = {e.get("data-node"): box(e) for e in root.iter() if tag(e) in ("rect", "polygon") and e.get("data-node")}
    boxes.update({f"artifact:{e.get('data-artifact')}": artifact_box(root, e.get("data-artifact"))
                  for e in find(root, "path") if e.get("data-artifact")})
    return boxes


def connectors(root: ET.Element) -> dict[str, list[tuple[float, float]]]:
    return {e.get("data-edge"): path_points(e.get("d")) for e in find(root, "path") if e.get("data-edge")}


def assert_no_connector_crosses_a_node(root: ET.Element) -> None:
    boxes = all_boxes(root)
    assert connectors(root), "no connectors drawn"
    for name, points in connectors(root).items():
        for node_id, rect in boxes.items():
            assert not crosses_box(points, rect), f"connector {name} crosses node {node_id}"


@pytest.fixture
def process_root(tmp_path: Path) -> ET.Element:
    return svg_root(tmp_path, PROCESS_SPEC)


def test_process_map_renders_at_860_units_and_passes_the_print_size_check(tmp_path: Path) -> None:
    result, out = render(tmp_path, PROCESS_SPEC)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"rendered {out}"
    svg = out.read_text(encoding="utf-8")
    assert canvas_width(ET.fromstring(svg)) == 860
    assert editorial_svg.check(svg) == []


def test_process_map_uses_the_bauhaus_tokens_and_only_space_grotesk(process_root: ET.Element) -> None:
    assert {t.get("font-family") for t in texts(process_root)} == {"Space Grotesk, sans-serif"}
    assert {t.get("font-weight") for t in texts(process_root)} <= {"400", "500", "600", "700"}
    assert find(process_root, "rect", width="860", fill=BG)
    kind = text_of(process_root, "MAPA DE PROCESO")
    assert (kind.get("fill"), kind.get("letter-spacing")) == (RED, "2.2")
    title = text_of(process_root, PROCESS_SPEC["title"])
    assert title.get("fill") == MUTED and title.get("y") == kind.get("y")


def test_lanes_are_columns_with_solid_headers_and_five_percent_tinted_bodies(process_root: ET.Element) -> None:
    lanes = {"equipo": RED, "ia": BLUE, "artifact": GREEN}
    for lane, colour in lanes.items():
        (head,) = find(process_root, "rect", data_lane_header=lane)
        (body,) = find(process_root, "rect", data_lane=lane)
        assert head.get("fill") == colour
        assert body.get("fill") == LANE_TINT[colour]
        assert box(body)[0] == box(head)[0] and box(body)[2] == box(head)[2] and box(body)[1] >= box(head)[3]
    xs = [box(find(process_root, "rect", data_lane=lane)[0])[0] for lane in lanes]
    assert xs == sorted(xs) and len(set(xs)) == 3
    label = text_of(process_root, "EQUIPO DE DESARROLLO")
    assert (label.get("fill"), label.get("font-weight")) == (WHITE, "700")


def test_steps_are_white_boxes_with_a_lane_border_and_a_numbered_corner_square(process_root: ET.Element) -> None:
    expected = {"s1": (RED, "1"), "s2": (BLUE, "2"), "s3": (BLUE, "3"), "s4": (BLUE, "4"), "s5": (BLUE, "5"),
                "s6": (RED, "6")}
    for step_id, (colour, number) in expected.items():
        (rect,) = find(process_root, "rect", data_node=step_id)
        assert (rect.get("fill"), rect.get("stroke"), rect.get("stroke-width")) == (WHITE, colour, "3")
        (corner,) = find(process_root, "rect", data_corner=step_id)
        assert (corner.get("width"), corner.get("height"), corner.get("fill")) == ("30", "30", colour)
        assert (corner.get("x"), corner.get("y")) == (rect.get("x"), rect.get("y"))
        digit = find(process_root, "text", data_number=step_id)
        assert [("".join(d.itertext()), d.get("fill")) for d in digit] == [(number, WHITE)]
    assert text_of(process_root, "Fijar principios").get("font-weight") == "700"
    assert text_of(process_root, "/constitution").get("fill") == MUTED


def test_decisions_are_saffron_diamonds_and_are_not_numbered(process_root: ET.Element) -> None:
    (diamond,) = find(process_root, "polygon", data_node="d1")
    assert diamond.get("fill") == SAFFRON
    assert not find(process_root, "rect", data_corner="d1") and not find(process_root, "text", data_number="d1")
    assert text_of(process_root, "¿Quedan ambigüedades?").get("fill") == INK
    numbers = sorted("".join(t.itertext()) for t in find(process_root, "text") if t.get("data-number"))
    assert numbers == ["1", "2", "3", "4", "5", "6"]  # six steps, the decision takes no number


def test_artifacts_are_folded_documents_joined_by_a_dashed_connector(process_root: ET.Element) -> None:
    (doc,) = find(process_root, "path", data_artifact="s1")
    assert (doc.get("fill"), doc.get("stroke")) == (WHITE, GREEN)
    (fold,) = find(process_root, "path", data_fold="s1")
    assert fold.get("fill") == GREEN
    (link,) = find(process_root, "line", data_edge="artifact:s1")
    assert (link.get("stroke"), link.get("stroke-dasharray")) == (GREEN, "4 4")
    assert text_of(process_root, "constitution.md").get("fill") == INK
    assert not find(process_root, "path", data_artifact="s6"), "steps without an artifact get no document"
    lane = box(find(process_root, "rect", data_lane="artifact")[0])
    doc_x0, _, doc_x1, _ = artifact_box(process_root, "s1")
    assert lane[0] < doc_x0 and doc_x1 < lane[2]


def test_flow_connectors_are_ink_and_branch_labels_are_uppercase(process_root: ET.Element) -> None:
    flows = {f"{f['from']}>{f['to']}" for f in PROCESS_SPEC["flow"]}
    paths = {p.get("data-edge"): p for p in find(process_root, "path") if p.get("data-edge")}
    assert set(paths) == flows
    for path in paths.values():
        assert (path.get("stroke"), path.get("fill"), path.get("marker-end")) == (INK, "none", "url(#tip-ink)")
    for edge, label in (("d1>s3", "SÍ"), ("d1>s4", "NO")):
        (found,) = find(process_root, "text", data_label=edge)
        assert "".join(found.itertext()) == label and found.get("font-weight") == "700"
    assert not find(process_root, "text", data_label="s1>s2")


def test_every_connector_of_the_sample_map_avoids_every_node(process_root: ET.Element) -> None:
    assert_no_connector_crosses_a_node(process_root)


def test_back_edge_loops_on_the_right_of_its_source_box(process_root: ET.Element) -> None:
    source = node_box(process_root, "s3")
    points = connectors(process_root)["s3>d1"]
    assert points[0][0] == pytest.approx(source[2]) and source[1] < points[0][1] < source[3]
    corridor = points[1][0]
    assert corridor > source[2] and all(p[0] >= source[2] - 1e-6 or p == points[-1] for p in points[1:-1])
    target = node_box(process_root, "d1")
    assert points[-1][1] == pytest.approx((target[1] + target[3]) / 2) and points[-1][0] > target[2]


def test_row_skipping_edge_runs_along_the_free_edge_of_its_source_lane(process_root: ET.Element) -> None:
    lane = box(find(process_root, "rect", data_lane="equipo")[0])
    points = connectors(process_root)["d1>s4"]
    run = points[1][0]
    assert lane[0] < run < node_box(process_root, "d1")[0]
    assert points[0][0] == pytest.approx(node_box(process_root, "d1")[0])  # leaves the left vertex
    assert points[-1][0] < node_box(process_root, "s4")[0] + 3  # enters the left side of s4
    assert points[2][1] == pytest.approx(points[3][1])


def _lattice_spec() -> dict:
    """Three actor lanes and an artifact lane, boxes and decisions, with every ordered pair as a flow."""
    steps = [
        {"id": "a", "lane": "l1", "title": "Alfa", "artifact": "alfa.md"},
        {"id": "b", "lane": "l2", "title": "¿Beta?", "decision": True},
        {"id": "c", "lane": "l3", "title": "Gamma", "artifact": "gamma.md"},
        {"id": "d", "lane": "l1", "title": "¿Delta?", "decision": True},
        {"id": "e", "lane": "l2", "title": "Épsilon", "artifact": "eps.md"},
        {"id": "f", "lane": "l1", "title": "Zeta"},
        {"id": "g", "lane": "l3", "title": "Eta", "artifact": "eta.md"},
        {"id": "h", "lane": "l2", "title": "Theta"},
    ]
    ids = [s["id"] for s in steps]
    return {"kind": "process_map", "title": "Todas las parejas",
            "lanes": [{"id": "l1", "label": "UNO"}, {"id": "l2", "label": "DOS"}, {"id": "l3", "label": "TRES"}],
            "artifact_lane": {"label": "ARTEFACTO"}, "steps": steps,
            "flow": [{"from": a, "to": b} for a in ids for b in ids if a != b]}


def test_no_connector_crosses_a_node_for_any_pair_of_steps(tmp_path: Path) -> None:
    root = svg_root(tmp_path, _lattice_spec())
    assert len(connectors(root)) == 8 * 7
    assert_no_connector_crosses_a_node(root)
    boxes = all_boxes(root)
    for name, points in connectors(root).items():
        source, target = name.split(">")
        sx0, sy0, sx1, sy1 = boxes[source]
        px, py = points[0]
        assert sx0 - 1e-6 <= px <= sx1 + 1e-6 and sy0 - 1e-6 <= py <= sy1 + 1e-6, f"{name} starts off its source"
        tx0, ty0, tx1, ty1 = boxes[target]
        qx, qy = points[-1]
        assert tx0 - 4 <= qx <= tx1 + 4 and ty0 - 4 <= qy <= ty1 + 4, f"{name} ends off its target"


def test_no_connector_crosses_a_node_with_two_lanes_and_no_artifact_lane(tmp_path: Path) -> None:
    spec = _lattice_spec()
    spec["lanes"] = spec["lanes"][:2]
    spec.pop("artifact_lane")
    for step in spec["steps"]:
        step["lane"] = "l1" if step["lane"] == "l1" else "l2"
        step.pop("artifact", None)
    root = svg_root(tmp_path, spec)
    assert not find(root, "rect", data_lane="artifact")
    assert_no_connector_crosses_a_node(root)


def test_the_legend_names_each_lane_and_the_decision(process_root: ET.Element) -> None:
    for key, colour, label in (("equipo", RED, "EQUIPO"), ("ia", BLUE, "ASISTENTE"), ("artifact", GREEN, "ARTEFACTO")):
        (line,) = find(process_root, "line", data_legend=key)
        assert (line.get("stroke"), line.get("stroke-width")) == (colour, "4")
        legend = [t for t in texts(process_root) if "".join(t.itertext()) == label and t.get("font-weight") == "700"]
        assert legend and legend[-1].get("fill") == colour
    (marker,) = find(process_root, "polygon", data_legend="decision")
    assert marker.get("fill") == SAFFRON
    assert text_of(process_root, "DECISIÓN").get("fill") == INK
    foot = max(float(e.get("y1")) for e in find(process_root, "line", data_legend="equipo"))
    assert foot > max(b[3] for b in all_boxes(process_root).values())


def test_a_map_without_decisions_has_no_decision_legend_entry(tmp_path: Path) -> None:
    spec = copy.deepcopy(PROCESS_SPEC)
    spec["steps"] = [s for s in spec["steps"] if s["id"] != "d1"]
    spec["flow"] = [{"from": "s1", "to": "s2"}, {"from": "s2", "to": "s3"}, {"from": "s3", "to": "s4"},
                    {"from": "s4", "to": "s5"}, {"from": "s5", "to": "s6"}]
    root = svg_root(tmp_path, spec)
    assert not find(root, "polygon", data_legend="decision")


def test_lane_colours_default_to_red_blue_green_ink_and_can_be_chosen(tmp_path: Path) -> None:
    spec = _lattice_spec()
    root = svg_root(tmp_path, spec)
    heads = {lane: find(root, "rect", data_lane_header=lane)[0].get("fill") for lane in ("l1", "l2", "l3", "artifact")}
    assert heads == {"l1": RED, "l2": BLUE, "l3": GREEN, "artifact": INK}
    spec["lanes"][0]["color"] = "green"
    spec["lanes"][2]["color"] = "red"
    swapped = svg_root(tmp_path, spec)
    assert find(swapped, "rect", data_lane_header="l1")[0].get("fill") == GREEN


def test_a_process_map_wider_than_860_units_fails_instead_of_shrinking(tmp_path: Path) -> None:
    spec = copy.deepcopy(PROCESS_SPEC)
    spec["lanes"].append({"id": "extra", "label": "TERCER ACTOR"})
    spec["steps"][0]["title"] = "Un título extraordinariamente largo para forzar el ancho"
    result, out = render(tmp_path, spec)
    assert result.returncode == 2
    assert re.fullmatch(
        r"bauhaus_maps: layout is \d+ units wide, over the 860-unit limit; the figure is never shrunk, "
        r"so split the map or shorten names and details\n", result.stderr), result.stderr
    assert not out.exists()


def _lane(lane_id: str, label: str, **extra: str) -> dict:
    return {"id": lane_id, "label": label, **extra}


PROCESS_CASES = [
    (_without(PROCESS_SPEC, "title"), "'title' is required"),
    (_without(PROCESS_SPEC, "lanes"), "'lanes' is required"),
    (_with(PROCESS_SPEC, [_lane("a", "A")], "lanes"), "'lanes' needs 2 or 3 actor lanes, not 1"),
    (_with(PROCESS_SPEC, [_lane(c, c.upper()) for c in "abcd"], "lanes"), "'lanes' needs 2 or 3 actor lanes, not 4"),
    (_without(PROCESS_SPEC, "lanes", 0, "label"), "'lanes[0].label' is required"),
    (_without(PROCESS_SPEC, "lanes", 1, "id"), "'lanes[1].id' is required"),
    (_with(PROCESS_SPEC, "equipo", "lanes", 1, "id"), "'lanes[1].id' repeats id 'equipo'"),
    (_with(PROCESS_SPEC, "saffron", "lanes", 0, "color"),
     "'lanes[0].color' is 'saffron'; use one of ['blue', 'green', 'ink', 'red']"),
    (_with(PROCESS_SPEC, "red", "lanes", 1, "color"), "'lanes[1].color' repeats colour 'red'"),
    (_with(PROCESS_SPEC, {"label": ""}, "artifact_lane"), "'artifact_lane.label' is required"),
    (_with(PROCESS_SPEC, {"label": "ARTEFACTO", "color": "red"}, "artifact_lane"),
     "'artifact_lane.color' repeats colour 'red'"),
    (_without(PROCESS_SPEC, "steps"), "'steps' is required"),
    (_with(PROCESS_SPEC, PROCESS_SPEC["steps"][:1], "steps"), "'steps' needs at least 2 steps"),
    (_without(PROCESS_SPEC, "steps", 0, "title"), "'steps[0].title' is required"),
    (_without(PROCESS_SPEC, "steps", 1, "id"), "'steps[1].id' is required"),
    (_without(PROCESS_SPEC, "steps", 1, "lane"), "'steps[1].lane' is required"),
    (_with(PROCESS_SPEC, "nope", "steps", 1, "lane"), "'steps[1].lane' is 'nope'; use one of ['equipo', 'ia']"),
    (_with(PROCESS_SPEC, "s1", "steps", 1, "id"), "'steps[1].id' repeats id 's1'"),
    (_with(PROCESS_SPEC, "sí", "steps", 2, "decision"), "'steps[2].decision' must be true or false"),
    (_with(PROCESS_SPEC, "x.md", "steps", 2, "artifact"), "'steps[2].artifact' is not allowed on a decision"),
    (_without(PROCESS_SPEC, "artifact_lane"), "'steps[0].artifact' needs an 'artifact_lane'"),
    (_without(PROCESS_SPEC, "flow"), "'flow' is required"),
    (_with(PROCESS_SPEC, "zzz", "flow", 0, "to"), "'flow[0].to' refers to unknown id 'zzz'"),
    (_with(PROCESS_SPEC, "zzz", "flow", 2, "from"), "'flow[2].from' refers to unknown id 'zzz'"),
    (_without(PROCESS_SPEC, "flow", 0, "to"), "'flow[0].to' is required"),
    (_with(PROCESS_SPEC, "s1", "flow", 0, "to"), "'flow[0]' links 's1' to itself"),
]


@pytest.mark.parametrize(("spec", "message"), PROCESS_CASES, ids=[m for _, m in PROCESS_CASES])
def test_malformed_process_specs_fail_naming_the_field_and_write_nothing(tmp_path: Path, spec: dict, message: str) -> None:
    result, out = render(tmp_path, spec, "--png", tmp_path / "fig.png")
    assert result.returncode == 2
    assert result.stderr == f"bauhaus_maps: {message}\n"
    assert result.stdout == ""
    assert not out.exists() and not (tmp_path / "fig.png").exists()


def test_a_repeated_flow_pair_is_rejected(tmp_path: Path) -> None:
    spec = copy.deepcopy(PROCESS_SPEC)
    spec["flow"].append({"from": "s1", "to": "s2", "label": "otra vez"})
    result, out = render(tmp_path, spec)
    assert (result.returncode, result.stderr) == (2, "bauhaus_maps: 'flow[7]' repeats the flow 's1' -> 's2'\n")
    assert not out.exists()


@needs_rsvg
def test_process_map_png_is_written_at_twice_the_svg_size(tmp_path: Path) -> None:
    png = tmp_path / "proceso.png"
    result, out = render(tmp_path, PROCESS_SPEC, "--png", png)
    assert result.returncode == 0, result.stderr
    data = png.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    root = ET.fromstring(out.read_text(encoding="utf-8"))
    assert (int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")) == (
        round(float(root.get("width")) * 2), round(float(root.get("height")) * 2))


# --------------------------------------------------------------------------
# existing editorial layouts stay untouched
# --------------------------------------------------------------------------

EDITORIAL_ACTOR = {
    "kind": "actor_map", "title": "Sistema de prueba", "scope": "Alcance MVP",
    "steps": [["Asignación", "y aprobación"], ["Seguimiento", ""], ["Cierre", "final"]],
    "note": "Cada evidencia queda ligada a una actividad.",
    "top": [{"name": "Estudiante", "category": "principal", "lines": ["registra"], "link": "both"},
            {"name": "Tutor", "category": "secundario", "lines": ["revisa"]},
            {"name": "Coordinador", "category": "responsable", "lines": ["asigna"]}],
    "bottom": [{"name": "Dirección", "category": "externo", "lines": ["consulta"], "link": "from_system"},
               {"name": "Tutor externo", "category": "secundario", "lines": ["valida"]},
               {"name": "Entidad", "category": "externo", "lines": ["acepta"]}],
    "designates": {"top": True, "bottom": True},
    "services": [{"name": "SIAAF", "lines": ["datos"], "out_of_scope": True},
                 {"name": "Correo", "lines": ["alertas"], "link": "from_system"}],
}
EDITORIAL_CONCEPT = {
    "kind": "concept_map",
    "center": {"title": "Spec-Driven Development", "subtitle": "flujo de GitHub Spec Kit"},
    "branches": [{"name": "Constitution", "link": "fija", "items": ["principios"]},
                 {"name": "Specify", "link": "describe", "items": ["qué y porqué", "historias"]},
                 {"name": "Clarify", "link": "resuelve", "items": ["ambigüedades"]},
                 {"name": "Plan", "link": "decide", "items": ["stack", "datos"]}],
}


def test_editorial_actor_and_concept_maps_render_byte_for_byte_as_before() -> None:
    golden = {
        "actor_map": ("d3897e202f64b5d2e327771ee6d0d08c3cbcb858b088d3434308285d8fdf4a2a", EDITORIAL_ACTOR),
        "concept_map": ("ea72f9a71b62291652b36d4d627ebe073335eee5b702d7c549f2213e1122ccf5", EDITORIAL_CONCEPT),
    }
    for kind, (digest, spec) in golden.items():
        svg = editorial_svg.render(spec)
        assert hashlib.sha256(svg.encode("utf-8")).hexdigest() == digest, kind
        assert editorial_svg.check(svg) == []
