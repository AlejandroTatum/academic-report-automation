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
- [x] T2 #32 validate_report: skip materia warning when pdf_path is already under the route-derived output folder; body-start marker route-aware. RED tests in `tools/test_output_location_guard.py`, `tools/test_cover_route_defaults.py`.
- [x] T3 #33 doc_status approval detail names every bound file (preview.md and body.md); deliver_report lists granted/missing gates from `validation.yml` `gates:`. RED tests in `tools/test_doc_status_approval.py`, `tools/test_deliver_report.py`.
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

- T2 done: `tools/validate_report.py` `common_validation` skips the materia
  warning when `config.pdf_path` already resolves under
  `GLOBAL_OUTPUTS / config.output_folder_slug` (guarded by
  `config.route_is_known` to avoid `publication_category`'s KeyError on an
  unknown route); the body-start heuristic (`body_marker_pattern`) now only
  applies on `config.route == DEFAULT_ROUTE` (academic).
  RED: `test_no_materia_warning_when_pdf_already_under_route_derived_folder`
  (tools/test_output_location_guard.py) and
  `test_technical_route_with_cover_does_not_false_warn_on_unnumbered_heading`
  (tools/test_cover_route_defaults.py) both failed before the fix.
  GREEN: both files -> 44 passed.
  Full suite: 961 passed (was 959; +2 new tests).

- T3 done: `tools/approval_marker.py` adds `BOUND_FILES`/`bound_file_names()`
  derived from `REQUIRED_KEYS`; `doc_status._phase_approval` DONE detail now
  names every bound file (`approval.yml matches preview.md and body.md`).
  `tools/deliver_report.py` adds `KNOWN_GATES` and derives the granted/missing
  gate list from the receipt's `gates:` instead of a fixed phrase.
  RED: `test_approval_current_is_done` (tools/test_doc_status_approval.py,
  the new `body.md` assertion) and
  `test_delivery_message_lists_gates_from_the_receipt`
  (tools/test_deliver_report.py) both failed before the fix.
  GREEN: both files -> 20 passed.
  Full suite: 962 passed.

## Next step
T4 #31: aspect-ratio figure sizing in `tools/build_latex_report.py`.
