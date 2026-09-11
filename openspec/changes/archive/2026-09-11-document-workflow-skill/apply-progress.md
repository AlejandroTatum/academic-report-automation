# Apply Progress: Document Workflow Orchestration Skill

**Change**: `document-workflow-skill`
**Phase**: `sdd-apply` — parent lifecycle reconciliation (all slices already committed)
**Artifact store**: `openspec` (authoritative)
**Branch/head at reconciliation**: `feat/document-workflow-skill-14-sync-registry` @ `39fd3fa`
**Strict TDD**: active (`openspec/config.yaml` → `strict_tdd: true`, runner `pytest`)
**Code edits during reconciliation**: none (checkbox reconciliation + this record only)
**Allowed edit surfaces**: `openspec/changes/document-workflow-skill/tasks.md`, `openspec/changes/document-workflow-skill/apply-progress.md`

## Structured status consumed

- `artifactStore: openspec` → status is **authoritative** (non-authoritative `resolve-via-engram` carve-out does not apply).
- `applyState: all_done`; parent prompt explicitly requests lifecycle reconciliation after all slices completed.
- `actionContext.mode`: standard apply (not `workspace-planning`); edit roots supplied explicitly by the parent (the two files above).
- No blocked reasons relevant to apply remained; no `allowedEditRoots` violation occurred.
- `next_recommended` (phase output): `parent-lifecycle`.

## Task checkbox reconciliation

- `openspec/changes/document-workflow-skill/tasks.md`: all **58** implementation-owned checkboxes toggled `- [ ]` → `- [x]` (tasks 1.1–5.6).
- No `sdd-owner` markers exist in the file (all rows are legacy `implementation`-owned); no parent-owned rows to defer.
- Diff verified as marker-only: `git diff --word-diff=porcelain` shows exactly `58 × [ ]→[x]` and nothing else.
- Re-read after edit: `grep -c '^- \[x\]'` = **58**, `grep -c '^- \[ \]'` = **0**.

## Final slice → commit map

Commits are linear on the `feature-branch-chain` tracer `feat/document-workflow-skill` (base `0d9c4df`, main `68ae295`). "Changed lines" = added + deleted per `git show --numstat`; where a commit also carries SDD plan-amendment text in `tasks.md`, implementation-only lines are noted.

| Slice | Branch | Commit | Changed lines (add+del) | Focused test evidence (re-run at reconciliation) | Full suite |
|-------|--------|--------|-------------------------|--------------------------------------------------|------------|
| 1a approval marker (PR 1) | `...-01-approval-marker` | `94500d9` | 269 (105 prod + 164 test) | `tools/test_approval_marker.py` → 4 passed | green |
| 1b publisher/build guard (PR 2) | `...-02-publisher-guard` | `89d1b67` | 286 (262 add / 24 del) | `tools/test_pdf_publication.py` → 11 passed; `tools/test_build_report_auto.py` → 36 passed | green |
| 2a early phases + helpers (PR 3) | `...-03-doc-status-early` | `1204ca9` | 375 | `tools/test_doc_status_phases_early.py` → 14 passed | green |
| 2b-i approval phase (PR 4) | `...-04-doc-status-approval` | `4b24b77` | 302 (210 impl + 92 `tasks.md` plan amendment) | `tools/test_doc_status_approval.py` → 7 passed | green |
| 2b-ii generate phase (PR 5) | `...-05-doc-status-generate` | `4b41dc6` | 175 | `tools/test_doc_status_generate.py` → 6 passed | green |
| 2b-iii validate+deliver (PR 6) | `...-06-doc-status-validate-deliver` | `69c6fc6` | 365 | `tools/test_doc_status_validate_deliver.py` → 12 passed | green |
| 2c-i derive + CLI (PR 7) | `...-07-doc-status-derive-cli` | `c347bc9` | 368 | `tools/test_doc_status_derive_cli.py` → 13 passed | green |
| 2c-ii renderers (PR 8) | `...-08-doc-status-render` | `2b38cc6` | 375 | `tools/test_doc_status_render_cli.py` → 9 passed | green |
| 3a-i SKILL.md core (PR 9) | `...-09-skill-core` | `83d0ef5` | 190 (186 impl + 4 `tasks.md`) | `tests/skills/test_document_workflow_contract.py` → 8 passed | green |
| 3a-ii phase references (PR 10) | `...-10-phase-references` | `1762349` | 265 | `tests/skills/test_document_workflow_contract.py` → 8 passed | green |
| 3b-i approval/generate refs (PR 11) | `...-11-approval-reference` | `7782e24` | 105 | `tests/skills/test_document_workflow_contract.py` → 8 passed | green |
| 3b-ii validate ref + collision (PR 12) | `...-12-validate-reference` | `728d67f` | 133 | `tests/skills/test_document_workflow_contract.py` → 8 passed | green |
| 4 existing-skill reference edits (PR 13) | `...-13-existing-references` | `2a9fc27` | 230 (226 impl + 4 `tasks.md`) | `tests/skills/test_report_builder_routing.py` → 62 passed | green |
| 5 sync/registry wiring (PR 14) | `...-14-sync-registry` | `39fd3fa` | 162 | `tests/skills/test_sync_skills.py` → 4 passed | green |

The `test_document_workflow_contract.py` file is shared across slices 3a-i/3a-ii/3b-i/3b-ii per the plan's per-PR staging rule; its current single run (8 passed) covers all four slices' assertions.

## Full-suite evidence

- Command: `.venv/bin/python -m pytest tools/ tests/ -q`
- Result at reconciliation (head `39fd3fa`): **800 passed in 24.36s** — matches the Slice 5 full-suite figure supplied by the parent prompt.
- All 12 focused files above re-run green individually at reconciliation.

