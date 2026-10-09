# Editorial technical style (default for report figures)

The house style for diagrams in reports: serious and clean, like a figure in a paper or an engineering book. It replaces the generic generator look the user rejected as "muy básicas, gritan IA" (#63). Approved on the DBP actor map, 2026-10-08.

## Principles

- One ink plus one accent. Hierarchy comes from type size and weight, not from colour.
- The title of the main element is a serif that matches the report body; every label is sans.
- Nodes are white with a hairline border and nearly square corners. A 5-unit bar on the left encodes the category, and a small-caps line names the role.
- Connectors are straight and thin, with open arrow tips. Each relation is named, either inside the node ("registra actividades") or as an italic label beside the link.
- A sequence is drawn as a sequence: a numbered timeline, not a row of pills.
- Generous white space; the content decides the layout, not a grid of cards.

## Tokens (`tools/editorial_svg.py`)

| Token | Value | Use |
|---|---|---|
| `INK` | `#1D2433` | names, titles, body text |
| `MUTED` | `#5B6472` | small caps roles, link labels, notes |
| `ACCENT` | `#1F5F8B` | the system or central concept, timeline, principal user |
| `HAIRLINE` | `#C9CED6` | node borders |
| `PANEL` | `#F3F6F9` | background of the central element only |
| Category bars | accent, ink, `#6F8FA8`, `#A39A8C`, `#B4BAC3` | principal, responsable, secundario, externo, sistema |
| Fonts | Noto Serif (titles), Noto Sans 300/400/600 (labels) | |
| Sizes (SVG units) | 22 title, 16 names, 14 body, 12.5 small caps | |

## Print size

A figure is printed at about 13.5 cm (0.86 of the UNL text width). Every text must print at 5.5 pt or more, so a figure is at most about 860 SVG units wide. Check it before inserting:

```bash
"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/editorial_svg.py" check <figure.svg>
```

A wider layout is split into two figures or set in portrait; text is never shrunk below the minimum.

## Layouts

Write a YAML spec in `visuals/specs/<materia>/<tarea>/`, then render it with `editorial_svg.py render <spec.yml> --out <asset.svg>`. Rasterize the SVG with `rsvg-convert -z 2` for the PNG the report links, and validate the folder with `visual_builder.py validate`.

- `actor_map`: three users above a system panel, three actors below, and up to two related services at the foot. The panel carries the title, the scope line, a numbered timeline of 2 to 6 process steps, and a note. Actor-to-actor relations (`designates`) are drawn as a labelled arrow between neighbours. A service outside the scope is dashed, and the key explains the dashing.
- `concept_map`: a central concept with a serif title and a small-caps subtitle fans out to 2 to 4 branches. Every link carries a connecting phrase in italics ("fija", "describe"), and each branch lists up to 5 sub-concepts with accent bullets. A map with more than four branches is split.

For a figure neither layout fits, hand-write the SVG with the same tokens and helpers (`text`, `node`, `connector`), and keep the print-size check.

## Never

- One pastel fill per category, or a chip legend of coloured squares.
- Rounded pill cards (`rx` above 2), drop shadows, gradients, or emoji icons.
- A dark slab holding white text for the main element.
- Floating labels that sit on a line, or connectors that cross nodes.
- Text that prints below 5.5 pt.

Show the user the rendered figure, opened at full size, before inserting it into the report.
