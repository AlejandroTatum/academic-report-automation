---
name: academic-report-flow
description: "Trigger: academic report, exercise/ejercicio, homework/tarea, APE, AA, university report, project documentation, professional or business report, technical document, PDF, DOCX, doc status. Routes source-backed documents from doc_status."
license: Apache-2.0
metadata:
  author: "gentleman-programming"
  version: "3.0"
  scope: "full-report-flow"
---

## Activation Contract

Use for creating, adapting, reviewing, exporting, resuming, or advancing a structured academic, project, professional, business, technical, PDF, or DOCX document. PDF or DOCX is a format signal only. The user chooses the document type; never infer it from format, prompt, files, or history.

Entry rule: when a work folder exists, run `doc_status.py` first on `$REPORT_CONTENT_ROOT/reports/<work-folder>/` and load only the current phase reference; without a work folder, run the standalone full route (`references/intake.md`), then the `next` token. Loop: `doc_status -> next -> reference -> delegate -> re-run`. See `references/routing-loop.md`.

### Mandatory Intake

Load `references/intake.md` for the `intake` phase and on every standalone run. It owns the `report.yml` record (`route:`, `output:`, `template:`, top-level `cover:`, `metadata:` fields) and the content-first minimum. The Document Contract is a data record and does not authorize generation. The single confirmation gate is post-preview and lives in `academic-report-flow/references/approval.md`; intake never asks for approval.

### Prohibition On Inferring Document Type

Recommend at most one type with a reason, but do not select it. Ambiguity stops the run; there is no default document type or academic fallback.

## Hard Rules

- Route exclusively from the `next` token; load only that phase's reference.
- Require rubric TDD checks in the plan before drafting; the draft turns them green.
- Use an independent judge for semantic verification; the drafter never grades itself.
- Require verified sources before research is finished.
- Apply batched edit orders verbatim before seeking re-approval.
- Present the human block verbatim and every human gate losslessly; never proceed on silence.
- Never build before approval is `done`; never present the approval gate before `draft` is `done`.
- Validate inputs, source binding, intermediate output, export, and final PDF/DOCX; stop at the earliest failed gate.
- Publish only the confirmed PDF output at `~/Documents/<automatic-category>/<document-slug>/<document-slug>-vNNN.pdf`, and only when a current `APPROVAL_CURRENT` marker exists; on the academic route the confirmed subject's canonical slug scopes the tree one level deeper (`~/Documents/Academicos/<subject-slug>/<document-slug>/`), and a `.bib` joins the versioned pair only when `deliver_bibliography: true` declares it a final artifact. Category comes from the confirmed route and slug from confirmed title. That folder contains versioned final artifacts only. Technical validation alone never triggers publication, and publication is not approval. See `references/clean-delivery.md`.
- No script, validator, or auditor ever grants `VISUAL_PASS`. `visual_pdf_auditor.py` PASS is only `AUDITOR_PRECHECK` evidence.
- Only independent semantic inspection of the assembled report may grant report-level `VISUAL_PASS`; human review after immutable hashes is required for `READY_TO_SUBMIT`.
- Never ghostwrite a final submission. Preserve privacy, provenance, citations, and consent boundaries.
- Use `academic-visual-builder` for figures, then inspect them again in the assembled report. Confirm the visual direction changes hierarchy and composition, not only decoration.
- When supplied a research-workflow evidence package, preserve claim-to-source traceability, limitations, and unresolved questions. Do not treat the package as confirmed document intake; this skill still owns intake, citation-style confirmation, composition, and document creation.
- Rendering defaults (template, cover, section numbering, list of figures) are derived from the confirmed `route:`; an explicitly written `report.yml` option always wins. See `references/document-routing.md`.
- Route A only: load `references/unl-shell.md` and matching `references/profiles/`; default to IEEE unless the teacher requires another style.

## Decision Gates

| Situation | Action |
|---|---|
| `next` names a phase | Load its reference and run its executor (this skill, `research-workflow`, or a judge). |
| Intake data missing or ambiguous | Stop and ask; recording the contract is never approval. |
| Approval marker absent or stale | Block generation and publication; request the single post-preview confirmation. |
| `next: approval` / `next: review` | Present the human gate; write `approval.yml` / `final-review.yml` only on an explicit answer. |
| Type ambiguous or non-academic | Recommend/resolve a route; never fall back to Route A. |
| Template or rubric confirmed | Mirror its sections, formatting, and criteria. |
| Visual-heavy section | Build and validate figures with `academic-visual-builder`, then inspect the assembled report. |
| Unsupported backend/output or unknown executor | Stop; never substitute silently. |
| Script PASS contradicts visible evidence | Record `VISUAL_FAIL`, correct, rebuild, and repeat all gates. |
| Inspection incomplete | Return `REVIEW_REQUIRED`, without `VISUAL_PASS`; a prior automatic PDF publication stays technical-copy status only. |
| `next: done` | Report completion; route no further. |

## Execution Steps

1. Run `doc_status.py`; present the human block verbatim; read `next`.
2. Load `automation-contract.md` and the one phase reference; run its executor.
3. Bind sections, claims, citations, tables, and figures to the confirmed contract.
4. Build with the canonical commands; record immutable artifact hash and page count.
5. Retain validator/auditor outputs as precheck evidence; inspect every contact-sheet page and applicable full-size pages directly.
6. After any correction, rebuild, rerun validators/readback/inspection, and explain material changes.
7. Confirm the single artifact, re-run `doc_status`; report `VISUAL_PASS` only after semantic inspection and `HUMAN_REVIEW` against hashes before `READY_TO_SUBMIT`.

## Output Contract

Return the verbatim human block, the `academic.doc-status/v1` block, the routed token, the executor, and the single artifact produced. Include the Document Contract, route, gates, hashes, page-count delta, readback and inspection evidence, defects, and review assumptions. Return `READY_TO_SUBMIT` only after approval.

## References

- `references/routing-loop.md` — phase/executor table, status template, content-first rules.
- `references/intake.md` — the single intake source: content-first minimum, full-route confirmations, `report.yml`.
- `references/research.md` — five-source IEEE gate (`sources.bib`).
- `references/plan.md` — rubric as machine-checkable plan (`rubric.yml`).
- `references/draft.md` — full draft (`body.md`).
- `references/approval.md` — human gate and literal edit-order loop.
- `references/verify.md` — report-only content check.
- `references/format.md` — single APE / AA / libre question.
- `references/generate.md` — approved build and PDF generation.
- `references/validate.md` — RDD or fallback validation.
- `references/review.md` — final human review gate.
- `references/deliver.md` — versioned publication.
- `references/document-routing.md`, `automation-contract.md`, `quality-gates.md`, `clean-delivery.md`, `visual-directions.md` — full-route contracts.
- `references/unl-shell.md` and `references/profiles/` — Route A only.
- `templates/academic_format.yml` — format and validator contract.
