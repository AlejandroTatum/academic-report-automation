# Preview phase

Executor: academic-report-builder
Artifact: `reports/<wf>/preview.md`

Load this reference only when `doc_status` returns `next: preview`. The executor is
`academic-report-builder` in its composition role, before any build; this skill
orchestrates the phase and never composes the preview itself.

## Contract

The preview exists to be the object the human approves, so it must show enough
content for a decision before any PDF is built. The executor produces exactly one
artifact: `reports/<wf>/preview.md`, ASCII, with the fixed H2 sections

    # Content Preview: <title>
    ## Contract Summary   - Route, Type, Audience, Purpose, Template/identity, Outputs, Visual direction
    ## Outline            - numbered sections, one-line intent each
    ## Evidence           - "<section> - <claim id> -> <source locator>" or "none (no external claims)"
    ## Output Type        - "Output type: PDF | DOCX | PDF+DOCX | VISUAL"

The preview binds to the confirmed `report.yml` record and to the evidence matrix
when the research phase produced one; it does not invent claims, sections, or a
document type. It stays ASCII and non-empty.

Done means `preview.md` exists with non-whitespace content. A missing or empty file
leaves the phase `pending`; an unreadable file is `blocked` (`preview_unreadable`).
Editing a confirmed field re-renders the preview, which invalidates any earlier
approval and presents the one gate again for the new bytes.

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
