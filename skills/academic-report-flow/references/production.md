# Production - verify, generate, validate, quality gates

Tools enforce quality between Decision 2 and 3: run each, report findings, never fix by silent polishing. Roots and interpreter: `routing.md`.

## Verify (artifact `reports/<wf>/content-check.yml`)

Runs only after `approval` is `done`: the check judges the approved draft.

1. `"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/content_check.py" "$REPORT_CONTENT_ROOT/reports/<work-folder>/" --judge-brief`. Do not pass the drafting conversation to a judge.
2. Give its exact output to two independent read-only judge subagents in parallel with the same brief; they must not coordinate and return the YAML the brief specifies (per criterion `cumple|flojo|falta`).
3. Save the YAML unchanged as `judgments-a.yml` and `judgments-b.yml`; the drafting agent never writes judgments. Run `content_check.py <folder> --judgments judgments-a.yml --judgments judgments-b.yml`.
4. The tool validates both files, adds the mechanical checks (citations resolve; at least 5, or the report's `min_sources:`, eligible sources cited), the strictest verdict wins per criterion (`falta` > `flojo` > `cumple`), and writes `content-check.yml` bound by hash to body, rubric and bib. A stale marker means re-run the independent judges on the current inputs, never reuse old judgments.

When the executor cannot launch subagents, it stops at verify and reports the judges pending; the orchestrator runs the two judges exactly as above (brief verbatim, two independent read-only subagents, YAML saved unchanged) and the executor never stands in for a judge.

The check only reports (per-criterion status, citation problems, confusing paragraphs, figures that serve no criterion). It never rewrites `body.md`; never add judgments for criteria the plan does not name or soften `falta` to `flojo`. Report every finding verbatim and collect literal edit orders (`approval.md`); a recorded `fail` blocks the route (`content_check_failed`) until fixed, and an edited draft stales the marker so the check reruns.

## Generate (artifact: the final PDF under `outputs/<materia>/`)

Runs only when `approval: done` (`approval.yml` exists and its `body_sha256` matches the current `body.md`). Never build before approval is done.

`"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/build_report_auto.py" "$REPORT_CONTENT_ROOT/reports/<work-folder>/"` builds from `report.yml` (including `format:`) plus the approved `body.md`, runs the configured technical validation, and reports the artifact hash and page count. It does not publish, copy or version, and never writes `approval.yml` or claims `VISUAL_PASS`, `HUMAN_REVIEW` or `READY_TO_SUBMIT`. Final PDF/DOCX stay under `outputs/<materia-slug>/`, intermediates in `build/` or `backups/`.

## Validate (`next: validate`, artifact `reports/<wf>/validation.yml`)

Receipt schema `academic.doc-validation/v1`: `artifact_sha256`, `result: pass|fail`, `mode: rdd|fallback`, `gates`, `recorded_at`, `evidence`, optional `reason`, and `bibliography_sha256` only when `report.yml` sets `deliver_bibliography: true`. There is no production writer: the executor records the hashes. Done = `result: pass` and `artifact_sha256` matches the current PDF; `fail` is `blocked` (`validation_failed`); a missing receipt or stale hash stays `pending`.

When `deliver_bibliography: true`, the receipt also records the exact SHA-256 of the declared `.bib`, written only after the applicable checks pass; missing, malformed or stale keeps validate pending and delivery refuses.

Branch: read `gentle-ai review mode status` once, read-only. `on` selects the RDD branch (`mode: rdd`; the native review flow checks and `evidence` is the identifier it returned, never self-issued; no identifier, no `pass`). `off`, an absent binary, non-zero exit, unparsable output or `unknown` selects the fallback, because an unknown state never lowers a gate. Never enable, activate or turn on RDD on the user's behalf. If the review preflight cannot bind `reports/<wf>/**` (for example `intended_untracked_selection_required`), fall through to the fallback and record `reason:`.

Fallback (`mode: fallback`, `evidence: backups/quality_report.md`), in order:
1. `"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/validate_report.py" "$REPORT_CONTENT_ROOT/reports/<work-folder>/"`: `common` is mandatory and PDF output also needs `pdf_layout` (only `--tex-only` skips it).
2. `"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/visual_pdf_auditor.py" "$REPORT_CONTENT_ROOT/outputs/<materia-slug>/<final-pdf>.pdf"`: report and `contact_sheet.png` are `AUDITOR_PRECHECK` evidence only (manual unless `validators: {visual_pdf: true}`).
3. Rendered readback and semantic inspection: headings, paragraphs, captions, bibliography, tables and figure labels present, legible and equivalent to the source.

Gates: both branches enforce the identical gate set `BUILD_PASS`, `VALIDATION_PASS`, `VISUAL_PASS`, `HUMAN_REVIEW`, `READY_TO_SUBMIT`; neither lowers, skips or renames one, or grants one it did not verify on the same immutable artifact. Validation is not approval.

| Gate | Proof |
|---|---|
| `APPROVAL_CURRENT` | `approval.yml` current for the exact `body.md` bytes |
| `BUILD_PASS` / `VALIDATION_PASS` | build completed / validators pass (layout still unproven) |
| `VERSIONED_PDF_PUBLISHED_OR_REUSED` | precondition `APPROVAL_CURRENT`; PDF-only version published or hash-reused; not approval |
| `VISUAL_PASS` | readback plus direct page inspection pass on one immutable artifact |
| `HUMAN_REVIEW` | `final-review.yml` for the same bytes |
| `READY_TO_SUBMIT` | every previous gate passes, artifacts unchanged |

`VISUAL_PASS` ownership: the validate phase executor that performed the direct page-by-page inspection (every page rendered and read back, no blocking defect) records `VISUAL_PASS` in `validation.yml` `gates:` and notes it in the evidence report; a receipt without an inspection never records `VISUAL_PASS`. `READY_TO_SUBMIT` follows once `HUMAN_REVIEW` exists for the same bytes (`deliver_report.py` derives it).  Never write `approval.yml`, `body.md` or `report.yml` here.

## Quality gates (inspection a tool cannot do)

Visible evidence overrides automation: a visible blocking defect fails the artifact even when every script passes. Record the artifact hash and page count first; inspect every contact-sheet page and open every page with diagrams, figures, captions or tables at readable size. After any correction rebuild the whole artifact and rerun everything (never only changed pages); explain material page-count changes.

Blocking defects:
- Academic route only: cover on page 1, body from page 2, UNL logo present.
- Headings without substantial following content (orphan heading: after a heading the same page must fit two lines of body text, a table header plus one data row, or a complete figure); clipped images, overfull boxes, accidental blank pages, pages under 20% meaningful content, half-empty pages from table pagination. `visual_pdf_auditor.py` only warns on orphans; inspect before judging.
- Whitespace: over 40% of the lower page empty without a natural section close. An intentional gap or natural close is approvable only with a recorded visual justification; page-break space, an unsplit table or a page holding an isolated title is a defect. Record every page under 20% content, over 40% lower empty, heading before a page break, or whole table displaced.
- Tables render as real grids (visible rules, distinct header, legible type; never raw Markdown pipes). Remove unneeded columns before compressing; split wide tables (e.g. `Code | Actor | Requirement | Priority` and `Code | Acceptance criterion`). Broken tables repeat the header. With `table_styles: {enabled: true}` every table needs a `<!-- table-style: <key> purpose=... -->` directive; run `tools/check_table_contexts.py <dir>`.
- Type shrunk to fit is a defect; a table that cannot split is a defect unless a split was attempted.
- Figures: lower border clears the footer, terminal nodes complete, no clipped or overlapped node or connector, full caption attached to the right asset. Each diagram models its module's real decisions and visually differentiates user, system, internal module, external service, validation, error, retry and final state. Diagrams that only restate the text, clipped terminal nodes and captions detached from their figure are defects. Reject repeated templates, generic decisions such as `¿Validación correcta?`, flows with no real alternatives, ambiguous arrows.
- Practice reports keep each exercise self-contained (data first, process and evidence after); conclusions never open with formulaic `Se concluye`; validate the rendered IEEE bibliography, not only the `.bib`.
