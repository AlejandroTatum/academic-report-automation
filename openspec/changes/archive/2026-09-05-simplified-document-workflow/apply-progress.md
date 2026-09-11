# Apply Progress — simplified-document-workflow

Phase: apply (U2, U3). Store: openspec. Worktree: `pi`. Strict TDD active. This file accumulates progress; never overwrites completed work.

## U2 — adaptive intake (COMPLETED this run)

### Persisted task checkbox updates (tasks.md lines 34–36)

All three U2 checkboxes flipped `- [ ]` → `- [x]` immediately after completion:
RED, GREEN, TRIANGULATE + REFACTOR. Re-read confirmed below.

### Files changed (this unit)

| File | Delta | Content |
|---|---|---|
| `tests/skills/test_report_builder_routing.py` | +44/−4 | Rewrote `test_confirmation_is_required_on_every_execution` (adaptive tokens + forbidden old string); added `test_intake_surfaces_conflicts_in_the_contract`, `test_derived_missing_questions_are_ad_hoc_not_permanent` |
| `skills/academic-report-builder/references/document-intake.md` | +10/−3 | Opening rewritten (candidate answers / reuse supplied / missing consequential / proposal-until-confirmed); new "Supplied inputs" Known/Missing/Conflicting section; Question-scope ad-hoc bullet; optional `Conflicts:` contract line |
| `skills/academic-report-builder/SKILL.md` | +5/−2 | Mandatory Intake reuse sentence; step 1 research-trigger evaluation sentence; step 2 "including inaccessible/stale flags" |
| `openspec/changes/simplified-document-workflow/tasks.md` | +5/−5 | 3 U2 checkboxes marked; 10-line pre-existing parent gate-resolution diff rode along (see Notes) |

Implementation total: 59 changed lines (3 files, excl. OpenSpec artifacts). Unit under 200-line cap; per-unit under 400 budget.

### TDD Cycle Evidence

| Task | RED (intentional failure) | GREEN (focused suite) |
|---|---|---|
| U2-RED | 3 failed / 51 passed — the 3 new/rewritten tests failed against unchanged markdown; every failure was an asserted U2 token | — |
| U2-GREEN | — | 54 passed / 0 failed |
| U2-TRIANGULATE+REFACTOR | — | 54 passed / 0 failed (assertions already generalized; no helper dedupe — would grow diff) |

Commands (worktree interpreter from original checkout):

- Focused: `/home/alejo/devwork/.projects/apps/academic-report-automation/.venv/bin/python -m pytest /home/alejo/devwork/apps/academic-report-automation-worktrees/pi/tests/skills/test_report_builder_routing.py`
- RED: `3 failed, 51 passed in 0.09s` — failures: `test_confirmation_is_required_on_every_execution` (missing adaptive tokens; forbidden string present), `test_intake_surfaces_conflicts_in_the_contract` (no `Conflicts:`/silently/re-render tokens), `test_derived_missing_questions_are_ad_hoc_not_permanent` (no `missing consequential`/`derived from`/permanence wording).
- GREEN: `54 passed in 0.03s` (51 pre-existing token guards + 3 U2 tests).
- Regression: `73 passed in 1.21s` for all of `tests/skills/` (U0 sync tests and the 7 untouched research-contract tests included; read-only check, no U3 files touched).

Evidence label: the above is **static-contract evidence** (markdown read as data). It is not runtime/render evidence; the rendered smoke remains outstanding (full-verification task, after U3).

### TRIANGULATE notes

- Conflicts pinned by four independent semantic properties: optional `Conflicts:` contract line documented; contradiction generalized to "supplied inputs" (rule-form, not one example); never-resolved-silently regex; re-render + confirm-it-once.
- Derived questions pinned by three: ad-hoc, never-permanent, derived-from confirmed route + supplied inputs.
- Adaptive reuse asserted over combined SKILL.md + intake.md corpus, so the wording cannot live in one file only.

