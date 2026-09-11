# Design — simplified-document-workflow

Phase: design (planning only). Store: openspec. Budget: 400 lines, ask-on-risk. Scope: skills/references + tests + conversation cases only. No implementation in this phase. Delivery: divide into reviewable units (user-authorized); no commits/PRs; no `size:exception`.

## 1. Architecture decisions

1. **Skills-only, agent-judged trigger.** The research trigger is prose criteria evaluated by the agent at intake from the confirmed brief and the local inspected corpus (`source_library.py` manifest). No `report.yml` field, no orchestrator, no Python change (exploration §9 resolved to slices 1–2).
2. **Adaptivity changes data gathering only.** The five-confirmations structure, Document Contract block, and the single confirmation-before-generation gate are untouched; intake gains a reuse rule plus missing/conflicting handling.
3. **Two separate research activation paths.** (a) Conditional automatic: fires only when claims required by the confirmed brief — any route, not only rubric-required — lack coverage by local `inspected: true` sources, with source freshness considered. (b) Explicit user request: always activates research-workflow regardless of coverage. External uninspected sources never count as coverage.
4. **Eligibility equalized explicitly.** External sources become eligible on the same terms as local once actually inspected with provenance complete; current text already implies this — one additive sentence makes it normative. Existing asserted substrings (see §5) are preserved verbatim so the 7 existing tests keep passing.
5. **Pipeline untouched.** Routes a–e, backends, `PUBLICATION_CATEGORIES`, build/validate/publish/approval flow unchanged. Non-academic no-UNL rule is already enforced (`test_unl_shell_not_loaded_outside_academic_route`, ROUTE_AGNOSTIC_FILES) and stays.

## 2. Data flow (one simple visible journey)

consigna + rubric supplied → intake reuses them (known), asks only missing consequential items derived from the confirmed route (e.g., subject/teacher on Route A), surfaces conflicts in the contract → conflicting answers resolved by the user (re-render) → Document Contract rendered once and confirmed exactly one time → **research need is evaluated from the confirmed brief** against the local inspected corpus → if uncovered or explicitly requested: research-workflow returns an evidence package (eligible vs leads, conflicts/limitations) → route written to `report.yml` by existing tooling → `build_report_auto.py` + validate gates → unchanged semantic-inspection posture → unchanged clean delivery. The contract confirmation precedes research; it is not duplicated after research returns.

**Missing vs known vs conflicting:**
- *Known*: supplied input covers a confirmation → reused verbatim and restated in the contract; never re-asked.
- *Missing*: ask exactly the missing consequential questions derived from route + supplied inputs; these are ad-hoc, never new permanent intake questions (Question scope bullet amended).
- *Conflicting*: contradiction between supplied inputs is stated in the rendered Document Contract (new optional `Conflicts:` line) for explicit user resolution; resolution re-renders the block and the user confirms the corrected contract once — no forced duplicate confirmation, nothing selected silently.

**Unsupported research safe behavior:** the earliest-failed-gate rule is preserved. If required claims lack eligible evidence after research (no accessible sources, leads only, or research cannot run), the affected gate stops the run for those claims; the gap is recorded as unresolved limitations (including inaccessible/stale flags) carried into the report limitations, leads are never cited, and nothing is fabricated. No promise that the build proceeds without required evidence — blocking at the earliest failed gate is the correct safe behavior. Existing provider/tool choices are preserved: local corpus first, no paid external research implied.

## 3. Exact file deltas

1. `skills/academic-report-builder/references/document-intake.md` (~+35/−8): rewrite opening — intake runs on every execution but treats supplied consigna/rubric/context/config as candidate answers, asks only missing consequential items, and "a prompt statement is a proposal until the contract confirms it" (single confirmation wording retained). Add "Supplied inputs" section with known/missing/conflicting rules. Add optional `Conflicts:` line to the contract block (additive; the five asserted fields stay). Add one Question-scope bullet: derived missing questions are ad-hoc, not permanent. Keep identity, paralelo, five types, visual directions, "must not" length/depth, and no `unl-shell` mention (all test-asserted).
2. `skills/academic-report-builder/SKILL.md` (~+7/−3): Mandatory Intake gains the reuse sentence; Execution Steps step 1 gains one sentence to evaluate the research trigger per intake criteria; step 2 gains "including inaccessible/stale flags" to carried limitations. `Mandatory Intake`, `Prohibition On Inferring Document Type`, "PDF or DOCX is a format signal only", route-qualified `unl-shell` lines preserved.
3. `skills/research-workflow/SKILL.md` (~+6): Activation Contract names both activation paths and points to protocol §1 trigger criteria; Output Contract mentions inaccessible/stale limitations. Hard Rules' asserted eligibility strings untouched.
4. `skills/research-workflow/references/research-protocol.md` (~+20): new "Trigger" subsection in §1 documenting criteria (a)/(b), coverage = local `inspected: true` with freshness considered; §2 additive sentence: an external source, once inspected and provenance-complete, is eligible on the same terms as local; §5 notes lead/citation boundary already present.
5. `tests/skills/test_report_builder_routing.py` (~+40/−10): RED-first rewrite of `test_confirmation_is_required_on_every_execution` → assert adaptive reuse wording ("reuse supplied"/"candidate answers"), "missing consequential", contract confirmation retained, and the old re-ask assertion `"even when the prompt appears to already contain"` now forbidden; keep an "every execution" presence check (SKILL.md keeps it). Add: conflicts-surfaced test; derived-questions-not-permanent test; no-regression guards for existing tokens.
6. `tests/skills/test_research_workflow_contract.py` (~+45, existing 7 untouched): add trigger-criteria test (protocol documents both paths + `inspected: true` coverage + freshness), explicit-request-preserved test, external-inspected-equal-eligibility test, builder-side trigger/limitations mention test, non-university-forced-identity wording check.
7. `tests/skills/conversation-cases.md` (~+45): positive cases — 5: complete consigna+rubric supplied, only missing consequential asked, contract rendered, nothing generated; 6: conflicting inputs stated in contract; 7: uncovered claims → trigger decision + evidence handoff; covered → no research. Negative: N10 re-asks supplied answers; N11 generates after "all supplied" without the one confirmation; N12 cites a `lead`.

