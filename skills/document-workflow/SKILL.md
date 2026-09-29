---
name: document-workflow
description: "Trigger: document workflow, doc status, where is my report, resume report, approve draft, publish report. Route the content-first flow from doc_status."
license: Apache-2.0
metadata:
  author: "gentleman-programming"
  version: "1.1"
  scope: "orchestration"
---

## Activation Contract

Use to resume, inspect, or advance an in-progress document run under
`$REPORT_CONTENT_ROOT/reports/<work-folder>/`. Run
`"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/doc_status.py"
"$REPORT_CONTENT_ROOT/reports/<work-folder>/"` first; the returned `next` token owns
the route. The selected interpreter (`REPORT_PYTHON`) and the roots are defined in
`academic-report-builder/references/automation-contract.md`; every path above is
absolute, so the working directory never changes the answer. This skill orchestrates
only: it never re-implements a phase and never reads executor internals to decide
where a run stands.

Loop: `doc_status -> next -> reference -> delegate -> re-run`.

## Hard Rules

- Route exclusively from the `next` token; load only that phase's reference.
- The phase/reference/executor routing table is the whole routing logic:

| next | reference | executor |
|---|---|---|
| intake | `references/intake.md` | `academic-report-builder` (`document-intake.md`) |
| research | `references/research.md` | `research-workflow` |
| plan | `references/plan.md` | this skill (document-workflow) |
| draft | `references/draft.md` | `academic-report-builder` (composition, body draft) |
| approval | `references/approval.md` | this skill - human gate, no executor |
| verify | `references/verify.md` | this skill (document-workflow) |
| format | `references/format.md` | this skill (document-workflow) |
| generate | `references/generate.md` | `academic-report-builder` (`automation-contract.md`) |
| validate | `references/validate.md` | `academic-report-builder` (`quality-gates.md`) or `gentle-ai review` |
| review | `references/review.md` | this skill - human gate, no executor |
| deliver | `references/deliver.md` | `academic-report-builder` (`clean-delivery.md`) |

- Each delegation produces exactly one artifact consumed by the derivation table.
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

## Decision Gates

| Situation | Action |
|---|---|
| `next` names a phase | Load its reference and delegate to the executor. |
| `next: approval` | Present the human gate; apply literal edit orders verbatim; write `approval.yml` only on an explicit answer. |
| `next: review` | Present the final PDF; write `final-review.yml` only on the user's explicit OK. |
| `next: done` | Report completion; route no further. |
| Unknown or unavailable executor | Stop, report the blocker, never substitute silently. |

## Execution Steps

1. Run
   `"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/doc_status.py"
   "$REPORT_CONTENT_ROOT/reports/<work-folder>/"`.
2. Read `next`; present the human status block verbatim.
3. Load only the reference for that token.
4. Delegate to the executor in the routing table.
5. Confirm the one artifact and re-run `doc_status`.

## Output Contract

Return the verbatim human block, the `academic.doc-status/v1` machine block, the
routed token, the delegated executor, and the single artifact it produced.

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

## References

- `references/intake.md` - the content-first minimum intake and `report.yml`.
- `references/research.md` - the mandatory five-source IEEE gate (`sources.bib`).
- `references/plan.md` - the teacher's rubric as a machine-checkable plan (`rubric.yml`).
- `references/draft.md` - the full draft, written to be reviewed (`body.md`).
- `references/approval.md` - the human gate and the literal edit-order loop.
- `references/verify.md` - the report-only content check (`content-check.yml`).
- `references/format.md` - the single APE / AA / libre question in `report.yml`.
- `references/generate.md` - approved build and PDF generation.
- `references/validate.md` - RDD or fallback validation branches.
- `references/review.md` - the final human review gate (`final-review.yml`).
- `references/deliver.md` - versioned publication to the delivery folder.
