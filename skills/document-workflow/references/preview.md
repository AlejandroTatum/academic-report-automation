# Preview phase

Executor: academic-report-builder
Artifact: `reports/<wf>/preview.md`

Load this reference only when `doc_status` returns `next: preview`. The executor is
`academic-report-builder` in its composition role, before any build; this skill
orchestrates the phase and never composes the preview itself.

## Contract

The preview exists to anchor the human decision, together with the full body the
`draft` phase writes next: the decision object is the preview plus the drafted
`body.md`, not the preview alone. The executor produces exactly one artifact:
`reports/<wf>/preview.md`, UTF-8, with the fixed H2 sections

    # Content Preview: <title>
    ## Contract Summary   - Route, Type, Audience, Purpose, Template/identity, Outputs, Visual direction
    ## Outline            - numbered sections, one-line intent each
    ## Evidence           - "<section> - <claim id> -> <source locator>" (evidence matrix, or the inspected local source when research was skipped)
    ## Output Type        - "Output type: PDF | DOCX | PDF+DOCX | VISUAL"

The preview binds to the confirmed `report.yml` record and to the evidence matrix
when the research phase produced one; it does not invent claims, sections, or a
document type. It is UTF-8: the human headings and the content may be written in
Spanish, accents included, and nothing in the preview is restricted to ASCII. It is
never empty.

Done means `preview.md` exists with non-whitespace content. A missing or empty file
leaves the phase `pending`; an unreadable file is `blocked` (`preview_unreadable`).
Editing a confirmed field re-renders the preview, which invalidates any earlier
approval and presents the one gate again for the new bytes. An approved preview is
never rewritten: `approval.yml` records `preview_sha256` over its exact bytes, so
rewriting the file without a fresh explicit approval would leave the marker stale.

## Steps

1. Read `report.yml` and, when present, `research/evidence-matrix.md`.
2. Draft the four fixed sections with the confirmed data and chosen outline.
3. Write `reports/<wf>/preview.md`.
4. Re-run `doc_status` and report the new current phase.

## Never

- Do not build, hash, publish, or write `approval.yml`: preview produces exactly one
  artifact and requests no confirmation.
- Do not summarize or reword the preview when presenting status: the human block is
  rendered verbatim, and the gate prompt is lossless.
- Do not describe the evidence package as confirmed intake.
