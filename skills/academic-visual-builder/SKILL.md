---
name: academic-visual-builder
description: "Trigger: figures, graphs, diagrams, infographics, academic visuals. Generates and validates visuals for Alejandro's UNL reports."
license: Apache-2.0
metadata:
  author: "gentleman-programming"
  version: "1.2"
  scope: "figures-and-visuals"
---

# Academic Visual Builder

## Activation Contract

Use when Alejandro needs visuals for university work: flowcharts, architecture diagrams, decision trees, UML-style diagrams, comparison charts, matrices, rankings, timelines, evidence tables, curves, model comparisons, HTML/CSS infographic cards, or visual validation before exporting DOCX/PDF.

## Hard Rules

- Generate original visuals from specs/code by default. Use external images only from teacher material, official documentation, or clearly citable/licensed sources.
- Keep editable specs in `visuals/specs/<materia>/<tarea>/` and rendered assets in `assets/generated/<materia>/<tarea>/`.
- Prefer SVG first; create PNG fallbacks only when LibreOffice/DOCX rendering needs raster.
- Every figure folder must include `figures.yml` following `references/figures-yml-schema.md` (file, title, caption, source, renderer, section — all required; `intended_section` accepted as legacy/backward-compatible alias). Every figure MUST have traceable metadata before insertion into a report; a figure with no `source` or no `section` must not be included in the final PDF/DOCX.
- Fail before report export if any figure is missing, unreadable at normal PDF zoom, too small, lacks caption/source, or creates excessive blank space.
- Reject raw Mermaid when labels are tiny, hierarchy is unclear, arrows are awkward, or styling is weak; use custom CSS or switch to HTML/Playwright.
- Preserve stable visual identity: correlate non-empty unique request/result IDs, canonical `section`, content hash, alt text, and license/status. Never silently crop, substitute, or overwrite a figure.
- Keep private evidence local unless the job has explicit scoped upload consent; redact secrets from diagnostics and provenance.

### Photo evidence handling

`academic-visual-builder` handles two distinct image types with different rules:

**Type A — Generated figures/diagrams:** Created by code (Mermaid, Vega-Lite, ECharts, Matplotlib, etc.). SVGs preferred. Editable specs kept in `visuals/specs/`.

**Type B — Photographic evidence / handwritten process photos:** Photographed or scanned by Alejandro (e.g. handwritten exercises, whiteboard sketches, physical lab notes). Rules:

- **Aspect ratio:** Preserve original. Do NOT crop to fit unless Alejandro explicitly approves the crop.
- **Max dimensions:** Scale down for A4 insertion if larger than 1200px wide, but never enlarge beyond original resolution. Keep readable at 100% PDF zoom.
- **No auto-cropping:** Never crop margins or extraneous background without explicit approval.
- **Captions:** Every photo must have a caption explaining WHAT is shown (e.g. "Proceso de planificación SJF manuscrito — ejercicio 3"). Captions must be tied to the image; do not leave photos floating unattributed.
- **Contact sheet visual review:** Before inserting photo evidence into a report, run the visual PDF auditor or visually scan the contact sheet to verify: (a) the photo is not clipped at page edges, (b) the photo is legible, (c) no blank space where the photo should be.
- **Source in figures.yml:** For photo evidence, use `source: "Fotografía/escaneo propio — [context]"` to distinguish from generated figures.
- **Renderer tag in figures.yml:** Use `photo` as the renderer value for photo evidence entries.
- **Validation:** If a photo is unreadable at normal PDF zoom, replace with higher-resolution source or split into multiple zoomed sections.

## Decision Gates

| Need | Renderer |
| --- | --- |
| Simple flow/process/tree | Mermaid |
| Academic chart/comparison | Vega-Lite / Altair / vl-convert |
| Dynamic dashboard-like visual | ECharts + SVG SSR |
| Custom infographic/card | HTML + Playwright screenshot |
| Simple math curve | Vega-Lite, unless custom math needs Matplotlib |
| Unsupported renderer/dependency | Fail explicitly; do not silently switch renderer. |

## Execution Steps

1. Choose visuals during outline; distinguish generated figures from photographic evidence.
2. Create editable specs and `figures.yml` before drafting; normalize `intended_section` to `section` when required.
3. Render with the canonical automation root and local environment, never an unverified system tool.
4. Validate metadata, stable identities, hashes, licensing, existence, readability, clipping, and photo rules before insertion.
5. Insert captions and sources, then run the PDF visual audit. A visual pass does not grant report readiness.

## Automation root convention

All report automation commands use a single canonical root. Before running commands, set this shell variable:

