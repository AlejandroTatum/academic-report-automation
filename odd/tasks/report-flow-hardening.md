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
- [x] T11 Content-check robustness (T9/T10/E2E advisories): validate both
      judgments files fully before merging and attribute every error to its file;
      tolerate non-list `judges` in state; read body.md once so the brief hash and
      the checks use the same bytes; tolerance text comes from one constant shared
      with rubric_checks; content-check.yml binds the guide hash (a changed guide
      stales the marker); move the T10 tests out of the middle of another test.
- [x] T12 verify_sources: registry-data errors (bad fields in a 200 response)
      report MISMATCH, not NETWORK_ERROR.
- [x] T13 guide_facts conflicts contract documented in its reference; proof test
      that a URL inside a moving argument (heading/caption) builds.
- [x] T14 Judge quote check: every single-quoted fragment in a judge `where` must
      appear in body.md (whitespace-normalized); a missing fragment is a warning
      naming the judge and criterion, never a block.

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
  Review: user OK 2026-09-29, final-review.yml bound to the same sha. Deliver:
  `...-v002.pdf` published and hash-matched; doc_status `next: done`. RDD advisories to triage: content-check.yml
  lacks a guide hash binding, rubric checks not tied to criterion semantics,
  judge B misattributed one quote, factual claims (commit/branch counts) are not
  verified by any check, sources-verification warning unresolved.

- T11: RED by the worker (10 failing tests + ImportError on TOLERANCE_RULES);
  parent's scratch-copy RED stopped at collection (TOLERANCE_RULES missing at
  HEAD). GREEN 1546 passed; the delivered APE report stays `next: done` (markers
  without guide_sha256 remain valid). Commit `4490701`; RDD lineage
  `review-b25435178a429457`: all four lenses approved, acknowledged/burned on
  resume (2026-09-29). The host relay timeout is now 1800000 ms; no runtime
  configuration was changed in this session. Non-blocking readability advisories
  are follow-ups, not a reason to reopen this candidate.

## Current work (2026-09-29 resume)
- T12 commit authorized (2026-09-29): invalid registry JSON/field shapes report `MISMATCH`;
  transport errors must remain `NETWORK_ERROR`, preserving HTTP 404 and retry
  behavior. Route: delegated writer (code plus tests; multi-file trigger).
- Allowed source surfaces: `tools/verify_sources.py`,
  `tools/test_verify_sources.py`. Forecast: about 60-120 authored diff lines;
  this is one work unit on the existing stacked feature branch.
- Checks: observed RED before implementation, focused source-verifier tests,
  full `pytest tools/ tests/ -q`, and native review of this work-unit slice.
- T12 implemented, functionally verified, and natively reviewed; work-unit
  commit delivery authorized. Observed RED: 4 failed / 14 passed before production changes. GREEN: focused
  source tests 18 passed; full suite 1550 passed; `git diff --check` clean.
  Independent read-only verifier repeated focused tests: 18 passed, diff clean.
- Scope: registry-specific `RegistryDataError`, malformed JSON classification,
  minimal CrossRef/OpenLibrary field guards, and offline continuation/network
  tests. Source diff: 98 insertions + 9 deletions (107 authored lines).
- Native assessment: high (`process_boundary`); writer self-verification plus
  independent verifier completed. No real-network smoke (offline-only scope).
- RDD `review-fb591c3c30c3ce7f`: four lenses approved, acknowledged/burned;
  reviewed work-unit tree `64351b408f00fcb05fa800d516e2e71057472455` (136 diff
  lines including the then-current task evidence). Source files are unchanged
  after review; this completion note is passive bookkeeping written afterward.
  Informational advisories only: R2-narrowed-except-chain,
  R2-repeated-inline-bib-literals, R3-001. No correction was offered.
- T12 marked done: focused source tests 18 passed and native review
  `review-fb591c3c30c3ce7f` burned; work-unit commit delivered on
  `feat/report-flow-hardening` as `4c82b43bd75846ab2c494198b8a92368e3a5dc0d`.
- Rollback boundary: reverse only the T12 changes in `tools/verify_sources.py`
  and `tools/test_verify_sources.py`; unrelated T11 remains intact.
- User authorized completing all remaining T tasks and their work-unit commits
  (2026-09-29); push, PR, and merge remain unauthorized.
- T13 in progress: document the existing `guide_facts` conflicts contract and
  prove that heading/caption URLs compile into a real PDF. Route: delegated
  writer (documentation plus test, multi-file trigger). Allowed surfaces:
  `skills/document-workflow/references/intake.md`, `tools/test_latex_links.py`.
  Forecast: about 60-80 authored diff lines. This is characterization of
  existing rendering, not a behavior fix; no artificial RED is required. Check:
  real PDF compile with available local engine, focused tests, full suite,
  structural doc check, then review/commit at this work-unit boundary.
