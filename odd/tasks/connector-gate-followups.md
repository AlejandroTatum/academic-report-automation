# Connector gate follow-ups (#43)

## Objective
Stop the connector gate from over-blocking correct diagrams, and make every geometry error a reported finding instead of a crash.

## Problem / why
After #10: undirected Mermaid links (`A --- B`) fail the direction check because the August spec required an end marker on every connector; every crossing fails, although the spec only rejects unnecessary or ambiguous crossings; some malformed geometry raises `IndexError` in the audit guards of `tools/visual_builder.py` and `tools/validate_report.py`, which also differ from each other.

## Decisions
- 2026-09-23, user: undirected links are valid when the `.mmd` source declares them (`---`, `-.-`, `===` without arrowheads). Direction and marker checks apply only to connectors declared with an arrow. Supersedes the August rule "every connector MUST use a defined end marker".
- Necessary-crossing exemption is conservative: a crossing is exempt only when the gate proves no alternative route avoids it; when in doubt it keeps failing.

## Scope (authorized 2026-09-22 "ataca los issues pendientes"; decision above 2026-09-23)
- `tools/connector_geometry.py`, `tools/visual_builder.py`, `tools/validate_report.py`, `tools/connector_pdf_stage.py`, related tests, `skills/academic-visual-builder/` docs.

## Constraints
- Strict TDD: on (source: user global config). Runner: `.venv/bin/python -m pytest tools/ tests/`.
- Derive from existing data (the `.mmd` source next to the SVG, parsed geometry); no new flags.
- RDD: on; one review per slice.

## Tasks
- [x] T1 undirected links: read the declared link type from the `.mmd` source (same stem as the SVG); skip direction/marker checks for undirected links; missing source falls back to the current strict rule and reports that it did. Route: delegated writer.
- [x] T2 one shared guard helper for both audit entry points that turns any geometry exception (including `IndexError`) into a finding. Route: delegated writer.
- [x] T3 necessary-crossing exemption: exempt a crossing only when no alternative route around protected regions exists; otherwise fail. Route: delegated writer.
- [x] T4 (coordinator follow-up, post-delivery review) mirrored-specs-tree lookup: the real pipeline stores `.mmd` specs under `visuals/specs/<materia>/<tarea>/` and renders under `assets/generated/<materia>/<tarea>/`, never as siblings, so T1's sibling-only lookup never found a real source. Try the sibling first, then the mirrored `visuals/specs` path derived from the SVG's own path. Route: delegated writer.

## Acceptance
- #43 expected behavior holds with tests observed RED then GREEN; full suite green; spec note updated in the visual-builder references.

## Progress / evidence
- Branch `fix/connector-gate-followups` from `main` 19648cb.
- T1 done, commit `ee8ef33` (9 files changed, 276 insertions(+), 22 deletions(-)).
  - RED: `test_parse_link_directions_classifies_declared_link_types`,
    `test_undirected_link_declared_in_source_skips_direction_check`,
    `test_undirected_link_without_source_falls_back_to_strict`,
    `test_no_sibling_source_reports_strict_mode_informational_finding`,
    `test_multiple_links_between_same_pair_match_by_ordinal` (tools/test_connector_geometry.py)
    plus `test_undirected_link_declared_in_source_skips_direction_check_at_final_size`,
    `test_no_sibling_source_reports_strict_mode_informational_finding_at_final_size`
    (tools/test_connector_pdf_stage.py) — all observed failing before the implementation.
  - GREEN: same tests pass after `connector_geometry.py`
    (`parse_link_directions`, `load_link_directions`, `direction_issues`,
    `audit_diagram`, `audit_connector_geometry`) and `connector_pdf_stage.py`
    (`audit_final_size`, `audit_svg_at_final_size`) changes.
  - Fixtures: real `mmdc` captures (`mmdc-undirected-clean.svg/.mmd`,
    `mmdc-undirected-multi.svg/.mmd`), rendered via
    `tools/visual_builder.py mermaid` with the installed `mmdc`; reused
    existing sourceless fixtures (`mmdc-direction-clean.svg`) for the
    no-source fallback case.
  - Full suite: `.venv/bin/python -m pytest tools/ tests/` — 1187 passed.

