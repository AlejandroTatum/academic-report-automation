# Verify - the hard content check

Executor: document-workflow
Artifact: `reports/<wf>/content-check.yml`

Judge every rubric criterion (`cumple|flojo|falta` + `where`) in a judgments
file, then run `"$REPORT_PYTHON"
"$REPORT_AUTOMATION_ROOT/tools/content_check.py"
"$REPORT_CONTENT_ROOT/reports/<work-folder>/" --judgments <judgments-file>`;
the tool adds the mechanical checks (citations resolve, five eligible sources
cited) and derives the verdict itself, binding body.md, rubric.yml and the
bib by hash. Findings are reported, never fixed silently: the user applies
the fixes through edit orders and the check reruns.