- T13 initial checks: 12 focused passed / 1 skipped; full 1550 passed / 1
  skipped. The real-compile test was skipped because its gate checked host
  engines only. Independent diagnosis verified Docker 29.8.0 and an existing
  local `texlive/texlive:latest` image (LuaHBTeX 1.24.0 / TeX Live 2026) with
  `--network none`. No install or download needed. Next: support this existing
  fallback in the test, run it using the shared Python venv, and require real
  PDF evidence before T13 closes.
- T13 final functional checks: 13 focused passed, full 1551 passed, zero skips;
  `git diff --check` clean. Actual Docker compile generated `main.pdf` (20380
  bytes, PDF-1.7) via LuaHBTeX 1.24.0. Heading/caption URL included query,
  underscores and ampersands; annotation URI recovered exactly from PDF bytes.
  Independent verifier repeated the focused checks: 13 passed, no skips, diff
  clean. The test enforces `--pull=never --network=none` for Docker, with no
  production renderer changes. Native assessment high (`process_boundary`).
  Characterization rationale: the test proves the existing rendering contract
  (heading/caption URLs compile offline into a real PDF); it is not a behavior
  fix, so no artificial RED was required. Rollback: reverse only the T13
  intake-reference and link-test additions. RDD lineage
  `review-12df821d0eb6e608`: native review approved, acknowledged/burned by the
  parent; no new native review run. Advisories informational; none blocking.
  Implementation verified and closed by work-unit commit `8cdb8e2`
  (8cdb8e20b1ac4ae416d2e5b7612e699ffe406d89).
- T14 in progress: a missing single-quoted fragment in a judge's `where`
  emits a warning naming that judge's file and criterion; body containment is
  case-sensitive and whitespace-normalized, never a new blocking check.
  Route: delegated writer (source, tests and verify-reference; multi-file).
  Allowed surfaces: `tools/content_check.py`, `tools/test_content_check.py`,
  `skills/document-workflow/references/verify.md`. Forecast: about 100-160
  authored diff lines. Check-first: missing quote warnings RED, then GREEN;
  preserve pass/state/exit code, both-judge attribution before merge, matching
  and unquoted evidence, whitespace variants, ordinary apostrophes. Run
  focused content-check tests, full suite, independent spot check as assessed,
  native review and work-unit commit. Rollback only T14 source/tests/prose.
- T14 functional evidence: observed RED 5 failures / 93 passes before any
  production edit; GREEN 98 focused tests and 1558 full-suite tests, zero
  skips, `git diff --check` clean. Independent verifier repeated 98 focused
  passes, diff clean. Warnings preserve both judge-file identities and
  criterion IDs before strictest merge; pass remains pass, semantic failure
  remains fail, ordinary/quoted apostrophes and normalized whitespace tested.
  Actual source/tests/prose diff: 166 authored lines (forecast 100-160).
  Native assessment high (`process_boundary`).
  RDD lineage `review-8b9d14e4194b8aca`: all four lenses approved against the
  reviewed work-unit tree `6fe7cffbb0047ecc402c208c182884990362bf76`;
  acknowledged/burned by the parent (2026-09-29). Advisory R3-001 is
  informational only; no correction was offered or required. The
  source/tests/prose files are unchanged after review; this completion note is
  passive bookkeeping. Implementation closed by work-unit commit `8ad1a9a`
  (8ad1a9ade9d55440088ba23df921d3eb98ae4f40) on `feat/report-flow-hardening`.
  Rollback boundary: reverse only the T14 changes in
  `tools/content_check.py`, `tools/test_content_check.py`, and
  `skills/document-workflow/references/verify.md`; unrelated T12/T13 remain intact.
- A different-guide E2E remains a future cycle, outside these T1-T14 tasks.
- Final status (2026-09-29): ALL tasks T1-T14 are complete. T14 was the last
  task; its work-unit commit is `8ad1a9a`
  (8ad1a9ade9d55440088ba23df921d3eb98ae4f40) and this entry is the closing
  passive, doc-only evidence note. No known failing or pending checks exist for
  the T tasks; the full suite last ran green at 1558 tests with zero skips.
  Push, PR, and merge remain unauthorized and were not performed. A
  different-guide E2E and any report publishing flow are separate future work,
  outside this feature's tasks. This bookkeeping does not start a new native
  review.

## Out of scope (user decision, report data not tooling)
- Factual claims in body.md (commit/branch counts) are not checkable without
  access to the student's repository.
- Prana year warning in research/sources-verification.yml.

## Historical follow-ups from T5b advisories (completed — not open work)
- DONE in T8 — fish quoting: backslashes inside single quotes, quoted directory
  in `set d`.
- DONE in T8/T12 — `verify_sources.py`: empty bib no longer passes vacuously;
  malformed registry JSON does not abort; DOI given as URL normalized; author
  compare accent/particle tolerant; retry on HTTP 429; registry-data errors
  report MISMATCH (T12).
- DONE in T13 — `guide_facts` conflicts contract documented; moving-argument
  URL proof test compiles a real PDF offline.
