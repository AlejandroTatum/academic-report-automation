# New report flow (content first, rubric driven)

Feature: `new-report-flow`. Branch: `feat/new-report-flow` (from `main` @ `cf3cc28`).
Worktree: `academic-report-automation-worktrees/pi`.
Engram mirror: topic `odd/new-report-flow/tasks`, project `academic-report-automation`.

## Objective
Replace the format-first document workflow with the user's content-first flow:
the AI drafts content against the teacher's rubric, the user reviews it with literal
edit orders, a hard content check reports findings, and only then the format
(APE, AA or libre, always IEEE) is applied, built, validated, and handed back to the
user for a final review before delivery.

## Problem / why
The current route asks for every formatting detail before a single line is written,
lets research be skipped, and has no notion of the rubric. The teachers require at
least five book or paper sources with a per-document `.bib`, IEEE citations, and
human-sounding prose. Decided with the user on 2026-09-28 (flow v3 diagram).

## Target route
`intake > research > plan > draft > approval > verify > format > generate > validate > review > deliver`

| phase | artifact | done when |
|---|---|---|
| intake | `report.yml` | exists, `title` and `student` present, guide recorded |
| research | `sources.bib` | >= 5 book/paper entries (`research: skipped` removed) |
| plan | `rubric.yml` | valid schema, >= 1 criterion, each mapped to a section |
| draft | `body.md` | present and non-empty |
| approval | `approval.yml` | explicit user approval bound to `body.md` bytes |
| verify | `content-check.yml` | `result: pass` bound to current `body.md` bytes |
| format | `report.yml` `format:` | `ape`, `aa` or `libre` + that format's metadata |
| generate | final PDF | newer than approval |
| validate | `validation.yml` | pass bound to PDF bytes (RDD or fallback) |
| review | `final-review.yml` | explicit user OK bound to PDF bytes |
| deliver | `<slug>-vNNN.pdf` | published copy hash-equal |

## Design decisions
- `preview` phase removed: the draft is the only thing the user reviews.
- A stale approval (body edited after approval) routes back to `approval` as
  `pending`, not `blocked`: editing after approval is the normal review loop.
  Malformed markers stay `blocked`.
- The review loop applies the user's edit orders verbatim; the AI never polishes
  user-authored text. The content check reports findings and never rewrites.
- Source eligibility = BibTeX types `book`, `inbook`, `incollection`, `article`,
  `inproceedings`, `conference`, `phdthesis`, `mastersthesis`, `techreport`.
- `format:` is orthogonal to the internal `route:`; `ape` and `aa` map to the
  academic route, `libre` to a user-specified spec (`format_spec:`) on the plain
  template. Every format uses biblatex `style=ieee`.
- APE = LaTeX replica of the teacher DOCX (no cover, identification table,
  10 fixed sections, Montserrat-like sans, header logo + "FEIRNNR - Carrera de
  Computación"), delivered as PDF.

## Scope / constraints
- Runner: `/home/alejo/devwork/.projects/apps/academic-report-automation/.venv/bin/python -m pytest tools/ tests/`.
- Test-first: observed RED, GREEN, refactor, per task.
- One work-unit commit per task (Conventional Commits, no AI attribution).
- Out of scope: existing documents under `reports/`, other skills' internals.

## Tasks
- [x] T1 Markers: approval binds `body.md` only (drop preview), stale -> pending;
      new `final-review.yml` marker bound to the PDF; deliver/publish require it.
- [x] T2 Research gate: >= 5 eligible book/paper entries in `sources.bib`;
      remove `research: skipped`.
- [x] T3 Rubric plan + content check: `rubric.yml` schema/validator and
      `content-check.yml` validator (per-criterion cumple/flojo/falta + where,
      mechanical checks: citations resolve, >= 5 eligible sources cited).
- [ ] T4 Format choice + APE template: `format: ape|aa|libre` in `report.yml`,
      per-format required metadata, template mapping, `templates/ape-report.tex`.
- [ ] T5 `doc_status` new 11-phase route, handlers, guidance, tests.
- [ ] T6 Rewrite `skills/document-workflow` (SKILL.md + references), contract
      tests, skill sync, flow diagram under `docs/`.

## Evidence
(commit ids recorded per task)
- T1: RED 19 focused failures + missing `final_review_marker`; GREEN `pytest tools/ tests/ -q`
  1222 passed (baseline 1208). Schema kept at `academic.doc-approval/v1`.
  Commit `78ed109`. RDD lineage `review-d6e32b187ef0cee2`: approved (high tier,
  4 lenses), acknowledged/burned. Advisory follow-ups (non-blocking):
  final-review marker has no producer yet (T5/T6 owns it); non-mapping YAML and
  missing-PDF cases in `final_review_marker.py`; gate ownership wording in
  `deliver_report.py`; hidden validated-PDF coupling in `test_pdf_publication.py`.
- T2: RED `source_count` missing + 27 focused failures; GREEN `pytest tools/ tests/ -q`
  1236 passed. `research: skipped` and matrix-only no longer complete research.
  Residual skip prose in `intake.md`, `draft.md`, `preview.md` left for T6.
  Commits `3744470` + correction `ccae95b` (non-UTF-8 `.bib` crashed doc_status;
  now reported as pending). RDD lineage `review-be9fa277b00c6f49`: correction
  validated, approved, acknowledged/burned. Advisory follow-ups: bib regex may count
  nested `@` entries inside field values; `research.md` wording; guidance at
  `doc_status.py:365`.
- T3: RED collection errors (`rubric_plan`, `content_check` missing); GREEN
  `pytest tools/ tests/ -q` 1316 passed (+77). `content_check.py` derives pass/fail
  itself (all criteria `cumple` + mechanical checks) and never writes `body.md`.

## Scope notes
- The AI-detector limit (<= 20 %) applies only to the course "Simulación"; the flow
  has no percentage gate for any course (user clarification 2026-09-28).
