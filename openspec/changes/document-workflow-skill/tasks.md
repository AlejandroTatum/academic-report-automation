# Tasks: Document Workflow Orchestration Skill

**Change**: `document-workflow-skill`
**Inputs**: `specs/document-workflow-orchestration/spec.md`, `specs/document-workflow/spec.md` (delta), `design.md`, `proposal.md`
**Strategy**: `auto-chain`, `review_budget_lines: 400` (hard, no size exception — maintainer standing rule: any observed overage is pre-split at the natural seam), Strict TDD (RED/GREEN/REFACTOR), test command `pytest tools/ tests/`
**Estimation model**: production/reference lines count 1:1; test lines counted per the original 2x factor. **Recalibrated** after Slice 2b's observed 559-line diff (doc_status 105, conftest 127, tests 327) against its flat ~250 estimate: remaining slices are forecast at the observed density scale (≈2.24× flat), and any forecast over 400 is pre-split at the natural seam below.
**Slice order** (authoritative, safety-critical guard first): 1a approval marker, 1b publisher/build guard, 2a doc_status early phases, 2b-i doc_status approval, 2b-ii doc_status generate, 2b-iii doc_status validate+deliver, 2c-i doc_status derive/CLI, 2c-ii doc_status renderers, 3a-i skill SKILL.md core, 3a-ii skill phase references, 3b-i gated approval/generate references, 3b-ii validate reference + collision check, 4 existing-skill reference edits, 5 sync/registry wiring.
**Per-PR staging**: only the slice's own hunks are staged for its PR (`git add -p` if needed) — this is mandatory for `tools/doc_status.py` (shared across 2a–2c-ii), `tools/conftest.py` (shared across 2a–2b-iii), and `tests/skills/test_document_workflow_contract.py` (shared across 3a-i–3b-ii).
**Plan amendment**: the 2b pre-split (and the later recalibrated pre-splits of 2c/3a/3b) is committed together with Slice 2b-i approval; the second amendment — 2b-i's observed 416-line PR (including the mandated amendment text) split again at the approval/generate seam into 2b-i approval (2.8–2.9) and 2b-ii generate (2.10–2.11), with the former 2b-ii validate+deliver renamed 2b-iii — is also committed together with Slice 2b-i approval; product scope is unchanged — tasks 2.8–2.15 keep their exact order and semantics, and no requirement is added, removed, or altered.

## Slice 1a — Approval marker (PR 1)

Files: `tools/approval_marker.py` (new), `tools/test_approval_marker.py` (new). Est. ~120 lines (module ~40 + tests at 2x factor).

- [ ] 1.1 RED `tools/test_approval_marker.py::test_approval_state_absent_current_stale_malformed` — absent, hash-match current, hash-mismatch stale, and malformed (bad YAML, missing `preview_sha256`/`approved_at`/`approved_by`, blank value, missing `preview.md`) cases; assert `approval_state()` writes and raises nothing.
- [ ] 1.2 GREEN `tools/approval_marker.py` — implement `ApprovalState`, `sha256_file()`, `approval_state()` to satisfy 1.1.
- [ ] 1.3 REFACTOR `tools/approval_marker.py` — finalize ASCII `detail` strings naming the offending file/key; keep the module pure and read-only.

Must leave green: `pytest tools/ tests/` fully green with the new module and its tests; nothing else touched.

## Slice 1b — Publisher/build guard (PR 2)

Files: `tools/publish_pdf.py`, `tools/test_pdf_publication.py`, `tools/build_report_auto.py`, `tools/test_build_report_auto.py`. Consumes slice 1a's `approval_marker`. Est. ~250 lines (production ~90 + tests at 2x factor).

