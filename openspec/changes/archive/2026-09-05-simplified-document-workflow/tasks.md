# Tasks — simplified-document-workflow

Phase: tasks (planning). Store: openspec. Root: worktree `pi` — `/home/alejo/devwork/apps/academic-report-automation-worktrees/pi` (paths below relative to it). Runner: `/home/alejo/devwork/.projects/apps/academic-report-automation/.venv/bin/python -m pytest tools/ tests/`. No tests run in this phase. No commits/PRs, no native attempts, no delivery operations authorized here. Single-threaded writes; preserve ALL uncommitted state incl. U0 sync fix.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | High; pending candidate estimate ~492 current (407 OpenSpec incl tasks.md + 85 sync) + implementation ~219 (U2 ~103, U3 ~116) + apply-progress/verify artifacts ~30–60 ≈ ~740–770 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes (U0→U3 matches slice shape; PRs are NOT authorized — decision gate below) |
| Suggested split | U0 (preserved, not authored) → U1 → U2 → U3, sequential, one writer |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Resolved — user authorized local unit commits; planning/sync isolated as 10ffb78 (85 lines), 80bf37c (176), 927f12e (231). No push/PR/merge or size:exception authorized. Native cumulative budgets remain binding.
Chained PRs recommended: Deferred — local commits only are selected.
Chain strategy: not selected
400-line budget risk: High for aggregate history; each implementation unit must remain within 400 lines.

**Budget honesty (binding):** unit labels do NOT shrink the candidate or bypass native attempt/review budgets. Pending candidate estimate is ~492 current (407 OpenSpec incl tasks.md + 85 sync); 439 is a historical pre-tasks estimate only. Units are execution isolation only: ordered scopes with own verification/rollback. Provider `--work-unit` is verified label-only — no documented tracked-subset selector; unit labels do not solve the cumulative budget, and no claim is made that the provider requires a commit. Concrete true reviewable boundaries require change/delivery isolation, not fake working-tree subsets. Budget resolution gate fires BEFORE apply (candidate already >400): minimal concrete decision (NOT a split-vs-exception re-ask — split is chosen): (a) authorize local unit-scoped commits if true per-unit isolation is required, or (b) another user-authorized change/delivery isolation. No chain/PR strategy is invented; no automatic exception.

## Units (start / finish / verify / rollback)

- **U0 — sync unit (existing uncommitted, preserved, not authored here):** `scripts/sync_skills.sh` + `tests/skills/test_sync_skills.py` ≈ 85 lines. Untouched by every task below; still passing at finish; nothing to roll back.
- **U1 — planning docs (this + prior planning phases):** `openspec/changes/simplified-document-workflow/{proposal,exploration,design}.md`, `specs/document-workflow/spec.md`, `openspec/config.yaml` ≈ 354 lines; grows past 400 as tasks/apply-progress/verify-report land. Verify: planning gates passed; rollback: revert openspec files only.
- **U2 — adaptive intake (~103):** `skills/academic-report-builder/references/document-intake.md`, `skills/academic-report-builder/SKILL.md`, `tests/skills/test_report_builder_routing.py`. Self-verifying via its test file.
- **U3 — research trigger (~116), depends on U2:** `skills/research-workflow/SKILL.md`, `skills/research-workflow/references/research-protocol.md`, `tests/skills/test_research_workflow_contract.py`, `tests/skills/conversation-cases.md` (wholly U3-owned). U3 tests assert U2's builder-side wording → strictly after U2.

Implementation surfaces exactly these 7 skill/test files (U2+U3); must NOT touch: `tools/`, `templates/`, `assets/`, `report.yml` schema, `scripts/sync_skills.sh`, `tests/skills/test_sync_skills.py`. Smoke fixtures are ephemeral under `outputs/_smoke/` (existing output config may be ignored for fixtures); NO report final delivery paths are approved by this change.

## Tasks — U2 (strict TDD; scoped: `…pytest tests/skills/test_report_builder_routing.py`)

