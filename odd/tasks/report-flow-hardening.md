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
- [x] T5a Content-check hardening: vacuous pass, re-derivation trusts the recorded
      mechanical list, unguarded `load_rubric`/rubric hash, pre-T2 markers report
      "re-run the judge", misleading errors after a parse failure, guide path
      confined and judge inputs resolved one way, rubric section parser (code
      fences, setext headings), unknown check type at run time, blocked `verify`
      Gate text.
- [x] T5b Sources and rendering: deterministic `verify_sources.py` (CrossRef/Open
      Library, mocked in tests); PDF handoff uses the exact file name with fish-safe
      quoting; guide facts report conflicting matches; URLs in headings/captions;
      loose lists; warn on figure-path precedence.
- [x] T6 Skill prose, contract tests, runtime sync, and an E2E re-run on the
      APE Semana 1 folder.
- [x] T7 E2E bug fixes (content check): legacy marker detected before the
      mechanical-set rule (stale, not malformed) with correct Gate text; judge
      brief explains `[@key]` renders as IEEE at build; `verbatim_from_guide`
      tolerates only a first-letter case difference (user decision 2026-09-29).
- [x] T8 Advisory fixes (sources and handoff): empty bib never passes; malformed
      registry JSON does not abort; DOI given as URL normalized; author compare
      accent/particle tolerant; one retry on HTTP 429; fish quoting escapes
      backslashes and quotes the directory.
- [x] T9 Two independent judges: content_check requires two judgments files from
      independent judges bound to the same body/rubric hashes, merges them per
      criterion keeping the strictest status (falta > flojo > cumple), records both
      judges and any disagreement; verify.md launches two judges (user decision
      2026-09-29, closes the judge-variance gap).
- [x] T10 Judge brief scope: `--judge-brief` lists the rubric checks already
      run on the current body (criterion, type, pass/fail, detail) plus the
      tolerance rules (verbatim: whitespace-normalized, first letter may differ
      in case; contains/headings: case- and accent-insensitive) and tells judges
      not to downgrade a criterion for a property a passing check verifies
      (fixes the T9 E2E false positive).

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
  Commit `1d72243`. RDD lineage `review-0c61912d7bd664c7`: approved, acknowledged/
  burned. Advisory, taken into T5b: URLs inside headings/captions (moving
  arguments), loose lists with blank lines, silent figure-path precedence.
- T5a: RED verified by the parent (implementation stashed: mechanical-set, boolean,
  no-criteria, legacy-marker, parse-cascade, invalid-rubric, guide-escape and
  verify-guidance tests fail); GREEN `pytest tools/ tests/ -q` 1481 passed.
  Commit `f0803f2`. RDD lineage `review-027442804a898217`: approved, acknowledged/
  burned. Advisory, taken into T5b: setext `---` vs thematic break, stale-marker
  guidance untested, narrow except in `run_check`, mechanical round-trip.
- T5b: RED 6 focused failures (handoff, guide conflicts, setext, moving-argument
  URLs, loose lists, figure precedence) + verify_sources collection error; GREEN
  `pytest tools/ tests/ -q` 1498 passed. Real-network smoke on the APE bib found a
  false MISMATCH (Open Library stores only the main title); fixed test-first. Final
  real run: 7/7 verified (Prana 2018/2019 year warning). Two worker attempts failed
  on a runtime incident (0 tool calls); retried after recovery.
  Commit `07f8c21`. RDD lineage `review-966e559bb44a4c17`: approved, acknowledged/
  burned.

- T6 (skill prose): RED verified by the parent (skill prose stashed: 7 new contract
  tests fail); GREEN `pytest tools/ tests/ -q` 1505 passed. Prose covers verified
  sources, rubric TDD before drafting, checks before presenting the draft, batched
  edit orders, independent judge only, exact fish handoff. SKILL.md 118 -> 122 lines.

## E2E re-run findings (APE Semana 1, 2026-09-29)
- A real pre-T1/T2 content-check marker reads `malformed` (verify BLOCKED), not the
  `stale` T5a promised: the complete-mechanical-set rule fires before the legacy
  rule. Legacy detection must run first. The blocked Gate still says "run the
  check" for the malformed case.
- Rubric TDD worked: a `verbatim_from_guide` check failed on the objective and the
  tool flagged "judged cumple despite failing check". Cause: sentence-initial
  capital ("Preparar" vs guide "preparar"). Decide whether verbatim tolerates a
  leading-capital difference.