- [ ] 1.4 RED `tools/test_pdf_publication.py::test_publish_refuses_absent_stale_malformed_marker` — add `_approved_work_folder(tmp_path)` fixture; assert absent/stale/malformed marker each raise `PublicationError` and create nothing (`documents_root` never created).
- [ ] 1.5 GREEN `tools/publish_pdf.py` — add required keyword-only `work_folder` to `publish_validated_pdf`; call `approval_marker.approval_state(work_folder)` and raise `PublicationError` immediately after `_require_pdf_file`/category-slug validation, before `sha256_file(source)`, `folder.mkdir`, or any temp file; re-export `sha256_file` from `approval_marker` (`build_report_auto.py:19` import stays valid).
- [ ] 1.6 GREEN `tools/test_pdf_publication.py` — update the eight existing positional calls (122,134,136,146,149,175,187,194) to pass `work_folder=` at the approved fixture; confirm the current-marker path still publishes `v001`/hash-matched-reuse exactly as today.
- [ ] 1.7 REFACTOR `tools/publish_pdf.py` — finalize the three Spanish refusal messages verbatim from design; confirm `build_report_auto.py:138` still prefixes `PDF PUBLICATION FAILED:`.
- [ ] 1.8 RED `tools/test_build_report_auto.py::test_publication_runs_after_build_and_validation_pass` — assert `publish.assert_called_once_with(..., work_folder=config.folder)`; add a `folder` attribute to `FakeReportConfig`.
- [ ] 1.9 GREEN `tools/build_report_auto.py:132` — pass `work_folder=config.folder` to the `publish_validated_pdf` call.
- [ ] 1.10 RED `tools/test_build_report_auto.py::test_validate_only_refuses_publication_pending_approval` — under `--validate-only` reaching publication with no current marker: stdout already printed `VALIDATION PASSED` (or `...WITH WARNINGS`) before the `SystemExit`, and the raised message explicitly states validation passed and publication was refused because approval is pending; `--validate-only`'s build-skip behavior is otherwise unchanged.
- [ ] 1.11 GREEN — confirm 1.10 passes with the 1.5–1.7 wording; only if it does not, adjust the absent-marker message text minimally (no semantics change to `--validate-only`).

Must leave green: `pytest tools/ tests/` fully green; publication refuses on absent/stale/malformed markers and still publishes on a current one; `build_report_auto.py:19` `sha256_file` import untouched.

## Slice 2a — `doc_status` early phases + shared helpers (PR 3)

Files: `tools/doc_status.py` (new), `tools/conftest.py` (new), `tools/test_doc_status_phases_early.py` (new). Consumes slice 1a's `approval_marker`. Est. ~250 lines including tests at 2x factor — below the 400-line budget. Staging: only this slice's hunks of `tools/doc_status.py` are staged (`git add -p` if needed).

- [ ] 2.1 RED `tools/test_doc_status_phases_early.py::test_intake_*` — create the shared fixture helpers in `tools/conftest.py` needed to author these tests (`_report`, `_preview`, `_approval`, `_pdf`, `_validation`, `_snapshot`, etc.); missing `report.yml` means **intake current and all later phases pending**, unknown `route:` (blocked `unknown_route`), incomplete route-mandatory metadata (pending).
- [ ] 2.2 GREEN `tools/doc_status.py` — `PHASES`, `PhaseState`/`DocStatus` dataclasses; `_phase_intake` building `ReportConfig` directly (never `load_report_config`, never `SystemExit`).
- [ ] 2.3 RED `tools/test_doc_status_phases_early.py::test_research_*` — evidence-matrix present (done), `research: skipped` (done), neither (pending).
- [ ] 2.4 GREEN `tools/doc_status.py` — `_phase_research` derivation.
- [ ] 2.5 RED `tools/test_doc_status_phases_early.py::test_preview_*` — non-empty (done), empty/whitespace (pending), unreadable (blocked `preview_unreadable`).
- [ ] 2.6 GREEN `tools/doc_status.py` — `_phase_preview` derivation.
- [ ] 2.7 REFACTOR `tools/conftest.py` — consolidate remaining duplicated fixture builders into the shared helpers; no behavior change to `doc_status.py`.

Must leave green: `pytest tools/ tests/` fully green; only `test_doc_status_phases_early.py` asserts `doc_status` behavior; no `derive()`/renderers/CLI yet.

## Slice 2b-i — `doc_status` approval phase (PR 4)

Files: `tools/doc_status.py`, `tools/conftest.py`, `tools/test_doc_status_approval.py` (new). Consumes slice 1a's `approval_marker`. Re-split from the former single 2b-i slice after its observed 416-line PR (doc_status, conftest, tests, plus the mandated plan-amendment text) breached the hard 400-line budget; split at the natural approval/generate phase seam. Est. ~190 lines at observed density (doc_status ~25, conftest ~32, tests ~90, amendment text ~45) — under the 400-line budget including the amendment text. Staging: only this slice's hunks of `tools/doc_status.py`/`tools/conftest.py` are staged (`git add -p` if needed). This PR also carries the plan amendment (2b → 2b-i/2b-ii/2b-iii, replacement of `tools/test_doc_status_phases_late.py` and of the former `tools/test_doc_status_approval_generate.py` by the per-seam test files); product scope is unchanged.

