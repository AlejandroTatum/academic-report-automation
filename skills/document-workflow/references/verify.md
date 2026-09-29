# Verify - the hard content check

Executor: document-workflow
Artifact: `reports/<wf>/content-check.yml`

Load this reference only when `doc_status` returns `next: verify`. This skill executes
the phase itself: it delegates semantic judgments to an independent read-only
judge and runs the hard content check.

## Contract

After approval, run `content_check.py <folder> --judge-brief`. Give its exact
output, and nothing from the drafting conversation, to ONE independent read-only
judge subagent. The judge must use only the named inputs, quote `where` locations,
and return YAML with `judge`, `body_sha256`, `rubric_sha256`, `criteria` (one
`id`, `status: cumple|flojo|falta`, `where`, `note` per rubric criterion), and
optional `findings`. Save that YAML unchanged as the judgments file; the drafting agent never writes judgments.
A stale marker means re-run the independent judge on the current inputs, not
reuse old judgments. Then run:

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

1. Run `content_check.py <folder> --judge-brief` using the same Python and folder
   as the command above. Do not pass the drafting conversation to the judge.
2. Launch ONE independent read-only judge subagent with only that brief.
3. Save the judge's YAML unchanged as `<judgments-file>`; run `content_check.py`
   with `--judgments` (absolute command above).
4. Report every finding verbatim and collect literal edit orders; never fix findings
   on your own initiative. Re-run `doc_status` and report the new phase.

## Never

- Do not rewrite `body.md` to make findings disappear: the check reports, the user
  decides.
- Do not add judgments for criteria the plan does not name, and do not soften a
  `falta` into `flojo` to clear the phase.
- Do not run the check before `approval` is `done`: the check judges the approved
  draft.