**Must not touch:** `scripts/sync_skills.sh`, `tests/skills/test_sync_skills.py` (uncommitted sync fix — preserved), `templates/`, `assets/`, `tools/`, `report.yml` schema.

## 4. Strict TDD plan (repo interpreter: pytest)

- **RED**: author the new/updated assertions first; run `pytest tests/skills/` — new tests fail against current markdown; prove the old wording test now fails intentionally.
- **GREEN**: apply the §3 markdown deltas minimally until the suite passes, including the 7 untouched research tests (their exact substrings are the compatibility contract).
- **TRIANGULATE**: the conflict, trigger, and explicit-request assertions force generalized wording, not one-off phrases.
- **REFACTOR**: dedupe repeated regex/token sets via helpers only if it shrinks the diff.
- **Evidence**: record RED/GREEN output in apply notes, labeling static-contract evidence per spec.

## 5. Smoke validation (before archive; rendered, sandboxed — corrected)

Verified publish behavior (factual correction): `build_report_auto.py:19` imports `publish_validated_pdf`; `:132–136` publish **every** validated PDF unconditionally after validation — including under `--validate-only` — with no CLI `documents_root`, so it writes to real `HOME/Documents` by default. Independently, `build_latex_report.py:936` and `build_docx_report.py:1107` call `publish_global_output` into `REPORT_CONTENT_ROOT/outputs/<materia>/` unless the fixture sets `publish_global: false`.

**Required safe rendered smoke** (tex-only does NOT satisfy the spec's rendered-smoke acceptance and is not proposed as a weakening default; it may only supplement):
1. Sandbox both roots under the worktree, e.g. `outputs/_smoke/home` (HOME) and `outputs/_smoke/content` (REPORT_CONTENT_ROOT) — never `/tmp`, never real `HOME/Documents`, never the real content root.
2. Fixture report folder with `publish_global: false` (belt-and-suspenders for the backend global publish).
3. Run the original repo interpreter with `HOME=<sandbox-home> REPORT_CONTENT_ROOT=<sandbox-content> python tools/build_report_auto.py <fixture>` — full compile + gates + sandboxed versioned publication, no network, no paid external research.
4. Result recorded as runtime evidence, explicitly distinct from static tests; remains an outstanding acceptance item until executed.

## 6. Delivery units and review risk (user decision: divide into reviewable units)

Fresh explicit user authorization: divide into reviewable units. **No commits/PRs are authorized in this phase; no `size:exception`.** Units run sequentially in the same tree with one writer at a time (no parallel writers, no shared-file overlap ambiguity).

- **U0 — sync unit (existing, preserved, not authored here):** `scripts/sync_skills.sh` (+3/−1) + `tests/skills/test_sync_skills.py` (81 lines) ≈ ~85 lines. Untouched by every other unit (proposal non-goal).
- **U1 — planning docs unit (this phase):** proposal.md (~47) + exploration.md (~61) + spec.md (~113) + design.md (~59 after this repair) ≈ **~280 lines measured** (counted from file reads; no shell measurement available in this phase — treat as ±5). Under 400 alone. The §2 dedup removes ~8 duplicated/stale lines with zero unique-semantics loss (provider/tool-preservation sentence merged into the surviving block); specs untouched. No further slimming required.
- **U2 — intake implementation unit:** `references/document-intake.md` (+35/−8) + `skills/academic-report-builder/SKILL.md` (+7/−3) + `tests/skills/test_report_builder_routing.py` (+40/−10) ≈ ~103 changed lines, self-verifying via its test file.
- **U3 — research implementation unit:** `skills/research-workflow/SKILL.md` (+6) + `references/research-protocol.md` (+20) + `tests/skills/test_research_workflow_contract.py` (+45) + **all** `tests/skills/conversation-cases.md` additions (+45) ≈ ~116 changed lines. The cases file is wholly owned by U3 (single writer); its intake cases verify U2 behavior after U2 lands. U3's contract tests assert builder-side wording authored in U2, so U3 follows U2.

Order: ask-on-risk human gate → U2 tests RED → U2 markdown GREEN → U3 RED/GREEN → full `tests/skills/` (sync-fix tests pass untouched) → sandboxed rendered smoke (§5) → archive. All changes are markdown/tests/fixtures: fully git-revertable, no migrations.

**Budget flag (mandatory):** the native full candidate — U0 ~85 + U1 ~280 + U2 ~103 + U3 ~116 ≈ **~584 changed lines — still exceeds the 400-line budget**. Each unit fits the budget individually. Per `ask-on-risk`, any apply that would merge units past the budget pauses for explicit human approval; no chained-PR strategy, commits, or `size:exception` is inferred or authorized here. Residual risk: over-tight static assertions constraining future wording — mitigated by semantic token assertions where the existing suite allows; and line-count approximations carry small uncertainty until `git diff --stat` at apply time.
