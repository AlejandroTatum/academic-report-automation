# Deliver phase

Executor: academic-report-builder
Artifact: `~/Documents/<category>/<slug>/<slug>-vNNN.pdf`

Load this reference only when `doc_status` returns `next: deliver`. The executor is
`academic-report-builder`, using its own `references/clean-delivery.md`; this skill
orchestrates publication and never copies or versions the PDF itself.

## Contract

Delivery exists to place the validated PDF in the confirmed delivery folder. The
executor calls the existing publisher, which re-checks the approval marker itself and
refuses an absent, stale, or malformed `approval.yml` before it creates anything. The
phase produces exactly one artifact: a versioned
`<slug>-vNNN.pdf` under `~/Documents/<category>/<slug>/`, where the category comes
from the confirmed route and the slug from the confirmed title. That folder holds
PDFs only.

Publication stays atomic and monotonic: a first unique artifact is `v001`, an
identical artifact is a hash-matched reuse, and a concurrent publisher never
overwrites an existing version. Done means a published `<slug>-vNNN.pdf` hashes equal
to the final PDF; delivery has no failure state, so an absent or non-matching copy is
`pending`.

Publication is not approval: it does not grant `VISUAL_PASS`, `HUMAN_REVIEW`, or
`READY_TO_SUBMIT`, which still require independent semantic inspection and human
review against immutable hashes.

## Steps

1. Confirm the routed block reports the validate phase `done` for the final PDF.
2. Run the publication step from `clean-delivery.md`.
3. Report the published path and its version, and state that approval receipts are
   unchanged.
4. Re-run `doc_status`; an all-`done` route reports `next: done`.

## Never

- Do not create, repair, or refresh `approval.yml` to make publication pass.
- Do not write any file other than the versioned PDF into the delivery folder.
- Do not report a run as `READY_TO_SUBMIT` from publication alone.
