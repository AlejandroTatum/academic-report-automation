# Intake phase

Executor: academic-report-builder
Artifact: `reports/<wf>/report.yml`

Load this reference only when `doc_status` returns `next: intake`. The executor is
`academic-report-builder`, using its own `references/document-intake.md` contract;
this skill orchestrates and never re-implements intake.

## Contract

Intake exists to turn a request into the one machine-readable record the whole route
derives from: `reports/<wf>/report.yml`. The record uses the keys the pipeline
actually reads; the full shape and its semantics live in
`academic-report-builder/references/document-intake.md`.

- top-level `route:` (document type), `output:` (delivery format), `template:` when
a template was confirmed, and `cover:` when the route default is overridden;
- `metadata:` for identity and context: the route-mandatory fields (academic:
`metadata.title`, `metadata.subject`, `metadata.teacher`, `metadata.student`,
`metadata.date`; every other route: `metadata.title`, `metadata.student`,
`metadata.date`), `metadata.members` for a group roster, and the recorded
`metadata.audience`, `metadata.purpose`, and `metadata.visual_direction`;
- top-level `research: skipped` when the research trigger does not fire.

`cover:` is top-level: `report.yml`'s own `cover:` key is the only one read, so a
nested `metadata.cover` would be ignored. Do not invent a parallel key for a meaning
that already has one.

Intake asks only the consequential fields that are still missing; supplied inputs are
candidate answers, and each missing route-mandatory field may be clarified once. It
never asks for a generation approval and never renders a confirmation prompt: the one
explicit human confirmation gate happens after `preview.md` exists
(`references/approval.md`).

Done means `report.yml` exists, `route:` is a known route, and every
route-mandatory metadata value is truthy. An unknown `route:` is `blocked`
(`unknown_route`); incomplete metadata leaves intake `pending`, so the route keeps
waiting at intake instead of advancing.

## Steps

1. Resolve the document type and route with the user; never infer either one.
2. Ask only for the missing consequential and route-mandatory values.
3. Write `reports/<wf>/report.yml` with the confirmed data record.
4. Re-run `doc_status` and report the new current phase.

## Never

- Do not write `preview.md`, `approval.yml`, or `validation.yml`, and do not build,
  validate, or publish anything: intake produces exactly one artifact.
- Do not treat a request text, prior document, or template as confirmed data.
- Do not add schema fields beyond the record above.
