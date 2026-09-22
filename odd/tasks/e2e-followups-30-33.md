# E2E follow-ups #30-#33

## Objective
Fix the four defects filed after the `engram-funcionamiento` end-to-end run of the document-workflow skill.

## Problem / why
The E2E run on a technical-route report surfaced gaps that only appear outside the academic route: validate has no fall-through when the RDD candidate cannot bind, figure sizing is keyed by old report filenames, the validator emits false warnings on non-academic routes, and status/delivery messages are hardcoded instead of derived from the receipts they gate on.

## Scope (authorized 2026-09-22, "dale con los 3 pendientes en automatico")
- #30 `skills/document-workflow/references/validate.md` fall-through rule.
- #32 `tools/validate_report.py` route-aware warnings.
- #33 `tools/doc_status.py`, `tools/deliver_report.py` receipt-derived messages.
- #31 `tools/build_latex_report.py` figure sizing (printed-label validator gate is out of scope; separate issue if needed).

## Constraints
- Strict TDD: on (source: user global config "Strict TDD Mode: enabled"). Runner: `.venv/bin/python -m pytest tools/ tests/`.
- Shrink the system: derive from existing data/receipts, no new flags.
- Delivery: forecast ~100-150 authored lines -> single PR (`ask-on-risk`, under budget).
- RDD: on (global). Review assessed per work-unit commit.

## Tasks
- [x] T1 #30 validate.md: when the native RDD candidate cannot bind to `reports/<wf>/**`, fall through to the fallback branch and record `reason:` in `validation.yml`. Route: delegated writer (4+ files overall).
- [ ] T2 #32 validate_report: skip materia warning when pdf_path is already under the route-derived output folder; body-start marker route-aware. RED tests in `tools/test_output_location_guard.py`, `tools/test_cover_route_defaults.py`.
- [ ] T3 #33 doc_status approval detail names every bound file (preview.md and body.md); deliver_report lists granted/missing gates from `validation.yml` `gates:`. RED tests in `tools/test_doc_status_approval.py`, `tools/test_deliver_report.py`.
- [ ] T4 #31 build_latex_report: remove filename-substring width table; size from image aspect ratio with a height cap; reconsider hard `[H]`. RED test in `tools/test_figure_detection.py`.

## Acceptance
- Each issue's expected behavior holds with a test that was observed RED then GREEN.
- Full suite green; one Conventional Commit per task.

## Progress / evidence
- Route: T1-T4 delegated to one writer (writer trigger: 2+ non-trivial files).
- T1 done: `skills/document-workflow/references/validate.md` "Branch selection" now
  names the RDD candidate (`reports/<wf>/**`, binaries excluded) and the fall-through
  condition (unbindable candidate -> fallback branch, `reason:` recorded in the
  `validation.yml` schema). Doc-only, no RED test needed.
  Evidence: `tests/skills/test_document_workflow_contract.py -q` -> 17 passed.
  Full suite: `.venv/bin/python -m pytest tools/ tests/ -q` -> 959 passed.

## Next step
T2 #32: route-aware materia warning and body-start heuristic in `tools/validate_report.py`.
