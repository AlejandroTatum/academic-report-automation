# Production - verify, generate, validate, quality gates

Tools enforce quality between Decisions 2 and 3: run each, report findings, never polish silently. Roots and interpreter: `routing.md`.

## Verify (artifact `reports/<wf>/content-check.yml`)

Runs only after `approval` is `done`, over the approved draft.

1. `"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/content_check.py" "$REPORT_CONTENT_ROOT/reports/<work-folder>/" --verify-brief`. Do not pass the drafting conversation to the verifier.
2. Give its exact output to ONE independent read-only verifier subagent. It never scores: it returns the requirement -> evidence matrix YAML the brief specifies (per rubric criterion, one or more `requirement` entries with `status: found|missing`, `location`, and `evidence`, an exact quote from `body.md`, required when `found`; plus `unmapped_paragraphs` and `findings`). Evidence it cannot quote is `missing`, never "seems to comply".
3. Save the YAML unchanged as `verification.yml`; the drafting agent never writes verification.yml. Run `content_check.py <folder> --verification verification.yml`.
4. The tool validates the file; a `found` requirement whose exact quote is not in `body.md` (whitespace-normalized) is downgraded to `missing` with a finding; a criterion is `cumple` when all its requirements are found, `falta` otherwise. It adds the mechanical checks (citations resolve; at least 5, or the report's `min_sources:`, eligible sources cited, or with `uncited_bibliography: true` at least 1 bib entry and no citation required; `links_resolve`: every http(s) URL in the body is opened, an HTTP error fails, a timeout or DNS failure only warns) and writes `content-check.yml` bound by hash to body, rubric, bib and guide. A stale marker means re-run the verifier on current inputs; a verification is reused only when the body change is markup-only (same `body_text_sha256`, same rubric). Legacy markers with `judges:` stay valid.
5. Re-verify after an edit: run step 1 with `--since verification.yml` (the previous file). The brief lists only the criteria whose mapped section changed for re-check and embeds the requirements of unchanged sections to copy verbatim; a rubric change forces a full verify. Then continue with steps 2-4 as usual.

When the executor cannot launch subagents, it stops at verify and reports the verifier pending; the orchestrator runs the verifier exactly as above (brief verbatim, one independent read-only subagent, YAML saved unchanged) and the executor never stands in for the verifier.

The check only reports (per-criterion `cumple|falta`, the requirement matrix with missing items, citation and link problems, unmapped paragraphs as deletion candidates). It never rewrites `body.md`; never add requirements for criteria the plan does not name. Report every finding verbatim and collect literal edit orders (`approval.md`); unmapped paragraphs are proposed for deletion, never added to. A recorded `fail` blocks the route (`content_check_failed`) until fixed; an edited draft stales the marker and reruns the check.

## Generate (artifact: the final PDF under `outputs/<materia>/`)

Runs only when `approval: done` (`approval.yml` exists and its `body_sha256` matches the current `body.md`). Never build before approval is done.

`"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/build_report_auto.py" "$REPORT_CONTENT_ROOT/reports/<work-folder>/"` builds from `report.yml` (including `format:`) plus the approved `body.md`, runs the configured technical validation, and reports the artifact hash and page count. It does not publish, copy or version, and never writes `approval.yml` or claims `VISUAL_PASS`, `HUMAN_REVIEW` or `READY_TO_SUBMIT`. Final PDF/DOCX stay under `outputs/<materia-slug>/`, intermediates in `build/` or `backups/`.

Optional `figure_placement: here` in `report.yml` pins every figure where it appears in `body.md` (LaTeX `[H]`) instead of letting it float to the end of the section; the default `float` keeps today's output, and any other value is rejected.

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
- Headings without substantial following content (orphan heading: after a heading the same page must fit two lines of body text, a table header plus one data row, or a complete figure); clipped images, overfull boxes, accidental blank pages, pages under 20% meaningful content, half-empty pages from table pagination. `visual_pdf_auditor.py` only warns on orphans; inspect before deciding.
- Whitespace: over 40% of the lower page empty without a natural section close. An intentional gap or natural close is approvable only with a recorded visual justification; page-break space, an unsplit table or a page holding an isolated title is a defect. Record every page under 20% content, over 40% lower empty, heading before a page break, or whole table displaced.
- Tables render as real grids (visible rules, distinct header, legible type; never raw Markdown pipes). Remove unneeded columns before compressing; split wide tables (e.g. `Code | Actor | Requirement | Priority` and `Code | Acceptance criterion`). Broken tables repeat the header. With `table_styles: {enabled: true}` every table needs a `<!-- table-style: <key> purpose=... -->` directive; run `tools/check_table_contexts.py <dir>`.
- Type shrunk to fit is a defect; a table that cannot split is a defect unless a split was attempted.
- Figures: lower border clears the footer, terminal nodes complete, no clipped or overlapped node or connector, full caption attached to the right asset. Each diagram models its module's real decisions and visually differentiates user, system, internal module, external service, validation, error, retry and final state. Diagrams that only restate the text, clipped terminal nodes and captions detached from their figure are defects. Reject repeated templates, generic decisions such as `¿Validación correcta?`, flows with no real alternatives, ambiguous arrows.
- Practice reports keep each exercise self-contained (data first, process and evidence after); conclusions never open with formulaic `Se concluye`; validate the rendered bibliography (IEEE, or APA with `citation_style: apa`), not only the `.bib`.
