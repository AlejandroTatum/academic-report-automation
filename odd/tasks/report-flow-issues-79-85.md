# Report flow issues #72 (points 2-7) and #79-#85

Feature: `report-flow-issues-79-85`. Branch: `fix/report-flow-issues-79-85` from `main` @ `bd7bd95`.
Engram mirror: topic `odd/report-flow-issues-79-85/tasks`, project `academic-report-automation`.
Runner: `.venv/bin/python -m pytest tools/ tests/`. RDD off (clone_local). One commit per issue.

## Specs

- S1 (#85) "AA reports never print a list of figures. Other templates (plain/libre, chamba) keep their current behaviour; non-academic routes still never get one."
- S2 (#79) "Document creation does not use RDD. The validate phase always runs the fallback chain (validators, visual auditor, page-by-page inspection) and records `mode: fallback` without asking, regardless of the global review switch. RDD stays for code changes in the automation repository." Proposed fix: "Delete the RDD branch from the validate phase ... Drop `mode: rdd` from the receipt schema (or keep it only for legacy receipts)."
- S3 (#80) "Choices the user already made about the document (format, output, delivery folder, group metadata) are recorded once and are not asked again. A request for changes only reopens the body approval; the next gate asks only "approve `body.md`?" plus any format field still missing." Proposed fix: "record the format answers in `report.yml` as soon as they are given ... keep only `approval.yml` bound to the approve answer."
- S4 (#81) "Text inside code listings is exempt from the literal-LaTeX check; only body prose and math are checked." Reproduction: a fenced code block with `title('4.2: errores en cos(\pi/3)')` must not fail with "COMANDOS LATEX RENDERIZADOS COMO TEXTO LITERAL EN EL PDF: \pi".
- S5 (#82) "A figure never crosses into the next subsection, the same guarantee #38 gave for sections." Proposed fix: "`\FloatBarrier` before each `\subsection` ... keeping `[tbp]`; no new report.yml key."
- S6 (#83) "An unusable delivery folder is reported when `delivery_dir` is recorded (format phase), before the build and the human reviews, so the user resolves it once, up front." Proposed fix: "Reuse the publisher's folder check in `doc_status` at the format phase (same function, earlier call), so `format` stays pending with that reason; no new state."
- S7 (#84) "The proposed folder follows the course's own naming (the practice type, e.g. `ejercicio`, `ape`, `aa`), not always the document format." Proposed fix: "default to `format`, but take the type from `metadata.practice_type`/the existing sibling folders when the course uses another word. Prefer reading the course layout over adding a new key."
- S8 (#72.2) "Add a test that walks a delivered report through a `delivery_dir` edit and asserts what `validate`, `review` and `deliver` report. The receipts stay bound to the same PDF bytes; deliver returns to pending for the new folder."
- S9 (#72.3) Cover check: "Alias keys (`titulo`, `tema`, `asignatura`) are not stripped ... A title hyphenated across lines ... A plain `str.replace` can cut inside a longer word. ... using `config.metadata` and a word-bounded match would be more robust."
- S10 (#72.4) "a profile that only sets `report_defaults` ... now also receives `delivery_dir` from the course repo. ... Document it in the module docstring and `data.md`, and add a test."
- S11 (#72.5-7) Readability: "Extract a `_delivery_template(config, profile, path, documents_root)` helper"; "`_course_folder_missing(config, documents_root)`"; render-record lifecycle "Group it, or move it into an `approval_marker` helper."

## Tasks

- [x] T1 S1 #85 inline — `6d7dd6b`
- [x] T2 S2 #79 inline (production.md, contract test, flow diagram) — `a4fd2e4`
- [x] T3 S3 #80 inline (approval.md, doc_status approval guidance) — `bfb30f5`
- [x] T4 S4 #81 inline (validate_report) — `4d71c3f`
- [x] T5 S5 #82 inline (four templates + real-compile test) — `550cdca`
- [x] T6 S6 #83 inline (doc_status format phase reuses scan_delivery_versions) — `045d0b6`
- [x] T7 S7 #84 inline (course_profile) — `6b8719a`
- [x] T8 S8 `e8d804f`, S9 `e6bcd29`, S10+S11 (5) `a4ce450`, S11 (6, 7) `4d96baf`
- [x] T9 S7 follow-up: never take another practice format as the course type — `cb51e67` (merged via PRs #86-#89)
- [x] T10 Review follow-ups (review `review-54ff631ced4fd3a5`), branch `fix/review-followups-86-89` from `main` @ `2440884`: F1 format-phase delivery scan survives `OSError` — `ac0bea9`; F2+F3 approval gaps from fields, folder check before the build — `6683084`; F4 folder suffix from the layout — `e4f7915`; F5 S4 exemption cuts only code the PDF renders, fences follow the builder's rule — see L8; F6 this entry

## Log

- L1 (2026-10-11) User: "hay issues pendientes, resuelve todos"
- L2 #72 point 1 already merged in PR #73 (`3f7c9bc`, `fedb831`); only points 2-7 remain.
- L3 The session was launched in duttyDent (no open issues there). User confirmed: "academic-report-automation" is the target repo.
- L4 #82: TeX Live's placeins has no `subsection` option ("Unknown option `subsection' for package `placeins'"); the templates prefix `\subsection` with `\FloatBarrier` instead. Real compile RED on old templates (plain, unl), GREEN after.
- L5 #84: `metadata.practice_type` is the APE Individual/Grupal field, so the folder type comes from the course's existing `unidad-<n>/<tipo>-<m>-<tema>/` folders; an existing folder for the same unit/type/number is reused.
- L6 #72.2 and #72.4 are characterization tests (behaviour already present, coverage missing): no RED by design.
- L7 Review `review-54ff631ced4fd3a5` (approved) left R3-literal-latex-global-subtraction: subtracting body.md code counts from the PDF count lets a dropped or re-rendered listing hide a prose defect, and the closing-fence regex required the opening fence's exact length.
- L8 F5: pdftotext extracts the listing wrap mark as "↪→", keeps line numbers, and can split an aligned trailing comment into its own column (real AVR APE PDF: 49 of 396 code lines not found whole, 9 after splitting at runs of spaces, none carrying a checked command). The check now cuts each code line out of the whitespace-free PDF text once, falls back to its space-separated pieces, and counts what remains; text the PDF does not hold stays counted. RED: listing missing from the PDF, longer closing fence, aligned comment column.
- L9 F5 checks: full suite 2327 passed. Native review `review-6b33c5f758e6290e` (resilience, reliability) approved and acknowledged; advisory follow-ups: R3-exemption-requires-verbatim-render, R3-lazy-import-path, R3-patterns-vs-collapsed-text, R3-whitespace-free-first-occurrence-cut.