- [ ] 2.8 RED `tools/test_doc_status_approval.py::test_approval_*` — absent (pending, not blocked), stale (blocked `approval_marker_stale`), malformed (blocked `approval_marker_malformed`), current (done); uses `tools/approval_marker.approval_state`.
- [ ] 2.9 GREEN `tools/doc_status.py` — `_phase_approval` derivation; `next` never advances past approval unless current.

Must leave green: `pytest tools/ tests/` fully green; early-phase tests from 2a unchanged and green; no generate/validate/deliver derivation yet.

## Slice 2b-ii — `doc_status` generate phase (PR 5)

Files: `tools/doc_status.py`, `tools/conftest.py`, `tools/test_doc_status_generate.py` (new). Consumes slice 1a's `approval_marker`. Second half of the 2b-i re-split at the natural approval/generate phase seam. Est. ~165 lines at observed density (doc_status ~25, conftest ~33, tests ~90) — under the 400-line budget. Staging: only this slice's hunks of `tools/doc_status.py`/`tools/conftest.py` are staged (`git add -p` if needed).

- [ ] 2.10 RED `tools/test_doc_status_generate.py::test_generate_*` — final PDF newer than marker (done), older (pending, stale PDF).
- [ ] 2.11 GREEN `tools/doc_status.py` — `_phase_generate` derivation via mtime comparison.

Must leave green: `pytest tools/ tests/` fully green; 2a and 2b-i tests unchanged and green; no validate/deliver derivation yet.

## Slice 2b-iii — `doc_status` validate + deliver phases (PR 6)

Files: `tools/doc_status.py`, `tools/conftest.py`, `tools/test_doc_status_validate_deliver.py` (new). Consumes slice 1a's `approval_marker`. Former Slice 2b-ii (validate+deliver), renamed and shifted to PR 6 by the 2b-i re-split; content, order, and semantics unchanged. Est. ~265 lines at observed density (doc_status ~55, conftest ~62, tests ~145) — below the 400-line budget, estimate unchanged. Staging: only this slice's hunks of `tools/doc_status.py`/`tools/conftest.py` are staged (`git add -p` if needed).

- [ ] 2.12 RED `tools/test_doc_status_validate_deliver.py::test_validate_*` — `result: pass` with matching hash (done), pass with mismatched hash (pending), `result: fail` (blocked `validation_failed`).
- [ ] 2.13 GREEN `tools/doc_status.py` — `_phase_validate` derivation.
- [ ] 2.14 RED `tools/test_doc_status_validate_deliver.py::test_deliver_*` — hash-matched published PDF under `~/Documents/<category>/<slug>/` (done), absent (pending).
- [ ] 2.15 GREEN `tools/doc_status.py` — `_phase_deliver` derivation.

Must leave green: `pytest tools/ tests/` fully green; 2a, 2b-i, and 2b-ii tests unchanged and green.

## Slice 2c-i — `doc_status` derive + CLI (PR 7)

Files: `tools/doc_status.py`, `tools/test_doc_status_derive_cli.py` (new). Recalibrated forecast ~265 lines at observed density (≈2.24× the flat 230/2 estimate) — pre-split from 2c at the derivation/rendering seam because the recalibrated whole-slice forecast (~515) exceeds the hard 400 budget. Staging: only this slice's hunks of `tools/doc_status.py` are staged (`git add -p` if needed).

- [ ] 2.16 RED `tools/test_doc_status_derive_cli.py::test_derive_purity_and_error_wrapping` — `derive()` composing the 2a/2b phase functions leaves the folder listing byte-identical before/after; missing/non-directory/unreadable work-folder argument exits 2 with a message and creates nothing; an unexpected exception in one phase's derivation yields `blocked` with a reason, never `done`, and later phases stay `pending`.
- [ ] 2.17 GREEN `tools/doc_status.py` — `derive()` plus `main(argv)` CLI with exit codes and per-phase exception-to-blocked wrapping.

