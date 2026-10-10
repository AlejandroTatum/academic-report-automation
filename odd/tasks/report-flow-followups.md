# Report flow follow-ups

Merge the open PR stack, then close the small follow-ups left by the DBP AA01 run.
Repo AlejandroTatum/academic-report-automation; worktree academic-report-automation-worktrees/pi.

## Specs

- S1. Merge the stack "#65 → #71" into main in order ("revisar el stack y mergearlo en orden"), after the full suite passes on its tip.
- S2. Issue #72 follow-ups: "rewriting `approval.yml` after a final build reopens format" (`R3-mtime-marker-rewrite`) and "add a test for equal mtimes (`>=` counts as final, the same as `_phase_generate`)" (`R3-mtime-tie-coverage`).
- S3. "The incremental brief makes the verifier re-copy every carried-over requirement, so it is larger than the full brief (17.6 KB vs 7.5 KB). The tool should merge them itself."
- S4. Optional advisories: "DOCX import math normalization ($x^2$ becomes $x^{2}$)", "rubric fallback strictness", "body_digest alias readability". Mechanical ones are fixed; ones that need a product decision go to the user.

## Tasks

- T1 (S1) merge stack #65-#71 with merge commits — route: parent — commit: merge commits on main
- T2 (S2) tie-mtime test + documented marker-rewrite behavior — route: parent, test-first — commit: pending
- T3 (S3) tool-side merge of carried-over requirements — route: parent, test-first, independent verify — commit: pending
- T4 (S4) body_digest alias; decisions for math normalization and rubric fallback — route: parent — commit: pending

## Log

- L1 (2026-10-10, user): "si dale arma el plan con los 4 puntos y ve trabajandolos hasta completar"
- L2: Stack is linear (#65 base main ... #71 base feat/editorial-visual-style), main unprotected, history uses merge commits. Issue #72 points 2-7 stay out of scope (not in the 4 points).
- L3: "rubric fallback" = 5208b57: a contains/matches check bound to a missing section widens to the whole draft. Math normalization is pandoc's own spelling. Both need a user decision.
