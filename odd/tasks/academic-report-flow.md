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
- [x] 5. Docs: to-be flow diagram, README, conversation cases.
- [x] 6. (User decision) Install the unified skill into Claude/Codex/OpenCode/Pi runtimes and
      remove the two old skill dirs there.

- [x] 7. Fix fresh-request entry gap (found in live test 2026-10-01): a new request with no work folder fell
      into the standalone full route (asks document type), so content-first never applied. New request ->
      create `reports/<slug>/` under the content root, then `doc_status` (empty folder -> `next: intake`).
      Full route only when the work-folder flow is unavailable. Test-first; update to-be diagram.

- [ ] 8. (a), (b), (e) done; (c)(d)(f)(g)(h)(i)(j) open. Live-test follow-ups (exercise 1.5 run, delivered as v002 on 2026-10-01): (a) draft.md must require
      level-1 `#` section headings and math for sub/superscripts, with a mechanical pre-approval check (Unicode
      sub/superscripts are missing from TeX Gyre Termes; `##`-only bodies number sections 0.1.); (b) verify.md:
      define the handoff when the executor cannot launch judge subagents (orchestrator runs the judges);
      (c) routing-loop.md and doc_status research gate text still say "at least 5" under min_sources;
      (d) build output path is keyed by title slug, so a second folder with the same title overwrites the first
      folder's working PDF; (e) VISUAL_PASS ownership unclear: the visual inspection ran and passed but nobody
      granted VISUAL_PASS, so delivery reported "sin VISUAL_PASS"; (f) plan.md has no no-rubric rule;
      (g) verify_sources.py is silent on failure and false-MISMATCHes LaTeX-escaped titles; (h) draft.md step 4
      names a content_check mode the CLI lacks; (i) quality-gates.md duplicate step number and stale line ref;
      (j) existing folder without report.yml undefined; "delivered" definition untested.

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
- Task 4 commit cdea392; native review review-80be9859f3850a32 approved, authority burned. Advisory follow-up
  (next commit, test-first: RED 2 failed -> GREEN 1665 passed): restored "resume or approve report" trigger
  (description 240 chars), SKILL.md type prohibition now names the content-first route exception, de-garbled the
  doc_status.py student guidance sentence. Remaining suggestions (test substring strictness, duplicated scope note
  intake.md:66-73) left as minor follow-ups.
- Rebased onto origin/main 54c7d01: Task 1 = 8435572, Task 2 = 302cdac, Task 3 = 9203619, Task 4 = 2a28625 + 8a39b50 (review lineages were bound to the pre-rebase trees).
  Rebase side effect: the rebase's internal checkout of origin/main re-synced the old skills into ~/.claude/skills and ~/.codex/skills; they were trashed again.
- Task 5: docs/diagrams/intake-flow.mmd (+ .png) to-be flow, as-is diagram marked historical, README "Document workflow" section, conversation case 5 (exercise 1.5 incident). `tests/skills tools` stays green. Commit recorded in git log.
- Task 6 (user-approved 2026-10-01): Claude/Codex runtimes already match the branch (synced by the rebase hook; old
  dirs trashed). Pi: `~/.pi/agent/skills/academic-report-flow` installed as a real copy of the branch skill;
  `academic-visual-builder` and `research-workflow` symlinks (into ~/dotfiles/ai-stack/pi/skills, stale names)
  replaced by real copies of the branch versions; old Pi `document-workflow` dir and `academic-report-builder`
  symlink moved to the trash (both were older than origin/main, no unique edits). Dotfiles untouched.
  `~/.pi/gentle-ai/skill-runtime/course-deliverables/academic-report-builder` left in place (no longer linked).
  Pi needs `/reload` to pick the change up.
- Task 7: RED 3 failed / 1682 passed (new entry-rule contract tests); GREEN `tests/skills tools` 1685 passed, 0 failed. SKILL.md body 997 tokens. Commit: see git log (`fix(skills): create the work folder for new requests...`).
- Task 7 review: review-0364c75be9645648 (1561238 + README 2f1057e) approved, burned. Advisory R3-same-document-criterion
  fixed next commit (test-first, RED 1 -> GREEN): same-document criterion defined; a delivered match asks one
  single-choice question (new suffixed version or resume) and never overwrites.
- Live test (exercise 1.5, folder metodos-numericos-ejercicio-1-5-flow) blocked at validate: validate_ieee_refs rejected
  distinct claims sharing one citation_key, impossible under min_sources: 1. Fix (test-first, RED 1 -> GREEN):
  only a repeated claim_id is an error; distinct claims may cite the same source. The existing "Duplicate mapping"
  test case was narrowed from shared citation_key to repeated claim_id.
- Live test 2026-10-01 (exercise 1.5, reports/metodos-numericos-ejercicio-1-5-flow): intake 1 batch / 2 questions
  (route + student derived), research min_sources 1, two verify rounds (4 judges, all cumple), validate failed twice
  (citation-key tool bug fixed in c0f31a6; missing glyphs + 0.1. headings fixed by an approved body edit), delivered
  ~/Documents/Academicos/analisis-numerico/solucion-analitica-y-numerica-del-ejercicio-1-5/...-v002.pdf
  (sha256 d67dd7e4...), v001 untouched. Same numbers as v001.
- Task 8 (a)(b)(e) (h partly: draft.md now names the real `--body-check` mode): RED 17 failed / 1688 passed (new
  format-check, `--body-check`, deliver gate and contract tests); GREEN `tests/skills tools` 1705 passed, 0 failed.
  Format defects ride on the existing `rubric_checks` mechanical entry (marker shape unchanged); deliver_report
  derives READY_TO_SUBMIT from receipt gates + current final-review. Commit: see git log.
