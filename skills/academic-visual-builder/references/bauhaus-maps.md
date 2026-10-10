# Bauhaus técnico maps (default for concept maps and process maps)

Concept maps and process maps are the figures that cost the most to draw by hand, so the author writes only content in a YAML spec and `tools/bauhaus_maps.py` lays it out and draws it. The user chose this look after rejecting the generic editorial maps ("se ven muy genericos, agregar colores, cambiar la tipografia") and approved it with "me gusta ese estilo".

Scope: concept maps and process maps only. Data charts (Matplotlib, Vega-Lite, ...) and the editorial `actor_map` (`editorial-style.md`) are unchanged.

## Commands

```bash
"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/bauhaus_maps.py" render <spec.yml> --out <asset.svg> [--png <asset.png>]
"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/editorial_svg.py" check <asset.svg>
```

- Keep the spec in `visuals/specs/<materia>/<tarea>/` and the render in `assets/generated/<materia>/<tarea>/`, like any other figure.
- `render` already runs the print-size check; run `editorial_svg.py check` again only on a hand-edited SVG.
- Graphviz (`dot`) places concept maps; `--png` needs `rsvg-convert`. A missing, unrunnable or hung tool (60 s limit) fails with a message naming it and writes nothing. SVG and PNG are written together or not at all.
- `--png` rasterises at 2x under a generated fontconfig that loads `assets/fonts` (Space Grotesk, OFL), so the PNG looks the same on any machine. Nothing is installed system-wide.
- Show the user the PNG at full size before inserting it into the report.

## Tokens

| Token | Value | Use |
|---|---|---|
| Font | Space Grotesk, weights 400/500/600/700 | every text; no second family |
| Paper | `#F6F4EE` | background |
| Ink | `#121212` | core concept, flow connectors, titles |
| Muted | `#4A4A4A` | header title, details, meaning text |
| Blue | `#2247B5` | a concept family or an actor lane |
| Red | `#E0452A` | a concept family or an actor lane; the kind label |
| Green | `#0D8B6C` | a concept family or an actor lane |
| Saffron | `#F2B233` | decisions and the core subtitle only |

Colour encodes meaning: a concept family or an actor lane. Never one colour per node. The header is an uppercase red kind label ("MAPA CONCEPTUAL", "MAPA DE PROCESO") with the title beside it in muted and a hairline below. The legend sits at the foot: a short coloured line and a bold uppercase label per colour, plus a meaning text for concept families.

## Print size and the 860-unit limit

A figure prints at about 13.5 cm, so every text must print at 5.5 pt or more: the layout is at most 860 SVG units wide. A wider layout is never shrunk. The render fails with `layout is N units wide, over the 860-unit limit; the figure is never shrunk, so split the map or shorten names and details`; split the map into two figures or shorten names and details, then render again. Process maps are always 860 units wide, so what fails there is text or corridors that no longer fit their lanes.

## Errors

A malformed spec raises a `SpecError` that names the field (`'concepts[2].family' is 'x'; use one of [...]`), prints `bauhaus_maps: <message>` on stderr, exits with exit code 2 and writes no file; an unreadable or non-UTF-8 spec and a list or mapping where text is expected get the same treatment. YAML reads a bare `yes`/`no` as true/false: quote branch labels (`label: "no"`).

## `concept_map`

```yaml
kind: concept_map
title: Spec-Driven Development en el proyecto de prácticas
core: {id: sdd, name: Spec-Driven Development, subtitle: desarrollo guiado por especificaciones}
families:
  que: {label: QUÉ, color: blue, meaning: problema y requisitos}
concepts:
  - {id: spec, name: Especificación, detail: "spec.md: qué y por qué", family: que, level: key}
links:
  - {from: sdd, to: spec, label: toma como artefacto principal}
spine: [sdd, spec]
```

