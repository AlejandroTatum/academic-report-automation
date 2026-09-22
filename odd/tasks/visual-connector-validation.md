# Visual connector validation (#10)

## Objective
Deny `VISUAL_PASS` when final report diagrams contain obstructed, crossing, crowded or misdirected connectors, using renderer-real geometry, both on the isolated SVG and at final printed size in the PDF.

## Problem / why
Visual validation only asks the agent to eyeball geometry (`skills/academic-visual-builder/references/visual-workflow.md:63`). The August SDD change `complete-visual-connector-validation` planned the fix; its implementation froze on a provider defect (gentle-ai#3129). Its phase 1 (`7f321f6`) existed only on an archive tag.

## Route
ODD delegated direct (user decision 2026-09-22: "flujo directo aplica odd"). The SDD artifacts in Engram are the design guidance, not an active SDD run:
- spec `sdd/complete-visual-connector-validation/spec` (#6402)
- design `sdd/complete-visual-connector-validation/design` (#6403)
- tasks `sdd/complete-visual-connector-validation/tasks` (#6404): named RED tests R1-R7, fixtures, 0.80 clearance, final-size stage.

## Constraints
- Strict TDD: on (source: user global config). Runner: `.venv/bin/python -m pytest tools/ tests/`.
- Stdlib-only geometry; derive from parsed SVG data; no new flags. Do not cherry-pick `551dd27`/`db6c326`.
- Delivery: forecast ~1,050-1,250 lines, over the 400 budget. One PR per slice, each merged to `main` in turn after its native review (stacked-to-main; supersedes the August feature-branch-chain because slices now merge sequentially).
- RDD: on (global); review per slice.

## Tasks
- [x] T1 (SDD phase 1, PR1) recover parser/corpus `7f321f6` as `bba66ec` `feat(visual): parse renderer-real connectors`. Route: delegated writer (cherry-pick, clean auto-merge in `tools/visual_builder.py`).
- [ ] T2 (SDD phase 2, PR2) `feat(visual): protect connector routes`: R2-R6 in `tools/test_connector_geometry.py` (protected regions, crossing vs touching, 0.80 clearance, source/target/direction, actionable evidence, chart silence) with the named fixtures. Route: delegated writer.
- [ ] T3 (SDD phase 3, PR3) `feat(visual): enforce final-size connector gate`: R7 in `tools/test_connector_pdf_stage.py`, contract REDs in `tests/skills/test_visual_builder_contract.py`, `tools/connector_pdf_stage.py`, `tools/validate_report.py`, SKILL.md and `visual-workflow.md` rules. Route: delegated writer.

## Acceptance
- SDD spec requirements hold with named tests observed RED then GREEN; full suite green; open connector failure denies `VISUAL_PASS`.

## Progress / evidence
- T1: `bba66ec` on `fix/visual-connector-validation`; `.venv/bin/python -m pytest tools/ tests/ -q` -> 978 passed.

## Next step
Verify T1 suite, then delegate T2-T3.
