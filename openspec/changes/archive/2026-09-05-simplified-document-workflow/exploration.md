# Exploration — simplified-document-workflow

Phase: explore (sdd-new cold-start). Store: openspec. Scope: planning only; no proposal/spec/design/tasks authored here.

## 1. Existing capabilities to preserve (verified in worktree)

- Canonical pipeline: `tools/build_report_auto.py` — report folder (`report.yml` + `body.md` + `sources.bib`) → backend builder (`build_latex_report.py` / `build_docx_report.py`; visual = validate-only) → `validate_report.py` gates → hash-checked publication via `publish_pdf.py` (`~/Documents/<category>/<slug>/vNNN.pdf`, category from route). Automatic publication is a technically validated copy, never human-approved final delivery. Per `quality-gates.md`/SKILL.md: report-level `VISUAL_PASS` is granted only by independent semantic inspection of the assembled report on the same immutable artifact (never by a script, validator, or auditor — auditor PASS is `AUDITOR_PRECHECK` only); `HUMAN_REVIEW` recorded against immutable hashes is the separate prerequisite for `READY_TO_SUBMIT`; incomplete inspection reports `REVIEW_REQUIRED` without visual approval.
- Preview pipeline: `tools/build_report.py` (HTML/WeasyPrint, single Markdown, no report.yml/bibliography). Not interchangeable; documented in README.
- Route system (`tools/report_config.py`): `route:` a–e → academic/project/business/technical/other; only academic requires `subject`/`teacher` (`ROUTE_REQUIRED_METADATA`); unknown route = hard error (no silent fallback); academic-only metadata warns on other routes; `PUBLICATION_CATEGORIES` derives delivery category from route.
- Backend selection: `LATEX_TYPES`/`VISUAL_TYPES`/`DOCX_TYPES` + explicit `backend:` override.
- Output routing: `tools/output_router.py` publishes finals to `outputs/<subject>/` under CONTENT_ROOT; `_` prefix = scratch (publication only); `publish_global` override; clean-outputs contract.
- Source library: `tools/source_library.py` — CONTENT_ROOT/academic-sources manifest; source types include `rubric`, `teacher_note`, `template`, `previous_work`; OFFICIAL_COURSES + keyword COURSE_RULES. This is the existing substrate for consigna/rubric/config reuse.
- Validation gates: `tools/validate_report.py` (common/ieee/pdf_layout/latex/latex_log/visual/visual_pdf/docx; quantified overfull thresholds; `visual_pdf_auditor` precheck-only integration).
- Skills (source of truth under `skills/`, synced outward): academic-report-builder (intake, routing, quality gates, clean delivery, Route-A-only unl-shell/profiles), academic-visual-builder, research-workflow (claim-level evidence, eligibility `eligible` vs `lead`, bibliography handoff boundary).
- Templates/assets: `templates/unl-report.tex`, `plain-report.tex` (non-institutional), `chamba-overleaf.tex`, `ensayo_unl.{md,css}`, `academic_format.yml`; UNL logos/backgrounds under `assets/`. Non-academic routes already have a template (`plain-report.tex`) — no new assets required by scope.

## 2. Visible journey mapped to existing pieces

consigna/idea → intake Confirmations 1–5 (document-intake.md) → missing consequential clarifications (adaptive) → research if needed (research-workflow skill + source_library corpus) → route resolution written to `report.yml` → `build_report_auto.py` build + gates → semantic/rendered review (auditor precheck + independent semantic inspection granting `VISUAL_PASS`; `HUMAN_REVIEW` against hashes as the `READY_TO_SUBMIT` prerequisite) → clean delivery (publish_pdf + output_router). Every stage exists; nothing orchestrates them as one adaptive flow, and the research stage has no conditional trigger.

## 3. Contradiction map (confirmed scope vs current contracts)

