# Proposal: Document Workflow Orchestration Skill

## Intent

Issue #21: execution phases and gates are invisible. Three skills cooperate (`academic-report-builder`, `research-workflow`, `academic-visual-builder`) but phase and gate state is scattered across their sections, so the user cannot see where a run is, what is done, or what blocks next. This change wires only `academic-report-builder` and `research-workflow` into the orchestrating skill; `academic-visual-builder` is intentionally deferred and out of scope (see the reusability scenario in `specs/document-workflow-orchestration/spec.md`). Issue #11: the research handoff is conversational with no disk path, so the research phase is not derivable.

Two safety defects follow from the same gap: the only human confirmation (the intake "Document Contract") fires **before any content exists**, and the versioned PDF publishes automatically right after technical validation with no human decision in between.

Success: every transition renders one explicit status block (route, current phase, what completed, what is next, pending gate/handoff); exactly one human confirmation, placed **after** a content preview; publication fail-closed behind that confirmation; no persisted run state machine.

## Scope

### In Scope

- `tools/doc_status.py` (~150 lines) + `tools/test_doc_status.py` — stateless, artifact-derived phase status; human-facing block plus machine block `academic.doc-status/v1`.
- `skills/document-workflow/SKILL.md` + `references/{intake,research,preview,approval,generate,validate,deliver}.md` — thin orchestrator that delegates each phase to the existing skills as executors.
- New content-root artifacts: `reports/<work-folder>/preview.md` and `reports/<work-folder>/approval.yml` (approval marker, hash-bound to the preview).
- Fail-closed approval gate: absent or stale marker means `next` can never be `generate`, and publication is gated behind it.
- `tools/approval_marker.py` + `tools/test_approval_marker.py` — one shared pure helper that reads and validates the marker, consumed by both the status tool and the publisher.
- Approval guard inside `tools/publish_pdf.py::publish_validated_pdf`: it verifies the marker before publishing and aborts on an absent, stale, or malformed one, so the gate binds every entry point rather than only the orchestrated path.
- Move the single confirmation from intake to post-preview; intake collects data only (targeted clarification for a missing mandatory field is allowed, an approval is not).
- Explicit research evidence path: `reports/<work-folder>/research/evidence-matrix.md`.
- `tests/skills/test_document_workflow_contract.py` (static contract test, existing style).
- `scripts/sync_skills.sh`: add `document-workflow`, a Codex target, and `gentle-ai skill-registry refresh`.

### Out of Scope

- Visual/typographic quality of the generated PDF (deferred to a future change).
- The parked W1 state machine: persistence, ledger, idempotency, bounded retries, any run record on disk.
- Rewriting the internal logic of the three existing skills (only their references change).
- Literal reuse or forking of `gentle-ai sdd-status`, `sdd-continue`, `sdd-attempt`.
- Changes to `report.yml` schema beyond the research-skip key.
- Changes to build/validate/publish tool internals beyond the approval guard in `publish_validated_pdf` (versioning, content addressing, atomic `os.link` claiming, hash continuity, and the validation chain itself are untouched).

## Capabilities

### New Capabilities

- `document-workflow-orchestration`: artifact-derived phase derivation, the status output contract, phase-executor delegation, and the research evidence disk path.

### Modified Capabilities

- `document-workflow`: `Single Document Contract Confirmation Gate` (the single confirmation moves from intake to post-preview) and `Unchanged Build, Publication, and Approval Controls` (publication becomes gated behind the approval marker instead of automatic after technical validation).

## Approach

Approach 1 from exploration: artifact-only status, no run ledger. Loop is always `doc_status -> next -> phase executor -> exactly one artifact -> doc_status`.

**Two-root split preserved.** Status derives only from content-root artifacts. `preview.md` and `approval.yml` live under `$REPORT_CONTENT_ROOT/reports/<work-folder>/`, never the code root.

**Artifact-to-phase derivation (sketch; design pins exact keys):**

| Phase | Derived from | `done` when |
|---|---|---|
| intake | `reports/<wf>/report.yml` | exists with `route:` and route-mandatory fields |
| research | `reports/<wf>/research/evidence-matrix.md` | file exists, or `report.yml` records `research: skipped` |
| preview | `reports/<wf>/preview.md` | exists and non-empty |
| approval | `reports/<wf>/approval.yml` | exists and `preview_sha256` matches current `preview.md` |
| generate | `build/`, `outputs/<materia-slug>/<final>.pdf` | PDF present and not older than the approved preview |
| validate | validator output (or RDD receipt) | recorded pass for that artifact hash |
| deliver | `~/Documents/<category>/<slug>/<slug>-vNNN.pdf` | published or hash-matched reuse |

Optional research stays derivable because skipping is recorded on disk, not in agent memory.

**Staleness rule.** `approval.yml` records `preview_sha256`, `approved_at`, `approved_by`. `doc_status` recomputes the preview hash on every call; a mismatch marks approval `blocked` (stale), returns the current phase to `approval`, and makes `generate` unreachable. The marker is never auto-refreshed or repaired.

**Status output.** Human block: front-loaded `**Gate**`/handoff line before the summary, one route line with the current phase in brackets (`intake > research > [preview] > approval > generate > validate > deliver`), `**Summary**` flat bullets with ASCII tokens `done|current|pending|blocked`, then `**Next**`. No tables, nested headers, box-drawing, or unicode symbols (research C8–C13). Machine block mirrors the `gentle-ai.sdd-status` field shape under schema `academic.doc-status/v1`.

