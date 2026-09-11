# Tasks: Document Workflow Orchestration Skill

**Change**: `document-workflow-skill`
**Inputs**: `specs/document-workflow-orchestration/spec.md`, `specs/document-workflow/spec.md` (delta), `design.md`, `proposal.md`
**Strategy**: `auto-chain`, 400 authored changed-lines/PR, Strict TDD (RED/GREEN/REFACTOR), test command `pytest tools/ tests/`
**Slice order** (authoritative, safety-critical guard first): 1 approval helper + publisher guard, 2 doc_status, 3 skill skeleton, 4 existing-skill reference edits, 5 sync/registry wiring.

## Slice 1 — Approval helper + publisher guard (PR 1)

Files: `tools/approval_marker.py` (new), `tools/test_approval_marker.py` (new), `tools/publish_pdf.py`, `tools/test_pdf_publication.py`, `tools/build_report_auto.py`, `tools/test_build_report_auto.py`. Est. ~310 lines.

- [ ] 1.1 RED `tools/test_approval_marker.py::test_approval_state_absent_current_stale_malformed` — absent, hash-match current, hash-mismatch stale, and malformed (bad YAML, missing `preview_sha256`/`approved_at`/`approved_by`, blank value, missing `preview.md`) cases; assert `approval_state()` writes and raises nothing.
- [ ] 1.2 GREEN `tools/approval_marker.py` — implement `ApprovalState`, `sha256_file()`, `approval_state()` to satisfy 1.1.
- [ ] 1.3 REFACTOR `tools/approval_marker.py` — finalize ASCII `detail` strings naming the offending file/key; keep the module pure and read-only.
- [ ] 1.4 RED `tools/test_pdf_publication.py::test_publish_refuses_absent_stale_malformed_marker` — add `_approved_work_folder(tmp_path)` fixture; assert absent/stale/malformed marker each raise `PublicationError` and create nothing (`documents_root` never created).
- [ ] 1.5 GREEN `tools/publish_pdf.py` — add required keyword-only `work_folder` to `publish_validated_pdf`; call `approval_marker.approval_state(work_folder)` and raise `PublicationError` immediately after `_require_pdf_file`/category-slug validation, before `sha256_file(source)`, `folder.mkdir`, or any temp file; re-export `sha256_file` from `approval_marker` (`build_report_auto.py:19` import stays valid).
- [ ] 1.6 GREEN `tools/test_pdf_publication.py` — update the eight existing positional calls (122,134,136,146,149,175,187,194) to pass `work_folder=` at the approved fixture; confirm the current-marker path still publishes `v001`/hash-matched-reuse exactly as today.
- [ ] 1.7 REFACTOR `tools/publish_pdf.py` — finalize the three Spanish refusal messages verbatim from design; confirm `build_report_auto.py:138` still prefixes `PDF PUBLICATION FAILED:`.
- [ ] 1.8 RED `tools/test_build_report_auto.py::test_publication_runs_after_build_and_validation_pass` — assert `publish.assert_called_once_with(..., work_folder=config.folder)`; add a `folder` attribute to `FakeReportConfig`.
- [ ] 1.9 GREEN `tools/build_report_auto.py:132` — pass `work_folder=config.folder` to the `publish_validated_pdf` call.
- [ ] 1.10 RED `tools/test_build_report_auto.py::test_validate_only_refuses_publication_pending_approval` — under `--validate-only` reaching publication with no current marker: stdout already printed `VALIDATION PASSED` (or `...WITH WARNINGS`) before the `SystemExit`, and the raised message explicitly states validation passed and publication was refused because approval is pending; `--validate-only`'s build-skip behavior is otherwise unchanged.
- [ ] 1.11 GREEN — confirm 1.10 passes with the 1.5–1.7 wording; only if it does not, adjust the absent-marker message text minimally (no semantics change to `--validate-only`).

Must leave green: `pytest tools/ tests/` fully green; publication refuses on absent/stale/malformed markers and still publishes on a current one; `build_report_auto.py:19` `sha256_file` import untouched.

## Slice 2 — `doc_status` derivation (PR 2)

Files: `tools/doc_status.py` (new), `tools/test_doc_status.py` (new). Consumes slice 1's `approval_marker`. Est. ~370 lines.