| Field | Rule |
|---|---|
| `title` | required; muted text beside the kind label |
| `core` | required: `id`, `name`, optional `subtitle`. Solid ink box, white bold name, saffron uppercase subtitle |
| `families` | required mapping: `label` (legend), `color` (blue, red or green, each used once), optional `meaning` |
| `concepts` | required list: `id`, `name`, `family`, optional `detail`, optional `level` (`key` = solid family colour with white text; `leaf`, the default = white with a 3-unit family border and a 14-unit corner square) |
| `links` | required list: `from`, `to`, `label` (every link carries its linking phrase, coloured by the source family), optional `cross: true` |
| `spine` | optional list of ids drawn as one straight central axis |

Rules: ids are unique (the core included); a pair `from -> to` appears once and never links a concept to itself. The order of the links leaving a concept is the left-to-right order of its children. A `cross` link is dashed and does not move any concept to another level, so use it for relations between branches; the rest of the links form the tree. Keep names short and details to a few words; a map that grows past the width limit is split.

## `process_map`

```yaml
kind: process_map
title: Flujo SDD con GitHub Spec Kit
lanes:
  - {id: equipo, label: EQUIPO DE DESARROLLO, short: EQUIPO}
  - {id: ia, label: ASISTENTE CON SPEC KIT, short: ASISTENTE}
artifact_lane: {label: ARTEFACTO}
steps:
  - {id: s1, lane: equipo, title: Fijar principios, detail: /constitution, artifact: constitution.md}
  - {id: d1, lane: equipo, title: "¿Quedan ambigüedades?", decision: true}
flow:
  - {from: s1, to: d1}
```

| Field | Rule |
|---|---|
| `title` | required |
| `lanes` | required, 2 or 3 actor lanes as columns: `id`, `label` (solid coloured header), optional `short` (legend name), optional `color` (blue, red, green or ink; lanes without one take the first of red, blue, green, ink that no lane chose, in column order; never repeated) |
| `artifact_lane` | optional last column for documents: `label`, optional `short`, `color` |
| `steps` | required, at least 2, one per row in the given order: `id`, `lane`, `title`, optional `detail`, optional `artifact` (a document with a folded corner, joined by a dashed connector), optional `decision: true` (saffron diamond, no number, no artifact) |
| `flow` | required list: `from`, `to`, optional `label` (printed in uppercase, e.g. "sí" becomes SÍ); a pair appears once |

Steps are numbered in order in a 30-unit corner square on a white box with a 3-unit lane border; decisions are not numbered. Connectors are orthogonal and ink-coloured, and no connector crosses a step: a flow to the next row goes through the gap between rows, a flow that skips rows runs down the free left edge of its source lane, and a back edge to an earlier row loops up the right edge of the rightmost of the two lanes. Connectors that run side by side down a lane margin each get their own line (the margin widens with the number of concurrent corridors), and connectors that meet one side of a step use separate slots on it: at most 5 per side, 4 when the step has an artifact, otherwise the render fails naming the step. A branch label is placed beside its connector where it touches no connector, step or document; if no spot is free the render fails naming `flow[i].label`, so shorten it. Lane ids `artifact` and `decision` are reserved. Keep branch labels to one short word. With three actor lanes plus an artifact lane there are four narrow columns: keep titles to about 13 characters and details to about 16, or the render fails with the width message.

## Examples

`assets/examples/concept-map-sdd.yml` (concept map of Spec-Driven Development) and `assets/examples/process-map-spec-kit.yml` (the Spec Kit flow, with a decision, a back edge, a row-skipping edge and artifacts), both from the DBP AA01 content. Copy one next to the report's visual specs and replace the content.

## Never

- Shrinking a wide map or its font to make it fit; split it.
- A second font, a fifth colour, or one colour per node.
- Saffron for anything except decisions and the core subtitle.
- Drawing a map by hand when a spec can express it; hand-written SVG is only for figures neither layout fits, with the same tokens and `editorial_svg.py check`.