Must leave green: `pytest tools/ tests/` fully green; 2a/2b-i/2b-ii/2b-iii tests unchanged and green; no renderers yet.

## Slice 2c-ii — `doc_status` renderers (PR 8)

Files: `tools/doc_status.py`, `tools/test_doc_status_render_cli.py` (new). Recalibrated forecast ~250 lines at observed density. Staging: only this slice's hunks of `tools/doc_status.py` are staged (`git add -p` if needed).

- [ ] 2.18 RED `tools/test_doc_status_render_cli.py::test_render_human_golden` — gate line front-loaded exactly when a phase is pending/blocked, omitted otherwise; static asserts: ASCII-only, no `|` tables, no `###`+ headers, exactly one route line with exactly one bracketed phase, tokens exactly `done|current|pending|blocked`.
- [ ] 2.19 RED `tools/test_doc_status_render_cli.py::test_render_machine_schema` — `academic.doc-status/v1`, `### Summary`, `### Blocked Reasons`, `### JSON` fenced payload with `schemaName/schemaVersion/workFolder/phases/current/next/gate/blockedReasons`; `--json` still renders both blocks (machine stdout, human stderr).
- [ ] 2.20 GREEN `tools/doc_status.py` — implement `_gate`/`_guidance`/`_payload` and `render_human()`/`render_machine()` per 2.18–2.19.
- [ ] 2.21 REFACTOR `tools/doc_status.py` — trim to ~150 lines (derivation ~90, renderers ~45, CLI ~15); dedupe phase-derivation helpers.

Must leave green: full suite; no skill or script touched; `doc_status` never shells out or imports `gentle-ai`.

## Slice 3a-i — `document-workflow` SKILL.md core (PR 9)

Files: `skills/document-workflow/SKILL.md` (new), `tests/skills/test_document_workflow_contract.py` (new). Recalibrated forecast ~280 lines at observed density — pre-split from 3a at the skeleton/references seam because the recalibrated whole-slice forecast (~560) exceeds the hard 400 budget. Staging: only this slice's hunks of `tests/skills/test_document_workflow_contract.py` are staged (`git add -p` if needed).

- [ ] 3.1 RED `tests/skills/test_document_workflow_contract.py::test_required_files_and_frontmatter` — `SKILL.md` + 7 references exist; frontmatter has `name`, `description` with `Trigger:`, `license: Apache-2.0`, `metadata.{author,version,scope}`.
- [ ] 3.2 GREEN `skills/document-workflow/SKILL.md` — frontmatter and the `doc_status -> next -> reference -> delegate -> re-run` loop with the phase/reference/executor routing table.
- [ ] 3.3 RED `tests/skills/test_document_workflow_contract.py::test_status_template_contract` — the fenced human-block template has no markdown tables, no nested headers, one route line with `[current]`, ASCII-only tokens.
- [ ] 3.4 GREEN `skills/document-workflow/SKILL.md` — embed the exact fenced human-block template (Gate/Route/Summary/Next) from design.

Must leave green: new contract test plus every existing test, unchanged.

## Slice 3a-ii — `document-workflow` phase references (PR 10)

Files: `skills/document-workflow/references/{intake,research,preview,generate,deliver}.md` (new), `tests/skills/test_document_workflow_contract.py`. Recalibrated forecast ~280 lines at observed density. Staging: only this slice's hunks of `tests/skills/test_document_workflow_contract.py` are staged (`git add -p` if needed).

- [ ] 3.5 RED `tests/skills/test_document_workflow_contract.py::test_referenced_paths_resolve` — every executor path named in `SKILL.md` resolves on disk.
- [ ] 3.6 GREEN `skills/document-workflow/references/{intake,research,preview,generate,deliver}.md` — each names its executor and the single artifact it must produce.

Must leave green: new contract test plus every existing test, unchanged.

## Slice 3b-i — gated approval/generate references (PR 11)

Files: `skills/document-workflow/references/{approval,generate}.md` (new), `tests/skills/test_document_workflow_contract.py`. Recalibrated forecast ~335 lines at observed density — pre-split from 3b at the human-gate/validate seam because the recalibrated whole-slice forecast (~670) exceeds the hard 400 budget. Staging: only this slice's hunks of `tests/skills/test_document_workflow_contract.py` are staged (`git add -p` if needed).

