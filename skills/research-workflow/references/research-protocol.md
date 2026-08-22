# Research protocol

## 1. Frame the inquiry

Record the research question, intended scope, relevant time period, jurisdiction or context, and the claims the downstream report must be able to support. State inclusion and exclusion criteria before collecting sources. If the question is underspecified, stop for clarification rather than silently narrowing it.

## 2. Evaluate sources

Prefer authoritative primary sources, peer-reviewed work, standards, official datasets, or clearly identified expert analysis appropriate to the question. For every retained source record author or organization, title, publication date, source type, stable URL/DOI or other source locator, access date when applicable, provenance, and eligibility/status. Note accessibility, recency, bias, and methodological limitations.

Classify a local source with `inspected: true` as `eligible` for final citation. Classify a local source without that inspection flag as `lead`, not bibliography-eligible, until it is inspected and its provenance is complete. Classify an externally discovered but unverified source as `lead`, not bibliography-eligible, until it is inspected and its provenance is complete.

Do not use a search-result snippet as evidence. Do not represent a secondary description as a primary finding. If a source is unavailable, paywalled, undated, or unverifiable, flag that condition and its `lead` status in the source inventory.

## 3. Capture claim-level evidence

Create one evidence-matrix row per claim. Give it a stable claim ID and record the exact claim, source locator, verbatim evidence, and the linked source's eligibility/status. If exact wording cannot be captured, label the entry `Paraphrase — verify against source`; never present it as a quotation. Record how the evidence supports, qualifies, or fails to support the claim, plus confidence and limitations.

## 4. Resolve uncertainty

Compare sources addressing the same claim. Preserve contradiction rather than selecting the convenient result. Mark unsupported claims as unresolved, identify evidence gaps, and distinguish source fact from analyst inference. Confidence reflects the available evidence, not the desired conclusion.

## 5. Package the handoff

Deliver the completed matrix with the research question, scope, inclusion/exclusion criteria, source inventory with eligibility/status, source access notes, conflicts, limitations, and unresolved questions. Put only `eligible` bibliography-ready entries in the bibliography handoff; keep `lead` entries separately visible for follow-up, never in that handoff. Include citation keys only as traceability aids; `academic-report-builder` chooses the confirmed citation style and creates the document. The package is evidence input, not confirmed document intake or final report prose.