```bash
REPORT_AUTOMATION_ROOT="/home/alejo/devwork/apps/academic-report-automation"
REPORT_CONTENT_ROOT="/home/alejo/devwork/.projects/university/.reports-system/automation"
```

Then use `$REPORT_AUTOMATION_ROOT` in all commands. This skill assumes you set this variable before execution.

Canonical root: `/home/alejo/devwork/apps/academic-report-automation`

## Commands

All commands run from `$REPORT_AUTOMATION_ROOT`. Always set working directory before executing:

```bash
cd "$REPORT_AUTOMATION_ROOT" && ./.venv/bin/python tools/visual_builder.py mermaid <spec.mmd> --out <asset.svg>
cd "$REPORT_AUTOMATION_ROOT" && ./.venv/bin/python tools/visual_builder.py vegalite <spec.vl.json> --out <asset.svg>
cd "$REPORT_AUTOMATION_ROOT" && ./.venv/bin/python tools/visual_builder.py echarts <spec.echarts.json> --out <asset.svg>
cd "$REPORT_AUTOMATION_ROOT" && ./.venv/bin/python tools/visual_builder.py html-shot <spec.html> --out <asset.png>
cd "$REPORT_AUTOMATION_ROOT" && ./.venv/bin/python tools/visual_builder.py validate assets/generated/<materia>/<tarea>
```

## Subject Presets

- Sistemas Operativos: VM vs containers, process flows, memory maps, scheduling comparisons, security decision trees.
- Diseño de Software: use cases, domain models, component diagrams, requirements flows, user journeys.
- Complejidad Computacional: automata, graphs, recursion trees, Big-O comparisons, Turing-machine flows.
- Investigación: article matrices, methodology flows, evidence maps, approach comparisons.
- Ecuaciones Diferenciales: solution curves, slope fields, model behavior comparisons, parameter sensitivity charts.

For Sistemas Operativos with Ing. Hernán Torres conceptual maps, use the approved editorial conceptual-map aesthetic reference when requested; do not apply that subject-specific style automatically elsewhere.

## Role

This skill is for **figures, diagrams, charts, infographics, and visual assets only** — not for full report text or document layout. Use `academic-report-builder` for overall reports and insert generated visuals as part of that workflow.

The visual builder owns specs, rendering, manifest entries, captions/sources and
asset validation. The report builder owns intake, prose, citations, assembly,
ordered gates, human review and `READY_TO_SUBMIT`. In `lab-report-agent`, the
repository adapter validates the stronger manifest contract (`request_id`,
`result_id`, `section`, accessibility, license and hash) before export.

## Failure rules

Stop on missing metadata, duplicate identity, missing/unreadable/mutated asset,
unknown license, clipped/cropped content, or unavailable renderer dependency.
Preserve source specs and prior receipts; report the asset-addressable failure.

## Readiness Model (visuals in reports)

Visual assets are part of the wider report flow:

| Gate | Label | What it proves |
|------|-------|----------------|
| 1 | **BUILD_PASS** | Figures rendered without errors (all commands exit 0). |
| 2 | **VALIDATION_PASS** | `figures.yml` validated, asset files exist, metadata complete. |
| 3 | **VISUAL_PASS** | Visual PDF audit (via `visual_pdf_auditor.py`) finds no blocking defects. |
| 4 | **HUMAN_REVIEW** | Parent report records reviewer approval against the passed artifacts. |
| 5 | **READY_TO_SUBMIT** | All previous gates pass and the approved artifacts remain unchanged. |

- Visuals are a component of the report flow; do NOT declare a report READY_TO_SUBMIT based on visual generation alone.
- The parent report's `academic-report-builder` or `reporte` skill owns the final READY_TO_SUBMIT gate.
- The strict order is `BUILD_PASS → VALIDATION_PASS → VISUAL_PASS → human review → READY_TO_SUBMIT`.
- **Output discipline:** Final report PDFs go into `outputs/<materia-slug>/`. Visual assets used in reports are intermediate artifacts kept in `assets/generated/<materia>/<tarea>/` — they are NOT final deliverables.

## Output Contract

Return asset paths, stable request/result IDs, `figures.yml` and repository-manifest status, renderer, hashes/licensing, validation result, and layout/readability issues. State `VISUAL_PASS` separately; never imply human review or `READY_TO_SUBMIT`.

## References

- `references/figures-yml-schema.md` — normative schema for `figures.yml` metadata, including required fields, traceability rule, example, and validation checklist. Canonical copy also at `$REPORT_AUTOMATION_ROOT/references/figures-yml-schema.md`.