- T2 done, commit `dd03ea5` (7 files changed, 119 insertions(+), 18 deletions(-)).
  - RED: `test_malformed_path_data_raises_indexerror_uncaught` (documents the
    underlying defect, stays RED forever by design),
    `test_connector_audit_indexerror_becomes_a_reported_finding`
    (tools/test_visual_builder_validate.py),
    `test_indexerror_becomes_a_reported_error_not_a_crash`
    (tools/test_validate_report_connector_wiring.py) — both observed
    failing (uncaught `IndexError`) before wiring `run_geometry_audit` in.
    Note: `run_geometry_audit` itself and its two direct unit tests
    (`test_run_geometry_audit_converts_indexerror_into_a_finding`,
    `..._passes_through_a_clean_result`) were written together with the
    helper rather than test-first — a narrow TDD-ordering gap on that one
    low-level function; the two entry-point wiring tests carried the real
    RED/GREEN evidence for #43's reported behavior.
  - GREEN: same tests pass after adding
    `connector_geometry.run_geometry_audit` and wiring it into
    `visual_builder.py`'s `command_validate` and
    `validate_report.py`'s `connector_final_size_validation`, replacing
    both previously-divergent `except (...)` tuples.
  - Fixture: `mmdc-malformed-indexerror.svg` (synthetic, deliberately
    malformed `d` path data — odd coordinate count triggers the crash).
  - Full suite: `.venv/bin/python -m pytest tools/ tests/` — 1192 passed.

