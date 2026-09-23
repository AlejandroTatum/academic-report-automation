# Contextual table styles (#13)

## Objective
Select one approved table style per table from document and data context, render it coherently in every backend, and record the selected ID and rationale in validation evidence.

## Problem / why
Every table renders as one generic grid (`table.style = "Table Grid"` in `tools/build_docx_report.py`); there is no catalog, no selection, and no evidence. The August SDD change `contextual-table-style-selection` designed the fix; implementation froze on a provider defect.

## Route
ODD delegated direct (user decision 2026-09-22). SDD artifacts in Engram are guidance, not an active SDD run:
- approved IDs (decision #6418): `TAB-CL-01`, `TAB-TC-02`, `TAB-MN-03`, `TAB-ZB-04`, `TAB-CE-05`, `TAB-ES-06`, `TAB-CC-07`
- explore #6419, proposal #6420, spec #6421, design #6422, tasks #6424 (named RED tests R1-R12, five slices).

## Constraints
- Strict TDD: on (source: user global config). Runner: `.venv/bin/python -m pytest tools/ tests/`.
- Versioned, source-controlled catalog; no runtime PDF parsing, no private absolute paths; teacher/institution overrides beat automatic selection; unsupported contexts block, never fall back silently.
- Delivery: forecast ~1,100-1,450 lines, over the 400 budget. One PR per slice merged to `main` in turn after its native review (stacked-to-main, as for #10-#12).
- RDD: on (global); review per slice.

## Tasks
- [x] T1 catalog + selector (R1-R4). Route: delegated writer.
- [x] T2 context model, override precedence, receipts (R5-R8). Route: delegated writer.
- [ ] T3 LaTeX tokens (R9 latex). Route: delegated writer.
- [ ] T4 DOCX tokens (R9 docx). Route: delegated writer.
- [ ] T5 HTML tokens + rendered corpus, multipage, grayscale/accessibility (R9 html, R10-R12). Route: delegated writer.

## Acceptance
- 7/7 requirements, 12/12 scenarios observed RED then GREEN; full suite green; auditor output is a precheck, never `VISUAL_PASS`.

## Progress / evidence
- Branch `feat/contextual-table-styles` from `main` d185e29.
- T1 done (23788da `feat(tables): catalog selector`). RED confirmed on parent
  (`ModuleNotFoundError: table_styles`) before `tools/table_styles.py`
  existed; GREEN after implementation. `templates/table_styles.yml` +
  `tools/table_styles.py` + `tools/test_table_styles.py`
  (+648 lines: yml 205, table_styles.py 325, tests 118).
  RED/GREEN tests: `test_issue_13_exact_versioned_catalog`,
  `test_issue_13_catalog_is_runtime_self_contained`,
  `test_issue_13_context_matrix_is_deterministic`,
  `test_issue_13_applicability_and_avoidance`. Full suite: 1055 passed
  (baseline before this slice, verified at e4d2588 in an isolated
  worktree: 1050; +4 from `tools/test_table_styles.py`; +1 from
  `tools/test_no_duplicate_definitions.py`'s existing parametrize picking
  up the new `table_styles.py` module automatically).
  Deviation from design: added an explicit `priority` field per catalog
  entry (design's schema names only `label`, `deprecated`, `tokens`,
  `applicability`, `avoidance`). Determinism requires an auditable
  tie-break when two approved styles are both applicable and not avoided
  for the same context (e.g. `TAB-CL-01` and `TAB-TC-02` both match a
  plain short reference table); an explicit integer is simpler and more
  reviewable than a computed specificity score. Documented in
  `templates/table_styles.yml`'s header.
  Tokens/applicability/avoidance were derived once from the private
  human-review catalog's prose (`/home/alejo/devwork/.projects/university/.reports-system/automation/reports/catalogo-estilos-tablas/body.md`,
  read only at authoring time, never at runtime) — matches design's
  "derived once from the catalog" instruction; `test_issue_13_catalog_is_runtime_self_contained`
  asserts no private-path/PDF-parsing dependency survives in the shipped
  loader or YAML.

- T2 done (addbcba `feat(tables): context receipts`). RED confirmed on
  parent (`ModuleNotFoundError: table_model`) before `tools/table_model.py`
  existed; GREEN after implementation. `tools/table_model.py` +
  `tools/test_table_model.py` + `ReportConfig.table_style_overrides` /
  `.institution_table_style` in `tools/report_config.py` + `tables:`
  section in `templates/academic_format.yml` (+299 lines: table_model.py
  129, tests 134, report_config.py +26, academic_format.yml +10). RED/GREEN
  tests: `test_issue_13_override_precedence`,
  `test_issue_13_invalid_override_rejection` (3 parametrized cases:
  unapproved, missing, context-incompatible),
  `test_issue_13_deprecated_override_rejection`,
  `test_issue_13_unsupported_context_blocks`,
  `test_issue_13_selection_evidence_receipt`. Full suite: 1063 passed
  (1055 + 7 new + 1 from the existing duplicate-top-level-function
  parametrize picking up `table_model.py`).
  Deviation from tasks #6424: `tools/check_table_contexts.py` and the
  markdown table-directive parser it needs (`parse_table_blocks`) were
  assigned to this slice but are deferred to T3. Nothing in R5-R8
  exercises them, and the directive syntax is an implementation detail
  the design doc leaves open ("explicit context directive adjacent to
  each Markdown table", no concrete grammar) — building it now, before
  any renderer consumes parsed table blocks, risked guessing an interface
  T3 would have to reshape. Not a product-decision gap; just resequenced.

## Decision gap found while scoping T3 (LaTeX tokens)

T3 needs a real markdown-table-directive parser plus per-style LaTeX token
mapping for all ten token dimensions (borders, header, alignment, padding,
density, row_rhythm, palette, indicators, caption, notes) across all seven
styles, backed by golden fixtures (`test_table_backend_contracts.py -k
latex`). Structural tokens (borders/header/alignment/padding/density/
caption position) map cleanly from the catalog. Two specifically do not,
and neither #6418 (approved IDs) nor #6421 (spec) nor #6422 (design)
settles them:

1. `TAB-CE-05` (`row_rhythm: column_emphasis`) needs to know WHICH column
   is the "protagonist" to shade/bold. Plain Markdown tables carry no
   per-column semantic markup, and `TableContext` (T1) has no
   `emphasis_column` field.
2. `TAB-TC-02` and `TAB-ES-06` (`indicators: symbol_color`) need to know
   WHICH cells carry a status/comparison meaning, to attach a symbol
   (✓/✗/▲) plus color. Nothing in the current pipeline marks cells this
   way.

Options:
   (a) Add an authoring convention now (e.g. a directive attribute
       `emphasis_column: <index>`, and a per-cell inline marker like
       `[[status:ok]]` the parser strips and maps to symbol+color) —
       changes the Markdown authoring contract every future table with
       these two styles must follow.
   (b) Scope T3-T5 to the eight tokens that ARE derivable now, and encode
       `column_emphasis`/`symbol_color` as a documented backend limitation
       (structurally coherent header/border/density/etc., but no per-cell
       semantic decoration) until an authoring convention is chosen.
   (c) Something else the user prefers.

I did not choose (a) unilaterally because it is an authoring-contract
change, not an implementation detail, and did not choose (b) either
because it would silently under-deliver two of the seven approved styles.
Stopping T3-T5 here rather than guessing.

## Next step
Ask the user to pick an option above for the two per-cell/per-column
semantic tokens, then resume T3 (LaTeX tokens — R9 latex) with the
deferred table-directive parser and `tools/check_table_contexts.py`,
followed by T4 (DOCX) and T5 (HTML + rendered validation). T1 and T2 are
merge-ready independently: they add no wiring into `build_latex_report.py`,
`build_docx_report.py`, or `build_report.py`, so no existing report's
output changed.
