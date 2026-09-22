# Draft phase

Executor: academic-report-builder
Artifact: `reports/<wf>/body.md`

Load this reference only when `doc_status` returns `next: draft`. The executor is
`academic-report-builder` in its composition role; this skill orchestrates the phase
and never drafts the body itself.

## Contract

Draft exists to turn the approved-to-be preview outline into the full document body
before the single human approval, so approval has something to approve. The executor
produces exactly one artifact: `reports/<wf>/body.md`, the full document body, drafted
from the preview's `## Outline` and `## Evidence` sections and the evidence matrix (or
the inspected local sources named in the preview when research was skipped), in the
document's language. Every claim in the body must trace back to a matrix claim id or a
named inspected source; draft never invents a claim the preview did not already carry.

The authoring format is Markdown: section headings from the confirmed outline,
Pandoc-style `[@key]` citations resolved against `sources.bib` (a citation-driven
bibliography: `sources.bib` is required only when the body contains `[@key]`
citations), and figures as `![caption](relative/path.png)` built with
`academic-visual-builder`. Route defaults -- numbering, cover, template -- come from
`report.yml` and are never restated in the body.

Done means `body.md` exists with non-whitespace content. A missing or empty file
leaves the phase `pending`; an unreadable file is `blocked` (`draft_unreadable`).
`approval.yml` binds `body_sha256` to the exact bytes of this file, so once approved
the body must never be rewritten without a fresh explicit approval.

## Steps

1. Read `report.yml`, `preview.md`, and the evidence matrix (or the inspected local
   sources the preview names).
2. Draft the full body from the confirmed outline, with every claim traceable to its
   source.
3. Build any figure with `academic-visual-builder` and reference it as
   `![caption](relative/path.png)`.
4. Write `reports/<wf>/body.md`.
5. Re-run `doc_status` and report the new current phase.

## Never

- Do not write `approval.yml`, `preview.md`, `report.yml`, or `validation.yml`: draft
  produces exactly one artifact and requests no confirmation.
- Do not build, hash, or publish anything.
- Do not present the approval gate: that stays with `references/approval.md`.
