# Document workflow stabilization

## Objective and rationale
Make the document workflow generate, validate, and deliver a report without hidden manual corrections or publication before validation. The prior implementation passed its suite, but the isolated Cata Club run exposed lifecycle, route-default, status, rendering, visual, and instruction defects (#22–27); treat each root cause separately (a shared file is not a shared cause). Defective-behavior tests became contract regressions.

## Scope and constraints
- Repo AlejandroTatum/academic-report-automation; base `9c9790d40cb46c3fafda0038daceb61f241ea1a8`; branch `fix/document-workflow-stabilization`; worktree `/home/alejo/devwork/.projects/apps/academic-report-automation-worktrees/pi`; root stays on `main`.
- Single writer, separate verification. Preserve explicit options, approval hashes, historical published PDFs; reuse existing lifecycle/publication checks; no redundant states or approvals.
- Narrowly relevant `skills/` references + contract tests in scope; review units ≤400 authored lines, subdivided without dropping tests or compressing code.
- No commits, push, PR, remote branch deletion, or issue closure; never modify/reclaim/delete/repair review authority stores.
- Excluded: connector geometry (#10), features #11–13/#21. Final-PDF figure readability stays an acceptance requirement. Archive tags are local preservation, not off-machine backup.

## Method and checks
- ODD; no new SDD change. Strict TDD from `openspec/config.yaml` (`strict_tdd: true`).
- cwd this worktree; interpreter `/home/alejo/devwork/.projects/apps/academic-report-automation/.venv/bin/python`; full suite `<interpreter> -m pytest tools/ tests/`; same interpreter for focused paths per RED/GREEN/refactor cycle.
- Reproduce each reported behavior with a failing regression before the source change; record observed results. The historical 800-pass suite is evidence only for the pre-stabilization tip.

## Tasks

### T0 — Preserve histories; clean local repo — DONE
- [x] Audit worktrees/branches/cleanliness/remote; preserve every former non-main tip; fast-forward main without a merge commit; remove the old Pi checkout and branches after checks.
- Evidence: main `68ae295` -> `9c9790d` (fast-forward); 25 tags `archive/pre-stabilization-20260916T015039Z/` verified against tips before deletion; old Pi history reachable via `.../feat-document-workflow-orchestrator-w1` `1f365bf`; three divergent outlier histories also tagged; remote main unchanged. Worker, independent verifier, and parent Git spot checks passed.

### T1 — Isolated implementation workspace — DONE
- [x] Branch from local main in a fresh Pi worktree; both checkouts clean at `9c9790d`; root deps/interpreter preserved; worktree registered and this plan recorded before source edits.
- Evidence: only `main` + implementation branch; `/home/alejo/devwork/apps/` symlinks to `/home/alejo/devwork/.projects/apps/`; no copied/reused `.codegraph`, no local `.venv`; this doc intentionally uncommitted; root clean.

### T2 — Separate generation from publication (#22) — DONE (parent accepted)
- [x] Reproduce premature publication; strip delivery side effects from generation; add explicit delivery reusing the guarded publisher; require current approval + validation for the exact PDF with byte/hash continuity; update affected references/tests.
- Acceptance: generation never publishes to `~/Documents`; delivery refuses missing/stale approval or validation and publishes only validated bytes (build copies ≠ final delivery).
- RED: test_build_report_auto.py 13 failed/23 passed; test_deliver_report.py ModuleNotFoundError.
- Fix (Unit A): build_report_auto.py drops `publish_validated_pdf`, verifies the hash is unchanged across validation (`PDF CHANGED DURING VALIDATION`), reports SHA-256 + a pointer to deliver_report.py (~124 authored lines; focused 36/36).
- Fix (Unit B): new deliver_report.py gate over the existing publisher (`validation.yml` pass + `artifact_sha256` == current bytes, then `publish_validated_pdf(expected_sha256)`); refusals exit 1; new test_deliver_report.py 9 cases (~270 lines; focused 68 passed).
- Fix (Unit C): automation-contract.md, deliver.md, generate.md, new routing test in tests/skills/test_report_builder_routing.py (~63 lines; RED exception doc-only, regression authored after text, green; routing+contract 71/71).
- CLI smoke (temp `--documents-root`): publish v001 exit 0 with SHA-256; rerun exit 0 REUTILIZADO; refusal exit 1 naming approval after marker removal; one versioned PDF. Full suite 811 passed (~22s).
- Rollback: revert Unit A files; delete Unit B's two new files; revert Unit C refs/tests. Independent verifier: 139 focused/contract + 16 hermetic CLI cases all PASS; parent read deliver_report.py. Accepted.

### T3 — Recoverable, consistent status (#24; part of #25) — DONE (parent accepted)
- [x] Reproduce stale failed validation blocking a new PDF; check validation receipt identity before interpreting its outcome; derive human/JSON gate output from one authoritative representation.
- Acceptance: stale failures do not block new bytes; current failures still block; human and JSON agree across relevant phase states.
- RED: 4 new contract tests failed/21 passed (stale fail receipt blocking; unbound identity; gate focus before approval; human/JSON divergence).
- Fix (doc_status.py): `_phase_validate` checks receipt identity (`artifact_sha256` vs current bytes + readability) before the result — stale/unbound (incl. `result: fail`) -> `pending`, only a fail bound to current bytes -> `blocked`/`validation_failed`; `derive` computes one authoritative gate (focus phase + its `_GUIDANCE`); `_gate` projects `status.gate` verbatim so `render_human` == JSON `payload["gate"]` (~144 lines over 4 files).
- GREEN: focused `tools/test_doc_status*.py` 65 passed; full suite 815 passed (~30s). Hermetic CLI: stale fail -> `validate pending`; current fail -> `validate blocked` + `validation_failed`; `--json` human gate == JSON gate.
- Rollback: revert the four files. Independent verifier re-ran the 65 focused tests (PASS); parent read the receipt/gate logic. Accepted.

### T4 — Route-derived rendering defaults (#23) — DONE (parent accepted)
- [x] Reproduce technical route receiving academic defaults; derive template/cover/front-matter from the route contract; align validation while preserving explicit options.
- Acceptance: technical reports get no UNL academic shell by default; academic defaults retained; explicit options remain effective.
- RED: test_route_defaults.py 37 failed/6 passed (technical route rendered `\begin{titlepage}`).
- Fix (Unit A): build_latex_report.py `ROUTE_TEMPLATE_DEFAULTS` (academic->unl, B-E->plain), `template_key_for()` explicit-wins, route-derived absent-key numbering, route-gated `{{LIST_OF_FIGURES}}`; templates/plain-report.tex; moved test_section_numbering.py; new test_route_defaults.py (241).
- Fix (Unit B): report_config.py `ROUTE_COVER_DEFAULTS` + `cover_value` coherence (`body_starts_on_page`->2, `logo_required`->True when required, explicit keys win); validate_report.py 4 call sites; new test_cover_route_defaults.py (163).
- Counts: tracked 152+/37- over 7 files; untracked tests 241+163 = 404; total ~593 across two units. GREEN focused 211 passed; full suite 867 passed (~20s). CLI smoke: academic+figures titlepage 1/LoF 1/numbering true; technical+figures 0/0/false; technical+explicit `cover.required: true` -> required/body 2/logo True.
- Correction round (both reproduced): (1) technical+figures expanded `\newpage\listoffigures`; RED 3 failed; `{{LIST_OF_FIGURES}}` is now academic-only, legacy plain keeps LoF. (2) technical+explicit `cover.required: true` gave body page 1/logo false (false "cover mixed with body"); RED 2 failed; fixed by dependent coherence. Template/cover independence documented in document-routing.md; stale docs/comments fixed; Docker note corrected (cached `texlive/texlive:latest` bd551dda2195 usable offline; compiled-PDF rendering assigned to T8).
- Rollback: Unit 1 = build_latex_report.py, plain-report.tex, test_section_numbering.py, test_route_defaults.py; Unit 2 = report_config.py, validate_report.py, test_cover_route_defaults.py; plus the document-routing.md section.

### T5 — Table and bibliography rendering (#26) — DONE (parent accepted)
- [x] Reproduce long two-column overflow and empty/duplicate bibliography; add wrapping without regressing layout; suppress empty/duplicate bibliography while keeping citation-driven references.
- Acceptance: rendered PDFs show no reported table overflow or empty/duplicate reference headings; cited reports keep correct references.
- RED: test_breakable_tables.py 3 failed/12 passed; new test_bibliography.py 3 failed/5 passed. Compile (hermetic docker `texlive` bd551dda2195, `--network none --pull never`, UID/GID 1000, `/tmp/t5-table-repro`): pre-fix 426.56pt overfull -> post-fix 0 overfulls across 2/1/4-column tables, stable on a second pass.
- Fix (Unit 1): <=2-column branch emits centered `p{\dimexpr(\textwidth-<8*cols>pt)/<cols>\relax}` wrapping columns (same longtable env, `\small`, grid, `\endhead`); >=3-column xltabular untouched.
- Fix (Unit 2): bibliography emission is citation-driven by the first rendered pass (`"\cite{" in body`); plain/unl/chamba replace the hardcoded print with `{{PRINT_BIBLIOGRAPHY}}`; `markdown_to_latex` suppresses a bibliography-named heading only when the citation-driven print occurs; `[@key]`->`\cite{key}` unchanged.
- GREEN: focused 250 passed; full suite 889 passed; after corrections focused 80, full suite 900 passed (~21s). Independent: 132 focused passed; hermetic cited/code-only PDFs 0 overfull, correct bibliography.
- Units: T5-A table 51 lines; T5-B citation-driven bibliography (plain/UNL + renderer + test_bibliography.py) ~251; T5-C chamba parity + test_bibliography_rendering.py ~174 — all <400. The earlier 378 was wrong (stale lengths); corrected split 51/251/174.
- Correction round (both reproduced): chamba-overleaf.tex still hardcoded the print -> `{{PRINT_BIBLIOGRAPHY}}` preserving `\Needspace{6\baselineskip}`; a raw-Markdown regex falsely counted fenced/inline `[@key]` -> rendered-pass detection, mixed case guarded. Hermetic chamba: cited 1 heading/1 bbl entry, uncited none, 0 overfull.
- Rollback: U1 = <=2-column colspec hunk + test_breakable_tables.py; U2 = citation hunks + two template lines + test_plain_template.py pin + two new bibliography tests; U3 = chamba line + test_bibliography_rendering.py. T2–T4 untouched.
- Out-of-scope: `convert_inline()` leaks literal `@@LATEX_KEEP_0@@` into inline-code output (base `9c9790d`, predates T5; T5 only needs zero rendered `\cite`).

### T6 — Mermaid scale and layout limits (#27) — DONE (parent accepted)
- [x] Reproduce missing Mermaid scale passthrough; support scale preserving default behavior; document ER direction limits without promising unsupported layout.
- Acceptance: supplied scale reaches the renderer; omission preserves native behavior; final figures readable at rendered size (raster scale alone is not proof).
- RED: new test_visual_builder_mermaid.py 8 failed/1 passed (no `--scale`). Fix: visual_builder.py mermaid gains `--scale` (float, default None = omit); nonpositive/nonfinite -> `SystemExit("--scale inválido: ...")` before running; valid -> append `-s <scale>`; help updated (+12/-1 plus a ~150-line test). GREEN focused 38 passed; full suite 909 passed (~18s). Hermetic stub-mmdc: omitted -> legacy shape (no `-s`); `--scale 3` -> `-s 3.0`; `0`/`nan` -> exit 1, renderer never spawned.
- Doc unit: skills/academic-visual-builder/references/visual-workflow.md +22/-0 ("Mermaid layout limits and raster scale": ER `direction` limitation, restructure/split or HTML-figure workaround, `--scale`->`-s` with native default, invalid rejection, density ≠ legibility). RED exception doc-only, guarded by the pre-existing passing doc contract test.
- Reconciliation: the earlier "real mmdc UNAVAILABLE" claim applied only to this worktree (no `node_modules/.bin/mmdc`); the preserved ROOT `node_modules/.bin/mmdc` renders via a temporary PATH — native and `--scale 1` -> PNG 258x348, `--scale 2` -> 516x696, browser from preserved `CONTENT_ROOT/.cache/puppeteer/...`, no install/pull. All CURRENT "unavailable engine" claims are superseded; the historical wrong assumption is kept only as superseded. Final-print legibility stays with T8. Accepted.

### T7 — Skill instructions sufficient without session context (#25) — DONE (parent accepted)
- [x] Document content-root discovery + required intake YAML keys; explain local-source evidence when research is skipped; remove inappropriate preview character restrictions without rewriting approved bytes; align generation/validation/delivery/status instructions; verify the supported sync route before claiming runtime copies active.
- Acceptance: fresh-context execution can follow the shipped instructions without guessing parameters or depending on this conversation; contract checks included; no unrelated rewrites.
- RED unit 1: test_doc_status_render_cli.py + test_doc_status_derive_cli.py + tests/skills/test_document_workflow_contract.py -> 9 failed/31 passed (relative cwd-dependent preview path; approval-front-loaded SKILL.md gate). Fix: `_guidance` prints the absolute work folder + runnable entrypoints; SKILL.md shows the focus-phase gate with an absolute activation command. Focused 40 passed; doc_status + tests/skills 164 passed.
- RED unit 2: tests/skills/ -> 12 failed/123 passed (hardcoded personal roots; no `report.yml` record; "automatically published"; research skip without local evidence; ASCII-only preview; `python tools/...`). Fix: automation-contract.md defines `REPORT_AUTOMATION_ROOT`/`REPORT_CONTENT_ROOT` with absolute commands; clean-delivery.md states generation never publishes and delivery is explicit under current `approval.yml` + `validation.yml`; document-intake.md/intake.md record canonical `report.yml` keys; research.md points to inspected local sources; preview.md allows UTF-8 and forbids rewriting approved bytes; generate.md/deliver.md absolute; the academic SKILL.md records intake keys + route-derived defaults. GREEN tests/skills 135 passed; focused 156 passed; full suite 929 passed (~17s).
- Correction round (both reproduced): (1) docs conflated the checkout holding `tools/` with the one holding `.venv`; RED 4 contract tests failed; fixed by separating `REPORT_AUTOMATION_ROOT` (may be a worktree) from `REPORT_PYTHON` (default `${REPORT_PYTHON:-$REPORT_AUTOMATION_ROOT/.venv/bin/python}`, overridable); the documented snippet was extracted and ran from an unrelated cwd (exit 0, printed the content root). (2) deliver_report.py is mode 644 so direct execution exits 126; RED 5 new tests failed; fixed in doc_status.py `_tool_command()` -> `shlex.join([sys.executable, <root>/tools/<script>, <folder>])`, no executable-bit change; the deliver gate parsed with `shlex.split`, run from an unrelated cwd on a spaced folder, published one byte-identical `-v001.pdf` with only `--documents-root`; the negative case exited non-zero naming `approval.yml` and created no Documents dir.
- Counts: Unit 1 315 added/33 removed; Unit 2 298/33; correction Unit A 144/0, Unit B 86/0, Unit C no new edits; all <400, nothing golfed. Sync route: `scripts/sync_skills.sh --apply` in an isolated HOME mirrored `~/.config/opencode/skills`, `~/.claude/skills`, `~/.codex/skills` exactly (`diff -r`), no host writes. Pi does NOT receive them: `~/.pi/agent/skills/` is not a sync target, has no `document-workflow/` copy, and its `academic-report-builder` copies differ; not updated (host mutation unauthorized).
- Independent verification: 183 status/skill + 9 delivery tests passed; parent read `_tool_command` (`sys.executable`/`shlex.join`); the `REPORT_AUTOMATION_ROOT`/`REPORT_PYTHON` separation is documented and executed. Full suite 936 passed in ~17s (929+7). Rollback: Unit 1 reverts `_GUIDANCE`/`_guidance`/`derive` hunks + SKILL.md block + tests; Unit 2 reverts the listed references and routing tests; correction units revert their named hunks. Accepted.

### T8 — Full workflow validation and remaining gaps — PARTIAL (final-size legibility acceptance fails)
- [x] Run focused regressions and the complete suite from this worktree.
- [x] Repeat the Cata Club report in a new content folder without deleting prior outputs.
- [x] Inspect rendered pages for route/cover, tables, and references.
- [ ] Inspect final-size figure legibility — inspection performed; acceptance fails (below).
- [x] Verify publication happens only after validation and delivers the exact validated bytes.
- [x] Record all failed/unavailable/skipped/pending checks; do not close issues on partial coverage.
- Acceptance: all applicable technical and visual checks pass with named evidence, or the remaining blocker is reported explicitly; preserve the human approval boundary.
- Independent evidence (parent-observed): full suite 936 passed in 17.54s; branch at `9c9790d` unchanged; root `main` untouched. Isolated fixture `outputs/stabilization-e2e-20260916/{content,documents,home,pages,logs}`; original CataClub report/preview/approval/body/PNGs copied byte-identical, no original writes, marker CURRENT (not refreshed/fabricated). Fresh PDF `outputs/stabilization-e2e-20260916/pdf-fresh-7ecedb13.pdf` = 14 pages vs 15 original, technical plain body starts p1, no academic cover, no LoF, 4 figures + a single Referencias.
- Technical: BUILD_PASS + VALIDATION_PASS WITH WARNINGS (overfull 3.16pt p5, 29.07pt p8, below the clipping threshold; annotation uncertainty).
- Visual: auditor PASS_WITH_WARNINGS / ORPHAN_HEADING p3, low-confidence, unadjudicated; independent vision + parent image inspection of page08 found tiny final-print labels (~2.6–3.3pt em sequence, ~4.6pt ER, ~3.5–5.5pt others). Same PNGs/placement as the base report, so this is not a stabilization regression. VISUAL_PASS / HUMAN_REVIEW / READY_TO_SUBMIT NOT granted; T8 stays PARTIAL on final-size legibility; do not silently fix report/source.
- Pipeline: no receipt -> delivery refused exit 1, no publication; the validated PDF then a NEW SANDBOX TEST receipt on the existing schema (only BUILD_PASS + VALIDATION_PASS, hash-matching); guarded `deliver --documents-root <sandbox>` copied the same `7ecedb13...` bytes; rerun REUTILIZADO single file; stale original hash `3667dd07` refused. Isolated HOME/Documents used only for a `doc_status` readback (`next done`), never visual acceptance. Real Documents v001/v002/v003 and the original manifest unchanged. Route-default minimal fixture (1 page, no institution) passed 92 focused tests independently.
- T7 prerequisites: end-to-end rerun in a new content folder, compiled-PDF inspection (route/cover, tables, references), and delivery strictly after validation were done; final-size figure legibility is the only failing item.

### T9 — Preserve T2–T7 as work-unit commits — DONE
- [x] Record the commit plan and its boundaries in this document before staging anything.
- [x] Create one reviewable commit per review surface; no file is split across commits, so every commit is internally coherent.
- [x] Re-run the full suite from this worktree on the final HEAD.
- [x] Leave `outputs/` untouched (gitignored) and the root checkout on `main` clean.
- Acceptance: `git status` clean over source and this document; each commit is a coherent reviewable surface with its tests and docs alongside the behavior; suite green at final HEAD; no push, PR, issue closure, or review-authority mutation.
- Evidence (writer-executed, parent-verified): commits `a75394b` (lifecycle, 5 files) -> `2ab87cf` (render, 14) -> `f9edb44` (status, 4) -> `154da22` (visual, 3) -> `309ca81` (skills docs, 12) -> `cc1ebd3` (ODD, 1) = 39 files, 2603 insertions / 228 deletions vs `9c9790d`. Parent-observed: `git status --porcelain` empty, `git diff HEAD` empty (the commits captured the working tree exactly, so no behavior changed), `outputs/` absent from all 6 commits, root checkout still clean at `9c9790d` on `main`, branch unchanged and nothing pushed.
- Suite: 936 passed in 18.40s on the committed HEAD (writer-observed). Because `git diff HEAD` is empty, this HEAD is byte-identical to the tree that had already passed 936 tests, so the result is not a new claim about changed content.
- No prohibited Git operation was run, so no host skill sync was triggered: `core.hooksPath=.githooks` defines only `post-checkout`/`post-merge`/`post-rewrite`, and `git commit` fires none of them. The root checkout was never touched.
- Deferred by decision: the T8 legibility blocker, the Pi runtime skill sync, and the `@@LATEX_KEEP_0@@` base-only leak.

#### Commit plan (surface-based, no shared files)
Task numbers are not the commit axis because T2/T3/T7 and T4/T5 share files. Grouping by surface keeps every commit self-consistent and avoids splitting hunks.

| # | Message scope | Files |
| --- | --- | --- |
| 1 | `feat(lifecycle)`: generation never publishes; explicit guarded delivery (#22) | `tools/build_report_auto.py`, `tools/test_build_report_auto.py`, `tools/deliver_report.py` (new), `tools/test_deliver_report.py` (new), `tests/skills/test_report_builder_routing.py` (new) |
| 2 | `fix(render)`: route-derived defaults, wrapping tables, citation-driven bibliography (#23, #26) | `tools/build_latex_report.py`, `tools/report_config.py`, `tools/validate_report.py`, `templates/*.tex`, `templates/academic_format.yml`, `tools/test_route_defaults.py` (new), `tools/test_cover_route_defaults.py` (new), `tools/test_section_numbering.py`, `tools/test_breakable_tables.py`, `tools/test_bibliography.py` (new), `tools/test_bibliography_rendering.py` (new), `tools/test_plain_template.py` |
| 3 | `fix(status)`: recoverable receipt, unified gate, context-free commands (#24, #25) | `tools/doc_status.py`, `tools/test_doc_status_validate_deliver.py`, `tools/test_doc_status_derive_cli.py`, `tools/test_doc_status_render_cli.py` |
| 4 | `feat(visual)`: mermaid `--scale` passthrough and documented layout limits (#27) | `tools/visual_builder.py`, `tools/test_visual_builder_mermaid.py` (new), `skills/academic-visual-builder/references/visual-workflow.md` |
| 5 | `docs(skills)`: context-free document workflow instructions (#25) | `skills/academic-report-builder/**`, `skills/document-workflow/**`, `tests/skills/test_document_workflow_contract.py` |
| 6 | `docs(odd)`: record document-workflow-stabilization T2–T9 | `odd/tasks/document-workflow-stabilization.md` |

- Staging is by explicit path only; `git add .` / `git add -A` are forbidden so `outputs/` and any stray artifact stay out.
- Commit ordering follows dependency: lifecycle -> render -> status -> visual -> docs. Intermediate commits are preservation checkpoints; the green-suite evidence is asserted at final HEAD, not per checkpoint, because the surfaces interlock through shared behavior.
- Rollback for T9 is `git reset --soft <base>`; it changes no file content.

#### Native review status — BLOCKED (not a candidate defect)
The RDD preflight ran on this candidate after the commits. The Pi-side facade first returned `stop`/`managed_assets_outdated`; `gentle-ai.real sync --agent pi` updated 1 managed file and the preflight then returned `ready`. Do not misread that first `stop` as a store or candidate problem: it was stale Pi managed assets, and its projection was stale too (its `base_tree` was the tree of the pre-cleanup `68ae295`, listing 55 paths no commit here touched).

Lineage `review-a4a39fd064f7225b` was started with `baseRef=9c9790d` + `committedOnly: true`, which scoped the candidate to exactly this work: tier `high`, 39 files, 2834 lines, lenses risk/resilience/readability/reliability. Three lenses were admitted; `review-readability` was refused three times at admission.

Root cause verified independently, not inferred: the preserved payloads under `<git-common-dir>/gentle-ai/rejected-results/review-a4a39fd064f7225b/` are valid binary wrappers whose inner `raw` field contains **11 `[` and 10 `]`** — an unclosed array. A local scan reproduced the provider's numbers exactly (6/6 objects, 11/10 arrays, scan end at byte 7678 of a 7677-byte `raw`), so the refusal is correct and not a false positive. Admitted lenses were 1929/4916/5278 bytes; refused attempts were 5722/5356/7678 bytes, always the longest and always cut at the last array. The relay prompt is ~219 KB, so this reads as a host-relay output ceiling on the longest lens. `gentle-ai review --help` exposes no token/budget/timeout flag, so it cannot be raised from gentle-ai.

Two operational facts worth keeping: a refusal does **not** consume the lens slot (`submitted_reviewers: 0`, `mutation_performed: false`), and per-slot capture is the correct isolation move — `gentle_review_capture` admitted `review-reliability` on the first attempt after two group runs had failed, because `readability` is submitted first and blocks everything behind it. Total cost: 8 model runs for 3 admitted lenses.

Status: lineage left in `reviewing`, reoffering only the `review-readability` (order 2) slot. The missing lens result was never fabricated and the authority store was never touched. The user decided (2026-09-18) to leave this pending rather than retry or abandon. This is a bounded review-transport defect, not a defect of the committed candidate: the candidate tree stayed constant throughout, and `git diff HEAD` is empty.

## Unresolved / out-of-scope (no fixes authorized here)
- Pi runtime has no `document-workflow` copy and a stale `academic-report-builder`; `scripts/sync_skills.sh` targets only opencode/claude/codex.
- `skills/academic-visual-builder/references/visual-workflow.md:6-7` still hardcodes both roots (outside the T7 grant).
- Base-only inline-code placeholder leak (`@@LATEX_KEEP_0@@`) seen in targeted tests, not in the E2E report; unchanged from `9c9790d`.
- No source fixes for the above; no commits, push, or issue closure.

## Verification notes and limitations
- Cleanup changed Git metadata/checkouts, not source; no commits.
- Checkout/merge hooks ran contract batches (68 and 90 passing) and synced skills into `~/.claude/skills` and `~/.codex/skills`; not a full-suite run or proof of Pi runtime sync.
- Native assessment unavailable (`native command returned empty output`); RDD off; independent read-only verification fulfilled that role; no review authority maintenance/bypass attempted.
- This bookkeeping edit changed only this document; no tests were run (documentation-only); all source changes remain uncommitted.

## Next step
T2–T7 independently accepted. T8 stays PARTIAL: only final-size figure legibility fails (page08 labels ~2.6–4.6pt em). Its remedy is a report-visual redesign and approval decision (figure layout/font sizing) — not re-running or silently editing report/source; no automatic new-scope task.

T9 is DONE (2026-09-18): the T2–T7 work is preserved as 6 work-unit commits (`a75394b`..`cc1ebd3`) on `fix/document-workflow-stabilization`, suite green at 936, working tree clean, nothing pushed. The T8 legibility blocker, the Pi runtime skill sync, and closing #22–#27 remain deferred and unauthorized. The next real decision is whether to push this branch and open a PR for human review.
