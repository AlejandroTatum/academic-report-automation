# Report flow follow-ups

Merge the open PR stack, then close the small follow-ups left by the DBP AA01 run.
Repo AlejandroTatum/academic-report-automation; worktree academic-report-automation-worktrees/pi.

## Specs

- S1. Merge the stack "#65 → #71" into main in order ("revisar el stack y mergearlo en orden"), after the full suite passes on its tip.
- S2. Issue #72 follow-ups: "rewriting `approval.yml` after a final build reopens format" (`R3-mtime-marker-rewrite`) and "add a test for equal mtimes (`>=` counts as final, the same as `_phase_generate`)" (`R3-mtime-tie-coverage`).
- S3. "The incremental brief makes the verifier re-copy every carried-over requirement, so it is larger than the full brief (17.6 KB vs 7.5 KB). The tool should merge them itself."
- S4. Optional advisories: "DOCX import math normalization ($x^2$ becomes $x^{2}$)", "rubric fallback strictness", "body_digest alias readability". Mechanical ones are fixed; ones that need a product decision go to the user.

## Tasks

- T1 (S1) merge stack #65-#71 with merge commits — route: parent — DONE: #65-#71 merged in order, main 8ffa0bf has the stack tip's tree (suite on tip 2117 passed, 1 skipped)
- T2 (S2) tie-mtime test + documented marker-rewrite behavior — route: parent — DONE fedb831 (pin tests, no meaningful RED: behavior already existed; docstring documents the rewrite case)
- T3 (S3) tool-side merge of carried-over requirements — route: parent, test-first, independent verify — DONE (commit below); RED 6 failed, GREEN; verifier FAIL D1 blank-quote carry, D2 unhashable criterion; RED 2 failed, fixed by _carryable; re-verify PASS; full suite 2128 passed, 1 skipped; DBP AA01 incremental brief 17.6 KB -> 8.0 KB
- T4 (S4) body_digest alias; decisions for math normalization and rubric fallback — route: parent — alias a4ee915 (guarded by existing test); math normalization and rubric fallback await the user's decision

## Log

- L1 (2026-10-10, user): "si dale arma el plan con los 4 puntos y ve trabajandolos hasta completar"
- L2: Stack is linear (#65 base main ... #71 base feat/editorial-visual-style), main unprotected, history uses merge commits. Issue #72 points 2-7 stay out of scope (not in the 4 points).
- L3: "rubric fallback" = 5208b57: a contains/matches check bound to a missing section widens to the whole draft. Math normalization is pandoc's own spelling. Both need a user decision.
- L4: Verifier noted residual risk: carrying also fills a criterion a full (non --since) verify forgot, when its section is unchanged; marker lists it under carried_criteria.
