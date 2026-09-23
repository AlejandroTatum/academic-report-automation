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
- [ ] T1 catalog + selector (R1-R4). Route: delegated writer.
- [ ] T2 context model, override precedence, receipts (R5-R8). Route: delegated writer.
- [ ] T3 LaTeX tokens (R9 latex). Route: delegated writer.
- [ ] T4 DOCX tokens (R9 docx). Route: delegated writer.
- [ ] T5 HTML tokens + rendered corpus, multipage, grayscale/accessibility (R9 html, R10-R12). Route: delegated writer.

## Acceptance
- 7/7 requirements, 12/12 scenarios observed RED then GREEN; full suite green; auditor output is a precheck, never `VISUAL_PASS`.

## Progress / evidence
- Branch `feat/contextual-table-styles` from `main` d185e29.

## Next step
Delegate T1-T5.
