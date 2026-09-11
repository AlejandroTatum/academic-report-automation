# Proposal — simplified-document-workflow

Phase: proposal (planning only). Store: openspec. Review budget: 400 lines, ask-on-risk. No implementation, spec, design, or tasks authored here.

## Intent

Simplify the document workflow so supplied consigna/rubric/config input is reused instead of re-asked, while keeping exactly one explicit Document Contract confirmation before generation. Research becomes need-driven with preserved claim-level traceability and eligible/lead boundaries. The product remains university-first but not exclusive: personal and technical/programming documents keep their routes, and no university identity is forced onto non-academic output. Build, validation gates, publication, and clean delivery behavior are unchanged.

## Scope

In scope (skill/reference updates plus tests and conversation fixtures only):

1. **Adaptive intake.** Amend `skills/academic-report-builder/references/document-intake.md` and matching SKILL.md wording: reuse supplied consigna/rubric/context; ask only missing consequential questions derived from the confirmed route and inputs; introduce no new permanent intake questions; keep the single Document Contract confirmation gate unchanged (adaptivity changes data gathering, never the one-confirmation-before-generation gate).
2. **Conditional research trigger.** The agent evaluates research need at intake from the confirmed brief and inspected available sources (`source_library.py` corpus): research runs only when route/rubric-required claims are not covered by local inspected sources. Document the trigger criteria in research-workflow skill/protocol. No new `report.yml` field; eligibility (`inspected: true` → eligible, else `lead`) is preserved.
3. **Contract tests and fixtures.** Update `tests/skills/test_report_builder_routing.py` (notably `test_confirmation_is_required_on_every_execution`, lines 164–169, which currently asserts the literal "every execution|every run" and "even when the prompt appears to already contain") and adjacent static assertions; add research-trigger contract tests alongside the 7-test `tests/skills/test_research_workflow_contract.py`; extend `tests/skills/conversation-cases.md`.

Non-goals: no new orchestrator, no route/backend redesign, no `report.yml` schema change, no template/asset modification or deletion, no model changes, no publication/delivery behavior change, and no changes to `scripts/sync_skills.sh` or `tests/skills/test_sync_skills.py` (uncommitted sync fix — preserve). This proposal is a scope document for user approval; it confers no implementation authority.

## Affected areas

`skills/academic-report-builder/` (SKILL.md, references/document-intake.md), `skills/research-workflow/` (SKILL.md, references/research-protocol.md), `tests/skills/` (two test files plus conversation-cases.md). Skills sync outward through the preserved sync script; `tests/skills/` is the enforcement point.

## Success criteria

1. Intake reuses supplied inputs, asks only missing consequential questions, and renders exactly one Document Contract confirmation before generation; static contract tests enforce the new wording with RED→GREEN evidence recorded.
2. Research is need-driven: the trigger decision is documented, evaluated from the confirmed brief and inspected sources, and preserves traceability, limitations, and the eligible/lead split.
3. Evidence-driven acceptance scenario: a conversation fixture demonstrates the research handoff — intake → trigger decision → evidence package (claim-level provenance, eligible entries separated from leads) → builder consumes the package without treating it as document intake.
4. Later, before archive: one representative rendered smoke validation on the existing pipeline (build → validate gates → semantic review posture). Static contract tests are explicitly distinct from real runtime evidence; nothing here claims research or build behavior is already demonstrated.

## Risks

- Static-text tests are weak proxies for runtime behavior (exploration §5); mitigated by the deferred representative rendered smoke validation and explicit evidence labeling.
- Adaptive intake could regress into skipping the confirmation gate; mitigated because the one-confirmation gate is settled scope and remains asserted.
- Agent-judged research triggering could over-trigger; mitigated by bounded criteria (only uncovered route/rubric-required claims).
- Skill sync is gated on `tests/skills/`; the uncommitted sync fix must stay untouched.

## Rollback

All changes are markdown references, static tests, and fixtures — fully reversible via git revert. No schema, tooling, asset, or model migrations exist to unwind.

## Review workload (rough)

Two skill reference areas, two test files, one fixture document — a small, single-area diff expected to sit under the 400-line budget; no exact line counts are fabricated here.

## Proposal question round

Waived by the confirmed pre-proposal handoff: university-first-not-exclusive with all assets/routes preserved; adaptive grillme-style intake integrated into the existing builder with one confirmation; need-driven research with traceability; semantic/rendered review and clean delivery unchanged. Exploration §9 is resolved toward the skills-only scope (slices 1–2); execution-level validation (slice 3) remains a later parent decision.
