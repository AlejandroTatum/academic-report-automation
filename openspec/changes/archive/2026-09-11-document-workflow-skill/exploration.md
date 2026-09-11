# Exploration: document-workflow-skill

Date: 2026-09-10
Phase: sdd-explore (content produced by the explore actor; persisted by the orchestrator because the actor has no write tool)
Supersedes: active change `document-workflow-orchestrator` (branch `feat/document-workflow-orchestrator-w1`, never merged; parked by user decision)
Motivating issues: #21 (surface execution phases and gates explicitly), #11 (evidence-first research)

## Confirmed Product Decisions (do not reopen)

1. Replace the W1 state machine (`tools/document_workflow.py`: persistence, ledger, idempotency, bounded retries) with a **stateless, artifact-derived** status tool plus a thin orchestrating skill, following the shape of Gentle AI's `gentle-sdd-*` skills.
2. Route: `intake -> research (optional) -> preview -> approval GATE -> generate -> validate -> deliver`. The loop is always `doc_status -> next -> phase executor -> one artifact -> doc_status`.
3. **Option A for the single human confirmation**: the only approval moves from the intake "Document Contract" to *after* the content preview. Intake collects data only; it may ask a targeted clarification for a missing mandatory field, but never an approval. The gate is fail-closed: without an approval marker on disk, `next` can never be `generate`. Auto-publish after validation is therefore gated behind that marker.
4. Reuse Gentle AI as-is where it fits and stays runtime-agnostic (Claude Code, Codex, OpenCode, Pi): `gentle-ai skill-registry refresh` for distribution, `gentle-ai review` (RDD) as the validate phase when enabled (fallback: existing rendered validation), Engram for cross-session run memory, the lossless blocking-prompt contract for gates.
5. Do **not** reuse `gentle-ai sdd-status`, `sdd-continue`, or `sdd-attempt` literally: they are bound to OpenSpec artifacts, code semantics, and strict-TDD forwarding.

## Current State

