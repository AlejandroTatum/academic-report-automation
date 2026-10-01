# Course deliverables hierarchy

## Objective and scope
Keep each course's Git-ready delivery tree separate from document production. Support an explicitly requested .bib bibliography alongside the final PDF.

## Decisions and constraints
- Academic delivery: ~/Documents/Academicos/<canonical-subject-slug>/<document-slug>/<document-slug>-vNNN.pdf, plus a paired versioned .bib only when declared.
- A course directory may be a Git repository; Git metadata stays at course level, outside per-document artifact folders.
- Production stays under REPORT_CONTENT_ROOT: reports, academic-sources, assets/generated, builds, audits and receipts never travel automatically.
- Preserve PDF-only reports and non-academic category layouts. DOCX publication is out of scope.
- No legacy-document migration, real-document publication, course Git initialization, pushes, or unrelated changes.
- Baseline: 37dcd9de10d3647b092d6f9c3933b01abf4058c9 (clean feat/report-flow-hardening, matching installed skills; main is its ancestor).
- Worktree: /home/alejo/devwork/.projects/apps/academic-report-automation-worktrees/pi-document-delivery; branch: feat/course-deliverables-hierarchy.
- Implementation commits were initially withheld pending explicit authorization. The user has now authorized commit/push and safe unused-worktree cleanup; delivery is tracked in course-deliverables-delivery.md.

## Routing and review workload
One delegated writer per bounded unit; command-running independent checks use the verifier. Interpreter: /home/alejo/devwork/.projects/apps/academic-report-automation/.venv/bin/python.
Initial forecast: 600-850 authored changed lines; revised after T1 to 1200-1700. Actual T1+T2: 2095 (+1980/-115) across 24 tracked files, mostly expanded regression coverage. Advisory only; never omit checks or compress code. Delivery strategy: ask-on-risk; any future PR/commit delivery must resolve review slicing. Native review uses only the user-owned RDD switch; blocked authority must not be repaired or bypassed.

## Tasks
- [x] T1 — Subject-scoped academic paths shared by publisher and doc_status, with tests and matching skill guidance. Status: verified; work-unit commit 82df3a757bf0839f56238d0c99ca7eb87e09e734. Route: delegated writer (multiple non-trivial files).
- [x] T2 — Optional declared .bib delivery with exact-byte validation/review binding, complete artifact-set version reuse, fail-closed refusals, tests and intake/delivery guidance. Status: verified; work-unit commit 82df3a757bf0839f56238d0c99ca7eb87e09e734. Route: delegated writer.
- [x] T3 — Final functional/contract checks, risk/review assessment and verified Pi skill synchronization; document activation/source-root requirements without overwriting runtime settings. Status: verified and installed; global runtime selectors remain unchanged. Route: delegated verifier, then narrow synchronization.

## Acceptance criteria and checks
1. Academic paths use confirmed metadata.subject with canonical aliases; publisher and doc_status agree. Non-academic layouts remain unchanged.
2. Existing PDF-only reports work. .bib is never copied merely because sources.bib exists.
3. Requested .bib bytes are bound to validation and human final-review evidence. Missing, malformed, changed or unsafe files refuse before publication.
4. Reuse compares the complete requested artifact set; same PDF plus changed .bib needs a new version. Partial versions never count as delivered.
5. Only declared final artifacts enter the delivery tree; existing documents remain untouched.
6. Skills explain roots, subject versus category, .bib opt-in, versioning and user ownership of Git operations.
Use deterministic test-first: observed RED, then GREEN and focused regression. All publication tests use sandbox roots, not real Documents. Final independent checks follow native assessment. PDF rendering is unnecessary for path/configuration-only changes; verify actual sandbox CLI publication/status instead.

