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

- [ ] 1. Record the as-is flow diagram and this plan. (docs)
- [ ] 2. Mechanical merge: create `skills/academic-report-flow/` from both skills (git mv, no
      rule changes), repoint all contract tests, sibling skills (`research-workflow`,
      `academic-visual-builder`), `scripts/sync_skills.sh` SKILLS list, tool comments,
      README; delete the old dirs. Full `tests/skills` + `tools` tests green.
- [ ] 3. Unify intake: merge `intake.md` + `document-intake.md` into one
      `references/intake.md` (content-first default, full-route confirmations as a
      section); remove the contradiction. Tests updated.
- [ ] 4. Harden intake (test-first): (a) route derived as `academic` when the request names a
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
