# Plan - the teacher's rubric as a machine-checkable plan

Executor: document-workflow
Artifact: `reports/<wf>/rubric.yml`

Load this reference only when `doc_status` returns `next: plan`. This skill executes
the phase itself: it turns the teacher's rubric (collected at intake) into
`rubric.yml` (schema `academic.rubric/v1`).

## Contract

The plan mirrors the teacher's rubric exactly: one criterion per rubric item, each
with an `id`, a `title`, and optional `weight`, and each criterion mapped to the
body section that satisfies it. The draft writes against this plan and the content
check judges one criterion at a time. A rubric item with no section that could
satisfy it is a gap to raise with the user, never a criterion to drop, merge, or
invent.

Validate the shape before drafting:
`"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/rubric_plan.py"
"$REPORT_CONTENT_ROOT/reports/<work-folder>/"`. A malformed rubric blocks the route
(`rubric_malformed`) until it is fixed; a valid one is `done` and the draft may
start.

## Steps

1. Read the teacher's guide and rubric material recorded at intake.
2. Write `reports/<wf>/rubric.yml`: one criterion per rubric item, each mapped to
   the body section that satisfies it.
3. Validate with `rubric_plan.py` and fix every schema error it names.
4. Re-run `doc_status` and report the new current phase.

## Never

- Do not invent, merge, or drop a rubric item: the plan is the teacher's rubric,
  not the agent's idea of it.
- Do not write `body.md` or any other phase artifact: the plan produces exactly
  one artifact.