- T3 done, commit `1d5cb89` (5 files changed, 233 insertions(+), 15 deletions(-)).
  - Approach: a conservative obstacle-aware visibility check (standard
    corner visibility graph over `{edge source, edge target} + every
    obstacle bbox corner`, obstacles = nodes/regions the edge does not own,
    bounded by the diagram's own viewBox). A crossing is exempt only when
    the search proves NEITHER edge can reach its own endpoints without
    crossing the other edge's exact rendered polyline (checked one edge at
    a time, per the accepted decision's own wording: "every route for one
    of the edges must cross the other"). Obstacle-interior blocking allows
    boundary-touching (legitimate routing around a corner); blocking by the
    *other* edge itself is inclusive of any touch, not just a strict
    interior cross (closes a hairline "graze one point, flip sides"
    loophole found during fixture verification). `MAX_VISIBILITY_VERTICES`
    (60) bounds state; past it the proof is inconclusive and the crossing
    keeps failing, the same default as finding an actual route.
  - Regression caught before commit: the pre-#43 always-fail fixtures
    (`mmdc-crossing-bad.svg`, and the T5 shared-vertex synthetic fixture)
    briefly turned GREEN-but-wrong after the first exemption pass, because
    a node placed outside the declared viewBox (deliberately, in those
    older fixtures) made the edge's OWN endpoint fall outside bounds,
    trapping the search into a false "no route" verdict. Fixed by
    expanding the effective bounds to always include the edge's own
    start/end before running the search — bounds constrain the
    alternative-route search area, never the edge's own required
    endpoints. `test_existing_crossing_fixtures_stay_unexempt` pins this.
  - RED/GREEN evidence: `_has_alternative_route`/`_crossing_is_provably_necessary`
    were developed together with their direct tests (ad hoc verification
    scripts first, formal pytest tests after) rather than strict
    test-first — disclosed TDD-ordering gap, same as T2's low-level
    helper. The regression cycle above IS genuine RED (two long-standing
    tests failed) → GREEN (fixed, same tests pass) evidence for the
    soundness-critical bounds handling.
    New tests: `test_k3_3_style_forced_crossing_is_exempt`,
    `test_avoidable_crossing_still_fails_despite_open_space`,
    `test_existing_crossing_fixtures_stay_unexempt`,
    `test_inconclusive_proof_keeps_failing_past_the_vertex_budget`
    (tools/test_connector_geometry.py).
  - Fixtures: hand-crafted synthetic SVGs (following this module's existing
    convention for slice-2 geometry fixtures, real mmdc cannot produce
    exact provable-topology layouts):
    `mmdc-crossing-necessary.svg` (four corner nodes, two full-diagonal
    connectors sealed to the viewBox — provably unavoidable, passes clean
    except the expected no-`.mmd`-source informational finding) and
    `mmdc-crossing-avoidable.svg` (same shape with generous open margin —
    a real route around exists, still fails).
  - Scope note: `connector_geometry.py` core addition is 150 lines
    (`git diff --stat`), well inside the ~350-line advisory budget.
  - Full suite: `.venv/bin/python -m pytest tools/ tests/` — 1196 passed.

- T4 done, commit `b6a9b3c` (4 files changed, 93 insertions(+), 18 deletions(-)).
  - RED: `test_mirrored_specs_tree_source_is_found_when_no_sibling_exists`
    (observed failing: fell back to strict + `CONNECTOR_DIRECTION_NO_SOURCE`
    before the fix). `test_sibling_source_takes_priority_over_the_mirrored_specs_tree`
    passed immediately (no new behavior exercised there, sibling lookup
    already worked) — added as a regression pin, not RED evidence.
  - GREEN: same test passes after `connector_geometry.py`'s
    `_mirrored_specs_path`/`_source_candidates`/`load_link_directions`
    changes; `connector_pdf_stage.py`'s informational-finding message text
    updated to match (no behavior change there, sibling-then-mirror lookup
    is shared via `load_link_directions`).
  - Full suite: `.venv/bin/python -m pytest tools/ tests/` — 1198 passed.

- T5 (native review hardening, post-delivery) done, commit `9c1cf7e`
  (5 files changed, 202 insertions(+), 51 deletions(-)). Native review of
  #43 approved with 5 WARNINGs; all verified real (no skips) and fixed:
  - R3-visibility-graph-omits-blocker-vertices: RED
    `test_alternative_route_around_blockers_tip_is_found` (a direct-diagram
    fixture with zero other obstacles — a trivial detour around a
    2-point blocker was wrongly ruled "unavoidable"). GREEN after adding
    blocker's own vertices to the visibility graph, exempting only the
    one blocker segment adjacent to a shared pivot vertex.
  - R2-no-bounds-inconclusive-contradiction /
    R2-provably-necessary-docstring: RED
    `test_no_declared_bounds_is_inconclusive_not_a_false_exemption`
    (`_has_alternative_route(..., bounds=None)` returned `False`, i.e.
    granted exemption, contradicting its own docstring). GREEN after
    returning `None` immediately when bounds are absent; both docstrings
    updated to state the inconclusive contract explicitly.
  - R3-link-regex-o-x-node-prefix: RED
    `test_link_regex_does_not_mistake_ox_prefixed_target_for_a_terminator`
    (`"A --- ox"` parsed target as `"x"`, dropping the leading `o`).
    GREEN after adding a negative lookahead so `o`/`x` only terminates as
    a circle/cross marker when not immediately followed by another
    identifier character.
  - R4-mmd-read-failure-masks-geometry-audit: RED
    `test_unreadable_mmd_source_falls_back_to_strict_mode` (a non-UTF-8
    `.mmd` raised `UnicodeDecodeError` out of `load_link_directions`).
    GREEN after catching `(OSError, UnicodeDecodeError)` per candidate
    source and falling through to the next candidate / strict mode.
  - R3-no-source-info-dropped-in-validate: RED
    `test_no_source_informational_finding_is_shown` (`visual_builder.py
    validate` filtered to `FAILURE`-only, dropping
    `CONNECTOR_DIRECTION_NO_SOURCE` entirely). GREEN after printing INFO
    findings alongside `VALIDATION_OK`/`VALIDATION FAILED`.
  - Regression: the T3 `mmdc-crossing-necessary.svg` fixture broke under
    the corrected (more sound) algorithm — its old topology relied on the
    exact loophole R3 closed. Redesigned as a fully sealed pocket for N1
    using overlapping wall pieces (each nominal wall corner buried inside
    the neighbouring wall's interior) with blocker's own endpoints buried
    the same way; `mmdc-crossing-avoidable.svg` and `mmdc-crossing-bad.svg`
    remain correctly un-exempt.
  - Full suite: `.venv/bin/python -m pytest tools/ tests/` — 1203 passed.

## Next step
All tasks (T1-T5) done. Remaining: push and open a PR (not done by this
writer — see delivery contract).