Three skills cooperate today but scatter phase and gate visibility across sections (the core complaint of #21):

- `skills/academic-report-builder/` owns intake (`references/document-intake.md`: five confirmations rendered as a "Document Contract" block, confirmed conversationally before drafting), routing (`references/document-routing.md`, routes A-E written to `report.yml` as `route:`), and build/validate/publish (`references/automation-contract.md`, `references/quality-gates.md`, `references/clean-delivery.md`). Readiness chain: `BUILD_PASS -> VALIDATION_PASS -> VERSIONED_PDF_PUBLISHED_OR_REUSED -> ... -> VISUAL_PASS -> HUMAN_REVIEW -> READY_TO_SUBMIT`.
- `skills/research-workflow/` produces a claim-level evidence package (`assets/evidence-matrix-template.md`) but hands it off conversationally; `references/research-protocol.md` names **no disk path** for the completed matrix. This blocks artifact-based derivation of the research phase.
- `skills/academic-visual-builder/` has its own readiness chain scoped to figures.

On-disk artifacts today (content root separate from the code root per `tools/report_config.py`):

| Artifact | Path | Produced by |
| --- | --- | --- |
| Report source | `reports/<work-folder>/{report.yml,body.md,sources.bib}` | intake + drafting |
| Intermediates | `build/`, `backups/` | `tools/build_report_auto.py` |
| Technical PDF copy | `outputs/<materia-slug>/<final>.pdf` | build + `tools/validate_report.py` |
| Visual QA | `visual_qa.md`, `contact_sheet.png` | `tools/visual_pdf_auditor.py` |
| Delivered PDF | `~/Documents/<category>/<slug>/<slug>-vNNN.pdf` | `tools/publish_pdf.py::publish_validated_pdf` (content-addressed, atomic `os.link`), tested by `tools/test_pdf_publication.py` |

Gaps relative to the confirmed route:

- No content-preview artifact exists.
- No fail-closed approval marker exists; the only gate today is the intake confirmation, which happens before any content exists.
- PDF publication is automatic right after technical validation, with no gate.
- The research handoff has no fixed disk path.

Infrastructure:

- `scripts/sync_skills.sh` syncs the three skills to `~/.config/opencode/skills` and `~/.claude/skills`, gated on `tests/skills/*_contract.py`. No Codex target, no `gentle-ai skill-registry refresh` step. `.githooks/post-checkout` runs `sync_skills.sh --apply` on branch checkout.
- Test conventions: flat `tools/test_*.py` beside the module under test; `tests/skills/test_*_contract.py` static markdown-contract tests (for example `tests/skills/test_report_builder_routing.py`).
- `openspec/` did not exist on `main`. The orchestrator imported `openspec/config.yaml`, `openspec/specs/document-workflow/spec.md`, and the archived change `2026-09-05-simplified-document-workflow` from the parked branch so this change can write a delta against the existing `document-workflow` spec. The parked active change `document-workflow-orchestrator` was intentionally not imported.
- Native `gentle-ai.sdd-status/v2` shape (see `~/.claude/skills/_shared/sdd-status-contract.md`): markdown header, `schema:`, `next:` (bounded token), `### Summary`, `### Blocked Reasons`, `### JSON`. `doc_status.py` mirrors this shape with its own schema name.

## Affected Areas

- `skills/document-workflow/SKILL.md` + `references/{intake,research,preview,approval,generate,validate,deliver}.md` (new): thin orchestrator, one reference per phase.
- `tools/doc_status.py` + `tools/test_doc_status.py` (new, ~150-line target): artifact-to-phase derivation with a concrete mapping table; preview and approval-marker artifacts must be designed since they do not exist yet.
- `tests/skills/test_document_workflow_contract.py` (new): static contract test in the existing style.
- `scripts/sync_skills.sh`: add `document-workflow`, a Codex target, and `gentle-ai skill-registry refresh`.
- `skills/research-workflow/references/research-protocol.md`: explicit disk path for the evidence package.
- `skills/academic-report-builder/references/{document-intake.md,automation-contract.md}`: remove the intake approval, gate publication behind the approval marker.
- `openspec/specs/document-workflow/spec.md`: delta must MODIFY "Single Document Contract Confirmation Gate" and "Unchanged Build, Publication, and Approval Controls".

## Approaches

1. **Artifact-only status; new `preview.md` and approval marker under the content-root report folder** (recommended). Reads `report.yml` (intake), a research subfolder or evidence file (research), `preview.md` (preview), an approval marker bound to the preview's hash (gate), `build/` + `outputs/` (generate), validator output (validate), delivered PDF presence (deliver). Pros: preserves the two-root privacy split, reuses build/validate/publish tools unchanged, matches the confirmed order exactly. Cons: touches three existing skills' references; needs staleness rules (a preview edited after approval invalidates the marker). Effort: medium.
2. **Single run-manifest `workflow.yml` with phase flags.** Trivial reader, but reintroduces a persisted record close to the rejected W1 design. Effort: medium. Not recommended.
3. **No new files; approval only in Engram.** Not disk-verifiable by a stateless tool; violates the fail-closed requirement. Non-viable.

## Recommendation

Approach 1. Proposal and design must pin: (a) exact `preview.md` and approval-marker paths inside `reports/<work-folder>/` (never the code root); (b) the research-package disk path; (c) the `doc_status.py` artifact-to-phase table with staleness rules (hash-binding the marker to the preview, echoing the W1a-1 integrity-guard idea without the ledger); (d) the `validate` phase contract for RDD on/off.

## Risks

- Skill-name collision with a Gentle AI-shipped registry entry: verify `document-workflow` before finalizing.
- `.githooks/post-checkout` runs `sync_skills.sh --apply`; adding `skill-registry refresh` changes hook behavior on every checkout.
- Total change likely exceeds the 400-line PR budget; delivery strategy is `auto-chain`. Candidate slices: (1) `doc_status.py` + tests; (2) `skills/document-workflow/` skeleton + contract test; (3) existing-skill reference updates (intake, publication gate, research path); (4) `sync_skills.sh` + registry wiring.
- Fail-closed gate correctness is safety-critical: tests must cover marker absent, marker stale (hash mismatch), and marker current.

## Ready for Proposal

Yes. Product decisions are confirmed (Option A), exploration is persisted, and the OpenSpec store is scaffolded on branch `feat/document-workflow-skill`.
