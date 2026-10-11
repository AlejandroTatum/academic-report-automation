# Review advisories after PR #90 and the Bauhaus map engine

Feature: `review-advisories-90`. Branch: `fix/review-advisories-90` from `main` @ `e7aa454`.
Engram mirror: topic `odd/review-advisories-90/tasks`, project `academic-report-automation`.

## Specs

- S1 R3-blocked-approval-untested (`tools/doc_status.py`, approval guidance when the format phase is blocked): pin it with a test.
- S2 R3-oserror-unbound-delivery (`tools/doc_status.py`, `_delivery_folder_problem` `except OSError`): an unreadable delivery folder is a reason, never a crash; pin it with a test.
- S3 R3-count-on-collapsed-text / R3-patterns-vs-collapsed-text (`tools/validate_report.py`): the literal-LaTeX count must run on the PDF text as extracted, not on a whitespace-free stream that can join `\` with the next word.
- S4 R3-fallback-pieces-cut-anywhere / R3-whitespace-free-first-occurrence-cut (`tools/validate_report.py`): a code line or its pieces are cut only at or after the listing's position, never from prose earlier in the document.
- S5 R3-exemption-requires-verbatim-render and R3-lazy-import-path: record the disposition.
- S6 Bauhaus engine follow-ups: R3-publish-file-mode, R3-publish-partial-overwrite, R3-last-resort-search-cost, R3-guard-rejects-baseline-specs, R3-parallel-run-not-contiguous (detail in L3 once mapped).
- S7 Delete the remote branches already merged into `main`.

## Tasks

- [x] T1 S1-S2 doc_status tests — inline — `cd14898`
- [x] T2 S3-S5 validator — inline — `9bcae96`
- [x] T3 S6 Bauhaus follow-ups — inline (one file after mapping) — `4e401fc`
- [x] T4 S7 remote branch cleanup — inline — 13 merged remote branches deleted (local copies kept); `origin` now holds only `main`

## Log

- L1 (2026-10-11) User: "dale soluciona eso en una nueva tanda" (the four advisories of review `review-e6a2a221e9643ed0`, the earlier Bauhaus R3 follow-ups, and the merged remote branches).
- L2 Issue #72 is closed; its points 2-7 shipped in `report-flow-issues-79-85` T8, so it is out of scope.
- L3 Bauhaus findings were recorded by ID only; an explore pass rebuilt them from `tools/bauhaus_maps.py`: publish leaves files 0600 (`NamedTemporaryFile` + `os.replace`); all-or-none held only for new files; the last-resort label search scanned every unit of every vertical connector, 36 candidates per unit; the side-by-side guard summed separate near-parallel samples.
- L4 T1: both tests pin behaviour already present (characterization, no RED by design); the OSError test asserts the "is not a readable folder" reason, so it exercises that branch.
- L5 T2: RED on a backslash ending a line joined with the next word, and on a split listing line cutting prose 600 characters later. The count now runs on the extracted text with code cut in place; listing lines match in document order, the rest of a located listing only within 400 non-blank characters. Real PDFs (AVR APE, Metodos 1.5): 0.04 s, no new errors.
- L6 S5 dispositions: R3-exemption-requires-verbatim-render is the intended fail-closed trade (an altered listing reports, never hides); R3-lazy-import-path keeps the module's existing lazy `build_latex_report` imports (three other call sites), no change.
- L7 T3: 5 RED (new-file mode 0600, replaced-file mode, partial overwrite, last-resort candidates on a 6000-unit connector, two 12-unit hugs summing to 18). Fixes: chmod the staged file, back up replaced files and restore them on failure, cap the last resort at `LAST_RESORT_REACH` 48 units, count only the longest unbroken run (engine and test oracle). Both shipped examples and both Engram maps render byte-identical before and after.
- L8 R3-guard-rejects-baseline-specs: the shipped examples already render under test (`tests/skills/test_visual_builder_contract.py:211`); the SDD flips rejected in bauhaus-map-followups L8 were real 78-unit hugs, rejected on purpose ("mia esas lineas tan pegadas"). No change.
- L9 Full suite after T1-T3: 2336 passed.
- L10 Verifier (S1-S3, S5, S7 PASS) and review `review-d74d7a433b97a83c` both found that `publish` registered a backup before `shutil.copy2` filled it, so a failed copy restored a truncated file over the intact original. RED reproduced it (`b"prec"`); the backup is now registered only after the copy, and a partial one is removed. Open design risk (verifier S4): more than 400 non-blank characters between two lines of one listing (a float or a page header) leaves the later lines counted, a fail-closed false positive.