### REFACTOR notes

No refactor: existing `read`/`plain`/`sections` helpers were reused; no duplicated regex/token sets introduced; dedupe would enlarge the diff. Skipped per task instruction ("only if it shrinks the diff").

### Deviations from design

- `document-intake.md` came out **leaner** than the design estimate (+10/−3 vs ~+35/−8): the Known/Missing/Conflicting rules and contract-line prose were written more compactly. All asserted tokens and design semantics are present; nothing was dropped.
- `SKILL.md` +5/−2 vs ~+7/−3 (within tolerance).
- Test file +44/−4 vs ~+40/−10 (slightly above adds, below deletes; net smaller).
- The five-confirmation structure and the single one-confirmation gate are untouched (asserted by the retained guards: 51 pre-existing tests pass).

### Notes

- Worktree baseline before edits: `52 passed` (verified; identical committed content to main checkout). Initial RED attempts against the default cwd silently ran the main checkout's copy — corrected by invoking the worktree test file by absolute path; the recorded RED/GREEN numbers are worktree-only.
- The pre-existing uncommitted `tasks.md` modification (parent's decision-gate resolution, 10 lines, checked `[x]` parent-owned rows) is included in the U2 commit because it is the authoritative planning state this unit applies against; parent-owned rows preserved byte-for-byte.
- One local U2 commit authorized (after scoped tests pass); no push/PR/merge; native attempt token `sha256:9a3f…ca32b` (parent owns settlement).

## U3 — research trigger (COMPLETED this run)

### Persisted task checkbox updates (tasks.md lines 40–42)

All three U3 checkboxes flipped `- [ ]` → `- [x]` immediately after completion:
RED, GREEN, Conversation cases. Re-read confirmed below.

### Files changed (this unit)

| File | Delta | Content |
|---|---|---|
| `tests/skills/test_research_workflow_contract.py` | +46 | 5 new tests (7 existing untouched): both activation paths in protocol (a: conditional automatic + inspected/freshness/does-not-fire; b: explicit user + regardless of coverage); both paths named in skill + `§1 Trigger` pointer; external-inspected equal eligibility + never-cited; builder-side trigger/confirmed-brief/inaccessible-stale-flags cross-unit assertions; per-file personal/technical non-university scope |
| `skills/research-workflow/references/research-protocol.md` | +8/−1 | §1 `### Trigger` subsection documenting both paths with local `inspected: true` coverage + freshness; §2 external-eligibility sentence (same terms as local once inspected + provenance-complete) + `Leads are never cited` |
| `skills/research-workflow/SKILL.md` | +4/−2 | Activation Contract: both activation paths + pointer to protocol §1 Trigger; scope widened to academic or personal/technical. Output Contract: limitations `including inaccessible or stale sources`. Hard Rules' asserted eligibility strings verbatim-untouched |
| `tests/skills/conversation-cases.md` | +35 | Cases 5 (consigna+rubric reused, only missing consequential asked), 6 (conflicts in contract, resolved once), 7 (trigger decision: uncovered→fires+handoff, covered→no research, explicit→regardless; personal/technical non-academic sub-case); negatives N10 re-asks supplied answers, N11 generates without the one confirmation, N12 cites a lead |
| `openspec/changes/simplified-document-workflow/tasks.md` | 3 checkbox flips | U3 rows marked; U4 and parent rows untouched |

Implementation total: 102 changed lines (4 files, excl. OpenSpec artifacts: 96+6). Under the 200-line unit cap and the 400-line per-unit budget.

### TDD Cycle Evidence

| Task | RED (intentional failure) | GREEN (focused suite) |
|---|---|---|
| U3-RED | 4 failed / 62 passed — every failure an asserted new U3 token (`### trigger`, activation-path wording, external eligibility, personal/technical scope). The 5th new test (`test_builder_evaluates_trigger_and_carries_limitation_flags`) passed at RED by design: it pins U2-authored builder wording, per design §3.6 | — |
| U3-GREEN | — | 66 passed / 0 failed (12 research incl. 7 untouched + 54 routing) |
| U3-TRIANGULATE+REFACTOR | — | 66 passed / 0 failed; no refactor (helpers reused; dedupe would grow diff) |

Commands (parent-specified focused runner, absolute worktree paths):

- Focused: `/home/alejo/devwork/.projects/apps/academic-report-automation/.venv/bin/python -m pytest <worktree>/tests/skills/test_research_workflow_contract.py <worktree>/tests/skills/test_report_builder_routing.py`
- RED: `4 failed, 62 passed in 0.07s`.
- GREEN: `66 passed in 0.04s`.
- Regression: `78 passed in 1.25s` for all of `tests/skills/` (U0 sync tests + routing + research contracts; builder routing file read/run only, never edited).

Evidence label: **static-contract evidence** (markdown read as data). The conversation cases are live-run behavioral cases requiring a live skill run; they are documented, not executed here. The rendered smoke remains outstanding (U4 task).

### TRIANGULATE notes

- Path (a) pinned by negative behavior (`does not fire` when covered), coverage tokens (`inspected: true`, `freshness`), and scope (`confirmed brief`).
- Path (b) pinned independently in both skill and protocol (`regardless of coverage`).
- Non-university scope asserted per-file (skill AND protocol must each name personal + technical).
- External equality pinned by three independent tokens; leads-never-cited asserted twice (never cited / N12 case).

### REFACTOR notes

No refactor: reused the existing `read()` helper; no duplicated token sets introduced; per task instruction, dedupe only if it shrinks the diff.

### Deviations from design

- `research-protocol.md` +8/−1 vs ~+20, `SKILL.md` +4/−2 vs ~+6: trigger prose written more compactly; all design-required semantics and asserted tokens present, nothing dropped.
- Tests +46 vs ~+45; conversation cases +35 vs ~+45 (tables kept tight). Within tolerance.

## U4 — runtime evidence: full runner + rendered smoke (COMPLETED this run)

### Persisted task checkbox updates (tasks.md, "Full verification + labeled evidence" block)

Both U4 implementation checkboxes flipped `- [ ]` → `- [x]` after passing; re-read confirmed below. Parent-gated rows preserved byte-for-byte.

### Task 1 — full runner

Command (worktree cwd, original interpreter): `/home/alejo/devwork/.projects/apps/academic-report-automation/.venv/bin/python -m pytest tools/ tests/` → **716 passed in 23.71s** (0 failed).

Evidence labels: `tools/` (638 tests) = **behavioral regression evidence** for the existing pipeline (config/validation/publication/routing). `tests/skills/` (78 tests, incl. the 3 U0 `test_sync_skills.py` tests) = **static-contract evidence** for the U2/U3 skill markdown. Neither label claims live research execution.

### Task 2 — mandatory rendered smoke (runtime/render evidence)

Fixture determination: no LaTeX toolchain exists in this environment (`xelatex`/`lualatex`/`pdflatex`/`latexmk` all absent), so the shipped latex example cannot compile here. The narrow renderable fixture through `tools/build_report_auto.py` is its **generic DOCX backend**, following existing project conventions: the `report.yml` shape of `tools/test_build_docx_report.py::make_report` (`type/backend/output: docx` + explicit `publish_global: false`, as the shipped example demands) and the documented placement under `$REPORT_CONTENT_ROOT/reports/`. `route: technical` (existing route vocabulary) keeps UNL identity out per the change constraint. No tool/template/asset was changed.

Fixture (ephemeral, deleted after evidence capture): `outputs/_smoke/content/reports/smoke_render_docx/{report.yml,body.md}` — 3 headings, paragraphs, one list, no citations (IEEE requires no bib without `[@cite]`).

Invocation (worktree cwd): `HOME=<worktree>/outputs/_smoke/home REPORT_CONTENT_ROOT=<worktree>/outputs/_smoke/content <venv>/python tools/build_report_auto.py outputs/_smoke/content/reports/smoke_render_docx` → **exit 0**.

Generated artifact path: `outputs/_smoke/content/reports/smoke_render_docx/outputs/report.docx` (37,698 bytes; the worktree path resolves through a symlink to `/home/alejo/devwork/.projects/apps/…` — same physical tree).

Validation outcome: router printed `DOCX generado` → `Tipo: docx | backend: docx | output: docx` → **`VALIDATION PASSED`** (no warnings) → quality report `backups/quality_report.md` (APROBADO; validators common, ieee, docx).

Isolation proof: smoke `HOME` stayed empty (no `Documents/` tree; DOCX output never calls `publish_validated_pdf`); global `content/outputs` never created (`publish_global: false` honored); real content root and real HOME untouched; no network, no paid research.

Render readback (reopened from disk, the repo's own convention): A4 `True`; Heading styles `['Alcance','Cuerpo','Verificacion']`; 11 non-empty paragraphs.

Cleanup: `outputs/_smoke/` removed after evidence capture (disposable, not an intended artifact; `outputs/*` is gitignored); `git status` clean afterwards.

### Deviations from design

- Smoke renders DOCX instead of the latex example: forced by absent LaTeX toolchain, not a design change; the router, config, validation, and publication-gate code paths are exercised end-to-end with a genuinely rendered artifact.
- No strict-TDD RED/GREEN cycle applies to U4 (no production code written); both tasks are verification tasks, satisfied by the recorded runtime evidence above.

## Remaining tasks (exact unchecked lines)

U4 is complete (both rows now `- [x]`; see U4 section). No implementation-owned rows remain in this change.

Parent-gated (deferred lifecycle actions, preserved):

- [ ] Post-apply bounded review: parent scope/evidence inspection only; never auto-spawn custom reviewers; native lifecycle only if a user-owned review mode enables it. <!-- sdd-owner: parent -->
- [ ] Before archive: confirm rendered-smoke runtime evidence exists, evidence labeling complete, outstanding items resolved. <!-- sdd-owner: parent -->

## Structured status consumed/produced

- Consumed (parent, authoritative): change `simplified-document-workflow`; store openspec; U2 complete at `f7e9060`; apply ready; nextRecommended U3 apply; attempt token `sha256:36fa0f1415e67cc4a53087f7af58d4e46a1c0de18bcfdd6f54b5bd7a748f053a` (proceed; parent owns settle).
- The stale injected native status (changeName null, "No active SDD changes found") was resolved against the CWD root, not the worktree; worktree artifacts verified directly; parent fresh status governed.
- Workload gate: delivery resolved by prior user authorization into local unit isolation — exactly one local U3 commit after tests pass; no chain, no size:exception, no push/PR/merge. Unit total 102 changed lines.
- actionContext warnings: none from parent. No cwd incidents this unit (all pytest invocations used absolute worktree paths / repo-relative `tests/skills/`).

- Consumed this run (U4): parent fresh status — U2/U3 complete; apply ready; attempt authority `sha256:c5bdb1b3d56529858df19c75cabedd015fb06a2e8d70a3c6df0be4fedc1022a2` (proceed; parent owns settle). The injected native status again resolved against the CWD planning home (changeName null), not the worktree; worktree artifacts verified directly (U2/U3 rows checked, commits present, clean tree at b9bbd33).
- Workload gate: resolved — delivery is local unit isolation; exactly one local U4 commit after both tasks pass (user-authorized); no push/PR/merge, no size:exception. U4 changed lines: 2 in tasks.md + this file — under the 120-line cap.
- actionContext warnings (U4): none; all edits inside allowed surfaces (tasks.md U4 rows, apply-progress.md, `outputs/_smoke/**` — cleaned up).
