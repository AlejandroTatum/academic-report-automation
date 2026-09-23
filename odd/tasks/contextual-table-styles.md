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
- [x] T3 LaTeX tokens (R9 latex). Route: delegated writer.
- [x] T4 DOCX tokens (R9 docx). Route: delegated writer.
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

**Resolved 2026-09-22 — user selected option (a).** Authoring convention
(documented in
`skills/academic-report-builder/references/quality-gates.md`, "Contextual
table styles (issue #13)"):
- `emphasis_column: <0-indexed int>` directive attribute for
  `TAB-CE-05`'s protagonist column. Required whenever that style applies;
  out of range blocks with a finding.
- `[[status:<value>]]` inline cell markers for `TAB-TC-02`/`TAB-ES-06`.
  Approved values are versioned in `templates/table_styles.yml`'s new
  `status_indicators:` section (`ok`, `fail`, `warn`, `up`, `down`); every
  value carries a distinct symbol AND an accessible label alongside its
  color — never color alone, so grayscale/colorblind rendering keeps
  meaning. An unknown marker value blocks with a finding.

## T3 evidence (LaTeX tokens, R9 latex)

Commit 9275bbe `feat(tables): latex tokens` (20 files changed, +1400/-5).
New production modules, each with a preceding failing test observed before
implementation:

- `tools/table_directives.py` — Markdown directive/marker parser.
  `<!-- table-style: <key> purpose=... [meaning=] [emphasis=]
  [color_policy=] [accessibility_needs=] [emphasis_column=] -->`
  immediately before a table (blank lines only in between); structural
  facts (columns/rows/length/pagination/density) always derived, never
  declared. `context_for_table` (backward-scan from a table's start line)
  is reused both by `parse_table_blocks` (whole-document scan, used by the
  CLI checker) and directly by `build_latex_report.py`'s existing
  line-scanning loop, so there is exactly one table-detection pass driving
  the actual renderer — no risk of two independent scanners disagreeing on
  table boundaries.
- `tools/table_styles.py` (extended) — `status_indicators:` catalog
  section (symbol + `#RRGGBB` color + accessible label per approved
  value, duplicate-symbol load blocked) and `TableContext.emphasis_column`
  (optional, default `None`, backward-compatible with T1).
- `tools/table_latex_tokens.py` — pure `render_styled_table_latex`: maps
  all ten style tokens to LaTeX (borders → vertical rules/`\hline`
  placement, header → `\rowcolor`/`\color{white}`, alignment →
  `\centering`/`\raggedright`/`\raggedleft`, padding →
  `\tabcolsep`/`\arraystretch`, density → font size, row_rhythm →
  `\rowcolors`/`\cellcolor`, indicators → inline symbol+color+label plus a
  trailing legend, caption/notes → above/below/inline). Keeps the existing
  longtable(≤2 cols)/xltabular(>2 cols) choice (#26) so wrapping/pagination
  behavior is unchanged. No import from `build_latex_report.py` (avoids a
  circular import) — `convert_inline` is injected.
- `tools/build_latex_report.py` (modified) — `markdown_to_latex` gains an
  optional `table_styles: TableStylesContext | None = None` parameter
  (default `None`, so every existing call site and every report without
  `table_styles: {enabled: true}` is byte-for-byte unchanged); when given,
  the table-detection branch looks up the table's directive via
  `context_for_table` and either renders through
  `render_styled_table_latex` or raises `SystemExit` for a table with no
  directive. `render_tex` constructs the context only when
  `config.table_styles_enabled`.
- `tools/table_model.py` (extended) — `TableStylesContext` (catalog +
  per-table teacher overrides + institution default) and `.request_for`.
- `tools/report_config.py` (extended) — `table_styles_enabled` property
  (default `False`).
- `tools/check_table_contexts.py` — read-only migration CLI:
  `scan_directory` reports directed/undirected tables per file and
  malformed-directive errors; exit code reflects only real errors
  (undirected is a migration note, not a failure). Verified against the
  fixture corpus: `.venv/bin/python tools/check_table_contexts.py
  tests/fixtures/table_styles` → "Tablas con directiva: 3 / sin
  directiva: 0 / inválidas: 0".
- `tests/fixtures/table_styles/sample-reports/latex/` — fixture report
  (`table_styles: {enabled: true}`, three directed tables: reference,
  column-emphasis comparison, status). Named `sample-reports/`, not the
  tasks-suggested `reports/`: `.gitignore` has an unanchored `reports/`
  rule for the private content tree that silently swallowed the first
  attempt (`git status` showed nothing after `git add`) — caught before
  committing by checking `git diff --cached --stat` line counts against
  expectation. `tests/fixtures/table_styles/golden/latex/results-summary.tex`
  — golden fragment captured from a real `build_latex_report.build(...,
  compile_pdf=False)` run (the harness command from tasks #6424,
  `--tex-only` equivalent) and hand-reviewed before being pinned.

**Bug found and fixed during golden capture, not from a named scenario**:
the first capture attempt showed the *next* table's directive comment
(`<!-- table-style: method-comparison ... -->`) rendered as literal
escaped text in the `.tex` output — directive lines were falling through
`markdown_to_latex`'s generic paragraph path. Fixed by skipping any line
matching the directive regex at the top of the main loop (before fence/
heading/etc. handling), unconditionally — a directive is inert whether or
not `table_styles` is enabled for that build. Regression test added:
`test_directive_comment_never_renders_as_visible_text` in
`tools/test_table_styles_latex_wiring.py` (passes after the fix; the raw
leaked comment text in the pre-fix golden capture is the RED evidence —
not re-derived by reverting, to avoid re-breaking a since-fixed file).

RED/GREEN tests (all named per-module, not spec `R`-numbers — R9 is
covered by `test_issue_13_backend_style_coherence_latex`, parametrized
over the seven approved IDs): `tools/test_table_directives.py` (9),
`tools/test_table_backend_contracts.py` (10, incl.
`test_issue_13_backend_style_coherence_latex[<7 IDs>]`),
`tools/test_table_styles_config.py` (7, incl. 2 pre-existing-but-untested
T2 properties retroactively covered), `tools/test_table_styles_latex_wiring.py`
(5), `tools/test_table_styles_latex_fixture.py` (2, incl. the golden
comparison), `tools/test_check_table_contexts.py` (3), plus one new test
in `tools/test_table_styles.py` (`status_indicators`) and one in
`tools/test_table_model.py` (`TableStylesContext.request_for`). Full
suite: 1104 passed (1063 baseline for this slice + 41 new tests incl.
duplicate-top-level-function parametrize hits for
`table_directives.py`/`table_latex_tokens.py`/`check_table_contexts.py`).

Deviation from the ~400-line advisory: this slice landed at +1400/-5
(commit shortstat); the golden `.tex` fragment itself is 18 of those
lines. Reason: T3 absorbed the
directive parser and `check_table_contexts.py` deferred from T2, plus all
ten LaTeX tokens across seven styles plus the two newly-approved
authoring-convention tokens, in one slice — splitting further would have
left an unusable half-wired state (a parser with no renderer, or a
renderer with no way to reach `emphasis_column`/status markers).

Not attempted in this slice: no LaTeX compilation (Docker TeX Live) —
T3's harness only proves `.tex` generation (`--tex-only`); PDF-level
rendered-quality/accessibility evidence is T5's explicit scope (R10-R12).

## T4 evidence (DOCX tokens, R9 docx)

Commit 51319af `feat(tables): docx tokens` (7 files changed, +580/-1).

- `tools/table_docx_tokens.py` — pure-ish `render_styled_table_docx`,
  mirroring `table_latex_tokens.py` token for token: borders via
  `w:tblBorders` (+ a header-only `w:tcBorders` bottom rule for `minimal`,
  applied after the header row exists — first attempt crashed on
  `table.rows[0]` before any row existed, fixed by splitting table-wide
  border setup from the header-underline step), header shading via
  `w:shd`, alignment via `WD_ALIGN_PARAGRAPH`, padding via `w:tcMar`,
  density via `Pt` font size, alternating/column-emphasis row shading,
  status indicators as a colored run + a same-text-color label run (never
  color alone), caption/notes as paragraphs or a merged inline row. No
  import from `build_docx_report.py` (avoids the circular import that
  module already flags by importing from `build_latex_report.py`);
  `fill_cell` is injected, matching `DocxRenderer._fill_cell`'s signature.
- `tools/build_docx_report.py` (modified) — `DocxRenderer.__init__` builds
  `self.table_styles` from `config.table_styles_enabled` (same opt-in as
  LaTeX); `render_body`'s table branch mirrors `markdown_to_latex`'s:
  directive lookup via `context_for_table`, `SystemExit` for an undirected
  table, `render_styled_table` otherwise. The directive-comment line is
  skipped unconditionally in the main loop (same fix as T3, applied
  up front this time since the bug was already known).
- Fixture: `tests/fixtures/table_styles/sample-reports/docx/` (same three
  directed tables as the LaTeX fixture) +
  `tools/test_table_styles_docx_fixture.py`, asserted against a **reopened**
  `Document(path)` — this repository's own established DOCX test
  convention (`tools/test_build_docx_report.py`), not the raw
  `word/document.xml` diff tasks #6424 suggested: python-docx's XML
  serialization is not byte-stable across environments (attribute
  ordering), so a byte-diff golden would be more fragile than the
  property-assertion style already used throughout this codebase's DOCX
  tests. Documented in the test file's docstring.

RED/GREEN: `tools/table_docx_tokens.py`'s tests live in
`tools/test_table_backend_contracts.py` (`test_issue_13_backend_style_coherence_docx[<7 IDs>]`
+ 3 more: caption/notes, unknown marker, missing emphasis_column — 13
total docx-suffixed tests), `tools/test_table_styles_docx_wiring.py` (4),
`tools/test_table_styles_docx_fixture.py` (1). Both wiring and fixture
tests observed a real failure before the fix each time (`table.rows[0]`
`IndexError` for the border ordering bug;
`_shd_fill(document.tables[0]...) == None` vs expected `EAEAEA` before
realizing `tables[0]` is the academic cover table, not the body table —
fixed by indexing `tables[-1]`/`tables[1:]`, not by weakening the
assertion). Full suite: 1120 passed (1104 baseline for this slice + 16
new tests).

Not attempted in this slice: `.docx` cannot be opened/inspected visually
in this environment; rendered readback (does it look coherent to a human)
is T5's explicit scope for HTML, and there is no equivalent DOCX
rendered-check task in #6424 — accepted as-is.

## Next step
T5 (HTML tokens + rendered corpus, multipage, grayscale/accessibility —
R9 html, R10-R12).
