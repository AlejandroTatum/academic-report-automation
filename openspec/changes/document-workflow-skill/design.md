# Design: Document Workflow Orchestration Skill

## Technical Approach

One pure derivation function turns on-disk artifacts into phase states; two renderers project that value; a thin skill routes from the projected `next` token to an existing executor skill. No run ledger, no persisted state machine, no new orchestration logic inside the three cooperating skills.

The approval gate is enforced twice from one shared helper: the orchestrated path can never route to `generate` without a current marker, and `publish_validated_pdf` itself refuses to publish without one. The second guard is what makes the spec sentence "publication MUST remain unreachable until an `approval.yml` marker exists" literally true for every entry point, including a direct `build_report_auto.py` invocation.

Layering (Clean/Hexagonal, matching the repo's existing `tools/` style):

    reports/<wf>/{report.yml,research/,preview.md,approval.yml,validation.yml}
    outputs/<materia>/<final>.pdf   ~/Documents/<cat>/<slug>/<slug>-vNNN.pdf
                     |
                     v  (read-only, no writes, no subprocess)
          approval_marker.approval_state()  ->  ApprovalState (pure value)
                     |                                    |
        doc_status.derive() -> DocStatus         publish_pdf.publish_validated_pdf()
                     |                                    |
          render_human()   render_machine()      abort with PublicationError
                     |                           unless state is `current`
        skills/document-workflow/SKILL.md routes on next
                     |
      academic-report-builder | research-workflow | (approval: human gate)

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| D1 | Derivation is a pure function over paths; renderers are separate | one `main()` that prints while deriving | golden-testable renderers; derivation is testable without string matching |
| D2 | Approval marker on disk, hash-bound to `preview.md` | Engram-only marker; run manifest `workflow.yml` | a stateless tool can only fail closed against disk; a manifest reintroduces the parked W1 ledger |
| D3 | `doc_status` never shells out and never touches `gentle-ai` | probe RDD inside the tool | keeps the tool deterministic, offline and hermetically testable; RDD state is a skill-level concern |
| D4 | The approval gate is enforced in BOTH places: `doc_status` never routes to `generate`, and `publish_validated_pdf` refuses to publish without a current marker | gate only at the orchestration entry point | a workflow-only gate leaves a direct tool invocation ungated; the spec sentence is unconditional, so the publisher must enforce it too |
| D5 | `doc_status` does not parse `preview.md` sections | schema-validate the preview | structure is a skill contract enforced by the static contract test; keeps the tool near 150 lines |
| D6 | One shared pure module `tools/approval_marker.py` owns the marker contract and the canonical `sha256_file`; `publish_pdf` re-exports `sha256_file` | duplicate the hash in the new module; keep `sha256_file` in `publish_pdf` and import `approval_marker` lazily inside the function to dodge the cycle | one hash implementation and a one-directional import graph with no lazy imports; the re-export keeps `build_report_auto.py:19` and the existing publication tests untouched |
| D7 | Build `ReportConfig` directly, not via `load_report_config` | call the loader | the loader raises `SystemExit` on an unknown route; a status tool must report, never exit |
| D8 | Machine block on stdout, human block on stderr under `--json` | `--json` suppresses the human block | every invocation still renders both blocks (spec), and stdout stays parseable |
| D9 | `work_folder` is a REQUIRED keyword-only parameter of `publish_validated_pdf` | optional parameter defaulting to `None` and refusing at runtime | a required parameter makes omission a `TypeError` at the call site, so no future caller can silently skip the guard; fail-closed by construction, not by a runtime check |
| D10 | The guard raises the existing `PublicationError` | a new exception type | `build_report_auto.py:138` already catches `PublicationError` and exits with `PDF PUBLICATION FAILED: <reason>`; no caller error handling changes |

## Artifact Schemas

**`reports/<wf>/report.yml`** — additive key only: `research: skipped` (string, trimmed, case-insensitive). Any other value or absence means research is not skipped. Intake-mandatory fields stay `report_config.ROUTE_REQUIRED_METADATA` resolved through `ReportConfig.metadata` (academic: title, subject, teacher, student, date; every other route: title, student, date).

**`reports/<wf>/preview.md`** — fixed H2 sections, ASCII, written by the preview executor:

    # Content Preview: <title>
    ## Contract Summary     -> Route, Type, Audience, Purpose, Template/identity, Outputs, Visual direction
    ## Outline              -> numbered sections, one-line intent each
    ## Evidence             -> "<section> - <claim id> -> <source locator>" or "none (no external claims)"
    ## Output Type          -> "Output type: PDF | DOCX | PDF+DOCX | VISUAL"

**`reports/<wf>/approval.yml`** — written only by the approval phase:

```yaml
schema: academic.doc-approval/v1
preview_sha256: <64 lowercase hex of the exact preview.md bytes>
approved_at: <ISO-8601 UTC, e.g. 2026-09-10T14:03:11Z>
approved_by: <non-empty human identity>
```

Approval happens only after an explicit human answer to the lossless gate prompt. Silence, an inferred yes, a restated plan, or an agent decision never produce this file; a decline writes nothing. No process ever rewrites or repairs an existing marker — the publisher reads it and refuses, it never creates or heals it.

**`reports/<wf>/research/evidence-matrix.md`** — the completed matrix, pre-document evidence only.

**`reports/<wf>/validation.yml`** — validate-phase receipt, identical shape in both RDD branches:

```yaml
schema: academic.doc-validation/v1
artifact_sha256: <hash of the final PDF that was validated>
result: pass | fail
mode: rdd | fallback
gates: [BUILD_PASS, VALIDATION_PASS, ...]
recorded_at: <ISO-8601 UTC>
evidence: backups/quality_report.md | <opaque acknowledged review identifier>
```

## Component Contracts

`tools/approval_marker.py` (~60 lines, pure, read-only, stdlib + PyYAML via `report_config.read_yaml`):

```python
PREVIEW_NAME = "preview.md"
MARKER_NAME = "approval.yml"
MARKER_SCHEMA = "academic.doc-approval/v1"
REQUIRED_KEYS = ("preview_sha256", "approved_at", "approved_by")

@dataclass(frozen=True)
class ApprovalState:
    state: str    # current | absent | stale | malformed
    reason: str   # "" | approval_marker_absent | approval_marker_stale | approval_marker_malformed
    detail: str   # short ASCII detail naming the offending file or key

def sha256_file(path: Path) -> str            # canonical home; re-exported by publish_pdf
def approval_state(work_folder: Path) -> ApprovalState
```

`approval_state` never writes, never creates a directory, and never raises for a bad marker — an unreadable or invalid marker becomes `malformed`, a missing `preview.md` with a marker present becomes `malformed` with `detail="preview.md missing"`, and a missing marker becomes `absent`. It is the single source of truth for both consumers: `doc_status` maps the state onto a phase state and a blocked reason token, `publish_pdf` maps it onto a Spanish user-facing abort message. Presentation stays at each boundary; the predicate does not.

`tools/publish_pdf.py` — the guard:

```python
def publish_validated_pdf(
    source: Path,
    category: str,
    slug: str,
    documents_root: Path | None = None,
    *,
    work_folder: Path,               # NEW, required keyword-only
    expected_sha256: str | None = None,
) -> Publication:
```

Placement: immediately after the existing `_require_pdf_file(source)` and the category/slug validation, and BEFORE `sha256_file(source)`, before `folder.mkdir(...)`, and before any temporary file — so a refused publication creates nothing anywhere on disk. The `expected_sha256` continuity check and the atomic `os.link` versioning are unchanged and still run after the guard.

The guard does not replace validation. In `build_report_auto.main` the order stays `build_backend -> sha256_file(before) -> validate(config) -> SystemExit on errors -> sha256_file(after) continuity check -> publish_validated_pdf(...)`; the approval guard is an additional gate inside the last step, not a reordering or a substitute for the rendered-validation chain.

Failure messages (Spanish, matching the module's existing `PublicationError` wording; `build_report_auto.py:138` prefixes them with `PDF PUBLICATION FAILED:`):

- absent — `Falta la aprobación humana: no existe approval.yml en {work_folder}. Ejecutá la fase de aprobación después de revisar preview.md; no se publica nada.`
- stale — `La aprobación está obsoleta: preview_sha256 de approval.yml no coincide con preview.md en {work_folder}. Volvé a aprobar el preview actual; no se publica nada.`
- malformed — `approval.yml es inválido en {work_folder}: {detail}. No se publica nada y el marcador nunca se repara automáticamente.`

The `publish_validated_pdf` docstring is amended: publication now requires both configured technical validation AND a current human approval marker, and still grants neither `VISUAL_PASS`, `HUMAN_REVIEW`, nor `READY_TO_SUBMIT`.

Call sites that must pass the new argument:

| Location | Change |
|---|---|
| `tools/build_report_auto.py:132-137` | add `work_folder=config.folder` (the loaded report folder is already in scope) |
| `tools/test_build_report_auto.py:361-366` | `publish.assert_called_once_with(...)` asserts the exact argument list and MUST gain `work_folder=config.pdf_path.parent`-equivalent (`config.folder`); `FakeReportConfig` needs a `folder` attribute |
| `tools/test_pdf_publication.py:122,134,136,146,149,175,187,194` | eight positional calls; each gains `work_folder=` pointing at an approved fixture folder |

No other production call site exists (`tools/build_latex_report.py` and `tools/build_docx_report.py` call `publish_global_output`, a different function). `tools/test_build_report_auto.py:277,355,379,397` patch the symbol with mocks that accept any keyword, so only the `assert_called_once_with` at :361 breaks.

`tools/doc_status.py` (~150 lines: derivation ~90, renderers ~45, CLI ~15):

```python
PHASES = ("intake", "research", "preview", "approval", "generate", "validate", "deliver")

@dataclass(frozen=True)
class PhaseState:   name: str; state: str; detail: str; blocked_reason: str
@dataclass(frozen=True)
class DocStatus:    work_folder: Path; phases: tuple[PhaseState, ...]; current: str
                    next_token: str; gate: str; blocked_reasons: tuple[str, ...]

def derive(folder: Path, *, documents_root: Path | None = None) -> DocStatus
def render_human(status: DocStatus) -> str
def render_machine(status: DocStatus) -> str
def main(argv: list[str] | None = None) -> int   # python tools/doc_status.py <work-folder> [--json]
```

`state` is exactly one of `done|current|pending|blocked`. `next_token` is a `PHASES` member or `done`. Exit 0 for any derivable folder (blocked is data, not process failure); exit 2 for a missing, non-directory, or unreadable folder argument.

Per-phase derivation and staleness:

| Phase | done when | blocked when |
|---|---|---|
| intake | `report.yml` exists, route known, every route-mandatory metadata key truthy | unknown `route:` value (`unknown_route`) |
| research | `research/evidence-matrix.md` exists non-empty, or `research: skipped` | — |
| preview | `preview.md` exists and has non-whitespace content | unreadable (`preview_unreadable`) |
| approval | marker parses and `preview_sha256` == sha256(preview.md) | hash mismatch (`approval_marker_stale`), missing/blank required key or bad YAML (`approval_marker_malformed`) |
| generate | final PDF exists and `pdf.st_mtime >= approval.yml.st_mtime` | — (stale PDF returns to `pending`) |
| validate | `validation.yml` `result: pass` and `artifact_sha256` == sha256(final PDF) | `result: fail` (`validation_failed`); hash mismatch returns to `pending` |
| deliver | a `<slug>-vNNN.pdf` under `~/Documents/<category>/<slug>/` hashes equal to the final PDF | — |

An absent approval marker is `pending`, not `blocked`; both keep `next` off `generate`. Any unexpected exception while deriving a phase yields `blocked` with a reason — never `done`.

## Status Output Contract

Human block (exact shape; `**Gate**` line only when a gate is pending or blocked):

    **Gate**: approval pending - generation runs only after you approve reports/<wf>/preview.md
    Route: intake > research > [preview] > approval > generate > validate > deliver

    **Summary**
    - intake: done - route=academic, metadata complete
    - research: done - skipped in report.yml
    - preview: current - preview.md missing
    - approval: pending
    - generate: pending
    - validate: pending
    - deliver: pending

    **Next**: preview - draft reports/<wf>/preview.md, then re-run doc_status

Constraints: ASCII only (every codepoint < 128), no `|` table syntax, no `###`+ headings, exactly one route line with exactly one bracketed phase, tokens exactly `done|current|pending|blocked`.

Machine block mirrors `gentle-ai.sdd-status/v2` markdown shape — `## Document Workflow Status`, `schema: academic.doc-status/v1`, `next: <token>`, `### Summary`, `### Blocked Reasons`, `### JSON` with a fenced payload (`schemaName`, `schemaVersion`, `workFolder`, `phases`, `current`, `next`, `gate`, `blockedReasons`). The nested-header ban applies to the human block only.

## Skill Layout and Executor Routing

`skills/document-workflow/SKILL.md` (frontmatter matching repo convention: `name`, `description` with `Trigger:`, `license: Apache-2.0`, `metadata.{author,version,scope}`). Loop: run `doc_status` -> read `next` -> load only that reference -> present the human block verbatim -> delegate -> executor produces exactly one artifact -> re-run `doc_status`.

| next | reference | executor |
|---|---|---|
| intake | `references/intake.md` | `academic-report-builder` (`document-intake.md`) |
| research | `references/research.md` | `research-workflow` |
| preview | `references/preview.md` | `academic-report-builder` (composition, pre-build) |
| approval | `references/approval.md` | this skill — human gate, no executor |
| generate | `references/generate.md` | `academic-report-builder` (`automation-contract.md`) |
| validate | `references/validate.md` | `academic-report-builder` (`quality-gates.md`) or `gentle-ai review` |
| deliver | `references/deliver.md` | `academic-report-builder` (`clean-delivery.md`) |

Validate branch: read `gentle-ai review mode status` (read-only). `on` -> native review, `evidence` records the opaque acknowledged identifier, `mode: rdd`. `off`, absent binary, non-zero exit, or unparsable output -> `unknown`/`off` -> existing chain (`validate_report.py`, auditor precheck, semantic inspection), `mode: fallback`, `evidence: backups/quality_report.md`. Gate names are identical in both branches; `unknown` never lowers or skips a gate, and RDD is never enabled on the user's behalf.

Existing-skill reference edits (internal logic untouched):

- `academic-report-builder/references/document-intake.md`: the Document Contract becomes a data record written to `report.yml`; the "generation begins only after the user confirms this block" sentence is removed; intake may ask one targeted clarification per missing route-mandatory field and never asks for an approval; the single confirmation is forward-referenced to `document-workflow/references/approval.md`.
- `academic-report-builder/references/automation-contract.md`: publication is gated on a current `approval.yml`; `VERSIONED_PDF_PUBLISHED_OR_REUSED` gains the precondition `APPROVAL_CURRENT`.
- `research-workflow/references/research-protocol.md` §5: names `$REPORT_CONTENT_ROOT/reports/<work-folder>/research/evidence-matrix.md` and restates the package as pre-document evidence, never confirmed intake.

## Sequence of One Full Run

    doc_status -> next=intake     -> builder writes report.yml            -> doc_status
    doc_status -> next=research   -> research-workflow writes evidence-matrix.md (or report.yml records skipped)
    doc_status -> next=preview    -> builder writes preview.md            -> doc_status
    doc_status -> next=approval   -> lossless gate prompt -> human answers -> approval.yml written
    doc_status -> next=generate   -> build_report_auto.py                 -> outputs/<materia>/<final>.pdf
    doc_status -> next=validate   -> RDD or fallback chain                -> validation.yml
    doc_status -> next=deliver    -> publish_validated_pdf (re-checks the marker) -> ~/Documents/... vNNN.pdf
    doc_status -> next=done

The marker is checked twice on purpose: once when routing (cheap, informational) and once at the irreversible step (authoritative). A marker that goes stale between the two checks stops the run at publication rather than delivering an unapproved PDF.

## Failure Modes and Fail-Closed Behavior

| Condition | Behavior |
|---|---|
| No approval marker | approval `pending`, `next=approval`, generate unreachable; `publish_validated_pdf` aborts with the absent message and creates nothing |
| Marker hash mismatch | approval `blocked` (stale), current phase returns to approval, never auto-repaired; publication aborts with the stale message |
| Marker unparsable | approval `blocked` (malformed); never treated as absent, never deleted; publication aborts with the malformed message |
| Preview edited after approval | mismatch path above; PDF older than the marker returns generate to `pending`; a marker that goes stale after routing is still caught at publication |
| `build_report_auto.py` run directly on an unapproved folder | publication aborts and `main()` exits non-zero via the existing `PublicationError` handler; the build and validation output it already produced is kept |
| `work_folder` omitted by a future caller | `TypeError` at the call site — the guard cannot be bypassed by forgetting an argument |
| Work folder missing or not a directory | CLI exit 2, message, no phase claims `done`, nothing created |
| `gentle-ai` absent | validate uses the fallback chain with the same gates; sync skips the refresh and still exits 0 |
| Derivation exception | that phase `blocked` with a reason; later phases `pending` |

## Distribution

`scripts/sync_skills.sh`: add `document-workflow` to `SKILLS`; add `$HOME/.codex/skills` to `TARGETS` (the loop already skips a non-existent target); after the rsync loop and only when `APPLY=1`, run `command -v gentle-ai >/dev/null && { gentle-ai skill-registry refresh || echo "!! skill-registry refresh failed (non-fatal)" >&2; }` so `set -euo pipefail` cannot abort. `.githooks/post-checkout` runs `--apply` on every checkout, so the step must stay non-fatal and silent when the binary is absent.

## Threat Matrix

| Boundary | Applicability | Design response | Planned RED tests |
|---|---|---|---|
| Documentation-like paths | N/A — nothing is classified as executable; markdown/YAML is read, never run | — | — |
| Git repository selection | N/A — no `git -C` or repo selection added; `sync_skills.sh` keeps its `BASH_SOURCE` `REPO_ROOT` | — | — |
| Commit state | N/A — no commit automation | — | — |
| Push state | N/A — no push automation | — | — |
| PR commands | N/A — no PR automation | — | — |
| Optional-binary subprocess (`gentle-ai skill-registry refresh`, `review mode status`) | Applicable — absent binary, non-zero exit, unparsable output | `command -v` probe; failure non-fatal; unknown RDD routes to the fallback chain with identical gates | sync exits 0 with the binary absent; `validate.md` states unknown -> fallback (static) |
| CLI work-folder argument | Applicable — missing path, file instead of directory, path outside the content root, symlink | resolve, require a directory, exit 2 with a message, create nothing anywhere | missing folder -> exit 2; `derive()` leaves the folder listing byte-identical |
| Publisher work-folder argument (irreversible step) | Applicable — omitted argument, folder without a marker, stale/malformed marker, marker pointing at a missing preview | required keyword-only parameter; guard runs before any `mkdir`, hash, or temp file; aborts with `PublicationError` and never creates or repairs a marker | absent / stale / malformed -> `PublicationError` and the Documents folder is never created; current -> publishes exactly as today |

## Testing Strategy

`tools/test_approval_marker.py` (unit): marker absent -> `absent`; matching hash -> `current`; mismatched hash -> `stale`; bad YAML, missing `preview_sha256`/`approved_at`/`approved_by`, blank value, or missing `preview.md` -> `malformed` with the naming detail; `approval_state()` writes nothing and raises nothing.

`tools/test_pdf_publication.py` (extends the existing file, same style): marker absent -> `PublicationError`, no PDF published and `documents_root` never created; marker stale (preview edited after approval) -> `PublicationError`, nothing created; marker malformed -> `PublicationError`, nothing created; marker current -> publishes exactly as today (`v001`, hash-verified, PDF-only folder). A `_approved_work_folder(tmp_path)` fixture writes `preview.md` plus a matching `approval.yml`, and the eight existing calls listed above pass `work_folder=`. Existing reuse, monotonic-version, concurrency, and non-PDF-rejection tests keep their current assertions with the new argument added.

`tools/test_build_report_auto.py`: `test_publication_runs_after_build_and_validation_pass` (:361) asserts `work_folder=config.folder` in the call; the ordering assertion `events == ["build", "validate", "publish"]` is unchanged, proving the guard did not displace validation.

`tools/test_doc_status.py` (unit, `tmp_path` folders): intake missing/unknown-route/incomplete-metadata; research present vs `skipped` vs neither; preview empty vs non-empty; approval absent / stale / malformed / current; generate PDF older than the marker; validate pass-matching / pass-mismatched / fail; deliver hash-matched; renderer goldens with and without the gate line; ASCII-only, no `|`, no `###` in the human block; purity (no files created).

`tests/skills/test_document_workflow_contract.py` (static, existing style): required files exist; frontmatter fields; the fenced status template satisfies every human-block constraint; every executor path named in `SKILL.md` resolves on disk; `approval.md` names `preview_sha256`/`approved_at`/`approved_by` and forbids approving on silence; `generate.md` forbids building before approval is `done`; `validate.md` names both branches with the same gate set.

`tests/skills/test_report_builder_routing.py`: update `test_confirmation_is_required_on_every_execution` and `test_document_contract_block_is_specified` for the data-record wording, and assert `document-intake.md` no longer authorizes generation.

## Slice Plan (auto-chain, 400 authored lines per PR)

The publisher guard does not fit in the doc_status slice: `doc_status.py` plus its table-driven tests is already ~370 authored lines, and the guard adds ~310 more (helper, guard, eight updated publication call sites, three new refusal tests, the `build_report_auto` assertion). It therefore becomes a fifth slice, and the chain is reordered so the safety-critical gate lands FIRST rather than last.

| # | Scope | Est. lines | Must leave green |
|---|---|---|---|
| 1 | `tools/approval_marker.py` + `tools/test_approval_marker.py`, `sha256_file` moved with a re-export from `publish_pdf`, the `publish_validated_pdf` guard, updated `tools/test_pdf_publication.py`, `tools/build_report_auto.py:132`, `tools/test_build_report_auto.py:361` | ~310 | full pytest suite; publication refuses on absent/stale/malformed markers and still publishes on a current one; `build_report_auto.py:19` import untouched |
| 2 | `tools/doc_status.py` + `tools/test_doc_status.py` (consumes the slice 1 helper) | ~370 | full pytest suite; no skill or script touched |
| 3 | `skills/document-workflow/` (SKILL.md + 7 references) + `tests/skills/test_document_workflow_contract.py` | ~300 | new contract test plus every existing test, unchanged |
| 4 | `document-intake.md`, `automation-contract.md`, `research-protocol.md` + updated `tests/skills/test_report_builder_routing.py` | ~150 | full suite with the updated assertions |
| 5 | `scripts/sync_skills.sh` + `tests/skills/test_sync_skills.py` | ~60 | full suite; dry run exits 0 with `gentle-ai` absent |

PR #1 targets `feat/document-workflow-skill`; each later PR targets the previous slice's branch. Ordering rationale: slice 1 first because it is the safety gate and because slice 2 imports its helper; slice 3 after slice 2 because the references quote `doc_status` behavior; slice 4 after slice 3 because intake's forward pointer targets `document-workflow/references/approval.md`, and because slice 4's `automation-contract.md` rewrite documents a publication gate that must already exist in code — documentation and behavior stay truthful at every merge point.

## Migration / Rollout

No data migration and no `report.yml` rewrite. All new files are additive; existing `reports/<work-folder>/` folders keep working with `preview.md`, `approval.yml`, and `validation.yml` simply absent, which places them at the preview phase.

One intentional behavior change: after slice 1, `build_report_auto.py` no longer publishes a PDF for a work folder that has no current approval marker — including under `--validate-only`, which reaches the publication step today. Such a run now exits non-zero at publication with a message naming the missing or stale marker, after build and validation output has already been produced. This is the point of the change, not a regression, but it means an in-flight folder must pass through the approval phase once before its next publication. Reverting the branch restores automatic publication.

## Open Questions

None. The previously recorded residual risk — a direct `build_report_auto.py` invocation publishing without approval — is closed by the `publish_validated_pdf` guard above, so the spec requirement "publication MUST remain unreachable until an `approval.yml` marker exists" now holds literally at every entry point and needs no spec-delta edit.
