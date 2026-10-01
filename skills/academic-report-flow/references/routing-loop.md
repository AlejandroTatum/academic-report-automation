# Routing loop

Loop: `doc_status -> next -> reference -> delegate -> re-run`.

A new request for a document creates the work folder `$REPORT_CONTENT_ROOT/reports/<slug>/`
first, so `doc_status` sees an empty folder (`next: intake`) and content-first intake
applies. The slug is lowercase ASCII kebab-case derived from the subject and assignment
named in the request (e.g. `metodos-numericos-ejercicio-1-5`); if that folder already
exists and belongs to a different document, append a numeric suffix. Never ask the user
for the slug; state the folder in the intake summary. An existing folder for the same
document is resumed, never recreated. The standalone full route applies only when the
work-folder flow is unavailable (no content root, or the user explicitly asks for a
one-off document outside the reports flow).

Run `"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/doc_status.py"
"$REPORT_CONTENT_ROOT/reports/<work-folder>/"` first; the returned `next` token owns
the route. The selected interpreter (`REPORT_PYTHON`) and the roots are defined in
`automation-contract.md`; every path above is absolute, so the working directory
never changes the answer. This skill never reads executor internals to decide where a run
stands; only the `next` token does.

The phase/reference/executor routing table is the whole routing logic:

| next | reference | executor |
|---|---|---|
| intake | `references/intake.md` | this skill (academic-report-flow, `intake.md`) |
| research | `references/research.md` | `research-workflow` |
| plan | `references/plan.md` | this skill |
| draft | `references/draft.md` | this skill (composition, body draft) |
| approval | `references/approval.md` | this skill - human gate, no executor |
| verify | `references/verify.md` | this skill |
| format | `references/format.md` | this skill |
| generate | `references/generate.md` | this skill (`automation-contract.md`) |
| validate | `references/validate.md` | this skill (`quality-gates.md`) or `gentle-ai review` |
| review | `references/review.md` | this skill - human gate, no executor |
| deliver | `references/deliver.md` | this skill (`clean-delivery.md`) |

- Each phase produces exactly one artifact consumed by the derivation table.
- Present the human block verbatim; never summarize or reword it.
- Present every human gate losslessly: complete options, consequences, exact
  allowed answers, no silent default, and never proceed on silence.
- Never build before approval is `done`; never publish without a current marker.
- Never present the approval gate before `draft` is `done`.
- Content-first: intake asks only the minimum and never formatting questions;
  research is mandatory (at least 5 book or paper sources, IEEE, never invented);
  the plan mirrors the teacher's rubric; the user's text is applied verbatim; the
  content check only reports findings; the format is one question (APE, AA or
  libre).

Render the human block exactly (ASCII only for this status block, flat bullets,
no tables, no nested headers); the `**Gate**` line names the phase the route is
actually waiting on and appears only while a phase is not `done`. The tool binds
`<report-folder>` to the absolute work folder it was given:

```text
**Gate**: plan pending - record the teacher's rubric in <report-folder>/rubric.yml, then re-run doc_status
Route: intake > research > [plan] > draft > approval > verify > format > generate > validate > review > deliver

**Summary**
- intake: done - route=academic, title and student recorded
- research: done - sources.bib has 5/5 book or paper sources
- plan: current - rubric.yml missing
- draft: pending
- approval: pending
- verify: pending
- format: pending
- generate: pending
- validate: pending
- review: pending
- deliver: pending

**Next**: plan - record the teacher's rubric in <report-folder>/rubric.yml, then re-run doc_status
```
