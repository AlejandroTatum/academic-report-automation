# Document Workflow Specification

## Purpose

Define the simplified document workflow: adaptive intake that reuses supplied consigna/rubric/context, exactly one Document Contract confirmation before generation, need-driven research with traceable evidence, and unchanged build/publication/approval controls. The product is university-first, not exclusive.

## Requirements

### Requirement: Adaptive Intake Reuses Supplied Inputs

Intake (academic-report-builder) MUST reuse supplied consigna, rubric, context, and configuration inputs instead of re-asking for them. It MUST ask only for missing consequential information derived from the confirmed route and supplied inputs, and MUST NOT introduce new permanent intake questions. When supplied inputs conflict, intake MUST surface the conflict in the Document Contract instead of silently resolving it.

#### Scenario: Known consigna and rubric are reused

- GIVEN the user supplies a consigna and rubric covering audience, purpose, and required sections
- WHEN intake runs
- THEN supplied inputs are treated as answered and the agent asks only for missing consequential items (for example, route-specific metadata such as subject or teacher on the academic route)

#### Scenario: Missing consequential information is asked, nothing more

- GIVEN the confirmed route requires metadata absent from supplied inputs
- WHEN intake runs
- THEN the agent asks exactly for that missing information and renders the Document Contract from known plus newly confirmed data

#### Scenario: Conflicting inputs are surfaced

- GIVEN the consigna and the prompt state contradictory deliverables
- WHEN intake runs
- THEN the conflict is stated in the rendered Document Contract for explicit user resolution, and no option is selected silently

### Requirement: Single Document Contract Confirmation Gate

The system MUST render the Document Contract and obtain exactly one explicit user confirmation before generation on every execution, regardless of input completeness. Adaptivity MUST change data gathering only; it MUST NOT bypass, duplicate, or remove the one-confirmation gate.

#### Scenario: Complete inputs still require one confirmation

- GIVEN all consequential inputs are supplied and no clarifying questions are needed
- WHEN intake completes
- THEN the Document Contract is rendered and generation does not start until the user explicitly confirms it once

### Requirement: University-First Routing Without Forced Identity

The system MUST keep the academic (university) route first-class while preserving personal, project, business, and technical/programming routes. Non-academic documents MUST NOT receive university identity (logos, covers, ensayo templates). All existing templates, assets, logos, and route profiles MUST be preserved without modification or deletion.

#### Scenario: Non-academic brief routes without university branding

- GIVEN a personal or technical document brief
- WHEN the route is confirmed and the document is built
- THEN a non-academic route and non-institutional template are used and no UNL logo, cover, or ensayo identity appears in the output

#### Scenario: Academic brief keeps the institutional shell

- GIVEN an academic consignment with rubric
- WHEN the document is built on the academic route
- THEN the institutional shell, profile, rubric mirroring, and confirmed citation style are preserved as before

### Requirement: Need-Driven Research Trigger

The agent MUST evaluate research need at intake from the confirmed brief and the local inspected source corpus. Two activation paths are explicitly separate: (a) the conditional automatic trigger, which MUST fire only when required claims in the confirmed brief — including non-academic briefs, not exclusively rubric-required claims — are not covered by local inspected (`inspected: true`) sources, with source freshness considered when judging coverage; and (b) explicit user research requests, which MUST activate research-workflow regardless of the automatic trigger's outcome.

#### Scenario: Covered claims need no research

- GIVEN required claims in the confirmed brief are covered by local inspected sources
- WHEN the automatic trigger is evaluated
- THEN it does not fire and the builder proceeds from reused inputs

#### Scenario: Uncovered claims trigger the evidence handoff

- GIVEN required claims in a confirmed brief — academic or non-academic — lack coverage by inspected sources
- WHEN the automatic trigger is evaluated
- THEN it fires, connecting the builder to research-workflow, and the returned evidence package is consumed as evidence, never as document intake

#### Scenario: Explicit research request is preserved

- GIVEN the user explicitly requested research regardless of coverage
- WHEN intake runs
- THEN research-workflow runs via the explicit-request path even though the automatic trigger's coverage condition is not met

### Requirement: Evidence Traceability and Eligibility Boundaries

The evidence package MUST preserve claim-level provenance, confidence, limitations, conflicts, and unresolved questions. Bibliography eligibility requires that a source's actual content was inspected and its provenance supports the claim — local and external inspected sources are equally eligible. Uninspected or unverified sources MUST remain visible leads excluded from the bibliography; leads are never cited. Inaccessible or stale sources MUST be flagged as limitations, not concealed, and are never presented as cited evidence; limitations MUST remain traceable into the built document.

#### Scenario: Lead is not cited

- GIVEN an evidence package mixes eligible inspected entries (local or external) and leads
- WHEN the builder composes the bibliography
- THEN only eligible entries are cited and leads remain visible for follow-up

#### Scenario: Conflicting or inaccessible evidence stays visible

- GIVEN two sources conflict or a key source is inaccessible or stale
- WHEN the evidence package is handed off
- THEN the conflict and the access/freshness limitation are recorded and carried into report limitations instead of being dropped, and the inaccessible source is not cited

### Requirement: Unchanged Build, Publication, and Approval Controls

This change MUST NOT introduce new `report.yml` schema fields, orchestrators, backends, or route/backend redesigns. Existing build, validation gates, versioned publication, and approval behavior (semantic-inspection-only `VISUAL_PASS`; `HUMAN_REVIEW` against immutable hashes before `READY_TO_SUBMIT`) MUST remain unchanged.

#### Scenario: Pipeline controls unchanged

- GIVEN a confirmed contract and report content
- WHEN the document is built and delivered
- THEN build, validation, publication, and approval flow through the existing pipeline with no new schema, backend, or approval step

### Requirement: Labeled Acceptance Evidence

Acceptance claims MUST label static contract tests as static-contract evidence, distinct from real runtime evidence. Before archive, one representative rendered smoke validation (build, validate gates, semantic review posture) on the existing pipeline MUST remain a visible outstanding acceptance item until executed; it MUST NOT be silently dropped or pre-claimed.

#### Scenario: Static tests are not claimed as runtime proof

- GIVEN static contract tests pass for intake and research wording
- WHEN acceptance is reported
- THEN the report labels them as static-contract evidence and separately lists the before-archive rendered smoke validation as still outstanding until performed
