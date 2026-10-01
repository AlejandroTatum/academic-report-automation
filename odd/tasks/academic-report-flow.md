# academic-report-flow — unify document-workflow and academic-report-builder

Branch: `refactor/academic-report-flow` (stacked on `feat/min-sources-override` @ f034725; main is stale).
Worktree: `academic-report-automation-worktrees/claude`.

## Goal

One skill, `academic-report-flow`, replaces `document-workflow` and
`academic-report-builder`: a single entry point (always `doc_status` first, then load
only the current phase reference) and ONE intake file, so intake rules can no longer
contradict each other. `research-workflow` and `academic-visual-builder` stay separate.

## Why

Observed 2026-10-01 (exercise 1.5): intake asked route/student/title, skipped the
guide/rubric, and the two intake files disagree (`document-workflow/references/intake.md:18,44`
requires the route; `academic-report-builder/references/document-intake.md:11` minimum omits it).
As-is flow: `docs/diagrams/intake-flow-current.mmd`.

## Constraints

- `.githooks` sync runs on checkout/merge/rewrite only (not commit); the sync script's
  `SKILLS` list is hardcoded. Never checkout/rebase this branch with a red skill tree.
- Pi runtime copies are manual (symlink into dotfiles) — runtime install is a separate,
  user-approved step after merge.
- New SKILL.md must meet `docs/skill-style-guide.md` (body <= 1000 tokens, section order).
- `tools/doc_status.py` intake validity (known route, real title/student) stays enforced.
- Historical `odd/` and `openspec/` entries are not rewritten.

## Tasks

- [x] 1. Record the as-is flow diagram and this plan. (docs)
- [x] 2. Mechanical merge: create `skills/academic-report-flow/` from both skills (git mv, no
      rule changes), repoint all contract tests, sibling skills (`research-workflow`,
      `academic-visual-builder`), `scripts/sync_skills.sh` SKILLS list, tool comments,
      README; delete the old dirs. Full `tests/skills` + `tools` tests green.
- [x] 3. Unify intake: merge `intake.md` + `document-intake.md` into one
      `references/intake.md` (content-first default, full-route confirmations as a
      section); remove the contradiction. Tests updated.
- [x] 4. Harden intake (test-first): (a) route derived as `academic` when the request names a
      subject/teacher/assignment (APE, AA, exercise), asked only when ambiguous; (b) a
      student identity the user saved as permanent counts as confirmed (still never
      invented); (c) guide/rubric/teacher-explanation always requested in content-first;
      (d) PDF/DOCX owned by the `format` phase; (e) triggers include exercise/homework/APE/AA.
      Keep `doc_status.py` guidance + `test_doc_status_guide.py` consistent.
- [ ] 5. Docs: to-be flow diagram, README, conversation cases.
- [ ] 6. (User decision) Install the unified skill into Claude/Codex/OpenCode/Pi runtimes and
      remove the two old skill dirs there.

## Evidence

(commit ids recorded per task)

- Task 1: 9cccd7c
- Task 2: mechanical merge into skills/academic-report-flow; `tests/skills tools` 1654 passed, 0 failed (RED before moves: 98 failed, 29 errors). SKILL.md body 906 tokens. Commit 993084d. Native review lineage review-a0a5eccf88e1c24d (base feat/min-sources-override, 4 lenses): approved, authority burned.
  Advisory findings carried into tasks 3-5: conflicting load rules / entry-contract conflict (SKILL.md:15-19),
  self-delegation leftovers (references/intake.md:7, draft.md:7), dropped decision gates (SKILL.md:46-56),
  stale test name (test_sync_skills.py:105), preview-guard substring hack (test_document_workflow_contract.py:603),
  stale old skill dirs remain in runtimes (sync_skills.sh does not delete dropped skills -> task 6).
- Task 3: references/intake.md + document-intake.md merged into one intake.md (git rm of the latter); advisory findings fixed (entry rule, self-delegation, decision gates, test name, preview guard). RED before skill edit: 2 failed, 1652 passed; GREEN: `tests/skills tools` 1654 passed, 0 failed. Commit recorded in git log.
- Task 3: 0b34617; native review review-395d42ec4e2ea8e8 approved, authority burned; advisory: intake.md:51-54 confirmation scope (fixed in task 4), minor test-readability suggestions.
- Task 4: hardened content-first intake (route derived for academic assignments, saved permanent student, guide always requested, format phase owns PDF/DOCX, free-text sanity, assignment triggers). RED before edits: 7 failed, 1657 passed; GREEN: `tests/skills tools` 1664 passed, 0 failed. Commit recorded in git log.
- Note: `git commit --amend` fires the post-rewrite hook and synced academic-report-flow into ~/.claude/skills and
  ~/.codex/skills early (old skills still there too). Do not amend/rebase on this branch.
- Runtime cleanup (user-approved, 2026-10-01): old `document-workflow` and `academic-report-builder` dirs in
  ~/.claude/skills and ~/.codex/skills verified identical to the repo, then moved to the trash (`trash-put`).
  Recurrence risk: any checkout/merge in another worktree whose `scripts/sync_skills.sh` still lists the old
  names re-syncs them until this branch is merged; sync never deletes dropped skills (task 6 follow-up).
