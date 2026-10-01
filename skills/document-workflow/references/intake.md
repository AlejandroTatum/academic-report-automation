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

The content-first route asks for the minimum only:

- `metadata.title` and `metadata.student` - the identity this phase is done on;
  suggest the default student Alejandro Padilla through ask_user_choice as a
  single-choice confirmation, but never auto-fill without the user's answer;
- the teacher's guide and rubric material, plus any teacher explanation, kept as
  inputs for the `plan` phase; record the folder-relative `guide:` path in
  `report.yml`, run `tools/guide_facts.py <folder>` and, when it detects a family,
  record `format_hint: ape` or `format_hint: aa` for planning (not `format:`);
- `guide_facts.py` reports only what the guide states explicitly, and it never
  guesses. When one fact key carries several distinct explicit values (say, an
  APE guide that also says "aprendizaje autónomo", or two different "Semana N"
  numbers), the key moves to a `conflicts:` mapping that lists the conflicting
  explicit values, and the fact is omitted from the facts themselves: no value
  is picked, and a conflicted family produces no `format_hint` at all. Any fact
  the conflicts leave unresolved is asked through the existing structured
  question policy (`ask_user_choice`); it is never inferred from context. This
  contract is existing behavior, proven by `tools/test_guide_facts.py`.
- top-level `route:` (document type), resolved with the user, never inferred;
- `metadata.date` and the optional record
  keys `metadata.audience`, `metadata.purpose`, `metadata.visual_direction`,
  top-level `template:`, `cover:`, and `output:` - fill them from supplied material
  when it names them, and never interrogate the user for them here;
- when the supplied requirement names the `.bib` as a submitted artifact, record
  `deliver_bibliography: true` (plus `bibliography:` when the file is not
  `sources.bib`) in `report.yml`: intake records the request, it never asks for
  it and never adds an approval gate for it.

Group work (`metadata.practice_type: Grupal` and `metadata.members`) is decided
at format, not intake. Intake never asks formatting questions: template, identity tables, cover, output
look, and the document format (APE, AA or libre) are decided at the `format` phase,
after the content is approved. `metadata.subject` and `metadata.teacher` are
recorded when the guide names them; the `format` phase completes whatever its
chosen format still requires.

Done means `report.yml` exists, `route:` is a known route, and `metadata.title` and
`metadata.student` are present and real (not bracket templates or fill-in marks).
An unknown `route:` is `blocked` (`unknown_route`); a missing or placeholder
identity leaves intake `pending`, so the route keeps waiting at intake instead of
advancing.

## Steps

1. Resolve the document type and route with the user; never infer either one.
2. Collect the minimum: title, student, the teacher's guide and rubric material,
   and any teacher explanation.
3. Write `reports/<wf>/report.yml` with the confirmed data record.
4. Re-run `doc_status` and report the new current phase.

## Never

- Do not ask formatting questions (template, cover, visual direction, output look):
  the `format` phase owns every formatting decision.
- Do not write `approval.yml`, `rubric.yml`, `sources.bib`, or `validation.yml`, and
  do not build, validate, or publish anything: intake produces exactly one artifact.
- Do not treat a request text, prior document, or template as confirmed data.
- Do not add schema fields beyond the record in `document-intake.md`.
