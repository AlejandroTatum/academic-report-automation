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
- [x] T1 (PR1, #12) confirmed structure contract: R1-R8 in `tools/test_structure_contract.py` and routing tests; `validate_report.py` final structure validation; unconfirmed structure blocks downstream phases via `doc_status`. Reuse `661fa6e` where it fits. Route: delegated writer.
  - Commit `32dca9d` `feat(structure): establish confirmed report contract`.
  - New `tools/structure_contract.py` (combine sources, schema, confirmation state/staleness); `tools/validate_report.py` gains `structure_validation` wired into `metadata_validation`; `tools/doc_status.py::_phase_intake` gates on `structure_confirmation_state` only when a report declares `structure:` at all (zero blast radius on the 85 pre-existing `doc_status` tests, none of which set that key — verified).
  - RED: `.venv/bin/python -m pytest tools/test_structure_contract.py -q` failed to collect (`ModuleNotFoundError: structure_contract`) with the implementation stashed; restored, then GREEN: `8 passed`.
  - Full suite before: `1008 passed`. After T1: `1018 passed` (`.venv/bin/python -m pytest tools/ tests/ -q`).
  - `git show 32dca9d --stat --shortstat`: 6 files changed, 832 insertions(+) — over the ~400 advisory heuristic (documented below).
  - Deviation from design: no `report.yml.structure.version`/hash-store departure; kept design's additive `structure:` block as specified. Gate activation is presence-based (`structure:` key must exist) rather than unconditional, per the design's own migration note ("new gates activate only when the new structure/evidence contract is present") — this was necessary to avoid retrofitting ~85 unrelated `doc_status` fixtures; documented as an implementation-level bounding of R6, not a product-decision gap.
- [x] T2 (PR2, #11) evidence package matrix: R9-R12 in `tools/test_evidence_contract.py`; the research phase gate validates the matrix structurally. Route: delegated writer.
  - Commit `fcffedb` `feat(research): add evidence package matrix`.
  - New `tools/evidence_contract.py` (`validate_claim`, `validate_evidence_package`, presence-gated `evidence_gate_engaged`); `tools/doc_status.py::_phase_research` validates `research/evidence.yml` structurally once a report writes it (same presence-gated pattern as T1, zero blast radius on existing `doc_status` fixtures — verified, none reference `evidence.yml`).
  - RED: `ModuleNotFoundError: evidence_contract` with implementation stashed; restored, then GREEN: `5 passed` (R9-R12 plus one research-gate integration test).
  - Full suite: `1024 passed` (`.venv/bin/python -m pytest tools/ tests/ -q`).
  - `git show fcffedb --stat --shortstat`: 5 files changed, 368 insertions(+), 1 deletion(-).
  - Docs: `skills/research-workflow/references/research-protocol.md` and `SKILL.md` updated to describe producing `evidence.yml` alongside the existing prose matrix.
- [ ] T3 (PR3, #11) source quality and citation reciprocity: R13-R16. Route: delegated writer.
- [ ] T4 (PR4, #11) visual provenance through the final gate: R17. Route: delegated writer.

## Acceptance
- #12 closes with R1-R8; #11 closes with R9-R17; tests observed RED then GREEN; full suite green.

## Progress / evidence
- Branch `feat/structure-and-research-contract` from `main` 71d95cd.

## Next step
Delegate T1-T4.
