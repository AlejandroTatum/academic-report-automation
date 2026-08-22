---
name: research-workflow
description: "Trigger: research, literature review, source research, evidence gathering, evidence matrix. Produces traceable claim-level evidence packages for academic reports."
license: Apache-2.0
metadata:
  author: "gentleman-programming"
  version: "1.0"
  scope: "research-evidence-handoff"
---

## Activation Contract

Use for source research, literature review, evidence gathering, or validating claims before an academic report is built. Produce a traceable evidence package for `academic-report-builder`; this skill does not create, format, export, or deliver a report.

## Hard Rules

- Separate source facts, supported inferences, and unresolved questions. Never invent a source, locator, quotation, date, author, or finding.
- Record claim-level provenance: every reusable claim needs a source locator, verbatim evidence or an explicit paraphrase note, confidence, and limitations.
- Record source eligibility/status on every source-inventory and evidence-matrix entry. A local source with `inspected: true` is eligible for final citation; a local uninspected source and an externally discovered but unverified source are `lead` and not bibliography-eligible until inspected and provenance-complete.
- Respect source access, licensing, privacy, and user-provided source constraints. Flag inaccessible or conflicting evidence; do not conceal it.
- Do not choose document type, structure, citation style, or final prose. `academic-report-builder` owns document intake and creation.

## Decision Gates

| Situation | Action |
| --- | --- |
| Research question or scope unclear | Ask for clarification before searching. |
| Source cannot support a claim | Exclude the claim or mark it unresolved. |
| Sources conflict | Record both positions and the conflict. |
| Evidence is sufficient | Package it; do not draft the report. |

## Execution Steps

1. Load `references/research-protocol.md` and define the research question, scope, inclusion/exclusion criteria, and claim needs.
2. Collect and assess sources; capture stable locators, access date where applicable, exact evidence, source limitations, provenance, and eligibility/status. Classify only local `inspected: true` sources as eligible for final citation; retain all other sources as leads until inspection and provenance are complete.
3. Populate `assets/evidence-matrix-template.md` at claim level. Distinguish quotations from paraphrases, link each claim to its source, and record that source's eligibility/status.
4. Reconcile duplicates, gaps, and contradictions. Assign confidence without converting uncertainty into fact.
5. Hand the completed evidence package to `academic-report-builder` with only eligible bibliography-ready entries in the bibliography handoff; keep leads separately visible for follow-up.

## Output Contract

Return an evidence package containing: research question and scope; method and source-selection criteria; source inventory with eligibility/status; completed evidence matrix; claim-to-source traceability; eligible bibliography-ready entries; separately visible leads for follow-up; conflicts, limitations, and unresolved questions; and a handoff note. State that document creation remains with `academic-report-builder`.

## References

- `references/research-protocol.md` — research, evaluation, and handoff procedure.
- `assets/evidence-matrix-template.md` — required claim-level evidence package fields.
