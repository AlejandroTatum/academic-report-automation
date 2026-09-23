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
- [x] T3 (PR3, #11) source quality and citation reciprocity: R13-R16. Route: delegated writer.
  - Commit `8933088` `feat(citations): validate sources and reciprocity`.
  - New `tools/source_quality.py` (`evaluate_source_quality`: authority/relevance/currency/primary-secondary/peer-review/accessibility, named rejection reasons `fabricated|unverifiable|irrelevant|superseded|unsuitable`). New `claim_support_and_reciprocity` in `tools/validate_ieee_refs.py` (unsupported claim, unresolved citation, uncited-unjustified bib entry, duplicate `citation_key`, malformed BibTeX entry); wired into `validate_ieee()` presence-gated on `research/evidence.yml`.
  - Avoided a module cycle: `evidence_contract` imports `ValidationResult` from `validate_ieee_refs` at module scope, so the new evidence.yml read inside `validate_ieee()` is a lazy import (documented in-file).
  - RED: stashed `tools/validate_ieee_refs.py`'s new functions + the new `tools/source_quality.py` via `git stash -u`; `ModuleNotFoundError`/`ImportError` on both new test files; popped, then GREEN: `5 passed` (R13-R16 plus one `validate_ieee` integration test).
  - Full suite: `1030 passed` (`.venv/bin/python -m pytest tools/ tests/ -q`).
  - `git show 8933088 --stat --shortstat`: 5 files changed, 361 insertions(+).
  - Did not touch `tools/source_library.py`'s manifest v2 fields (design's suggested file) — no existing test covers it, and the R13/R14 scenarios are fully satisfiable as a standalone quality-judgment function without migrating the manifest schema. Documented as a bounded scope choice, not a product-decision gap: manifest v2 migration remains open follow-up work if the team wants CLI-level source quality entry.