- [ ] 3.7 RED `tests/skills/test_document_workflow_contract.py::test_approval_reference_contract` — `approval.md` names `preview_sha256`/`approved_at`/`approved_by` and states silence/inferred-yes/agent-decision never produce `approval.yml`.
- [ ] 3.8 GREEN `skills/document-workflow/references/approval.md` — human-gate reference (no executor), lossless prompt contract, marker schema.
- [ ] 3.9 RED `tests/skills/test_document_workflow_contract.py::test_generate_reference_forbids_unapproved_build` — `generate.md` forbids building before approval is `done`.
- [ ] 3.10 GREEN `skills/document-workflow/references/generate.md` — state the precondition explicitly.

Must leave green: new contract test plus every existing test, unchanged.

## Slice 3b-ii — validate reference + collision check (PR 12)

Files: `skills/document-workflow/references/validate.md` (new), `tests/skills/test_document_workflow_contract.py`. Recalibrated forecast ~335 lines at observed density. Staging: only this slice's hunks of `tests/skills/test_document_workflow_contract.py` are staged (`git add -p` if needed).

- [ ] 3.11 RED `tests/skills/test_document_workflow_contract.py::test_validate_reference_both_branches` — `validate.md` names the RDD branch (`gentle-ai review mode status`) and the fallback chain with the identical gate set, and states `unknown` routes to fallback.
- [ ] 3.12 GREEN `skills/document-workflow/references/validate.md` — write both branches per design's routing table.
- [ ] 3.13 Verify skill-name collision — run `gentle-ai skill-registry refresh`, then check the registry for a non-project `document-workflow` entry (read-only lookup); adjust `SKILL.md`'s `name:` only if a collision is found.

Must leave green: new contract test plus every existing test, unchanged.

## Slice 4 — Existing-skill reference edits (PR 13)

Files: `skills/academic-report-builder/references/document-intake.md`, `skills/academic-report-builder/references/automation-contract.md`, `skills/research-workflow/references/research-protocol.md`, `tests/skills/test_report_builder_routing.py`. Recalibrated forecast ~360 lines at observed density — kept whole, below the hard 400 budget; split only if observed authoring exceeds it.

- [ ] 4.1 RED `tests/skills/test_report_builder_routing.py::test_confirmation_is_required_on_every_execution` and `::test_document_contract_block_is_specified` — update to expect data-record wording (no approval-to-generate sentence); assert `document-intake.md` no longer authorizes generation.
- [ ] 4.2 GREEN `skills/academic-report-builder/references/document-intake.md` — Document Contract becomes a data record written to `report.yml`; remove "generation begins only after the user confirms this block"; allow one targeted clarification per missing route-mandatory field; forward-reference the single confirmation to `document-workflow/references/approval.md`.
- [ ] 4.3 RED `tests/skills/test_report_builder_routing.py::test_publication_gated_on_approval` — `automation-contract.md`'s `VERSIONED_PDF_PUBLISHED_OR_REUSED` lists `APPROVAL_CURRENT` as a precondition.
- [ ] 4.4 GREEN `skills/academic-report-builder/references/automation-contract.md` — add the `APPROVAL_CURRENT` precondition; leave other gates unchanged.
- [ ] 4.5 RED `tests/skills/test_report_builder_routing.py::test_research_protocol_names_evidence_path` — §5 of `research-protocol.md` names `$REPORT_CONTENT_ROOT/reports/<work-folder>/research/evidence-matrix.md` and labels the package pre-document evidence, never confirmed intake.
- [ ] 4.6 GREEN `skills/research-workflow/references/research-protocol.md` — name the evidence-matrix path and pre-document-evidence wording in §5.
- [ ] 4.7 REFACTOR `tests/skills/test_report_builder_routing.py` — confirm the single-confirmation rule is asserted exactly once across the whole route, traceable to `document-workflow/references/approval.md`.

Must leave green: full suite with the updated assertions.

## Slice 5 — Sync/registry wiring (PR 14)

Files: `scripts/sync_skills.sh`, `tests/skills/test_sync_skills.py`. Recalibrated forecast ~235 lines at observed density — kept whole, below the hard 400 budget.

