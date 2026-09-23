# Visual connector validation (#10)

## Objective
Deny `VISUAL_PASS` when final report diagrams contain obstructed, crossing, crowded or misdirected connectors, using renderer-real geometry, both on the isolated SVG and at final printed size in the PDF.

## Problem / why
Visual validation only asks the agent to eyeball geometry (`skills/academic-visual-builder/references/visual-workflow.md:63`). The August SDD change `complete-visual-connector-validation` planned the fix; its implementation froze on a provider defect (gentle-ai#3129). Its phase 1 (`7f321f6`) existed only on an archive tag.

## Route
ODD delegated direct (user decision 2026-09-22: "flujo directo aplica odd"). The SDD artifacts in Engram are the design guidance, not an active SDD run:
- spec `sdd/complete-visual-connector-validation/spec` (#6402)
- design `sdd/complete-visual-connector-validation/design` (#6403)
- tasks `sdd/complete-visual-connector-validation/tasks` (#6404): named RED tests R1-R7, fixtures, 0.80 clearance, final-size stage.

## Constraints
- Strict TDD: on (source: user global config). Runner: `.venv/bin/python -m pytest tools/ tests/`.
- Stdlib-only geometry; derive from parsed SVG data; no new flags. Do not cherry-pick `551dd27`/`db6c326`.
- Delivery: forecast ~1,050-1,250 lines, over the 400 budget. One PR per slice, each merged to `main` in turn after its native review (stacked-to-main; supersedes the August feature-branch-chain because slices now merge sequentially).
- RDD: on (global); review per slice.

## Tasks
- [x] T1 (SDD phase 1, PR1) recover parser/corpus `7f321f6` as `bba66ec` `feat(visual): parse renderer-real connectors`. Route: delegated writer (cherry-pick, clean auto-merge in `tools/visual_builder.py`).
- [x] T2 (SDD phase 2, PR2) `feat(visual): protect connector routes`: R2-R6 in `tools/test_connector_geometry.py` (protected regions, crossing vs touching, 0.80 clearance, source/target/direction, actionable evidence, chart silence) with the named fixtures. Route: delegated writer.
- [x] T3 (SDD phase 3, PR3) `feat(visual): enforce final-size connector gate`: R7 in `tools/test_connector_pdf_stage.py`, contract REDs in `tests/skills/test_visual_builder_contract.py`, `tools/connector_pdf_stage.py`, `tools/validate_report.py`, SKILL.md and `visual-workflow.md` rules. Route: delegated writer.
- [x] T4 (post-T1 native review, non-blocking findings) `fix(visual): harden connector parsing`: RED tests first for — edge/node id parsing breaking on underscores (`connector_geometry.py:43`), SVG path sampling ignoring relative commands/other unhandled commands (`:89-114`), circle nodes not resolved as node regions (`:130-152`), the "fix" boundary-grazing-only detection (`:281-286`), unguarded connector audit letting parse exceptions escape `visual_builder.py` instead of becoming a reported finding (`:387-392`), missing integration/edge-case coverage (`test_connector_geometry.py:72-84`), plus the minor misplaced constant comment and node-id-holding-the-label naming. Route: delegated writer.
- [x] T5 (post-T2/T3 native review, non-blocking findings) `fix(visual): close connector gate gaps from review`: RED tests first for — transversal crossings landing exactly on a polyline vertex and genuine collinear segment overlap escaping detection entirely (`connector_geometry.py` crossing check, ~490-604), the `mmdc-touching-clean.svg` fixture hiding exactly that crossing behind a "touching" label, duplicated protected-region ownership rules between obstruction and clearance plus a cluster-label docstring/owner_id mismatch (~288, ~554-560), the final-size figure audit silently skipping an unresolved figure reference or a figure with no matching SVG (`validate_report.py:675-683`), its exception guard being too narrow to catch a malformed-SVG parse error (~693-697), and the wiring having no integration test at any commit. Two findings verified NOT to be defects and left unchanged (documented in code instead): undirected Mermaid links failing direction-marker validation matches the accepted spec text and the existing named RED fixture; unconditional crossing failure is a real spec gap but the "necessary crossing" exemption needs a dedicated obstacle-avoidance route-finding algorithm, deferred as a follow-up rather than folded into this hardening pass. Route: delegated writer.

## Acceptance
- SDD spec requirements hold with named tests observed RED then GREEN; full suite green; open connector failure denies `VISUAL_PASS`.

## Progress / evidence
- T1: `bba66ec` on `fix/visual-connector-validation`; `.venv/bin/python -m pytest tools/ tests/ -q` -> 978 passed.
- T2: `3b5fc19` `feat(visual): protect connector routes`. RED (against parent `bba66ec`, verified by
  temporarily restoring the parent's `tools/connector_geometry.py`): 5 failed —
  `test_connector_through_protected_regions_fails`, `test_unnecessary_connector_crossing_fails`,
  `test_minimum_clearance_to_edges_and_regions_fails`, `test_source_target_and_direction_defects_fail`,
  `test_connector_failure_evidence_is_actionable` (the 5 "...pass"/"...clean"/"...silent" companions
  were trivially green against the parent, since no new check existed yet to fire). GREEN: all 10 new
  tests pass (`.venv/bin/python -m pytest tools/test_connector_geometry.py -q` -> 15 passed). Full
  suite: `.venv/bin/python -m pytest tools/ tests/ -q` -> 988 passed. Shortstat:
  `11 files changed, 436 insertions(+), 9 deletions(-)`. Confirmed the new checks flow through the
  existing `tools/visual_builder.py validate` FAILURE gate unchanged (spot-checked
  `mmdc-crossing-bad.svg` -> `VALIDATION FAILED`, `mmdc-clearance-clean.svg` -> `VALIDATION_OK`).
  All 9 named phase-2 fixtures are hand-written synthetic SVGs mirroring the real mmdc DOM shape the
  parser already handles (`mmdc` itself is installed and was used to confirm the phase-1 corpus, but
  its own layout never produces these specific geometric defects deterministically); each fixture was
  iteratively verified against the implementation before being checked in.

- T3: `07bc644` `feat(visual): enforce final-size connector gate`. RED (module `connector_pdf_stage`
  did not exist; confirmed by temporarily removing the file after writing it):
  `ModuleNotFoundError` collecting `tools/test_connector_pdf_stage.py`. GREEN: all 3 R7 tests pass
  (`.venv/bin/python -m pytest tools/test_connector_pdf_stage.py -q` -> 3 passed). Contract REDs in
  `tests/skills/test_visual_builder_contract.py` (`test_visual_skill_documents_automated_connector_gate`,
  `test_visual_workflow_replaces_eyeball_instruction_with_automated_gate`) observed failing before the
  SKILL.md/visual-workflow.md edits, green after
  (`.venv/bin/python -m pytest tests/skills/test_visual_builder_contract.py -q` -> 11 passed). Full
  suite: `.venv/bin/python -m pytest tools/ tests/ -q` -> 994 passed. Shortstat:
  `9 files changed, 359 insertions(+), 24 deletions(-)`. End-to-end sanity check (outside the repo, in
  scratch): a minimal `backend: latex` report embedding the known-defect `github-workflow-page4.svg`
  produces `connector_final_size_validation` errors for `CONNECTOR_THROUGH_NODE` (FIX/RS, scale-invariant,
  matches the isolated stage) AND a `CONNECTOR_CLEARANCE` pair the isolated stage alone did not catch —
  confirming the final-print-scale stage is independent enforcement, not a restated precheck. This wires
  into `validate()` unconditionally for `backend == "latex"` (mirroring `pdf_layout`'s own unconditional
  gating), so an open failure blocks `VALIDATION_PASS`/`BUILD_PASS` before `VISUAL_PASS` is ever
  reachable; `validate_report.py` never claims to grant `VISUAL_PASS` itself (existing, tested contract
  preserved verbatim in `test_report_skill_keeps_visual_pass_owned_by_direct_semantic_inspection`).
  **Scope delivered vs. design**: derives the final print SCALE deterministically (closed-form, replaying
  `build_latex_report.py`'s own `FIGURE_WIDTH_FRACTION`/`FIGURE_MAX_HEIGHT_FRACTION` formula against each
  template's parsed `\usepackage[...]{geometry}` margins) and re-audits connector geometry at that scale,
  with clearance measured against a fixed physical minimum in PDF points
  (`MIN_CLEARANCE_PRINT_PT = 2.0`, documented in `connector_pdf_stage.py`). Page number and exact
  top-left position (the full placement-receipt/PDF-hash binding the original design specified) remain
  OUT of scope: investigated and confirmed genuinely unavailable — LaTeX float placement decides those at
  compile time and there is no cheap, stdlib-only way to recover them after the fact (`pdfimages -list`
  reports per-image dimensions/DPI, never a bounding box). Diagram-to-SVG resolution assumes a same-stem
  `.svg` sibling next to the `\includegraphics`-referenced PNG/PDF asset; this convention is not yet
  verified against a real generated report (no PDF exists in this checkout — content lives in the
  separate `CONTENT_ROOT`), only against a hand-built scratch report.

- T4: `c0257d6` `fix(visual): harden connector parsing`. RED (all 6 new tests, observed failing before
  their fix): `test_edge_ids_with_underscored_node_labels_resolve` (CONNECTOR_PARSE on a valid
  underscored label), `test_sample_path_supports_relative_and_line_only_commands` (relative `l`
  misread as absolute), `test_circle_node_shape_is_resolved` (0 nodes instead of 1), two graze tests
  (`test_multi_segment_endpoint_graze_is_exempt` false-positive; its `..._beyond_epsilon_still_fails`
  companion was already correctly green and stayed green), and
  `test_connector_audit_parse_error_becomes_a_reported_finding` in the new
  `tools/test_visual_builder_validate.py` (raw `xml.etree.ElementTree.ParseError` escaping uncaught).
  GREEN: `.venv/bin/python -m pytest tools/test_connector_geometry.py tools/test_visual_builder_validate.py -q`
  -> 21 passed. Full suite: `.venv/bin/python -m pytest tools/ tests/ -q` -> 1000 passed. Shortstat:
  `6 files changed, 243 insertions(+), 26 deletions(-)`. Scope: the underscore-id fix required
  restructuring `parse_svg` into a node-then-edge two-pass (real mmdc emits `g.edgePaths` before
  `g.nodes`, so a single pass never has the label set an ambiguous split needs); the "fix" grazing
  defect turned out to be a real false-positive risk (contiguous multi-segment grazes from a curved
  departure were checked segment-by-segment, flagging the second segment as an unrelated traversal) and
  is now measured as one contiguous run per the same `CONTACT_EPS` budget. The `Node.id`-holds-the-label
  rename was intentionally NOT done (would ripple through `Edge.source/target`,
  `ProtectedRegion.owner_id`, and the whole T2/T3 test suite); addressed with a clarifying docstring
  instead, noted honestly as a scope choice rather than the full rename.

- T5: `37d0560` `fix(visual): close connector gate gaps from review`. RED (all new/changed tests,
  observed failing before their fix): `test_transversal_crossing_through_a_shared_vertex_is_detected`
  and `test_collinear_overlapping_segments_are_detected_as_crossing` (no `CONNECTOR_CROSSING` reported —
  both escaped detection entirely, confirmed against the pre-fix `crossing_issues`); the existing
  `test_shared_endpoint_and_touching_are_not_crossings` against the ORIGINAL `mmdc-touching-clean.svg`
  content (its second edge pair crossed transversally at a shared vertex and was silently passing,
  confirming R2-touching-fixture-hides-crossing before the fixture was rebuilt as a genuine tangential
  touch); `test_cluster_label_region_has_no_owner_id` (`owner_id == 'my-svg-cluster-A'` instead of `''`);
  and, in the new `tools/test_validate_report_connector_wiring.py` (verified RED by temporarily
  restoring the parent's `tools/validate_report.py` via `git checkout`):
  `test_unresolved_figure_reference_is_reported_not_silently_skipped`,
  `test_figure_without_matching_svg_is_reported_not_silently_skipped` (both silent, no warning) and
  `test_malformed_svg_becomes_a_reported_error_not_a_crash` (uncaught `xml.etree.ElementTree.ParseError`
  propagating out of `connector_final_size_validation`). GREEN:
  `.venv/bin/python -m pytest tools/test_connector_geometry.py tools/test_connector_pdf_stage.py tools/test_visual_builder_validate.py tools/test_validate_report_connector_wiring.py tests/skills/test_visual_builder_contract.py -q`
  -> 43 passed. Full suite: `.venv/bin/python -m pytest tools/ tests/ -q` -> 1008 passed. Shortstat:
  `6 files changed, 290 insertions(+), 21 deletions(-)`.
  Findings addressed: R3-transversal-vertex-and-overlap-escape (new `_polyline_passes_through_vertex`/
  `_collinear_overlap_length` checks feeding `_edges_cross`, reused by `crossing_issues` and therefore
  by `connector_pdf_stage.py`'s final-size stage too); R2-touching-fixture-hides-crossing (fixture
  rebuilt with the touching edge's tip landing tangentially on the other edge, both neighbour points on
  the same side); R2-duplicated-region-ownership-rules (`_node_text_endpoint_exemption`/
  `_is_own_edge_label` now the single source both `obstruction_issues` and `pairwise_clearances` read,
  no behavior change, protected by the full existing T2 suite staying green); R2-cluster-owner-docstring-
  mismatch (`_cluster_label_regions` now sets `owner_id=""` matching `ProtectedRegion`'s own documented
  contract; dead data before the fix, since no exemption check ever read cluster `owner_id`);
  R4-fail-open-unresolved-figures/R3-silent-figure-skip (`connector_final_size_validation` now appends
  a warning naming the figure for an unresolved reference or a missing SVG sibling, instead of a bare
  `continue`); R3-narrow-audit-exception/R4-narrow-exception-guard (except clause widened to
  `(OSError, ValueError, ET.ParseError)`); R2-docstring-contradicts-silent-skip (resolved by the same
  fix — the function's own docstring already promised "never silently skipped"); R2-final-rule-
  misdescribed-in-workflow (`visual-workflow.md` now states the warn-not-skip behavior explicitly);
  R3-untested-wiring (new `tools/test_validate_report_connector_wiring.py`: clean, final-size-defect,
  unresolved-reference, missing-sibling and malformed-SVG cases against `connector_final_size_validation`
  itself, not just `connector_pdf_stage` directly).
  Two findings verified NOT real defects (or real but out of proportionate hardening scope) and left
  unchanged, with the reasoning recorded as a docstring at the point of decision so it survives independent
  of this task file: R3-undirected-links-fail — the spec's "Endpoints and direction" requirement is
  unconditional ("every connector MUST ... use a defined end marker"), the checked-in
  `mmdc-direction-bad.svg` RED fixture already encodes "no end marker" as a failure by accepted design,
  and there is no SVG-only signal to distinguish a legitimately undirected `---` link from a broken
  marker; supporting it would need a new spec scenario, not a hardening fix. R3-all-crossings-fail — real
  against the spec's literal text (crossing should only fail "when a non-crossing route exists or the
  crossing makes direction ambiguous"), but the design's own prescribed fix is a full obstacle-expanded
  orthogonal visibility graph; no diagram in the real corpus currently exercises an unavoidable crossing,
  and an incorrect from-scratch route-finding heuristic risks the opposite, worse failure mode (a real
  defect silently exempted as "necessary"). Deferred as a dedicated follow-up ODD task, not folded into
  this response.

## Next step
Issue #10's four planned slices (T1-T4) plus the T5 post-review hardening pass are complete on this
branch. One real, disclosed gap remains open for a future task: the spec's "necessary crossing" exemption
(obstacle-avoidance route-finding) is not implemented; `crossing_issues` conservatively fails every
crossing instead. Delivery (PR review/merge per the stacked-to-main strategy) is the user's decision
under ordinary repository policy; no further ODD task is queued unless new findings arrive.