**Gentle AI reuse, runtime-agnostic.** `gentle-ai review` (RDD) serves the validate phase when RDD is on, falling back to the existing rendered validation chain when off or unknown — the fallback keeps the same gates, it does not lower them. `gentle-ai skill-registry refresh` handles distribution; Engram holds cross-session run memory; gates follow the lossless blocking-prompt contract.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `tools/doc_status.py`, `tools/test_doc_status.py` | New | Stateless derivation + status rendering |
| `tools/approval_marker.py`, `tools/test_approval_marker.py` | New | Shared pure marker check; canonical `sha256_file` home |
| `tools/publish_pdf.py` | Modified | Required `work_folder` keyword-only argument; approval guard before any write; `sha256_file` re-exported for existing callers |
| `tools/test_pdf_publication.py` | Modified | Eight call sites gain `work_folder=`; new absent/stale/malformed refusal tests |
| `tools/build_report_auto.py` | Modified | One call site passes `work_folder=config.folder` |
| `tools/test_build_report_auto.py` | Modified | `assert_called_once_with` at :361 gains the new argument |
| `skills/document-workflow/` | New | Thin orchestrator, one reference per phase |
| `tests/skills/test_document_workflow_contract.py` | New | Static markdown-contract test |
| `tests/skills/test_sync_skills.py` | Modified | Covers the new skill, the Codex target, and the non-fatal registry refresh |
| `skills/academic-report-builder/references/document-intake.md` | Modified | Intake collects data only; no approval block |
| `skills/academic-report-builder/references/automation-contract.md` | Modified | Publication gated behind the approval marker |
| `skills/research-workflow/references/research-protocol.md` | Modified | Names the evidence-package disk path |
| `scripts/sync_skills.sh` | Modified | New skill, Codex target, registry refresh |
| `openspec/specs/document-workflow/spec.md` | Modified | Two requirements changed via delta |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Fail-closed gate is safety-critical | Med | Strict TDD: cover marker absent, stale (hash mismatch), malformed, and current, at both the status tool and the publisher |
| `build_report_auto.py` (including `--validate-only`) stops publishing for unapproved folders | Med | Intentional and documented; the failure message names the missing or stale marker and the approval phase that produces it |
| Adding a required argument to `publish_validated_pdf` breaks callers | Low | Only one production call site (`build_report_auto.py:132`); a required keyword-only parameter turns any missed caller into an immediate `TypeError` instead of a silent bypass |
| Skill-name collision with a Gentle AI registry entry | Med | Verify `document-workflow` against the registry before the skeleton slice |
| `.githooks/post-checkout` runs `sync_skills.sh --apply`; adding registry refresh changes checkout behavior | Med | Make the refresh step non-fatal and skipped when the binary is absent |
| Change exceeds the 400-line review budget | High | `auto-chain` delivery, four slices below |
| Two-root split leaked by writing new artifacts to the code root | Low | Paths resolved through `tools/report_config.py`; test asserts content-root placement |
| Renderer fidelity for OpenCode/Pi unverified (research gap) | Low | Lowest-common-denominator ASCII output; no tables or nested headers |

## Rollback Plan

All new files are additive; revert the branch to restore current behavior. The three modified reference files are text-only edits with no data migration. Existing `reports/<work-folder>/` folders keep working: `preview.md` and `approval.yml` are simply absent. Reverting `tools/publish_pdf.py` and `tools/build_report_auto.py` (a required argument and a guard block, no schema or storage change) plus `automation-contract.md` restores automatic publication. No `report.yml` rewrite is required.

## Dependencies

- `gentle-ai` binary optional at runtime (registry refresh, RDD validate); both paths must degrade cleanly when it is absent.
- `.githooks/post-checkout` behavior after `sync_skills.sh` changes.
- Existing `tools/report_config.py` two-root resolution.

## Delivery Forecast

Delivery strategy `auto-chain`, 400-line review budget per PR. Five chained slices; the safety-critical publication guard lands first, and each later PR targets the previous slice's branch:

1. `tools/approval_marker.py` + tests, the `publish_validated_pdf` guard, and the updated publication/build call sites and assertions (~310 lines).
2. `tools/doc_status.py` + `tools/test_doc_status.py` (derivation, staleness, both output blocks; consumes the slice 1 helper) (~370 lines).
3. `skills/document-workflow/` skeleton + `tests/skills/test_document_workflow_contract.py` (~300 lines).
4. Existing-skill reference updates (intake approval removal, publication gate, research evidence path) + updated builder contract test (~150 lines).
5. `scripts/sync_skills.sh` + `tests/skills/test_sync_skills.py` registry/Codex wiring (~60 lines).

## Success Criteria

- [ ] `doc_status.py` returns the correct phase for every state in the derivation table, from disk alone, with no persisted run record.
- [ ] With no approval marker, or with a marker whose hash does not match `preview.md`, `next` is never `generate` and publication does not run — enforced both by the router and by `publish_validated_pdf`, so a direct `build_report_auto.py` invocation also refuses and creates no file.
- [ ] Exactly one human confirmation exists in the route, and it occurs after the content preview.
- [ ] The status block renders route, summary, next, and a front-loaded gate/handoff line using only ASCII tokens and flat sections.
- [ ] A completed research evidence package has a fixed disk path that `doc_status` reads.
- [ ] The three existing skills keep their internal logic; only their references change.