- [ ] 2.1 RED `tools/test_doc_status.py::test_intake_*` — missing `report.yml` (all phases pending), unknown `route:` (blocked `unknown_route`), incomplete route-mandatory metadata (pending).
- [ ] 2.2 GREEN `tools/doc_status.py` — `PHASES`, `PhaseState`/`DocStatus` dataclasses; `derive()` intake logic building `ReportConfig` directly (never `load_report_config`, never `SystemExit`).
- [ ] 2.3 RED `tools/test_doc_status.py::test_research_*` — evidence-matrix present (done), `research: skipped` (done), neither (pending).
- [ ] 2.4 GREEN `tools/doc_status.py` — research phase derivation.
- [ ] 2.5 RED `tools/test_doc_status.py::test_preview_*` — non-empty (done), empty/whitespace (pending), unreadable (blocked `preview_unreadable`).
- [ ] 2.6 GREEN `tools/doc_status.py` — preview phase derivation.
- [ ] 2.7 RED `tools/test_doc_status.py::test_approval_*` — absent (pending, not blocked), stale (blocked `approval_marker_stale`), malformed (blocked `approval_marker_malformed`), current (done); uses `tools/approval_marker.approval_state`.
- [ ] 2.8 GREEN `tools/doc_status.py` — approval phase derivation; `next` never advances past approval unless current.
- [ ] 2.9 RED `tools/test_doc_status.py::test_generate_*` — final PDF newer than marker (done), older (pending, stale PDF).
- [ ] 2.10 GREEN `tools/doc_status.py` — generate phase derivation via mtime comparison.
- [ ] 2.11 RED `tools/test_doc_status.py::test_validate_*` — `result: pass` with matching hash (done), pass with mismatched hash (pending), `result: fail` (blocked `validation_failed`).
- [ ] 2.12 GREEN `tools/doc_status.py` — validate phase derivation.
- [ ] 2.13 RED `tools/test_doc_status.py::test_deliver_*` — hash-matched published PDF under `~/Documents/<category>/<slug>/` (done), absent (pending).
- [ ] 2.14 GREEN `tools/doc_status.py` — deliver phase derivation.
- [ ] 2.15 RED `tools/test_doc_status.py::test_cli_and_purity` — missing/non-directory/unreadable work-folder argument exits 2 with a message and creates nothing; `derive()` leaves the folder listing byte-identical before/after; an unexpected exception in one phase's derivation yields `blocked` with a reason, never `done`, and later phases stay `pending`.
- [ ] 2.16 GREEN `tools/doc_status.py` — `main(argv)` CLI, exit codes, per-phase exception-to-blocked wrapping.
- [ ] 2.17 RED `tools/test_doc_status.py::test_render_human_golden` — gate line front-loaded exactly when a phase is pending/blocked, omitted otherwise; static asserts: ASCII-only, no `|` tables, no `###`+ headers, exactly one route line with exactly one bracketed phase, tokens exactly `done|current|pending|blocked`.
- [ ] 2.18 RED `tools/test_doc_status.py::test_render_machine_schema` — `academic.doc-status/v1`, `### Summary`, `### Blocked Reasons`, `### JSON` fenced payload with `schemaName/schemaVersion/workFolder/phases/current/next/gate/blockedReasons`; `--json` still renders both blocks (machine stdout, human stderr).
- [ ] 2.19 GREEN `tools/doc_status.py` — implement `render_human()`/`render_machine()` per 2.17–2.18.
- [ ] 2.20 REFACTOR `tools/doc_status.py` — trim to ~150 lines (derivation ~90, renderers ~45, CLI ~15); dedupe phase-derivation helpers.

Must leave green: full suite; no skill or script touched; `doc_status` never shells out or imports `gentle-ai`.

## Slice 3 — `document-workflow` skill skeleton (PR 3)

Files: `skills/document-workflow/SKILL.md` (new), `skills/document-workflow/references/{intake,research,preview,approval,generate,validate,deliver}.md` (new), `tests/skills/test_document_workflow_contract.py` (new). Est. ~300 lines.

- [ ] 3.1 RED `tests/skills/test_document_workflow_contract.py::test_required_files_and_frontmatter` — `SKILL.md` + 7 references exist; frontmatter has `name`, `description` with `Trigger:`, `license: Apache-2.0`, `metadata.{author,version,scope}`.
- [ ] 3.2 GREEN `skills/document-workflow/SKILL.md` — frontmatter and the `doc_status -> next -> reference -> delegate -> re-run` loop with the phase/reference/executor routing table.
- [ ] 3.3 RED `tests/skills/test_document_workflow_contract.py::test_status_template_contract` — the fenced human-block template has no markdown tables, no nested headers, one route line with `[current]`, ASCII-only tokens.
- [ ] 3.4 GREEN `skills/document-workflow/SKILL.md` — embed the exact fenced human-block template (Gate/Route/Summary/Next) from design.
- [ ] 3.5 RED `tests/skills/test_document_workflow_contract.py::test_referenced_paths_resolve` — every executor path named in `SKILL.md` resolves on disk.
- [ ] 3.6 GREEN `skills/document-workflow/references/{intake,research,preview,generate,deliver}.md` — each names its executor and the single artifact it must produce.
- [ ] 3.7 RED `tests/skills/test_document_workflow_contract.py::test_approval_reference_contract` — `approval.md` names `preview_sha256`/`approved_at`/`approved_by` and states silence/inferred-yes/agent-decision never produce `approval.yml`.
- [ ] 3.8 GREEN `skills/document-workflow/references/approval.md` — human-gate reference (no executor), lossless prompt contract, marker schema.
- [ ] 3.9 RED `tests/skills/test_document_workflow_contract.py::test_generate_reference_forbids_unapproved_build` — `generate.md` forbids building before approval is `done`.
- [ ] 3.10 GREEN `skills/document-workflow/references/generate.md` — state the precondition explicitly.
- [ ] 3.11 RED `tests/skills/test_document_workflow_contract.py::test_validate_reference_both_branches` — `validate.md` names the RDD branch (`gentle-ai review mode status`) and the fallback chain with the identical gate set, and states `unknown` routes to fallback.
- [ ] 3.12 GREEN `skills/document-workflow/references/validate.md` — write both branches per design's routing table.
- [ ] 3.13 Verify skill-name collision — run `gentle-ai skill-registry refresh`, then check the registry for a non-project `document-workflow` entry (read-only lookup); adjust `SKILL.md`'s `name:` only if a collision is found.

