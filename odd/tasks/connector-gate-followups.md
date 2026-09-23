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
- [ ] T1 undirected links: read the declared link type from the `.mmd` source (same stem as the SVG); skip direction/marker checks for undirected links; missing source falls back to the current strict rule and reports that it did. Route: delegated writer.
- [ ] T2 one shared guard helper for both audit entry points that turns any geometry exception (including `IndexError`) into a finding. Route: delegated writer.
- [ ] T3 necessary-crossing exemption: exempt a crossing only when no alternative route around protected regions exists; otherwise fail. Route: delegated writer.

## Acceptance
- #43 expected behavior holds with tests observed RED then GREEN; full suite green; spec note updated in the visual-builder references.

## Progress / evidence
- Branch `fix/connector-gate-followups` from `main` 19648cb.

## Next step
Delegate T1-T3.
