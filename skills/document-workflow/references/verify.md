# Verify - the hard content check

Executor: document-workflow
Artifact: `reports/<wf>/content-check.yml`

Load this reference only when `doc_status` returns `next: verify`. This skill executes
the phase itself: it judges the approved draft against the plan and runs the hard
content check.

## Contract

After approval, judge every rubric criterion in a judgments file - one record per
criterion with `id`, `status: cumple|flojo|falta`, and `where` (the paragraph or
section the judgment comes from) - plus optional free-text `findings` such as
confusing paragraphs or figures that serve no criterion. Then run:

```bash
"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/content_check.py" "$REPORT_CONTENT_ROOT/reports/<work-folder>/" --judgments <judgments-file>
```

The tool adds the mechanical checks (every `[@key]` citation resolves, at least five
eligible book or paper sources are actually cited), derives the verdict itself, and
writes `content-check.yml` bound to `body.md`, `rubric.yml`, and the bib by hash.

The check only REPORTS findings: per-criterion cumple/flojo/falta with where,
citation problems, the cited-source count, confusing paragraphs, and figures that
serve no criterion. It never rewrites `body.md`, and it judges content only:
coverage, citations, and clarity. Findings are fixed by the user through the same
literal edit orders as the approval loop - never by silent polishing - and the
check reruns on the edited draft. A recorded `fail` blocks the route
(`content_check_failed`) until the findings are fixed and the check passes; an
edited draft, rubric, or bib simply stales the marker and the check reruns.

## Steps

1. Judge every `rubric.yml` criterion in a judgments file (`cumple`, `flojo`, or
   `falta`, each with its `where`), and record free-text findings.
2. Run `content_check.py` with `--judgments` (absolute command above).
3. Report every finding to the user verbatim and collect literal edit orders for the
   fixes; never fix findings on your own initiative.
4. Re-run `doc_status` and report the new current phase.

## Never

- Do not rewrite `body.md` to make findings disappear: the check reports, the user
  decides.
- Do not add judgments for criteria the plan does not name, and do not soften a
  `falta` into `flojo` to clear the phase.
- Do not run the check before `approval` is `done`: the check judges the approved
  draft.
