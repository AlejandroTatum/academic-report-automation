# Format - APE, AA or libre

Executor: document-workflow
Artifact: `reports/<wf>/report.yml`

Load this reference only when `doc_status` returns `next: format`. This skill executes
the phase itself.

## Contract

Ask the user exactly one question: APE, AA or libre. Record the answer as `format:`
in `report.yml` together with that format's required metadata. Never invent the
answer, and never split the one question into several.

- `ape` - the practical-experimental technical report, a LaTeX replica of the
  teacher's DOCX. Its sections are fixed: Objetivo(s), Materiales, Procedimiento
  (steps as a list), Resultados, Preguntas de Control, Conclusiones (tied to the
  objective), Recomendaciones, Bibliografía/Referencias IEEE, and Anexos. Extract
  the identification fields it prints (cycle, unit, learning outcome, practice
  number, practice type, schedule, place, planned time) from the teacher's guide
  recorded at intake, and ask the user only to confirm them or fill the gaps.
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

1. Ask the one question: APE, AA or libre.
2. For `ape`, extract the identification fields from the teacher's guide and confirm
   or fill the gaps with the user; for `libre`, collect `format_spec:` verbatim.
3. Write `format:` and the chosen format's required metadata into
   `reports/<wf>/report.yml`.
4. Re-run `doc_status` and report the new current phase.

## Never

- Do not ask a second formatting question: the one question is the whole contract.
- Do not fill identification fields on the user's behalf, and do not invent metadata
  the teacher's guide does not supply.
