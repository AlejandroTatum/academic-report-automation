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

Use for creating, adapting, reviewing, or exporting a structured academic,
project, professional, business, technical, PDF, or DOCX document. PDF or DOCX is a format signal only. The user chooses the document type; never infer it from
format, prompt, files, or history.

### Mandatory Intake

Load `references/document-intake.md` on every execution. Confirm document type,
audience, purpose, template/identity, delivery format, and visual direction.
Render the Document Contract and wait for explicit confirmation before generation.

### Prohibition On Inferring Document Type

Recommend at most one type with a reason, but do not select it. Ambiguity stops
the run; there is no default document type or academic fallback.

## Hard Rules

- Validate inputs, source binding, intermediate output, export, and final PDF/DOCX; stop at the earliest failed gate.
- No script, validator, or auditor ever grants `VISUAL_PASS`. `visual_pdf_auditor.py` PASS is only `AUDITOR_PRECHECK` evidence.
- Only independent semantic inspection of the assembled report may grant report-level `VISUAL_PASS`; human review after immutable hashes is required for `READY_TO_SUBMIT`.
- Never ghostwrite a final submission or expose final paths before semantic inspection and approval. Preserve privacy, provenance, citations, and consent boundaries.
- Use `academic-visual-builder` for figures, then inspect them again in the assembled report. Confirm the visual direction changes hierarchy and composition, not only decoration.

### Academic Route Only

Load `references/unl-shell.md` and matching `references/profiles/` only for Route A.
Preserve the cover/body boundary, academic metadata, institutional shell, rubric,
and required citation style. Default to IEEE unless the teacher requires another
style, and validate the rendered bibliography.

## Decision Gates

| Situation | Action |
|---|---|
| Intake or confirmation missing | Stop and ask; render the contract. |
| Type ambiguous or non-academic | Recommend/resolve a route; never fall back to Route A. |
| Template or rubric confirmed | Mirror its sections, formatting, and criteria. |
| Visual-heavy section | Build and validate figures, then inspect the assembled report. |
| Unsupported backend/output | Stop; never substitute silently. |
| Script PASS contradicts visible evidence | Record `VISUAL_FAIL`, correct, rebuild, and repeat all gates. |
| Inspection incomplete | Return `REVIEW_REQUIRED`, without `VISUAL_PASS` or final paths. |

## Execution Steps

1. Load `automation-contract.md`, `document-intake.md`, `document-routing.md`, and `quality-gates.md`; run and confirm intake, then load only the resolved route references.
2. Bind sections, claims, citations, tables, and figures to the confirmed contract and preserve provenance.
3. Build with the canonical commands; record immutable artifact hash and page count.
4. Retain validator/auditor outputs as precheck evidence. Read back rendered content and inspect every contact-sheet page plus applicable full-size pages directly.
5. After any correction, rebuild the complete artifact, rerun validators/readback/inspection, compare pagination, and explain material changes.
6. Report `VISUAL_PASS` only after semantic inspection; record `HUMAN_REVIEW` against hashes before `READY_TO_SUBMIT`.

## Output Contract

Return the confirmed Document Contract, route, each gate, hashes, page-count delta,
readback and direct-inspection evidence, defects, source/citation, privacy, visual
manifest, and review assumptions. Return final paths only after approval.

## References

- `references/document-intake.md` — mandatory confirmations and contract block.
- `references/document-routing.md` — routes and route-specific loading.
- `references/automation-contract.md` — canonical commands, evidence gates, and readiness receipts.
- `references/quality-gates.md` — rendered readback and semantic inspection rules.
- `templates/academic_format.yml` — format and validator contract.
- `references/unl-shell.md` and `references/profiles/` — Route A only.
