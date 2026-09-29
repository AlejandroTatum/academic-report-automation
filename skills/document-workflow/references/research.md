# Research phase

Executor: research-workflow
Artifact: `reports/<wf>/sources.bib`

Load this reference only when `doc_status` returns `next: research`. The executor is
`research-workflow`, using its own `references/research-protocol.md`; this skill never
performs research, and `research-workflow` never creates or formats the report.

## Contract

Research is mandatory: every document needs at least 5 academic sources, and the
phase artifact is the document's own BibTeX file, `reports/<wf>/sources.bib`
(or the `bibliography:`/`bib:` path declared in `report.yml`). The phase is done
only when that file carries at least 5 eligible entries -- `book`, `inbook`,
`incollection`, `article`, `inproceedings`, `conference`, `phdthesis`,
`mastersthesis`, or `techreport`. Web-only types such as `@misc` and `@online`
never count toward the gate, and a report can no longer record its way past
research: `doc_status` keeps the phase `pending` until the file holds the five
sources.

The executor also keeps its claim-level evidence practice: `research/
evidence-matrix.md` (and, once written, `research/evidence.yml`) carries claims,
conflicts, and unresolved questions into the report, but neither file satisfies
the phase on its own. The matrix is pre-document evidence, never confirmed
document intake: it does not choose document type, structure, citation style, or
prose. Document creation stays with `academic-report-builder`.

Local inspected sources feed the bibliography: list them by stable locator from
the local source library over `$REPORT_CONTENT_ROOT/academic-sources/manifest.yml`:

```bash
"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/source_library.py" pack --only-inspected <query>
```

Only `inspected: true` entries are bibliography-eligible; an uninspected local
source stays a `lead` and is never written into `sources.bib`.

## Steps

1. Define the research question, scope, and inclusion/exclusion criteria.
2. Collect, inspect, and assess sources; retain stable locators and provenance.
3. Write the document's `sources.bib` with every eligible book or paper entry
   (at least 5) and the claim-level matrix, separating quotations from
   paraphrases.
4. Reconcile duplicates, gaps, and contradictions without converting uncertainty
   into fact.
5. Re-run `doc_status` and report the new current phase.

## Never

- Do not invent a source, locator, quotation, date, author, or finding.
- Do not count a `@misc`/`@online` entry, or an uninspected `lead`, toward the
  five-source gate.
- Do not write `report.yml`, `preview.md`, `approval.yml`, or `validation.yml`.
- Do not draft, build, or deliver the document.
