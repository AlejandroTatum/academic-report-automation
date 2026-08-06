---
name: academic-report-builder
description: "Trigger: academic report, university report, project documentation, professional or business report, technical document, PDF, DOCX. Builds source-backed documents with intake, routing, and rendered validation."
license: Apache-2.0
metadata:
  author: "gentleman-programming"
  version: "2.0"
  scope: "full-report-builder"
---

## Activation Contract

Use when Alejandro needs to create, adapt, review, or export a structured document: university academic work, project documentation, professional or business reports, technical documents, or any PDF/DOCX deliverable with templates, instructions, or rubrics.

This skill is document-type agnostic. The document type is a user decision, never a skill inference.

## Mandatory Intake

Run the intake in `references/document-intake.md` on **every** execution, before designing, drafting, or generating anything — even when the prompt appears to already contain the answers.

| # | Confirmation | Must be confirmed |
| --- | --- | --- |
| 1 | Document type (academic / project doc / professional / technical / other) | Always |
| 2 | Audience **and** purpose, as two independent fields | Always |
| 3 | Template, institutional format, or visual identity to respect | Always |
| 4 | Delivery format: PDF, DOCX, or both | Always |
| 5 | Visual direction: Sober, Institutional, Technical, Executive, Custom | Always |

Render the Document Contract block and wait for explicit confirmation. Generation begins only after that block is confirmed.

## Prohibition On Inferring Document Type

- Never infer, assume, or auto-select the document type from the prompt, the repository, the file names, or past work.
- You MAY recommend one option with a short reason; you MUST NOT proceed on it until the user picks.
- A request for PDF or DOCX is a format signal only. It never implies academic work, a university shell, or an institutional cover.
- There is no default document type and no fallback profile. Ambiguity stops the run and returns the intake question.

## Routing

Resolve one route from Confirmation 1, then load only that route's references. Full definitions in `references/document-routing.md`.

| Route | Document type | Loads |
| --- | --- | --- |
| A | University academic work | `references/unl-shell.md`, `references/profiles/`, `references/quality-gates.md` |
| B | Project documentation | `references/document-routing.md`, `references/visual-directions.md`, `references/quality-gates.md` |
| C | Professional/business report | `references/document-routing.md`, `references/visual-directions.md`, `references/quality-gates.md` |
| D | Technical document | `references/document-routing.md`, `references/visual-directions.md`, `references/quality-gates.md` |
| E | Other | Contract built with the user; never a silent fallback to Route A |

`references/unl-shell.md` and `references/profiles/` load on Route A only.

## Hard Rules

- Do not ghostwrite a final submission or declare `READY_TO_SUBMIT` without Alejandro's explicit review bound to immutable artifact hashes.
- Validate inputs, intermediate document, export, and final PDF/DOCX. Stop and correct the earliest failed gate.
- Treat validator and auditor output as evidence, never authority. Neither `validate_report.py` nor `visual_pdf_auditor.py` proves rendered correctness or grants `VISUAL_PASS`. No script, validator, or auditor ever grants `VISUAL_PASS`.
- Do not project `VISUAL_PASS`, claim visual validation, or return final delivery paths until an independent semantic inspection of the complete contact sheet and applicable full-size rendered pages passes `references/quality-gates.md`.
- Read back rendered content, not only source. Confirm headings, prose, captions, tables, figures, labels, and bibliography retained their intended semantics.
- After any content, layout, renderer, or asset correction, rebuild the complete artifact and rerun validators, readback, and semantic visual inspection. Compare page count and pagination with the previous build and explain every material change.
- Own intake, prose, source/citation binding, assembly, readiness gates, human review, and final export. Delegate figure specs/rendering/manifest checks to `academic-visual-builder`, then inspect figures again in the assembled report.
- Preserve provenance and privacy. Admit sources before claims, redact secrets, keep local-only content local, and require scoped consent before external upload.
- The confirmed visual direction must materially change typography, composition, tables, charts, density, and hierarchy. It is never a decorative label.

### Academic Route Only

- Preserve the UNL shell: page-one cover, logo, metadata, required header/footer, and body from page 2.
- Load any matching `references/profiles/` teacher/course profile before generation.
- Default to IEEE citations unless the teacher requires another style; validate the rendered bibliography.
- Apply the academic cover, teacher/subject/parallel/period metadata, rubric alignment, and institutional footer.

## Decision Gates

| Situation | Action |
| --- | --- |
| Intake not confirmed | Stop. Ask the five confirmations and render the Document Contract. |
| Prompt already "contains" the answers | Still confirm. Restate them as a proposal, never as a decision. |
| Document type ambiguous | Recommend one, do not select it. Never fall back to the academic route. |
| Non-academic route | Never load `unl-shell.md` or `references/profiles/`. |
| Instructions only, academic route | Mirror the assignment wording; use the matching profile. |
| Template or rubric confirmed | Mirror required sections, formatting, and grading criteria. |
| Template mentioned but unconfirmed | Treat it as not applicable. |
| Visual-heavy section | Use `academic-visual-builder`, then inspect the assembled report independently. |
| Word required | Use DOCX; otherwise honor the confirmed delivery format. |
| Unsupported backend/output | Stop at capability preflight; never substitute silently. |
| Script PASS contradicts rendered evidence | Record `VISUAL_FAIL`; correct and rebuild. Visible evidence prevails. |
| Inspection incomplete | Report `REVIEW_REQUIRED` without `VISUAL_PASS`, validation claims, or final paths. |

## Execution Steps

1. Load `references/automation-contract.md`, `references/document-intake.md`, `references/document-routing.md`, and `references/quality-gates.md`. Do not load route-specific references yet.
2. Run the intake, render and confirm the Document Contract, resolve the route, and load ONLY the matching route's references.
3. Derive required sections from the confirmed route and contract; bind content, tables, and figures to that structure.
4. Research with provenance and bind each claim to a source and citation entry.
5. Draft assistively while separating metadata, content, layout, assets, and citation notes.
6. Run the canonical build and validators from the automation contract. Record artifact hash and page count.
7. Open and inspect every page in `contact_sheet.png` directly. Open every suspected page and every page containing diagrams, figures, captions, or tables at readable size; perform rendered-content readback and every applicable quality check.
8. If any visible check fails, record `VISUAL_FAIL` even if scripts report PASS or zero warnings. Correct the earliest invalid stage, rebuild, and repeat all gates on the complete artifact.
9. Report `REVIEW_REQUIRED` with actual gate states. Only after Alejandro approves the reviewed immutable artifacts may you report `READY_TO_SUBMIT`.

## Output Contract

Return the confirmed Document Contract and resolved route, each gate separately, artifact hash, page-count delta and explanation, rendered-readback result, direct-inspection evidence, defects, sources/citation status, privacy status, visual manifest status, and assumptions for review. Return final output paths only after semantic inspection passes; before that, identify working artifacts only. Never call a legacy build `READY_TO_SUBMIT`.

## References

- `references/document-intake.md` — the five mandatory confirmations and the Document Contract block.
- `references/document-routing.md` — the five routes with recommended sections, forbidden sections, format sources, and reading priorities.
- `references/visual-directions.md` — operational meaning of each visual direction.
- `references/automation-contract.md` — canonical root, commands, routing, pipeline integration, output placement, and readiness receipts.
- `references/quality-gates.md` — mandatory rendered readback, semantic inspection, whitespace, table, diagram, contradiction, and regression gates.
- `templates/academic_format.yml` — format and validator contract.
- `references/unl-shell.md` — UNL shell and visual profile. Route A only.
- `references/profiles/` — teacher/course preferences and alignment rules. Route A only.
