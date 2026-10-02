# Format - APE, AA or libre

Executor: academic-report-flow
Artifact: `reports/<wf>/report.yml`

Load this reference only when `doc_status` returns `next: format`. This skill executes
the phase itself.

The format answers are normally collected in the approval batch (`approval.md`) and
this phase is then `done` without a stop. It is a completeness check plus a fallback
question: when `report.yml` lacks a known `format:`, `output:` or that format's
required metadata (legacy runs, a gap left by an answer), ask only the missing
fields named by `doc_status` and never re-ask what `report.yml` already records.

## Contract

Ask one question for format selection through `ask_user_choice` with APE, AA and libre as
suggested options, putting `format_hint:` (if present) first. The hint is not a
choice: wait for the user's answer before recording `format:`. Ask every remaining
metadata gap through `ask_user_choice` with suggested options, never free text.
Record confirmed answers in `report.yml`; do not invent missing values.

Ask the delivery format (PDF or DOCX) in the same format step, alongside APE, AA
or libre. It has no default and is never inferred from the request or the
material; record the answer as `output:`.

- `ape` - the practical-experimental technical report, a LaTeX replica of the
  teacher's DOCX. Its sections are fixed: Objetivo(s), Materiales, Procedimiento
  (steps as a list), Resultados, Preguntas de Control, Conclusiones (tied to the
  objective), Recomendaciones, Bibliografía/Referencias IEEE, and Anexos. Extract
  the identification fields it prints (cycle, unit, learning outcome, practice
  number, practice type, schedule, place, planned time) from the teacher's guide
  recorded at intake, and ask the user only to confirm them or fill the gaps.
  Decide group work here: when `practice_type` is Grupal, confirm the members
  here and record `metadata.members`.
- `aa` - the UNL academic template (`unl-report.tex`), its current look unchanged.
- `libre` - the user's own specification: wait for it and record it as
  `format_spec:` in `report.yml`; the plain template applies by default.

Every format cites and builds with IEEE (biblatex `style=ieee`). The format is a
presentation choice, independent of the internal route: `ape` and `aa` map to the
academic route, `libre` to the user's spec on the plain template. A chosen format
with missing or placeholder metadata keeps the phase `pending`, naming the missing
keys; an unrecognised value is `blocked`, never a silent fallback to a look the user
did not pick.

## Steps

1. Ask the format question with `ask_user_choice`: APE, AA or libre (hint first).
2. For `ape`, extract the identification fields from the teacher's guide and confirm
   or fill the gaps with the user; for `libre`, collect `format_spec:` verbatim.
3. Write `format:` and the chosen format's required metadata into
   `reports/<wf>/report.yml`.
4. Re-run `doc_status` and report the new current phase.

## Never

- Do not ask a second format-selection question; metadata gaps are separate
  `ask_user_choice` prompts with suggested options.
- Do not fill identification fields on the user's behalf, and do not invent metadata
  the teacher's guide does not supply.
