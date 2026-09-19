---
name: document-workflow
description: "Trigger: document workflow, doc status, where is my report, resume report, approve preview, publish report. Route phases from doc_status and delegate to the existing executor skill."
license: Apache-2.0
metadata:
  author: "gentleman-programming"
  version: "1.0"
  scope: "orchestration"
---

## Activation Contract

Use to resume, inspect, or advance an in-progress document run under
`$REPORT_CONTENT_ROOT/reports/<work-folder>/`. Run
`"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/doc_status.py"
"$REPORT_CONTENT_ROOT/reports/<work-folder>/"` first; the returned `next` token owns
the route. The source root, the selected interpreter (`REPORT_PYTHON`) and the
content root are all defined in
`academic-report-builder/references/automation-contract.md`; the source root may be a
worktree with no `.venv` of its own. Every path above is
absolute, so the working directory never changes the answer. This skill orchestrates
only: it never re-implements intake, research,
build, validation, or publication, and never reads executor internals to decide
where a run stands.

Loop: `doc_status -> next -> reference -> delegate -> re-run`.

## Hard Rules

- Route exclusively from the `next` token; load only that phase's reference.
- The phase/reference/executor routing table is the whole routing logic:

| next | reference | executor |
|---|---|---|
| intake | `references/intake.md` | `academic-report-builder` (`document-intake.md`) |
| research | `references/research.md` | `research-workflow` |
| preview | `references/preview.md` | `academic-report-builder` (composition, pre-build) |
| draft | `references/draft.md` | `academic-report-builder` (composition, body draft) |
| approval | `references/approval.md` | this skill - human gate, no executor |
| generate | `references/generate.md` | `academic-report-builder` (`automation-contract.md`) |
| validate | `references/validate.md` | `academic-report-builder` (`quality-gates.md`) or `gentle-ai review` |
| deliver | `references/deliver.md` | `academic-report-builder` (`clean-delivery.md`) |

- Each delegation produces exactly one artifact consumed by the derivation table.
- Present the human block verbatim; never summarize or reword it.
- Never build before approval is `done`; never publish without a current marker.
- Never present the approval gate before `draft` is `done`.
- Present the approval gate losslessly: complete options, consequences, exact
  allowed answers, no silent default, and never proceed on silence.

## Decision Gates

| Situation | Action |
|---|---|
| `next` names a phase | Load its reference and delegate to the executor. |
| `next: approval` | Present the human gate; write `approval.yml` only on an explicit answer. |
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
**Gate**: preview pending - draft <report-folder>/preview.md, then re-run doc_status
Route: intake > research > [preview] > draft > approval > generate > validate > deliver

**Summary**
- intake: done - route=academic, metadata complete
- research: done - skipped in report.yml
- preview: current - preview.md missing
- draft: pending
- approval: pending
- generate: pending
- validate: pending
- deliver: pending

**Next**: preview - draft <report-folder>/preview.md, then re-run doc_status
```

## References

- `references/intake.md` - intake contract and `report.yml` completion.
- `references/research.md` - optional evidence collection and `research: skipped`.
- `references/preview.md` - pre-build content preview composition.
- `references/draft.md` - full document body drafted before approval.
- `references/approval.md` - the single human approval gate.
- `references/generate.md` - approved build and PDF generation.
- `references/validate.md` - RDD or fallback validation branches.
- `references/deliver.md` - versioned publication to the delivery folder.