- [x] RED: rewrite/extend `tests/skills/test_report_builder_routing.py` — assert adaptive reuse wording ("reuse supplied", "candidate answers"), "missing consequential" questions only, optional `Conflicts:` line surfaced, derived questions ad-hoc not permanent, old re-ask string "even when the prompt appears to already contain" forbidden, "every execution" presence kept, existing tokens guarded; run scoped suite, record intentional failures. <!-- sdd-owner: implementation -->
- [x] GREEN: apply minimal deltas to `references/document-intake.md` (+35/−8) and `academic-report-builder/SKILL.md` (+7/−3) until passing; five-confirmations structure and the single one-confirmation gate untouched. <!-- sdd-owner: implementation -->
- [x] TRIANGULATE + REFACTOR: force generalized wording for conflict/derived-question cases; dedupe regex/token helpers only if it shrinks the diff; record RED/GREEN evidence as static-contract evidence. <!-- sdd-owner: implementation -->

## Tasks — U3 (after U2; scoped: `…pytest tests/skills/test_research_workflow_contract.py tests/skills/test_report_builder_routing.py`)

- [x] RED: add tests (7 existing untouched) to `tests/skills/test_research_workflow_contract.py` — protocol documents BOTH separate activation paths: (a) conditional automatic trigger firing only when claims required by the confirmed brief — academic AND personal/technical — lack local `inspected: true` coverage with freshness considered, vs (b) explicit user research request always activating research-workflow regardless of coverage; external source eligible on the same terms as local once inspected with provenance complete; leads never cited; builder-side trigger + inaccessible/stale-limitation wording; non-university identity wording. <!-- sdd-owner: implementation -->
- [x] GREEN: apply `references/research-protocol.md` (+20: §1 Trigger subsection, external-eligibility sentence in §2) and `skills/research-workflow/SKILL.md` (+6) until passing; asserted eligibility substrings preserved verbatim. <!-- sdd-owner: implementation -->
- [x] Conversation cases (+45) in `tests/skills/conversation-cases.md` — positive 5: complete consigna+rubric reused, only missing consequential asked; 6: conflicts stated in contract; 7: uncovered claims → trigger decision + evidence handoff, covered → no research, explicit request → research regardless; negative N10 re-asks supplied answers, N11 generates without the one confirmation, N12 cites a lead; include personal/technical non-academic trigger cases. <!-- sdd-owner: implementation -->

## Full verification + labeled evidence (after U3)

- [x] Run the full runner (`tools/ tests/`) — all pass including untouched U0 sync-fix tests; record output. Label evidence precisely: `tools/` suites = behavioral regression evidence for the existing pipeline; `tests/skills/` = static-contract evidence; the rendered smoke = separate runtime/render evidence. None of these proves live research behavior unless actually executed. <!-- sdd-owner: implementation -->
- [x] Mandatory rendered smoke before archive: fixture under `outputs/_smoke/` with `publish_global: false`; run original interpreter with `HOME=<root>/outputs/_smoke/home` and `REPORT_CONTENT_ROOT=<root>/outputs/_smoke/content` via `tools/build_report_auto.py` — never real `HOME/Documents`, never the real content root, no network, no paid research; record as independent runtime evidence distinct from static tests; remains outstanding until executed. <!-- sdd-owner: implementation -->

## Parent-gated actions (post-apply; not inline work)

- [x] BEFORE apply: user authorized local unit-scoped commits; existing sync/planning committed as 10ffb78, 80bf37c, 927f12e, each below 400 lines. Continue U2 then U3 with native attempt authority; no assumption that commits reset cumulative budgets. <!-- sdd-owner: parent -->
- [x] Post-apply bounded review: parent scope/evidence inspection confirmed U2/U3/U4 evidence and clean unit commits; native inspect returned `rdd_disabled`, so no review lifecycle was started. <!-- sdd-owner: parent -->
- [x] Before archive: parent confirmed sandboxed DOCX runtime/render evidence exists, evidence labels are complete, and only documented non-blocking limitations remain (LaTeX unavailable; conversation cases not live-executed). <!-- sdd-owner: parent -->
