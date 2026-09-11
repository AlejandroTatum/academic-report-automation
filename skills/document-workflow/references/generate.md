# Generate phase

Executor: academic-report-builder
Artifact: `outputs/<materia>/<final>.pdf`

Load this reference only when `doc_status` returns `next: generate`. The executor is
`academic-report-builder`, using its own `references/automation-contract.md` for the
canonical build and validation commands; this skill never builds the document itself.

## Precondition

Generation runs only when the routed block reports `approval: done` for the work
folder: `approval.yml` exists and its `preview_sha256` matches the current
`preview.md`. An absent, stale, or malformed marker keeps `approval` `pending` or
`blocked`, so `doc_status` never returns `next: generate` and this reference must not
be loaded or acted on. Never build before approval is `done`: a build made on an
unapproved preview is discarded at publication, where the publisher re-checks the
marker and refuses to deliver anything.

## Contract

Generation exists to turn the confirmed report content into the single final PDF the
later phases read. The executor runs the canonical pipeline
(`python tools/build_report_auto.py ...`), which builds from the confirmed
`report.yml` plus its content, runs the configured technical validation, and records
the artifact hash and page count. The phase produces exactly one artifact: the final
PDF under `outputs/<materia>/<final>.pdf`.

Done means that final PDF exists and is not older than `approval.yml`, so a PDF that
predates the marker is `pending` and the build simply reruns. Generate is never
`blocked`: a missing or stale PDF is ordinary progress. The phase does not publish;
the publisher belongs to `references/deliver.md`, and approval state is derived by
`tools/doc_status.py` and re-checked by the publisher.

## Steps

1. Read the routed `doc_status` block and the preview reference for the work folder.
2. Run the canonical build and validation command from `automation-contract.md`.
3. Keep validator output as precheck evidence and record the immutable hash.
4. Re-run `doc_status` and report the new current phase.

## Never

- Do not publish, copy, or version the PDF: generate produces exactly one artifact.
- Do not build before approval is `done`; an unapproved preview never produces the
  final PDF.
- Do not write `approval.yml`. No process creates, repairs, or refreshes a marker.
- Do not claim `VISUAL_PASS`, `HUMAN_REVIEW`, or `READY_TO_SUBMIT` from a build or a
  validator exit code.