- Independent judge worked and was stricter than self-grading: it found a real gap
  (README steps omit LuaLaTeX/Biber listed in Materiales). It also raised a false
  issue (IEEE not visible in body.md): the judge brief must say `[@key]` renders as
  IEEE at build time.
- The blocked-verify Gate now correctly says "fix findings ... through the user's
  literal edit orders, then re-approve".

- T7: RED verified by the parent (implementation stashed: judge-brief, initial-case
  verbatim and malformed-guidance tests fail). The worker's legacy test used a
  pre-T1 shape that already passed; the parent reproduced the real E2E marker
  shape (rubric/bib hashes, no judge, 3 mechanical checks: old code `malformed`,
  new code `stale`) and added it as a regression test. GREEN 1513 passed.
  Commit `604627b`. RDD lineage `review-9597b0e2bb0bb6e1`: approved, acknowledged/
  burned.
- T8: RED verified by the parent (implementation stashed: 8 tests fail across the
  6 items); GREEN 1519 passed. Real-network smoke on the APE bib still 7/7 verified
  (Prana year warning). The worker reported "blocked, no changes" while it had in
  fact written the full change; the parent verified the tree directly.
  Commit `8a14315`. RDD lineage `review-d1031b274fdc0a67`: approved, acknowledged/
  burned. Advisory: registry-data errors reported as NETWORK_ERROR (should be
  MISMATCH), minor readability.

- After T7/T8: content check passes (13/13 rubric checks, the verbatim objective
  now passes). A second independent-judge run on the SAME inputs marked
  instrucciones-reproducibles `cumple`, while the first run had found a real gap
  (LuaLaTeX/Biber missing from install steps). Judge verdicts are not stable.
  Next cycle: turn that class of gap into a deterministic check, or keep the
  stricter verdict of two judges per criterion.

- T9: RED verified by the parent (implementation stashed: two-judge merge,
  exactly-two, identical-files and guidance tests fail); GREEN 1525 passed.
  Commit `4dbf1d3`. RDD lineage `review-b32871479c3c6bac`: approved, acknowledged/
  burned. Advisory: merge runs before full validation of both files, identical-
  bytes heuristic, len() on non-list judges in state, judge errors unattributed.

- T9 E2E (2026-09-29): two judges disagreed on repositorio-organizado (flojo vs
  cumple); strictest verdict blocked verify as designed. But judge A's reason
  ("Preparar" capitalized) re-judged something the deterministic
  `verbatim_from_guide` check already passed under the user's first-letter rule.
  Fix: the judge brief must list the rubric checks already verified and the
  tolerance rules, and tell judges not to re-judge them.

- T10: RED verified by the parent outside the repo (HEAD content_check.py in a
  scratch copy: 4 judge_brief tests fail); GREEN 1529 passed. Real APE brief now
  lists every rubric check as PASS plus the tolerance rules and the
  no-re-judge instruction. Commit `5edebcb`. RDD lineage
  `review-f9f06d79554f3b45`: approved, acknowledged/burned (one resilience
  capture refused for a wrong subject_hash echo, re-run cleanly). Advisory: test
  block inserted mid-function, tolerance prose duplicates check semantics and
  can drift from rubric_checks, body.md read twice (brief can race an edit).

- T10 E2E (2026-09-29): with the new brief both judges returned `cumple` on all 7
  criteria, citing the passing checks and judging only what they do not cover; no
  capital-letter false positive. Content check pass (13/13), verify done. Validate:
  cross-repo RDD `review-83eb9311a0c1c081` (user-authorized, 10 text files,
  medium, reliability lens) approved/burned + `validate_report.py` pass (one
  unrelated outputs/ clutter warning); validation.yml for PDF sha `b8d92a43...`.
  Now at review (human PDF review). RDD advisories to triage: content-check.yml
  lacks a guide hash binding, rubric checks not tied to criterion semantics,
  judge B misattributed one quote, factual claims (commit/branch counts) are not
  verified by any check, sources-verification warning unresolved.

## Follow-ups (next cycle, from T5b advisories)
- Fish quoting: backslashes inside single quotes, unquoted directory in `set d`.
- `verify_sources.py`: empty bib must not pass vacuously; malformed registry JSON
  must not abort the run; DOI given as URL; author compare false mismatch; retry
  on HTTP 429.
- `guide_facts` conflicts contract documented; moving-argument URL proof test.