- [ ] 5.1 RED `tests/skills/test_sync_skills.py::test_document_workflow_and_codex_target_present` — `document-workflow` is added to `SKILLS`; `$HOME/.codex/skills` is added to `TARGETS`.
- [ ] 5.2 GREEN `scripts/sync_skills.sh` — add `document-workflow` to `SKILLS`; add `$HOME/.codex/skills` to `TARGETS`.
- [ ] 5.3 RED `tests/skills/test_sync_skills.py::test_sync_exits_zero_without_gentle_ai_binary` — with `APPLY=1` and `gentle-ai` absent from `PATH`, sync exits 0 and the registry-refresh step is skipped without aborting under `set -euo pipefail`.
- [ ] 5.4 GREEN `scripts/sync_skills.sh` — after the rsync loop, only when `APPLY=1`: `command -v gentle-ai >/dev/null && { gentle-ai skill-registry refresh || echo "!! skill-registry refresh failed (non-fatal)" >&2; }`.
- [ ] 5.5 RED `tests/skills/test_sync_skills.py::test_sync_exits_zero_when_refresh_fails` — `gentle-ai` present but exits non-zero; sync still exits 0.
- [ ] 5.6 GREEN — confirm 5.4's `|| echo ... non-fatal` satisfies 5.5; adjust only if a gap is found.

Must leave green: full suite; dry run exits 0 with `gentle-ai` absent.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~3620 total across 14 slices (remaining slices recalibrated at observed 2b density, ≈2.24× the failed flat estimate; +100 from the 2b-i approval/2b-ii generate re-split) |
| 400-line budget risk | Low — every slice is pre-split to ≤400 at observed density; highest forecast is Slice 4 at ~360; no size exception |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (1a approval marker) → PR 2 (1b publisher/build guard) → PR 3 (2a early phases) → PR 4 (2b-i approval) → PR 5 (2b-ii generate) → PR 6 (2b-iii validate+deliver) → PR 7 (2c-i derive/CLI) → PR 8 (2c-ii renderers) → PR 9 (3a-i SKILL.md core) → PR 10 (3a-ii phase references) → PR 11 (3b-i approval/generate refs) → PR 12 (3b-ii validate ref + collision) → PR 13 (4 existing-skill edits) → PR 14 (5 sync/registry) |
| Delivery strategy | auto-chain |
| Chain strategy | feature-branch-chain |

Estimated changed lines (per slice): Slice 1a ~120, Slice 1b ~250, Slice 2a ~250 (delivered as planned; Slice 2b observed actual 559), Slice 2b-i approval ~190 (including the mandated plan-amendment text; observed 416 for the former combined 2b-i), Slice 2b-ii generate ~165, Slice 2b-iii ~265, Slice 2c-i ~265, Slice 2c-ii ~250, Slice 3a-i ~280, Slice 3a-ii ~280, Slice 3b-i ~335, Slice 3b-ii ~335, Slice 4 ~360, Slice 5 ~235.

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: Low

Chain strategy `feature-branch-chain` was selected by the user and recorded in `openspec/config.yaml` (`session_preflight.chain_strategy`). Tracker branch `feat/document-workflow-skill` unchanged; PR order 1a → 1b → 2a → 2b-i → 2b-ii → 2b-iii → 2c-i → 2c-ii → 3a-i → 3a-ii → 3b-i → 3b-ii → 4 → 5; PR 1 targets the tracker, each later slice PR targets the previous slice's branch, only the tracker merges to `main`. Do not re-ask.

Plan amendment (maintainer standing rule: hard 400, no exception, pre-split observed overages at natural seams): Slice 2b's observed 559-line diff was split into 2b-i (approval+generate, ≤400) and 2b-ii (validate+deliver, ≤400); `tools/test_doc_status_phases_late.py` was removed from the plan and replaced by the per-seam test files. The combined 2b-i PR was then observed at 416 lines including the mandated amendment text, so it is re-split at the approval/generate seam into 2b-i approval (tasks 2.8–2.9, `tools/test_doc_status_approval.py`, ~190 lines) and 2b-ii generate (tasks 2.10–2.11, `tools/test_doc_status_generate.py`, ~165 lines); the former 2b-ii validate+deliver is renamed 2b-iii (PR 6, estimate unchanged at ~265). Later PR positions and chain order are renumbered accordingly (PRs 7–14); all later estimates are unchanged. Both amendments are committed together with Slice 2b-i approval and do not change product scope — tasks 2.8–2.15 keep their exact order and semantics.
