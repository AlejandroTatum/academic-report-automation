# Deliver phase

Executor: academic-report-builder
Artifact: `~/Documents/<category>/[<subject-slug>/]<slug>/<slug>-vNNN.pdf (+ the same-version <slug>-vNNN.bib only when deliver_bibliography: true)`

Load this reference only when `doc_status` returns `next: deliver`. The executor is
`academic-report-builder`, using its own `references/clean-delivery.md`; this skill
orchestrates publication and never copies or versions the PDF itself.

## Contract

Delivery exists to place the validated PDF in the confirmed delivery folder. The
executor runs the deliver entrypoint, `"$REPORT_AUTOMATION_ROOT/tools/deliver_report.py"`
over `"$REPORT_CONTENT_ROOT/reports/<work-folder>/"`, which is a thin gate-checker
over the existing publisher:
it requires a `validation.yml` receipt recording `result: pass` for the exact final
PDF bytes (`artifact_sha256` match) and a current `final-review.yml` marker whose
`pdf_sha256` matches those same bytes (the human's final OK on the PDF itself),
then calls the publisher, which re-checks both human markers and refuses an
absent, stale, or malformed `approval.yml` or `final-review.yml` before it
creates anything. Generation never publishes; this entrypoint is the only
publication route. The
phase produces exactly one artifact: a versioned
`<slug>-vNNN.pdf` under `~/Documents/<category>/<slug>/`, where the category comes
from the confirmed route and the slug from the confirmed title. On the academic
route the confirmed subject scopes it one level deeper,
`~/Documents/Academicos/<subject-slug>/<slug>/`: the canonical alias when the
shared `output_router` vocabulary knows the subject, otherwise the subject's own
stable ASCII slug, so a newly named course still gets its own folder; only a
missing subject has no level. That folder holds versioned final artifacts only:
PDFs by default, plus the same-version `<slug>-vNNN.bib` when the report declared
its bibliography (`deliver_bibliography: true`, source from the existing
`bibliography:`/`bib:` key). The declared `.bib` ships bound to evidence —
`validation.yml` and `final-review.yml` must record its exact
`bibliography_sha256` — and reuse compares the complete requested set: the same
PDF with a changed `.bib` claims a new version, a partial pair is never a
delivery, and a `sources.bib` that was never declared never travels.

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
2. Run the publication entrypoint (the step `clean-delivery.md` defines); every path
   is absolute, so the working directory is irrelevant:

   ```bash
   "$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/deliver_report.py" "$REPORT_CONTENT_ROOT/reports/<work-folder>/"
   ```
3. Report the published path and its version, and state that approval receipts are
   unchanged.
4. Re-run `doc_status`; an all-`done` route reports `next: done`.

## Never

- Do not create, repair, or refresh `approval.yml` or `final-review.yml` to make
  publication pass.
- Do not write any file other than the versioned PDF — and the declared,
  versioned `.bib` pair when `deliver_bibliography: true` — into the delivery
  folder.
- Do not run any Git command (`git init`, `git add`, `git commit`, `git push`) in
  the delivery tree: a course folder that is a repository belongs to the user, and
  Git metadata stays at the course root, outside the per-document folders.
- Do not report a run as `READY_TO_SUBMIT` from publication alone.