- [x] T4 (PR4, #11) visual provenance through the final gate: R17. Route: delegated writer.
  - Commit `04e267b` `feat(visual): preserve provenance through final gate`.
  - New `evidence_package_sha256` in `tools/evidence_contract.py`; new `validate_visual_evidence_provenance` in `tools/visual_metadata.py` (opt-in per figure via `evidence_package_sha256`/`claim_ids`); `validate_visual_manifest` gained a `report_folder` parameter (figures.yml's folder can differ from the report root) and now composes provenance errors; `validate_report.py`'s `visual_validation` passes `report_folder=config.folder`.
  - RED: `ImportError`/missing symbol on both new functions with the test file present before implementation; implemented, then GREEN: `3 passed` (the R17 paired case plus one composed-gate integration test).
  - Full suite: `1033 passed` (`.venv/bin/python -m pytest tools/ tests/ -q`).
  - `git show 04e267b --stat --shortstat`: 5 files changed, 250 insertions(+), 1 deletion(-).
  - Docs: `skills/academic-visual-builder/references/figures-yml-schema.md` documents the optional provenance fields.

- [x] T5 hardening: fix non-blocking native-review WARNINGs across T1-T4 (structure, evidence/citations, visual provenance). Route: delegated writer.
  - Commit `4fef345` `fix(research): harden structure and evidence contracts from review`.
  - `tools/structure_contract.py`: `validate_structure_schema` now rejects non-numeric limit values (dead crash in `validate_report.py`'s word-count check, fixed at the schema layer so a bad limit never reaches "confirmed") and malformed `sources` shape; `_stale_reason` now treats a missing recorded source as `stale` (was fail-open into "confirmed"); `combine_assignment_sources` now detects cross-source section-order disagreements and records them as an `"order"`-typed conflict (was silently picking the first source's order — closes the document-intake.md doc/code mismatch on "reordered blocks confirmation"). Added clarifying comment on the "proposed"-marker error message (R2-001).
    RED: `test_structure_rejects_non_numeric_limit_values`, `test_structure_rejects_malformed_sources_shape`, `test_structure_missing_source_file_is_stale_not_confirmed`, `test_intake_combine_surfaces_order_conflict` — all failed against pre-fix code; GREEN after.
  - `tools/validate_report.py`: `structure_validation` now calls `structure_confirmation_state` first and rejects anything but `"confirmed"` (previously certified a body against a stale/reconfirmation-pending contract); `BODY_HEADING_RE` narrowed to H1-only so a `##` subsection no longer splits its enclosing section's text bucket and silently truncates content-criteria/word-count checks.
    RED: `test_final_structure_validation_rejects_stale_structure`, `test_final_structure_validation_ignores_subsection_headings`; GREEN after.
  - `tools/validate_ieee_refs.py`: `claim_support_and_reciprocity` now guards non-dict claim entries, exempts justified common-knowledge claims from the `citation_key` requirement (matching `evidence_contract.validate_claim`'s own exemption — was a genuine contract mismatch), and documents why duplicate `citation_key` across distinct claims stays a rejection (matrix-row distinctness, not a ban on citing one source from many claims in the rendered body). `validate_ieee` now guards a malformed (non-list) `bibliography_justifications`.
    RED: `test_claim_support_and_reciprocity_rejects_nondict_claim`, `test_claim_support_and_reciprocity_exempts_justified_common_knowledge`, `test_validate_ieee_ignores_malformed_bibliography_justifications`; GREEN after.
  - `tools/evidence_contract.py`: named `CONFIDENCE_INSUFFICIENT` constant, accepted by `validate_claim`'s enum check (a legitimately declared `"insufficient"` no longer also fails as an invalid confidence value — it now blocks drafting exactly once, via `_drafting_block_reason`); a quotation's missing `locator` is reported once instead of twice (generic + quotation-specific messages de-duplicated).
    RED: `test_declared_insufficient_confidence_is_not_also_a_schema_error`, `test_matrix_quotation_missing_locator_reports_once`; GREEN after.
  - `tools/source_quality.py`: `verifiable`/`relevant`/`accessible` must now be positively `True`, not merely "not explicitly False" (an unevaluated/absent field no longer silently passes); `fabricated`'s false-by-default is unchanged (an accusation needs positive evidence, an asymmetric default this fix preserves deliberately). Eligible rationale no longer asserts unverified `"vigente"` (currency was never actually checked); reports the recorded year instead.
    RED: `test_research_rejects_source_with_missing_quality_fields`, `test_research_eligible_rationale_reports_actual_year_not_unverified_currency`; GREEN after.
  - `tools/visual_metadata.py`: `validate_visual_evidence_provenance` — once a figure engages provenance via either field, `evidence_package_sha256` is now required exactly like `claim_ids` already was (closed the fail-open gap against `figures-yml-schema.md`'s documented "once a figure declares either field, both are required" contract); every error now names the offending figure (`Figura N (file)`); malformed `evidence.yml` YAML and a non-list `figures` argument no longer crash.
    RED: `test_visual_provenance_requires_hash_once_engaged_via_claim_ids_alone`, `test_visual_provenance_errors_name_the_offending_figure`, `test_visual_provenance_rejects_malformed_evidence_yml_without_crashing`, `test_visual_provenance_rejects_non_list_figures_without_crashing`; GREEN after.
  - **Verified, not a defect** (left unchanged, with reasoning):
    - `dup-citation-key`: the spec's own acceptance scenario names "duplicate mapping" as a required rejection; `tools/test_validate_ieee_refs.py::test_claim_support_or_reciprocity_failure_blocks_build` already asserts it. Added the missing rationale comment (R2, "unexplained rule") rather than changing behavior.
    - Visual provenance opt-in-per-figure gating (R1-001/R3-001/R4-002's broader framing): `skills/academic-visual-builder/references/figures-yml-schema.md` already documents this exactly as "(#11, optional)" — not every figure traces to research evidence, and forcing coverage on every figure once `evidence.yml` exists would misclassify purely illustrative visuals. This matches the feature's presence-gated architecture used throughout T1-T4. The genuine, narrower fail-open gap (hash not required once engaged via `claim_ids` alone) was real and is fixed above.
  - Full suite: `1050 passed` (`.venv/bin/python -m pytest tools/ tests/ -q`), up from `1033` — 17 new named RED-then-GREEN tests, zero regressions.
  - `git show 4fef345 --stat --shortstat`: 11 files changed, 541 insertions(+), 42 deletions(-).

## Acceptance
- #12 closes with R1-R8; #11 closes with R9-R17; tests observed RED then GREEN; full suite green. All 17 scenarios named and passing; full suite 1008 -> 1033 passed across the four slices with zero regressions.

## Progress / evidence
- Branch `feat/structure-and-research-contract` from `main` 71d95cd.
- T1 `32dca9d`+`2b967e4`, T2 `fcffedb`+`f1d794c`, T3 `8933088`+`3bffed3`, T4 `04e267b` (docs commit pending), T5 `4fef345` (hardening from native review, docs commit pending).
- Deviations from the SDD design, honestly noted: (1) gates are presence-based (`structure:`, `research/evidence.yml`) rather than unconditional on every report, to avoid retrofitting ~85 unrelated pre-existing `doc_status` fixtures; the design's own migration note supports this ("new gates activate only when the new structure/evidence contract is present"). (2) `tools/source_library.py`'s manifest v2 migration (suggested in the design's File Changes table) was not touched — R13/R14 are fully satisfiable as a standalone `source_quality.py` judgment function; manifest-level CLI integration remains open follow-up work. (3) Final structure content checks use an optional `content_anchor` per criterion rather than open-ended semantic judgment of rubric satisfaction (a deterministic, testable approximation of "required content").
- Two commits in T1 and T2 slipped strict RED-first discipline for supplementary integration/doc-consistency tests (not the named R-scenarios) written concurrently with their wiring rather than before it; every named R1-R17 test was properly RED-then-GREEN.

## Next step
Feature complete: #12 and #11 both closable on this branch. Push and open PRs are the user's decision (stacked-to-main per the delivery strategy already recorded); not performed by this writer.
