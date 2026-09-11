# Research phase

Executor: research-workflow
Artifact: `reports/<wf>/research/evidence-matrix.md`

Load this reference only when `doc_status` returns `next: research`. The executor is
`research-workflow`, using its own `references/research-protocol.md`; this skill never
performs research, and `research-workflow` never creates or formats the report.

## Contract

Research exists to close claim coverage the confirmed brief needs and local
`inspected: true` sources do not provide. The executor produces exactly one artifact:
`reports/<wf>/research/evidence-matrix.md`, a claim-level matrix with a stable source
locator, verbatim evidence or an explicit paraphrase note, confidence, limitations,
and eligibility/status per entry. Only `eligible` entries are bibliography-ready;
`lead` entries stay separately visible for follow-up.

The matrix is pre-document evidence, never confirmed document intake: it carries
claims, conflicts, and unresolved questions into the report, and it does not choose
document type, structure, citation style, or prose. Document creation stays with
`academic-report-builder`.

When the confirmed brief needs no external claims, the phase closes without the
matrix by recording `research: skipped` in `report.yml`; that key is the recorded
decision, and it never stands in for an inspected source. Done means a non-empty
`research/evidence-matrix.md`, or `research: skipped` in `report.yml`. Research is
never `blocked`, so an absent matrix without that key leaves the phase `pending`.

## Steps

1. Define the research question, scope, and inclusion/exclusion criteria.
2. Collect, inspect, and assess sources; retain stable locators and provenance.
3. Write the claim-level matrix, separating quotations from paraphrases.
4. Reconcile duplicates, gaps, and contradictions without converting uncertainty
   into fact.
5. Re-run `doc_status` and report the new current phase.

## Never

- Do not invent a source, locator, quotation, date, author, or finding.
- Do not write `report.yml`, `preview.md`, `approval.yml`, or `validation.yml`.
- Do not draft, build, or deliver the document.
