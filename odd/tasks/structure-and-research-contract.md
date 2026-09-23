# Structure and research contract (#12, #11)

## Objective
Confirm the teacher-required section structure before research (#12), then require a traceable evidence package before drafting or visual production (#11).

## Problem / why
Intake only lists "teacher, client, or company requirements" generically (`skills/academic-report-builder/references/document-intake.md`); the research phase gate only checks that `research/evidence-matrix.md` is non-empty (`tools/doc_status.py`), and the protocol in `skills/research-workflow/` is prose the agent is trusted to follow. The August SDD change `academic-structure-and-research-contract` designed the fix; implementation froze on a provider defect. A partial #12 slice (`661fa6e`) exists only on an archive tag and its own issue comment says it does not meet acceptance.

## Route
ODD delegated direct (user decision 2026-09-22). SDD artifacts in Engram are guidance, not an active SDD run:
- decision #6408 (combined per-section requirements: mandatory rubric/content criteria plus optional quantitative limits)
- proposal #6409, spec #6410, design #6411, tasks #6413 (named RED tests R1-R17, four slices).
The design predates the document-workflow phases (`tools/doc_status.py` intake → research → preview → draft → approval → generate → validate → deliver); reconcile with them instead of adding a parallel workflow.

## Constraints
- Strict TDD: on (source: user global config). Runner: `.venv/bin/python -m pytest tools/ tests/`.
- Extend `report.yml`/manifest/validators and the existing phase gates; no new flags or parallel state.
- Delivery: forecast ~1,250-1,500 lines, over the 400 budget. One PR per slice merged to `main` in turn after its native review (stacked-to-main, as for #10).
- RDD: on (global); review per slice.

## Tasks
- [ ] T1 (PR1, #12) confirmed structure contract: R1-R8 in `tools/test_structure_contract.py` and routing tests; `validate_report.py` final structure validation; unconfirmed structure blocks downstream phases via `doc_status`. Reuse `661fa6e` where it fits. Route: delegated writer.
- [ ] T2 (PR2, #11) evidence package matrix: R9-R12 in `tools/test_evidence_contract.py`; the research phase gate validates the matrix structurally. Route: delegated writer.
- [ ] T3 (PR3, #11) source quality and citation reciprocity: R13-R16. Route: delegated writer.
- [ ] T4 (PR4, #11) visual provenance through the final gate: R17. Route: delegated writer.

## Acceptance
- #12 closes with R1-R8; #11 closes with R9-R17; tests observed RED then GREEN; full suite green.

## Progress / evidence
- Branch `feat/structure-and-research-contract` from `main` 71d95cd.

## Next step
Delegate T1-T4.