## Evidence and progress
- Read-only mapping complete. Existing final-review marker and validation receipt are PDF-bound; bibliography delivery must extend exact-byte evidence rather than indiscriminately copying sources.
- Worktree creation ran the existing post-checkout baseline skill sync to Claude/Codex, skipping tests because this worktree lacks .venv. Pi skills were unaffected. This is not validation evidence; use the shared interpreter.
- T1 worker muoek47d-5-r5c4 resumed after interruption and completed hierarchy behavior in 15 files (+729/-31). Initial RED: ImportError for missing shared API and 5 publisher failures for unsupported subject. Corrective RED for new confirmed courses: 5 failed, 1 passed. GREEN: shared interpreter -m pytest tools/test_report_config.py tools/test_pdf_publication.py tools/test_deliver_report.py tools/test_doc_status_validate_deliver.py tools/test_doc_status_render_cli.py -q: 105 passed; -m pytest tests/skills/ -q: 138 passed; git diff --check: clean.
- Confirmed course slug is the known canonical alias or ASCII normalization of the confirmed name, so newly named courses also get their own folder. Existing invalid configs without subject still fail academic validation. Internal output routing is unchanged.
- T1 rollback boundary: its 15 source/test/skill files, relative to 37dcd9d. No academic rendering required for this path-only unit. Sandbox tests covered Git course roots, hash reuse, gates-before-write, nonacademic layout and doc_status parity.
- T2 worker evidence: RED 29 failed/123 passed before new source writes; GREEN 144 passed for the six targeted runtime modules, 8 passed in tools/test_verify_delivery.py, 144 passed in tests/skills/, git diff --check clean. Sandbox real deliver_report CLI published a PDF/.bib pair and matching doc_status delivery derived done. Option: report.yml deliver_bibliography (strict bool, default false). Both validation.yml and final-review.yml require bibliography_sha256 only when opted in. Set-exact reuse and directory-FD flock protect pair publication on POSIX; failure cleanup owns only this call's files. Outside POSIX only single-writer safety is supported. Bibliography uses existing parser, no new style/DOI rules. Rollback boundary: 24 modified feature files against 37dcd9d.
- Native assess returned risk unassessable because untracked files need explicit declaration; RDD on, candidate outcome unknown. Required plan: writerSelfVerification true, structuralReadbackOnly false, independentVerifier true. Treat as high risk. No review approval or delivery authority claimed.
- Independent verifier: 152 focused runtime tests, 144 skill contracts and 1484 full tools tests passed; diff check clean. Real sandbox CLI delivered v001 PDF/.bib, reused the same pair, and produced v002 after bibliography changes plus refreshed sandbox evidence. Direct delivery derivation was done; full doc_status CLI emitted valid schema but remained research-gated for the deliberately minimal fixture. A complete academic route/PDF rendering was not performed (not applicable to this publication feature).
- Native inspect excluded only untracked task bookkeeping; native review review-153fc19ea4160bed approved candidate sha256:33ef01ec044e1105fbca20a8c6ca78b447511a51093ecb8c6ac704bf3588a917. Exact acknowledgement burned approved authority at revision sha256:aee6d4ff93f95e4d63aacf1e6b75e842638e799af2aec228d650f0dc36d58257. Nonblocking follow-ups only: R2-001..004 readability suggestions and R4-001 resilience warning. No correction opened.
- Installation preflight aborted before writes because the academic installed root was a symlink into ~/dotfiles/ai-stack/pi/skills/academic-report-builder. The backup was never modified. Created a preserved live copy at ~/.pi/gentle-ai/skill-runtime/course-deliverables/academic-report-builder, replaced four reviewed files, and atomically repointed only that installed symlink. Old target remains intact and can restore the prior pointer. Workflow remains a real installed directory; copied deliver/review/validate only and patched intake with the exact .bib hunk, preserving its pre-existing omitted guide_facts paragraph and all other files.
- Installation readback: seven exact copies match source bytes; live intake equals source minus only that pre-existing paragraph. Five other academic files match the original target; original target's four reviewed files still match baseline. Post-writer spot-check: 163 tests passed in tools/test_deliver_report.py, tools/test_final_review_marker.py and the two changed skill contract modules; diff check clean.
- One-off selector proof used the actual shared interpreter, imported report_config from this feature worktree, loaded synthetic YAML through ReportConfig.load(Path), and computed Academicos/fisica-cuantica/proof: PASS. Earlier optional probes used an incorrect interpreter or API argument type; corrected proof passed. REPORT_AUTOMATION_ROOT/PYTHON/CONTENT_ROOT global/session values were not changed. Future execution must select this compatible feature source and dependency-equipped interpreter.
- Source/test/skill work-unit commit 82df3a757bf0839f56238d0c99ca7eb87e09e734 created after explicit user authorization; full tree exactly equals approved e7177e50ba9386f6332d8fc7427ebc88bb600314. No migrations, real-document publication or course repo creation. No failed required check remains; skipped full academic render/route is explicitly out of scope.

## Next step
Complete authorized delivery in course-deliverables-delivery.md. For tomorrow's real reports, use the installed skill with REPORT_AUTOMATION_ROOT pointing to this retained worktree and REPORT_PYTHON to the shared interpreter (REPORT_CONTENT_ROOT remains the production root). Reload skill discovery if required. No PR/merge/main update or legacy migration is authorized; review suggestions remain follow-up work.
