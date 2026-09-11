# Document Workflow Orchestration Specification

## Purpose

Define a stateless, artifact-derived phase-status layer for the document workflow: no persisted run ledger, one status recomputation per call, a fail-closed approval gate for publication, an explicit research-evidence disk path, a portable status output contract, and a thin orchestrating skill that delegates each phase to the existing skill executors.

## Requirements

### Requirement: Stateless Artifact-Derived Phase Status

The system MUST derive the current phase and its `done|current|pending|blocked` state solely from on-disk artifacts under `$REPORT_CONTENT_ROOT/reports/<work-folder>/`, `build/`, `outputs/`, and the delivery folder. `tools/doc_status.py` MUST NOT read or write any run ledger, ID, or persisted state machine, and MUST recompute the full derivation on every invocation.

| Phase | Derived from | `done` when |
|---|---|---|
| intake | `report.yml` | exists with `route:` and route-mandatory fields |
| research | `research/evidence-matrix.md` | file exists, or `report.yml` records `research: skipped` |
| preview | `preview.md` | exists and non-empty |
| approval | `approval.yml` | exists and `preview_sha256` matches current `preview.md` |
| generate | `build/`, `outputs/<materia-slug>/<final>.pdf` | PDF present and not older than the approved preview |
| validate | validator output or RDD receipt | recorded pass for that artifact hash |
| deliver | `~/Documents/<category>/<slug>/<slug>-vNNN.pdf` | published or hash-matched reuse |

#### Scenario: Fresh work folder starts at intake

- GIVEN a work folder with no `report.yml`
- WHEN `doc_status` runs
- THEN the current phase is `intake`, every later phase is `pending`, and no run record is read or created

#### Scenario: Two independent calls agree without shared state

- GIVEN a work folder with `report.yml` and `preview.md` on disk
- WHEN `doc_status` is invoked twice in separate processes with no shared cache
- THEN both invocations report the identical current phase and summary derived only from the files present

#### Scenario: Optional research recorded on disk is derivable

- GIVEN `report.yml` records `research: skipped` and no evidence-matrix file exists
- WHEN `doc_status` runs
- THEN the research phase is reported `done`, not `blocked` or `pending`

### Requirement: Fail-Closed Approval Gate

Publication and the `generate` phase MUST remain unreachable until an `approval.yml` marker exists under the work folder and its recorded `preview_sha256` matches the SHA-256 of the current `preview.md`. `approval.yml` MUST record `preview_sha256`, `approved_at`, and `approved_by`. The system MUST NOT auto-create, auto-repair, or silently refresh a stale or absent marker; a human MUST re-run the approval phase to produce a new one.

#### Scenario: Marker absent blocks generation

- GIVEN a work folder with a non-empty `preview.md` and no `approval.yml`
- WHEN `doc_status` computes `next`
- THEN `next` is `approval`, never `generate`, and no publication command is reachable from the reported route

#### Scenario: Marker stale after preview changes

- GIVEN `approval.yml` records a `preview_sha256` that does not match the current `preview.md` hash
- WHEN `doc_status` runs
- THEN approval is reported `blocked` (stale), the current phase returns to `approval`, and `next` is never `generate`

#### Scenario: Marker current unblocks generation

- GIVEN `approval.yml` records a `preview_sha256` matching the current `preview.md` hash
- WHEN `doc_status` runs
- THEN approval is reported `done` and `next` advances to `generate`

#### Scenario: Stale marker is never auto-repaired

- GIVEN a stale `approval.yml` as above
- WHEN any phase executor or `doc_status` call runs
- THEN no process rewrites `preview_sha256`, `approved_at`, or `approved_by` automatically; only an explicit human approval action produces a new marker

### Requirement: Portable Status Output Contract

Every `doc_status` invocation MUST render two blocks: a human-facing block and a machine-facing block under schema `academic.doc-status/v1`. The human block MUST front-load a `**Gate**`/handoff line before the summary whenever a gate is pending or blocked, MUST show exactly one route line with the current phase in brackets (for example `intake > research > [preview] > approval > generate > validate > deliver`), MUST list phases as a flat `**Summary**` bullet list using only the ASCII tokens `done`, `current`, `pending`, `blocked`, and MUST end with a `**Next**` line. The human block MUST NOT use markdown tables, nested headers, box-drawing characters, or non-ASCII status symbols. The machine block MUST mirror the `gentle-ai.sdd-status` field shape: schema identifier, next bounded token, summary, blocked reasons, and a JSON payload.

#### Scenario: Pending gate is front-loaded

- GIVEN the approval phase is pending
- WHEN `doc_status` renders the human block
- THEN the `**Gate**` line appears before `**Summary**` and names the pending approval action

#### Scenario: No pending gate omits the gate line

- GIVEN every phase up to and including the current one is `done` and none is `blocked`
- WHEN `doc_status` renders the human block
- THEN no `**Gate**` line is rendered and the block starts directly with the route line

#### Scenario: Output renders without unicode or tables

- GIVEN any workflow state
- WHEN `doc_status` renders the human block
- THEN the output contains no markdown table syntax, no box-drawing characters, and no non-ASCII status glyphs