## TDD cycle evidence

Strict TDD is active; per-slice RED→GREEN→REFACTOR structure is evidenced by the test files shipped in the same commit as each implementation change (e.g. `94500d9`: `test_approval_marker.py` + `approval_marker.py`; `1204ca9`: `test_doc_status_phases_early.py` + `doc_status.py`). Reconciliation did **not** re-execute the historical RED steps, so this table records structural TDD evidence plus current green state, not re-observed RED failures.

| Slice | RED artifact (new/updated test) | GREEN artifact | Current focused result |
|-------|---------------------------------|----------------|------------------------|
| 1a | `tools/test_approval_marker.py` | `tools/approval_marker.py` | 4 passed |
| 1b | `tools/test_pdf_publication.py`, `tools/test_build_report_auto.py` | `tools/publish_pdf.py`, `tools/build_report_auto.py` | 11 + 36 passed |
| 2a | `tools/test_doc_status_phases_early.py`, `tools/conftest.py` | `tools/doc_status.py` | 14 passed |
| 2b-i | `tools/test_doc_status_approval.py` | `tools/doc_status.py` (`_phase_approval`) | 7 passed |
| 2b-ii | `tools/test_doc_status_generate.py` | `tools/doc_status.py` (`_phase_generate`) | 6 passed |
| 2b-iii | `tools/test_doc_status_validate_deliver.py` | `tools/doc_status.py` (`_phase_validate`, `_phase_deliver`) | 12 passed |
| 2c-i | `tools/test_doc_status_derive_cli.py` | `tools/doc_status.py` (`derive`, `main`) | 13 passed |
| 2c-ii | `tools/test_doc_status_render_cli.py` | `tools/doc_status.py` (renderers) | 9 passed |
| 3a-i | `tests/skills/test_document_workflow_contract.py` | `skills/document-workflow/SKILL.md` | 8 passed |
| 3a-ii | `tests/skills/test_document_workflow_contract.py` | `skills/document-workflow/references/{intake,research,preview,generate,deliver}.md` | 8 passed |
| 3b-i | `tests/skills/test_document_workflow_contract.py` | `references/{approval,generate}.md` | 8 passed |
| 3b-ii | `tests/skills/test_document_workflow_contract.py` | `references/validate.md` | 8 passed |
| 4 | `tests/skills/test_report_builder_routing.py` | builder skill + 3 references | 62 passed |
| 5 | `tests/skills/test_sync_skills.py` | `scripts/sync_skills.sh` | 4 passed |

## Deviations from design / plan

1. **Slice granularity.** `design.md` planned 5 slices; `tasks.md` escalated to 14 slices via two recorded plan amendments (2b → 2b-i/ii/iii; 2c → 2c-i/ii; 3a → 3a-i/ii; 3b → 3b-i/ii). Both amendments are committed with Slice 2b-i; product scope, requirement set, and task order/semantics (2.8–2.15) are unchanged.
2. **Estimation recalibration (documented in `tasks.md`).** Several slices exceeded their flat forecasts but none breached the hard 400-line budget: 1a 269 (forecast ~120), 1b 286 (~250), 2a 375 (~250), 2b-i 210 impl + 92 amendment (~190), 5 162 (~235). Slice 2b's observed 559-line diff drove the recalibration.
3. **`tools/doc_status.py` final size 399 lines** vs task 2.21's stated REFACTOR target of ~150 lines. The trim target was not reached; all tests remain green. Not corrected here because this reconciliation phase is forbidden from altering implementation code.
4. **Intentional behavior change (per design, not a deviation).** After Slice 1b, `build_report_auto.py`, including under `--validate-only`, no longer publishes without a current approval marker; it exits non-zero at publication after build/validation output. This is the change's purpose ("Migration / Rollout" in `design.md`).
5. **Task 3.13 (skill-name collision check).** `skills/document-workflow/SKILL.md` `name:` has been `document-workflow` since its only commit (`83d0ef5`) and never changed, consistent with no collision requiring a rename. The registry-refresh command itself was not re-executed during reconciliation (read-only verify; no code impact).

## Unrelated staged-file warning

`git status` at reconciliation shows **unrelated files already staged** on this branch that are NOT part of this change and were left byte-for-byte untouched:

- `openspec/changes/archive/2026-09-05-simplified-document-workflow/*` (apply-progress, archive-report, design, exploration, proposal, specs/document-workflow/spec.md, sync-report, tasks, verify-report)
- `openspec/specs/document-workflow/spec.md`

These are pre-existing staged artifacts from a separate archived change. They must not be committed with this change's reconciliation; verify staging scope before any commit.

## Remaining tasks

None. All implementation-owned tasks 1.1–5.6 are `- [x]` in `openspec/changes/document-workflow-skill/tasks.md`. No unchecked `- [ ]` rows remain.

## Workload / PR boundary

- Delivery strategy: `auto-chain`, chain strategy `feature-branch-chain`; tracker `feat/document-workflow-skill`; 14 slice PRs (1a → 5), each targeting the previous slice's branch, only the tracker merges to `main`.
- Per-slice changed lines all under the hard 400-line budget (max observed 375).
- This reconciliation phase produces no PR of its own; it only updates the persisted tasks/progress artifacts for the parent lifecycle.

## actionContext warnings

- None unsafe: standard apply mode, explicit allowed edit roots honored, no target file outside them.
- `artifactStore: openspec` → authoritative status; no Engram fallback required for this phase's inputs (tasks/spec/design read from `openspec/changes/document-workflow-skill/`).
- No subagents launched; no commit made.
