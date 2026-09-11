# Delta for Document Workflow

## MODIFIED Requirements

### Requirement: Single Document Contract Confirmation Gate

The system MUST render the Document Contract during intake for data confirmation only, without seeking approval to generate at that point. The single explicit user confirmation gate MUST occur after a content preview (`preview.md`) is produced, and generation MUST NOT start until that post-preview confirmation is given exactly once. Adaptivity MUST change data gathering only; it MUST NOT bypass, duplicate, remove, or relocate the one-confirmation gate away from post-preview.

(Previously: the Document Contract confirmation was the single gate and fired at intake, before any content existed.)

#### Scenario: Complete inputs still require one post-preview confirmation

- GIVEN all consequential inputs are supplied and no clarifying questions are needed
- WHEN intake completes and a content preview is produced
- THEN the confirmation gate is presented after the preview, and generation does not start until the user explicitly confirms it once

#### Scenario: Intake confirms data, not generation

- GIVEN intake renders the Document Contract with confirmed type, audience, purpose, template/identity, outputs, and visual direction
- WHEN the user confirms the contract data
- THEN the workflow proceeds to produce a preview, and no generation or publication step is authorized by that intake-time confirmation alone

#### Scenario: Preview change re-triggers the single gate

- GIVEN the post-preview confirmation gate was already presented once for a given preview
- WHEN a confirmed field changes and the preview is regenerated
- THEN the gate is presented again for the new preview, and the prior confirmation does not carry over

### Requirement: Unchanged Build, Publication, and Approval Controls

This change MUST NOT introduce new `report.yml` schema fields (beyond the research-skip key defined in `document-workflow-orchestration`), orchestrators, backends, or route/backend redesigns. Existing build and validation gates (`BUILD_PASS`, `VALIDATION_PASS`) MUST remain unchanged. Versioned PDF publication (`VERSIONED_PDF_PUBLISHED_OR_REUSED`) MUST NOT run automatically after technical validation; it MUST be gated behind a current, hash-matched `approval.yml` marker as defined in `document-workflow-orchestration`. Semantic-inspection-only `VISUAL_PASS` and `HUMAN_REVIEW` against immutable hashes before `READY_TO_SUBMIT` MUST remain unchanged.

(Previously: publication ran automatically right after technical validation with no human decision gating it, and no schema or gate distinction for approval-gated publication existed.)

#### Scenario: Pipeline controls unchanged except publication gating

- GIVEN a confirmed contract and report content
- WHEN the document is built and delivered
- THEN build and validation flow through the existing pipeline with no new schema, backend, or approval step, and publication additionally requires a current approval marker before it runs

#### Scenario: Publication does not run without a current approval marker

- GIVEN technical validation (`VALIDATION_PASS`) has passed for the built artifact
- WHEN no `approval.yml` marker exists, or an existing marker's `preview_sha256` does not match the current preview
- THEN `VERSIONED_PDF_PUBLISHED_OR_REUSED` does not execute and the artifact is not copied to the delivery folder

#### Scenario: Publication proceeds once approval is current

- GIVEN technical validation has passed and `approval.yml` records a `preview_sha256` matching the current preview
- WHEN the generate/publication phase runs
- THEN the existing atomic publication behavior (first unique artifact `v001`, hash-matched reuse, monotonic versioning without overwriting a concurrent publisher) proceeds unchanged