Must leave green: new contract test plus every existing test, unchanged.

## Slice 4 — Existing-skill reference edits (PR 4)

Files: `skills/academic-report-builder/references/document-intake.md`, `skills/academic-report-builder/references/automation-contract.md`, `skills/research-workflow/references/research-protocol.md`, `tests/skills/test_report_builder_routing.py`. Est. ~150 lines.

- [ ] 4.1 RED `tests/skills/test_report_builder_routing.py::test_confirmation_is_required_on_every_execution` and `::test_document_contract_block_is_specified` — update to expect data-record wording (no approval-to-generate sentence); assert `document-intake.md` no longer authorizes generation.
- [ ] 4.2 GREEN `skills/academic-report-builder/references/document-intake.md` — Document Contract becomes a data record written to `report.yml`; remove "generation begins only after the user confirms this block"; allow one targeted clarification per missing route-mandatory field; forward-reference the single confirmation to `document-workflow/references/approval.md`.
- [ ] 4.3 RED `tests/skills/test_report_builder_routing.py::test_publication_gated_on_approval` — `automation-contract.md`'s `VERSIONED_PDF_PUBLISHED_OR_REUSED` lists `APPROVAL_CURRENT` as a precondition.
- [ ] 4.4 GREEN `skills/academic-report-builder/references/automation-contract.md` — add the `APPROVAL_CURRENT` precondition; leave other gates unchanged.
- [ ] 4.5 RED `tests/skills/test_report_builder_routing.py::test_research_protocol_names_evidence_path` — §5 of `research-protocol.md` names `$REPORT_CONTENT_ROOT/reports/<work-folder>/research/evidence-matrix.md` and labels the package pre-document evidence, never confirmed intake.
- [ ] 4.6 GREEN `skills/research-workflow/references/research-protocol.md` — name the evidence-matrix path and pre-document-evidence wording in §5.
- [ ] 4.7 REFACTOR `tests/skills/test_report_builder_routing.py` — confirm the single-confirmation rule is asserted exactly once across the whole route, traceable to `document-workflow/references/approval.md`.

Must leave green: full suite with the updated assertions.

## Slice 5 — Sync/registry wiring (PR 5)

Files: `scripts/sync_skills.sh`, `tests/skills/test_sync_skills.py`. Est. ~60 lines.

- [ ] 5.1 RED `tests/skills/test_sync_skills.py::test_document_workflow_and_codex_target_present` — `document-workflow` is added to `SKILLS`; `$HOME/.codex/skills` is added to `TARGETS`.
- [ ] 5.2 GREEN `scripts/sync_skills.sh` — add `document-workflow` to `SKILLS`; add `$HOME/.codex/skills` to `TARGETS`.
- [ ] 5.3 RED `tests/skills/test_sync_skills.py::test_sync_exits_zero_without_gentle_ai_binary` — with `APPLY=1` and `gentle-ai` absent from `PATH`, sync exits 0 and the registry-refresh step is skipped without aborting under `set -euo pipefail`.
- [ ] 5.4 GREEN `scripts/sync_skills.sh` — after the rsync loop, only when `APPLY=1`: `command -v gentle-ai >/dev/null && { gentle-ai skill-registry refresh || echo "!! skill-registry refresh failed (non-fatal)" >&2; }`.
- [ ] 5.5 RED `tests/skills/test_sync_skills.py::test_sync_exits_zero_when_refresh_fails` — `gentle-ai` present but exits non-zero; sync still exits 0.
- [ ] 5.6 GREEN — confirm 5.4's `|| echo ... non-fatal` satisfies 5.5; adjust only if a gap is found.

Must leave green: full suite; dry run exits 0 with `gentle-ai` absent.

## Review Workload Forecast

Chained PRs recommended: Yes
400-line budget risk: High
Estimated changed lines (total): ~1190
Estimated changed lines (per slice): Slice 1 ~310, Slice 2 ~370, Slice 3 ~300, Slice 4 ~150, Slice 5 ~60
Decision needed before apply: No — chain strategy is `feature-branch-chain`, selected by the user and recorded in `openspec/config.yaml` (`session_preflight.chain_strategy`). Tracker branch `feat/document-workflow-skill`; PR 1 targets the tracker, each later slice PR targets the previous slice's branch, only the tracker merges to `main`. Do not re-ask.
