# Plan - the teacher's rubric as a machine-checkable plan

Executor: document-workflow
Artifact: `reports/<wf>/rubric.yml`

Record the teacher's rubric as `rubric.yml` (schema `academic.rubric/v1`): one
criterion per rubric item, each with an `id`, a `title`, and the `body.md`
section that satisfies it. Validate the shape with
`"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/rubric_plan.py"
"$REPORT_CONTENT_ROOT/reports/<work-folder>/"` before drafting: the draft
writes against this plan and the content check judges one criterion at a time.
A malformed rubric blocks the route until it is fixed.
