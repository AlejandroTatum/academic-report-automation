# Draft phase

Executor: academic-report-flow
Artifact: `reports/<wf>/body.md`

Load this reference only when `doc_status` returns `next: draft`. The executor is
`academic-report-flow` in its composition role; this skill orchestrates the phase
and never drafts the body itself.

## Contract

Draft exists to produce the full document body the user will review: the phase's
single artifact is `reports/<wf>/body.md`, drafted from `rubric.yml` and the
researched sources, in the document's language. It covers every rubric criterion in
the section the plan mapped, carries the text plus proposed figures, and cites with
Pandoc-style `[@key]` keys resolved against `sources.bib`; every claim traces back
to an entry there. Figures are referenced as `![caption](relative/path.png)` and
built with `academic-visual-builder`.

Writing style: human and natural - neither overly technical nor flattering or
obsequious. Model the tone on how the user writes: their own messages and prompts in
the session are the reference. Avoid stock AI phrasing. The draft is a starting
point for the user's own review, not the final voice; it is offered for literal edit
orders, not admiration.

Route presentation defaults (numbering, cover, template) come from `report.yml` and
the `format` phase, never from the draft.

Done means `body.md` exists with non-whitespace content. A missing or empty file
leaves the phase `pending`; an unreadable file is `blocked` (`draft_unreadable`).
`approval.yml` binds `body_sha256` to the exact bytes of this file, so once approved
the body changes only through the user's literal edit orders (see
`references/approval.md`).

## Steps

1. Read `report.yml`, `rubric.yml`, and `sources.bib`.
2. Draft the full body covering every rubric criterion, with every claim traceable
   to its source and proposed figures where they genuinely help.
3. Build any figure with `academic-visual-builder` and reference it as
   `![caption](relative/path.png)`.
4. Write `reports/<wf>/body.md`. Turn every rubric check green; run the
   mechanical part of `content_check.py` against the draft before presenting it.
   Fix failed checks in the draft, without writing semantic judgments or an
   approval marker.
5. Re-run `doc_status` and report the new current phase.

## Never

- Do not write `rubric.yml`, `report.yml`, or `validation.yml`: the phase never
  writes `approval.yml`, produces exactly one artifact, and requests no
  confirmation.
- Do not build, hash, or publish anything.
- Do not present the approval gate: that stays with `references/approval.md`.
- Do not pad the prose to sound accomplished: flattering, obsequious, or stock AI
  phrasing is a defect, not a style.
