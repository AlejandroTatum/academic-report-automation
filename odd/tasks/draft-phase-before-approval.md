# Draft phase before approval

Feature: `draft-phase-before-approval`. Branch: `feat/draft-phase-before-approval` (from `main` @ `60627f8`).
Engram mirror: topic `odd/draft-phase-before-approval/tasks`, project `academic-report-automation`.

## Objective
The document body (`reports/<wf>/body.md`) is drafted in its own workflow phase
`draft`, placed between `preview` and `approval`, and the approval marker binds the
exact bytes of both `preview.md` and `body.md` (`body_sha256`).

## Problem / why
First real E2E run (`engram-funcionamiento`, 2026-09-19) reached the approval gate with
nothing to approve: no phase drafts `body.md`, yet `generate` compiles it. The user
decided (2026-09-19) that drafting happens before the single human approval.

## Design (mechanical decisions)
- New phase `draft` (not an extension of `preview`): the contract test enforces one
  artifact per phase reference, and that invariant keeps `doc_status` honest.
- Route: `intake > research > preview > draft > approval > generate > validate > deliver`.
- `approval.yml` gains `body_sha256`; the shared predicate `approval_state()` in
  `tools/approval_marker.py` stays the single source of truth (malformed / stale
  semantics mirrored for body.md). Existing markers without `body_sha256` become
  `malformed` (fail closed; a fresh explicit approval re-creates the marker).
- Body authoring format is unchanged: Markdown, `[@key]` citations, `![caption](path)`
  figures, citation-driven bibliography from `sources.bib`.

## Scope / constraints
- Authorized edits: `tools/approval_marker.py`, `tools/doc_status.py`,
  `tools/publish_pdf.py`, `tools/conftest.py`, `tools/test_doc_status_*.py`,
  `skills/document-workflow/**`, `tests/skills/test_document_workflow_contract.py`,
  synced skill copies only through the existing sync route.
- Out of scope: the `engram-funcionamiento` document itself, other tools, other skills.
- TDD: strict (session config). Runner: `.venv/bin/python -m pytest tools/ tests/`.
  Observed RED before implementation, GREEN, then refactor.
- RDD: on (global). Candidate = each work-unit commit; assess with
  `gentle-ai review assess --cwd <repo> --base-ref <boundary> --committed-only --json`.
- Forecast: ~380 authored changed lines. Delivery strategy: `ask-on-risk` (default).

## Tasks
- [ ] T1 `approval_marker.py`: `BODY_NAME`, `body_sha256` in `REQUIRED_KEYS`,
      hash/compare mirroring preview. Tests: `tools/test_doc_status_approval.py`
      (body edited after approval -> blocked stale; marker without body_sha256 ->
      malformed; body missing -> malformed). Conftest: `_body()` helper,
      `_approval(body=..., body_sha256=...)`.
- [ ] T2 `doc_status.py`: `draft` in `PHASES` after `preview`; `_phase_draft`
      (done non-empty body.md, pending missing/empty, blocked `draft_unreadable`);
      `_GUIDANCE["draft"]`; route/human render. Tests in
      `tools/test_doc_status_phases_early.py` (or new `test_doc_status_draft.py`)
      plus render/derive CLI tests that assert the route string.
- [ ] T3 `publish_pdf.py`: `_approval_refusal` names body.md for stale/malformed.
      Tests in `tools/test_doc_status_validate_deliver.py` or publish tests.
- [ ] T4 Skill docs: new `references/draft.md` (Executor: academic-report-builder,
      Artifact: `reports/<wf>/body.md`, authoring format, Never list); SKILL.md
      routing table + route line + status example; `approval.md` schema and Done;
      `generate.md` names body.md as approved input; `preview.md` unchanged in
      scope (one artifact). Contract test: `OWNED_REFERENCES`/`REFERENCE_*` maps
      gain `draft`; assertions for `body_sha256`. RED first via the contract test.
- [ ] T5 Sync skill copies via the existing sync route and verify
      `tests/skills/test_sync_skills.py`; full suite green.

## Acceptance
- `doc_status` on a folder with preview.md but no body.md returns `next: draft`.
- A marker whose `body_sha256` no longer matches -> `approval blocked (approval_marker_stale)`.
- Full suite passes; contract tests cover the new reference.

## Progress / evidence
(filled per task: RED/GREEN output, commit ids, assess tier and outcome)

## Next step
T1.