#### Scenario: Machine block matches the SDD status field shape

- GIVEN any workflow state
- WHEN `doc_status` renders the machine block
- THEN it declares schema `academic.doc-status/v1` and includes a next bounded token, a summary, a blocked-reasons field, and a JSON payload, matching the field shape used by `gentle-ai.sdd-status`

### Requirement: Thin Orchestrating Skill With Single-Artifact Phases

`skills/document-workflow/SKILL.md` MUST route exclusively from the `next` token returned by `doc_status`; it MUST NOT re-implement intake, research, build, validation, or publication logic. Each phase referenced by the orchestrator MUST be delegated to its existing executor skill (`academic-report-builder`, `research-workflow`) and MUST produce exactly one artifact consumed by the derivation table. Every gate presented to the user MUST follow the lossless blocking-prompt contract: complete options, consequences, and exact allowed answers, with no silent default.

#### Scenario: Orchestrator routes without reading executor internals

- GIVEN a user asks how to proceed on an in-progress work folder
- WHEN the orchestrator responds
- THEN it states the route and next action derived from `doc_status` output alone, without requiring the user or the agent to read `academic-report-builder` or `research-workflow` internals to understand where the run is

#### Scenario: Each phase yields exactly one artifact

- GIVEN the orchestrator delegates the preview phase to its executor
- WHEN the phase completes
- THEN exactly one artifact (`preview.md`) exists that the derivation table reads, with no additional undocumented side files required for status derivation

#### Scenario: Approval gate presented losslessly

- GIVEN the approval phase is reached
- WHEN the orchestrator presents the confirmation prompt
- THEN it states plainly that generation happens only after this approval, presents the complete decision with no partial or reworded envelope, and does not proceed on silence

### Requirement: Runtime-Agnostic Validation With RDD Fallback

The validate phase MUST use `gentle-ai review` (receipt-driven development) when RDD is enabled for the repository, and MUST fall back to the existing rendered validation chain (`validate_report.py`, auditor prechecks, semantic inspection) when RDD is off or its status is unknown. Both paths MUST enforce the same gates (`BUILD_PASS`, `VALIDATION_PASS`, `VISUAL_PASS`, `HUMAN_REVIEW`, `READY_TO_SUBMIT`); the fallback MUST NOT lower or skip any gate reachable under RDD.

#### Scenario: RDD on delegates to native review

- GIVEN receipt-driven development is enabled for the repository
- WHEN the validate phase runs
- THEN it uses `gentle-ai review` for the applicable check and the resulting status feeds the same gate names as the fallback path

#### Scenario: RDD off or unknown uses the existing chain

- GIVEN receipt-driven development is disabled or its status cannot be determined
- WHEN the validate phase runs
- THEN it runs the existing rendered validation chain and enforces the identical gate set, without treating the unknown state as a reason to skip a gate

### Requirement: Cross-Runtime Skill Distribution

`document-workflow` MUST be added to `scripts/sync_skills.sh` alongside the existing skill targets, including a Codex target, and the sync process MUST invoke `gentle-ai skill-registry refresh`. When the `gentle-ai` binary is absent, the refresh step MUST be skipped without failing the sync.

#### Scenario: Sync includes the new skill and Codex target

- GIVEN `scripts/sync_skills.sh` runs
- WHEN it completes
- THEN `document-workflow` is present among the synced runtime targets, including Codex

#### Scenario: Missing binary does not fail the sync

- GIVEN `gentle-ai` is not installed on the machine running the sync
- WHEN `scripts/sync_skills.sh` runs
- THEN the registry refresh step is skipped and the overall sync still exits successfully

### Requirement: Issue #21 Phase and Gate Visibility Acceptance

The orchestrated workflow MUST satisfy the acceptance criteria behind issue #21: the route is explainable without reading skill source files, research output is labeled as pre-document evidence rather than confirmed intake, the approval gate states that generation happens only after approval, phase transitions are surfaced to the user, the single-confirmation rule from `document-workflow` is preserved, and the orchestration layer is reusable unchanged across the three cooperating skills.

#### Scenario: Research output is labeled as evidence, not intake

- GIVEN the research phase hands off an evidence matrix
- WHEN the orchestrator reports phase status
- THEN the evidence package is labeled as pre-document evidence input, never as confirmed document intake

#### Scenario: Phase transitions are surfaced

- GIVEN a phase completes and the workflow advances
- WHEN the next `doc_status` call runs
- THEN the rendered status reflects the new current phase, so the transition is visible to the user without inspecting files manually

#### Scenario: Single confirmation rule is preserved end to end

- GIVEN the orchestrated workflow runs from intake through delivery
- WHEN the full route is traced
- THEN exactly one human confirmation gate exists in the route (post-preview approval), matching the `document-workflow` single-confirmation requirement

#### Scenario: Orchestration layer is reusable across the three skills

- GIVEN the orchestrator delegates to `academic-report-builder` and `research-workflow`
- WHEN a third cooperating skill (for example a future visual builder) is added
- THEN the same `doc_status` derivation and status contract apply without orchestrator-specific rewrites for that skill
