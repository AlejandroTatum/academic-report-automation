---
name: academic-visual-builder
description: "Trigger: figures, graphs, diagrams, infographics, academic visuals. Generates and validates visuals for Alejandro's UNL reports."
license: Apache-2.0
metadata:
  author: "gentleman-programming"
  version: "1.2"
  scope: "figures-and-visuals"
---

## Activation Contract

Use for figures, diagrams, charts, infographics, photo evidence, visual specs,
rendering, or visual checks before a PDF/DOCX export. This skill owns visual
assets only; `academic-report-builder` owns prose, assembly, and report readiness.

## Hard Rules

- Prefer original, editable SVG visuals. Keep specs and generated assets in the paths defined by `references/visual-workflow.md`.
- Visual assets, specs, manifests, and audits are working evidence: they live in the repo-defined work paths and are never copied to the user's Documents delivery folder. Only the final assembled PDF/DOCX produced by `academic-report-builder` reaches that folder; see `references/clean-delivery.md` in that skill.
- Every manifest must follow `references/figures-yml-schema.md`. Require stable unique `request_id`/`result_id`, raw-byte SHA-256, source/provenance, explicit license text and status, canonical section, caption, and `alt_text` accessibility text.
- Treat `section` as canonical; accept `intended_section` only when section is absent or identical after trimming. Reject conflicts and integrity mismatches; never silently crop, substitute, overwrite, or accept unknown licensing.
- Validate asset existence, listed/unlisted assets, metadata, readability, clipping, and photo rules before insertion. Stop on missing metadata, duplicate identity, missing/unreadable/mutated assets, or unavailable dependencies. Renderer values remain open-ended; unsupported dependencies fail explicitly.
- The visual PDF auditor PASS is automated `AUDITOR_PRECHECK` evidence only; the auditor does not grant `VISUAL_PASS`. Direct semantic inspection of the assembled report owns report-level `VISUAL_PASS`; `HUMAN_REVIEW` after immutable hashes is required for `READY_TO_SUBMIT`.
- Keep private evidence local unless explicit scoped upload consent exists; redact secrets from diagnostics and provenance.

## Decision Gates

| Need | Renderer |
|---|---|
| Flow/process/tree | Mermaid |
| Chart/comparison | Vega-Lite / Altair / vl-convert |
| Dashboard-like visual | ECharts SVG SSR |
| Custom card | HTML + Playwright |
| Unsupported dependency | Fail; do not substitute silently. |

## Execution Steps

1. Load `references/figures-yml-schema.md` and `references/visual-workflow.md`; choose the visual and distinguish generated figures from photos.
2. Create the editable spec and complete manifest before drafting; render with the canonical local toolchain.
3. Run `tools/visual_builder.py validate`, then run the report validator when the asset is assembled. Retain hashes and provenance.
4. Inspect the complete assembled report and applicable full-size pages directly; use the auditor only as precheck evidence. Report defects and stop on failure.

## Readiness Model

`BUILD_PASS → VALIDATION_PASS → AUDITOR_PRECHECK → RENDERED_READBACK →
SEMANTIC_VISUAL_INSPECTION → VISUAL_PASS → HUMAN_REVIEW → READY_TO_SUBMIT`.
Only the parent report skill can expose final report readiness.

## Output Contract

Return asset paths, request/result IDs, manifest status, renderer, raw-byte hashes,
source/license status, alt text, validation/precheck result, semantic-inspection
evidence, and readability/layout issues. Never imply `HUMAN_REVIEW` or readiness.

## References

- `references/figures-yml-schema.md` — executable metadata contract and examples.
- `references/visual-workflow.md` — asset classes, photo rules, renderer gates, and commands.
