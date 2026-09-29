# Report flow hardening (rubric TDD, independent judge, E2E fixes)

Feature: `report-flow-hardening`. Branch: `feat/report-flow-hardening`, stacked on
`feat/new-report-flow` @ `e1f7b23` (not merged yet).
Worktree: `academic-report-automation-worktrees/pi`.
Engram mirror: topic `odd/report-flow-hardening/tasks`, project `academic-report-automation`.

## Objective
Close the gaps the first end-to-end run (APE Semana 1, 2026-09-28) exposed: the AI
graded its own draft, half of the user's turns were tool friction, and the PDF had
rendering bugs. Decided with the user on 2026-09-28 after the hard audit.

## Design decisions
- Self-grading is replaced by two layers (the user dropped an optional
  judgment-day layer):
  1. Rubric TDD: each rubric criterion may carry deterministic `checks:` written in
     the `plan` phase, before the draft exists. They start red and the draft turns
     them green. The content check fails when any check fails.
  2. Independent judge: semantic judgments come from a read-only subagent that
     receives only the rubric, the body, the sources, and the guide, never the
     drafting conversation. The judgments file records the judge and the exact
     `body_sha256` it judged; a mismatch is rejected.
- RDD keeps checking technical integrity; it is not a rubric grader.
- The review loop and report-only rules are unchanged: no layer rewrites the user's
  text.

## Scope / constraints
- Runner: `/home/alejo/devwork/.projects/apps/academic-report-automation/.venv/bin/python -m pytest tools/ tests/`.
- Test-first per task; one work-unit commit per task; RDD review per commit.
- Out of scope: the judgment-day layer; delivered documents under `reports/`.

## Tasks
- [x] T1 Rubric TDD: `checks:` schema in `rubric.yml` (heading present, text or
      regex present in a section, verbatim text from the guide, ordered list in a
      section, minimum cited sources, figure referenced, link present, keywords
      from the objective in a section); runner; content check fails on any red
      check; `plan` reports how many criteria have checks.
- [x] T2 Independent judge: judgments file requires `judge` and `body_sha256`;
      mismatch or drafter-authored judgments rejected; skill verify.md launches a
      read-only judge with only rubric, body, sources, guide.
- [x] T3 Friction (P1): default student Alejandro Padilla; intake detects the
      document family from the guide (APE) and the practice number from "Semana N";
      format question and missing metadata through `ask_user_choice`; group work
      decided at format; documents shared as short `brave` commands, never
      screenshots.
- [x] T4 PDF quality (P2): nested ordered lists keep numbering; `<https://...>`
      autolinks become clickable `\url`; figure paths resolve from the report folder
      (build-relative still accepted); long monospace URLs break; deliver grants
      `HUMAN_REVIEW` from a current `final-review.yml`.
- [ ] T5 Rigor and cost (P3): deterministic source verification script
      (CrossRef/Open Library); blocked `verify` Gate text; content-check hardening
      (vacuous pass, recorded mechanical list, unguarded `load_rubric`, legacy
      markers); skill tells the agent to batch edit orders before re-approval.
- [ ] T6 Skill prose, contract tests, runtime sync, and an E2E re-run on the
      APE Semana 1 folder.

## Evidence
(commit ids recorded per task)
- T1: RED 10 focused failures; GREEN `pytest tools/ tests/ -q` 1439 passed. New
  `tools/rubric_checks.py`; content check adds a `rubric_checks` mechanical check.
  Commits `215fc5b` + correction `f2de8c7` (every well-formed `min_citations` check
  was rejected: integer `count` failed the string rule). RDD lineage
  `review-585ecb610a36931c`: correction validated, approved, acknowledged/burned.
  Advisory, taken into T5: fragile section parser in `rubric_checks.py`, unknown
  check type not caught at run time, state gate not proved end to end.
- T2: RED verified by the parent (implementation stashed: 2 new tests fail); GREEN
  `pytest tools/ tests/ -q` 1446 passed. Judgments need `judge.role: independent`,
  allowed `inputs`, and `body_sha256`/`rubric_sha256` of the current files;
  `content_check.py --judge-brief` prints the judge's bounded brief.
  Commit `fdfadbd`. RDD lineage `review-644eb267eabc3055`: approved, acknowledged/
  burned. Advisory, taken into T5: guide path not confined to the report folder;
  judge-input resolution differs between brief and validation; misleading errors
  after a parse failure; unguarded rubric hash; pre-T2 markers become malformed.
- T3: RED `guide_facts` missing + handoff quoting failure; GREEN `pytest tools/ tests/ -q`
  1456 passed. On the real APE guide `guide_facts.py` returns family ape, practice 1,
  Individual, 3 horas. Optional `format_hint:`; guidance uses ask_user_choice and a
  two-line `brave` command.
  Commit `e359a32`. RDD lineage `review-66f28982e101a927`: approved, acknowledged/
  burned. Advisory, taken into T5: fish quoting/escaping of the handoff path, the
  glob may match a stale PDF (prefer the exact file name), guide facts can be
  ambiguous (report the conflicting matches), `format_hint` gate divergence.
- T4: RED 4 + 3 focused failures (autolinks, nested lists, figure precedence,
  HUMAN_REVIEW, SSH remote rendering, URL escaping, xurl); GREEN `pytest tools/ tests/ -q`
  1464 passed. Real E2E PDF rebuilt: 0 Overfull hbox (was 4), 5 GitHub URI links,
  4 DOI links, 7 cite links, steps numbered 5 and 6. First pass missed the
  overflow; the parent's PDF check caught it before commit.
