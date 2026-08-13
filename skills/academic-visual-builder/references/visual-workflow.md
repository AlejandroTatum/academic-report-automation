# Visual workflow details

## Canonical roots and placement

```bash
REPORT_AUTOMATION_ROOT="/home/alejo/devwork/apps/academic-report-automation"
REPORT_CONTENT_ROOT="/home/alejo/devwork/.projects/university/.reports-system/automation"
```

Run commands from `REPORT_AUTOMATION_ROOT`. Final report PDFs belong in
`outputs/<materia-slug>/`; visual assets are intermediate files in
`assets/generated/<materia>/<tarea>/`. Visual assets, specs, manifests, and
audits are working evidence and are never copied to the user's Documents
delivery folder — only the assembled final PDF/DOCX from
`academic-report-builder` is delivered there (see that skill's
`references/clean-delivery.md`).

## Asset classes

Generated figures (Mermaid, Vega-Lite, ECharts, Matplotlib, or HTML/Playwright)
keep editable specs in `visuals/specs/<materia>/<tarea>/` and rendered assets in
`assets/generated/<materia>/<tarea>/`. Prefer SVG; add PNG only when DOCX or
LibreOffice requires raster output.

Photographic or handwritten evidence is not regenerated: preserve aspect ratio,
do not crop without explicit approval, never enlarge, and scale only when the
source exceeds 1200px wide. Give each photo a descriptive caption and use
`source` text that identifies the own photograph/scan and its context. Set
`renderer: photo`. Inspect clipping, legibility, and blank space at normal PDF
zoom before insertion; replace or split unreadable evidence.

## Renderer gates

| Need | Renderer |
|---|---|
| Flow, process, or tree | Mermaid |
| Academic chart or comparison | Vega-Lite / Altair / vl-convert |
| Dashboard-like visual | ECharts SVG SSR |
| Custom card or infographic | HTML + Playwright screenshot |
| Simple curve | Vega-Lite, unless custom mathematics requires Matplotlib |

Unsupported dependencies fail explicitly. Do not substitute a renderer silently.
Reject raw Mermaid when labels are tiny, hierarchy is unclear, arrows are
awkward, or styling is weak; use custom CSS or HTML/Playwright instead.

## Subject presets

Use these only as topic suggestions, not automatic style selection: Sistemas
Operativos (VMs, containers, process flows, memory, scheduling, security),
Diseño de Software (use cases, domain/component models, requirements, journeys),
Complejidad Computacional (automata, graphs, recursion, Big-O, Turing machines),
Investigación (article matrices, methodology, evidence maps), and Ecuaciones
Diferenciales (curves, slope fields, sensitivity, model comparisons). Apply the
approved conceptual-map aesthetic for Sistemas Operativos only when requested.

## Commands

Run from the canonical automation root, after setting the content root described
by the skill. Use the local environment and preserve specs/manifests:

```bash
./.venv/bin/python tools/visual_builder.py mermaid <spec.mmd> --out <asset.svg>
./.venv/bin/python tools/visual_builder.py vegalite <spec.vl.json> --out <asset.svg>
./.venv/bin/python tools/visual_builder.py echarts <spec.echarts.json> --out <asset.svg>
./.venv/bin/python tools/visual_builder.py html-shot <spec.html> --out <asset.png>
./.venv/bin/python tools/visual_builder.py validate assets/generated/<materia>/<tarea>
```