1. Adaptive intake vs mandatory re-asking: `document-intake.md` opens with "Run this intake on **every** execution… even when the prompt appears to already contain the answers". `tests/skills/test_report_builder_routing.py::test_confirmation_is_required_on_every_execution` asserts the literal strings "every execution|every run" and "even when the prompt appears to already contain". The confirmed scope (reuse supplied consigna/rubric/config; ask only missing consequential questions) contradicts both. Fixing this requires amending the reference wording AND this static test together — `scripts/sync_skills.sh` gates sync on `tests/skills/`, so tests are the enforcement point.
2. "No additional permanent questions may be introduced into this intake without explicit approval" — grillme-style questioning must stay within the five confirmations or be explicitly approved; missing-question logic must derive from supplied inputs, not from new permanent questions.
3. Existing routing/types must not be removed — confirmed; five-route table and backend sets stay intact. Non-exclusivity is already supported by routes B–E and `plain-report.tex`; the gap is intake behavior, not route existence.

## 4. Research trigger — current state

No conditional research trigger exists anywhere. research-workflow triggers on explicit research requests; academic-report-builder only says "when supplied a research-workflow evidence package…". Nothing decides "research needed". Eligibility rules (`inspected: true` → eligible; else `lead`) exist only as prose + static text assertions.

## 5. End-to-end validation gaps

- `tests/skills/` are static-text assertions over skill markdown. `test_research_workflow_contract.py` has exactly 7 test functions, all inspecting static text — matching the parent's "seven tests inspect static text" for the research pipeline; no execution-level validation of the evidence handoff exists.
- `tests/skills/conversation-cases.md` documents intake conversation cases as prose; not automated.
- No test executes the journey (consigna → clarifications → research → build → review → delivery). Delivery/publication behavior IS execution-tested (`test_pdf_publication.py`, `test_verify_delivery.py`, `test_output_location_guard.py`), so the gap is the intake/research stages, not delivery.

## 6. Smallest reviewable slices (recommendation for proposal)

- Slice 1 (skills+tests only): adaptive intake — amend `document-intake.md` ("reuse supplied consigna/rubric/config; ask only missing consequential confirmations; render one Document Contract; single confirmation before generation") and the matching SKILL.md wording; update `test_confirmation_is_required_on_every_execution` and adjacent assertions to enforce the adaptive rule; add conversation cases. ~small diff, pure docs+tests, reviewable.
- Slice 2 (skills+tests only): conditional research trigger — define trigger criteria (research only when claims required by the confirmed route/rubric are not covered by local inspected sources) in `document-intake.md` + research-workflow references; add contract tests.
- Slice 3 (optional, needs parent decision): execution-level validation — a pytest that runs the evidence handoff over fixture files (no network), or a thin orchestrator. Only if code changes are declared in scope.

## 7. Affected files (exact)

Slice 1–2: `skills/academic-report-builder/SKILL.md`, `skills/academic-report-builder/references/document-intake.md`, `skills/research-workflow/SKILL.md`, `skills/research-workflow/references/research-protocol.md`, `tests/skills/test_report_builder_routing.py`, `tests/skills/test_research_workflow_contract.py`, `tests/skills/conversation-cases.md`.
Must NOT touch: `scripts/sync_skills.sh` + `tests/skills/test_sync_skills.py` (uncommitted sync fix — preserve), `templates/`, `assets/`, `tools/` routing/build/validate code (routes/types/backends unchanged).

## 8. Confirmed product choices (settled — do not re-ask)

University-first not exclusive; preserve all assets/templates/profiles; no university branding on non-academic documents; adaptive grillme intake integrated into existing builder; one clear confirmation before generation; research only when needed; preserve provenance/consent and publication-vs-submission distinction; preserve existing delivery behavior; keep existing routing/types.

## 9. Genuine unresolved decisions (for parent/user)

1. Skills-only vs tool-code change: scope says "integrated into existing builder" — Slice 1–2 need zero Python; Slice 3 adds code. Which is in scope?
2. Who evaluates the research trigger: agent judgment at intake (skills-only) vs a declarative field in `report.yml` (code change). No precedent in repo.

Settled by confirmed scope (not a decision point): the single Document Contract confirmation gate is preserved — adaptivity changes only data gathering (ask only missing consequential questions), never the one-confirmation-before-generation gate.

## 10. External SDD research value

Low. All needed context is in-repo; behavior is already specified by confirmed scope. External research would add value only for adaptive-questioning prior art, which is not blocking. Not recommended before proposal; parent may offer it after exploration.
