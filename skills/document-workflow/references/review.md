# Review - the final human review

Executor: document-workflow
Artifact: `reports/<wf>/final-review.yml`

Load this reference only when `doc_status` returns `next: review`. This phase is the
human gate on the built PDF: no executor is delegated, the orchestrator presents the
validated PDF and only the human's explicit OK produces the marker.

## Contract

Present the validated final PDF to the user for the final review: the exact PDF the
`validate` phase recorded, read or opened in full, never a summary. Only an explicit
OK of that exact PDF produces `final-review.yml`, bound to the bytes through
`pdf_sha256` (with `reviewed_at` and `reviewed_by`). Silence is never a yes and the
marker is never inferred; a decline writes nothing. A rebuilt PDF stales the marker
and returns the route to `review` as `pending`: the current build must be reviewed
again. Delivery runs only after this gate is `done`.

## PDF handoff

Present the current PDF with the exact short fish command produced by
`doc_status` guidance: `set d <folder>`, `set f <exact PDF filename>`,
`brave $d/$f`. Copy its quoting exactly; do not glob or truncate the filename.
Never send screenshots; the user reviews the PDF itself. The default viewer
zathura does not follow internal links.

## Steps

1. Point the user to the exact final PDF (`report.yml`'s `pdf:` path) and state that
   delivery happens only after their explicit OK.
2. Write `reports/<wf>/final-review.yml` only on the explicit OK, recording
   `pdf_sha256`, `reviewed_at`, and `reviewed_by`.
3. On any other answer, write nothing and report review as `pending`.
4. Re-run `doc_status` and report the new current phase.

## Never

- Do not write `final-review.yml` on an inferred or partial OK, and do not refresh a
  stale marker without a fresh explicit OK of the current bytes.
- Do not deliver before `review` is `done`.
