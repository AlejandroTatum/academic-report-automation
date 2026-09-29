"""Static contract tests for the document-workflow orchestration skill.

These tests read the skill markdown as data. They never run the pipeline: they
prove the orchestrator keeps a single route loop, a fixed eleven-reference
routing table, a portable ASCII status template, and the content-first prose
rules of the new-report-flow route (research gate, verbatim review loop,
report-only content check, single format question).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = ROOT / "skills" / "document-workflow"
SKILL_MD = SKILL_ROOT / "SKILL.md"
TOOLS_DIR = ROOT / "tools"


def tool_doc_status():
    """Import the real ``tools/doc_status.py`` so documented text cannot drift."""
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    import doc_status

    return doc_status

PHASES = (
    "intake",
    "research",
    "plan",
    "draft",
    "approval",
    "verify",
    "format",
    "generate",
    "validate",
    "review",
    "deliver",
)
STATE_TOKENS = ("done", "current", "pending", "blocked")
EXECUTORS = ("academic-report-builder", "research-workflow")

# Slice 3a-ii owns the six executor references below. `approval.md` and
# `validate.md` belong to Slices 3b-i and 3b-ii and are asserted by their own
# contract tests, never here. new-report-flow T5 adds the four self-executed
# phase references (plan, verify, format, review); T6 rewrites the prose of
# every reference for the content-first route.
OWNED_REFERENCES = (
    "intake",
    "research",
    "plan",
    "draft",
    "verify",
    "format",
    "generate",
    "review",
    "deliver",
)
REFERENCE_EXECUTOR = {
    "intake": "academic-report-builder",
    "research": "research-workflow",
    "plan": "document-workflow",
    "draft": "academic-report-builder",
    "verify": "document-workflow",
    "format": "document-workflow",
    "generate": "academic-report-builder",
    "review": "document-workflow",
    "deliver": "academic-report-builder",
}
# The single artifact each phase must produce, exactly as its reference declares it.
REFERENCE_ARTIFACT = {
    "intake": "reports/<wf>/report.yml",
    "research": "reports/<wf>/sources.bib",
    "plan": "reports/<wf>/rubric.yml",
    "draft": "reports/<wf>/body.md",
    "verify": "reports/<wf>/content-check.yml",
    "format": "reports/<wf>/report.yml",
    "generate": "outputs/<materia>/<final>.pdf",
    "review": "reports/<wf>/final-review.yml",
    "deliver": "~/Documents/<category>/<slug>/<slug>-vNNN.pdf",
}


def read(path: Path) -> str:
    assert path.is_file(), f"missing required contract file: {path}"
    return path.read_text(encoding="utf-8")


def frontmatter(text: str) -> str:
    parts = text.split("---", 2)
    assert len(parts) == 3, "SKILL.md must open with a frontmatter block"
    return parts[1]


def fenced_blocks(text: str) -> list[str]:
    return re.findall(r"```[^\n]*\n(.*?)```", text, re.DOTALL)


def human_template(text: str) -> str:
    for block in fenced_blocks(text):
        if "**Summary**" in block and "**Next**:" in block:
            return block
    raise AssertionError("SKILL.md must embed the fenced human status block template")


def test_verify_uses_independent_judge_without_drafting_conversation() -> None:
    text = read(SKILL_ROOT / "references" / "verify.md")
    assert "--judge-brief" in text
    assert "independent read-only judge" in text
    assert "Do not pass the drafting conversation" in text
    assert text.count("Executor:") == 1
    assert text.count("Artifact:") == 1


def test_required_files_and_frontmatter() -> None:
    text = read(SKILL_MD)
    meta = frontmatter(text)
    assert re.search(r"^name:\s*document-workflow\s*$", meta, re.MULTILINE)
    assert re.search(r'^description:\s*".*Trigger:', meta, re.MULTILINE)
    assert re.search(r"^license:\s*Apache-2\.0\s*$", meta, re.MULTILINE)
    for key in ("author", "version", "scope"):
        assert re.search(rf"^\s+{key}:\s*\S", meta, re.MULTILINE), f"metadata.{key} missing"
    for phase in PHASES:
        assert f"references/{phase}.md" in text, f"routing table must name references/{phase}.md"


def test_routing_loop_and_table_contract() -> None:
    text = read(SKILL_MD)
    assert "doc_status -> next -> reference -> delegate -> re-run" in re.sub(r"\s+", " ", text)
    for phase in PHASES:
        assert re.search(rf"^\|\s*{phase}\s*\|", text, re.MULTILINE), f"routing row {phase} missing"
    for executor in EXECUTORS:
        assert executor in text, f"routing table must name {executor}"
    assert "human gate" in text.lower(), "the approval row must identify the human gate"


def test_status_template_contract() -> None:
    block = human_template(read(SKILL_MD))
    assert all(ord(char) < 128 for char in block), "template must be ASCII only"
    assert "|" not in block, "template must not use markdown tables"
    assert not re.search(r"^#{3,}", block, re.MULTILINE), "template must not nest headers"

    route_lines = [line for line in block.splitlines() if line.startswith("Route: ")]
    assert len(route_lines) == 1, "exactly one route line"
    assert route_lines[0] == (
        "Route: intake > research > [plan] > draft > approval > verify > format"
        " > generate > validate > review > deliver"
    )
    brackets = re.findall(r"\[([a-z]+)\]", route_lines[0])
    assert len(brackets) == 1 and brackets[0] in PHASES, "exactly one bracketed phase"
    route_body = route_lines[0].split("Route: ", 1)[1].replace("[", "").replace("]", "")
    assert route_body.split(" > ") == list(PHASES), "route must list every phase in order"

    assert block.splitlines()[0].startswith("**Gate**: ")
    assert block.index("**Gate**:") < block.index("**Summary**"), "gate line must be front-loaded"

    summary = block.split("**Summary**", 1)[1].split("**Next**:", 1)[0]
    bullets = re.findall(r"^- ([a-z]+): ([a-z]+)", summary, re.MULTILINE)
    assert [name for name, _ in bullets] == list(PHASES)
    assert {state for _, state in bullets} <= set(STATE_TOKENS)

    assert re.search(r"^\*\*Next\*\*: [a-z]+", block, re.MULTILINE), "closing Next line missing"


def test_status_template_gate_is_phase_projected_not_approval_frontloaded() -> None:
    """T3/T7: the documented gate is the focus phase's own gate, never approval.

    The embedded block claims to be the exact human output for its state, so it is
    compared against the real derivation instead of a hand-written string.
    """
    doc_status = tool_doc_status()
    block = human_template(read(SKILL_MD))
    gate_line = next(line for line in block.splitlines() if line.startswith("**Gate**: "))

    expected = "plan pending - " + doc_status._guidance("plan", Path("<report-folder>"))

    assert gate_line == f"**Gate**: {expected}"
    assert "approval pending" not in gate_line, "the approval front-load must stay gone"


def test_status_template_next_line_matches_the_tool_guidance() -> None:
    """The documented ``**Next**`` line is the tool's own guidance sentence."""
    doc_status = tool_doc_status()
    block = human_template(read(SKILL_MD))
    next_line = next(line for line in block.splitlines() if line.startswith("**Next**: "))

    assert next_line == (
        "**Next**: plan - " + doc_status._guidance("plan", Path("<report-folder>"))
    )


def test_status_template_gate_guidance_is_ascii_and_absolute() -> None:
    """The documented human block stays ASCII and names real, absolute entrypoints."""
    doc_status = tool_doc_status()
    block = human_template(read(SKILL_MD))

    assert all(ord(char) < 128 for char in block)
    for phase, script in (("generate", "build_report_auto.py"), ("deliver", "deliver_report.py")):
        entrypoint = doc_status.ROOT / "tools" / script
        assert entrypoint.is_file(), "documented entrypoints must exist"
        assert str(entrypoint) in doc_status._guidance(phase, Path("/wf"))


def test_referenced_paths_resolve() -> None:
    """Every executor reference owned by Slice 3a-ii resolves on disk.

    `approval.md` and `validate.md` are deliberately absent from this list: Slice
    3b-i and Slice 3b-ii own those paths and verify them in their own contract
    tests, so a missing path here names only a Slice 3a-ii regression.
    """
    unresolved = [
        f"references/{phase}.md"
        for phase in OWNED_REFERENCES
        if not (SKILL_ROOT / "references" / f"{phase}.md").is_file()
    ]
    assert not unresolved, f"unresolved phase references: {', '.join(unresolved)}"


def test_approval_reference_contract() -> None:
    """Slice 3b-i owns `approval.md`: the human gate, its marker schema, and its refusal to infer consent.

    The reference must exist on disk, name the three marker keys, and state that
    silence or an agent-side inference never produces `approval.yml`.
    """
    path = SKILL_ROOT / "references" / "approval.md"
    assert path.is_file(), f"missing required contract file: {path}"
    text = read(path)
    for key in ("body_sha256", "approved_at", "approved_by"):
        assert key in text, f"approval.md must name the marker key {key}"
    assert "preview_sha256" not in text, (
        "approval.md must not bind preview.md any more: the marker binds body.md only"
    )
    assert "approval.yml" in text, "approval.md must name the marker file"
    flat = re.sub(r"\s+", " ", text).lower()
    assert re.search(r"binds?[^.]*body\.md", flat), (
        "approval.md must state that the marker binds body.md"
    )
    for phrase in ("silence", "inferred yes", "agent decision"):
        assert phrase in flat, f"approval.md must name `{phrase}` as a non-consent signal"
    assert re.search(r"never (?:produce|produces|writes|creates)[^.]*approval\.yml", flat), (
        "approval.md must state that a non-explicit answer never produces approval.yml"
    )
    assert "human gate" in flat, "approval.md must identify the human gate"
    assert "lossless" in flat, "approval.md must name the lossless prompt contract"
    assert not re.search(r"^Executor:", text, re.MULTILINE), (
        "approval.md is the human gate: it must declare no executor"
    )


def test_generate_reference_forbids_unapproved_build() -> None:
    """Slice 3b-i extends `generate.md` with the approval-done precondition.

    Generation is the first phase that spends build effort on approved bytes, so the
    reference must state the precondition and forbid acting before it holds. T1 cut
    the preview binding: the approval marker binds `body.md` only.
    """
    text = read(SKILL_ROOT / "references" / "generate.md")
    flat = re.sub(r"\s+", " ", text).lower()
    assert "approval: done" in flat, "generate.md must name the `approval: done` precondition"
    assert "body_sha256" in flat, "generate.md must name the hash the approval binds to"
    assert "body.md" in flat, "generate.md must name body.md as the approved input"
    assert "preview" not in flat, "the preview binding is gone: approval binds body.md only"
    assert re.search(r"(?:never|must not|do not|does not) build (?:before|until)", flat), (
        "generate.md must forbid building before approval is done"
    )


def test_validate_reference_both_branches() -> None:
    """Slice 3b-ii owns `validate.md`: both validation branches behind one gate set.

    The reference must exist on disk, name the read-only RDD probe
    (`gentle-ai review mode status`) and its `mode: rdd` receipt, name the fallback
    rendered chain with `mode: fallback`, and route the `unknown` status to that
    fallback without lowering the shared gate set.
    """
    path = SKILL_ROOT / "references" / "validate.md"
    assert path.is_file(), f"missing required contract file: {path}"
    text = read(path)
    flat = re.sub(r"\s+", " ", text).lower()

    assert re.search(r"^Artifact: `reports/<wf>/validation\.yml`$", text, re.MULTILINE), (
        "validate.md must declare its single artifact `reports/<wf>/validation.yml`"
    )
    assert "gentle-ai review mode status" in flat, (
        "validate.md must name the read-only RDD probe `gentle-ai review mode status`"
    )
    assert "mode: rdd" in flat, "validate.md must label the RDD branch `mode: rdd`"
    assert "mode: fallback" in flat, (
        "validate.md must label the fallback branch `mode: fallback`"
    )
    for step in ("validate_report.py", "visual_pdf_auditor.py", "semantic"):
        assert step in flat, f"validate.md must name the fallback step `{step}`"
    gates = ("BUILD_PASS", "VALIDATION_PASS", "VISUAL_PASS", "HUMAN_REVIEW", "READY_TO_SUBMIT")
    for gate in gates:
        assert gate in text, f"validate.md must name the shared gate {gate}"
    assert re.search(r"unknown[^.]{0,200}fallback", flat), (
        "validate.md must route an unknown RDD status to the fallback chain"
    )
    assert re.search(r"never (?:enable|enables|activate|activates|turn on|turns on)[^.]*rdd", flat), (
        "validate.md must state that RDD is never enabled on the user's behalf"
    )
    assert "backups/quality_report.md" in flat, (
        "validate.md must name the fallback evidence path"
    )
    assert "next: validate" in flat, "validate.md must state the phase it owns"
    assert "identical gate set" in flat, (
        "validate.md must state that both branches enforce the identical gate set"
    )
    assert "read-only" in flat, "validate.md must state that the RDD probe is read-only"
    assert re.search(r"mode: fallback[^.]*backups/quality_report\.md", flat), (
        "validate.md must couple the fallback receipt mode to its evidence path"
    )


def test_phase_references_name_executor_and_single_artifact() -> None:
    """Each owned reference declares one executor and exactly one artifact.

    The declaration is a labelled line contract, so a reference can never claim two
    artifacts or fall back to an implicit executor, and `doc_status` derivation
    keeps reading exactly the path each phase promises. The T5 phases (plan,
    verify, format, review) are executed by this skill itself.
    """
    for phase in OWNED_REFERENCES:
        text = read(SKILL_ROOT / "references" / f"{phase}.md")
        executors = re.findall(r"^Executor: (.+?)\s*$", text, re.MULTILINE)
        artifacts = re.findall(r"^Artifact: (.+?)\s*$", text, re.MULTILINE)
        assert executors == [REFERENCE_EXECUTOR[phase]], (
            f"references/{phase}.md must declare exactly Executor: {REFERENCE_EXECUTOR[phase]}"
        )
        assert artifacts == [f"`{REFERENCE_ARTIFACT[phase]}`"], (
            f"references/{phase}.md must declare exactly Artifact: `{REFERENCE_ARTIFACT[phase]}`"
        )
        assert REFERENCE_EXECUTOR[phase] in text, (
            f"references/{phase}.md must name its executor in prose too"
        )


def test_preview_reference_is_gone() -> None:
    """new-report-flow T5: the preview phase no longer exists in the route."""
    assert not (SKILL_ROOT / "references" / "preview.md").exists(), (
        "preview.md must be deleted: the draft is the only thing the user reviews"
    )
    assert "references/preview.md" not in read(SKILL_MD), (
        "SKILL.md must not route to the removed preview reference"
    )


def test_new_phase_references_state_their_intent() -> None:
    """T5: plan/verify/format/review are minimal self-executed phase references.

    Each names its marker contract and the one tool that derives its state; the
    full prose rewrite is T6.
    """
    expected_tokens = {
        "plan": ("rubric.yml", "rubric_plan.py"),
        "verify": ("content-check.yml", "content_check.py"),
        "format": ("format:", "APE"),
        "review": ("final-review.yml", "pdf_sha256"),
    }
    for phase, tokens in expected_tokens.items():
        text = read(SKILL_ROOT / "references" / f"{phase}.md")
        flat = re.sub(r"\s+", " ", text)
        for token in tokens:
            assert token in flat, f"references/{phase}.md must name `{token}`"


def test_draft_reference_names_authoring_format_and_single_artifact() -> None:
    """`draft.md` names the body authoring format and produces exactly one artifact.

    The body is Markdown with Pandoc-style `[@key]` citations resolved against
    `sources.bib` and `![caption](path)` figures; the phase never writes the
    approval marker.
    """
    text = read(SKILL_ROOT / "references" / "draft.md")
    for token in ("[@", "![", "sources.bib"):
        assert token in text, f"draft.md must name the authoring format token {token}"
    flat = re.sub(r"\s+", " ", text).lower()
    assert "exactly one artifact" in flat, "draft.md must state it produces exactly one artifact"
    assert re.search(r"never[^.]*writes?[^.]*approval\.yml", flat), (
        "draft.md must state it never writes approval.yml"
    )


# --------------------------------------------------------------------------
# T7 — instructions sufficient without session context
# --------------------------------------------------------------------------


def test_research_reference_names_the_five_source_gate() -> None:
    """new-report-flow T2: research is a hard gate, never a skippable phase.

    The reference must name the per-document BibTeX artifact, the five-source
    minimum, and the forbidden web-only types -- and the recorded skip path
    must be gone.
    """
    text = read(SKILL_ROOT / "references" / "research.md")
    flat = re.sub(r"\s+", " ", text).lower()

    assert "sources.bib" in flat, "the phase must name the per-document BibTeX file"
    assert re.search(r"at least 5\b", flat), "the reference must state the five-source minimum"
    assert "@misc" in flat and "@online" in flat, (
        "the reference must name the web-only types that never count"
    )
    assert "research: skipped" not in flat, "the recorded skip decision must be gone"
    assert "source_library.py" in flat, (
        "the reference must still name the local source inventory tool"
    )
    assert "inspected" in flat, "only inspected local sources are bibliography-eligible"


def test_intake_reference_states_the_record_keys_without_inventing_a_schema() -> None:
    """The workflow intake must name the existing keys, not a parallel vocabulary."""
    text = read(SKILL_ROOT / "references" / "intake.md")
    flat = re.sub(r"\s+", " ", text)

    for key in ("metadata.audience", "metadata.purpose", "metadata.visual_direction"):
        assert key in flat, f"the intake record must place {key} in the consumed metadata map"
    assert "`cover:`" in flat, "cover is a top-level key"
    assert "document-intake.md" in flat, "the record semantics stay owned by the builder reference"


def test_generate_and_deliver_references_print_runnable_absolute_commands() -> None:
    """Both phase references must show a command that runs from any working directory."""
    for name, script in (("generate", "build_report_auto.py"), ("deliver", "deliver_report.py")):
        text = read(SKILL_ROOT / "references" / f"{name}.md")
        flat = re.sub(r"\s+", " ", text)

        assert '"$REPORT_PYTHON"' in flat, (
            f"{name}.md must run under the selected interpreter, not one colocated with tools/"
        )
        assert f'"$REPORT_AUTOMATION_ROOT/tools/{script}"' in flat, name
        assert '"$REPORT_CONTENT_ROOT/reports/<work-folder>/"' in flat, name
        assert '"$REPORT_AUTOMATION_ROOT/.venv/bin/python"' not in flat, (
            f"{name}.md must not assume a .venv beside the tools"
        )
        assert not re.search(r"python tools/", flat), (
            f"{name}.md must not leave the tool path relative to an assumed cwd"
        )


def test_deliver_reference_names_the_executable_and_the_receipt_precondition() -> None:
    """T2/T7: deliver names the entrypoint, its receipt gate, and never auto-publishes."""
    flat = re.sub(r"\s+", " ", read(SKILL_ROOT / "references" / "deliver.md"))

    assert '"$REPORT_AUTOMATION_ROOT/tools/deliver_report.py"' in flat
    assert "validation.yml" in flat
    assert "approval.yml" in flat
    assert "never publishes" in flat


# --------------------------------------------------------------------------
# T6 — content-first prose rules
# --------------------------------------------------------------------------


def all_skill_files() -> list[Path]:
    """Every markdown file the document-workflow skill loads: SKILL.md plus references."""
    return [SKILL_MD] + [SKILL_ROOT / "references" / f"{phase}.md" for phase in PHASES]


def test_no_document_workflow_file_mentions_the_removed_preview() -> None:
    """T6: the preview phase and its artifact are gone from every skill file."""
    offenders = [
        str(path.relative_to(SKILL_ROOT))
        for path in all_skill_files()
        if "preview" in read(path).lower()
    ]
    assert offenders == [], f"stale preview mentions remain: {offenders}"


def test_skill_tree_adds_no_detector_or_percentage_gate() -> None:
    """T6 rule 6: the flow has no AI-detector or percentage gate, and never will."""
    offenders = [
        str(path.relative_to(SKILL_ROOT))
        for path in all_skill_files()
        if re.search(r"detector|percent", read(path), re.IGNORECASE)
    ]
    assert offenders == [], f"detector/percentage gate wording in: {offenders}"


def test_intake_reference_asks_only_the_content_first_minimum() -> None:
    """T6 rule 1: intake collects identity plus guide material, never formatting."""
    flat = re.sub(r"[*_`]", "", read(SKILL_ROOT / "references" / "intake.md")).lower()
    flat = re.sub(r"\s+", " ", flat)
    for token in ("title", "student", "guide", "rubric"):
        assert token in flat, f"intake.md must name the minimum input `{token}`"
    assert "formatting questions" in flat, "intake.md must refuse formatting questions"
    assert "format phase" in flat, "intake.md must defer formatting to the format phase"


def test_builder_intake_defers_formatting_to_the_format_phase() -> None:
    """T6 rule 1: the executor intake names the content-first minimum and the deferral."""
    text = read(
        ROOT / "skills" / "academic-report-builder" / "references" / "document-intake.md"
    )
    flat = re.sub(r"\s+", " ", re.sub(r"[*_`]", "", text)).lower()
    assert "content-first" in flat, "document-intake.md must name the content-first route"
    for token in ("title", "student", "guide", "rubric"):
        assert token in flat, f"document-intake.md must name the minimum input `{token}`"
    assert "format phase" in flat, "document-intake.md must defer formatting to the format phase"


def test_research_reference_demands_verifiable_ieee_sources() -> None:
    """T6 rule 2: sources are real, verifiable, and cited IEEE."""
    flat = re.sub(r"\s+", " ", read(SKILL_ROOT / "references" / "research.md")).lower()
    assert "ieee" in flat, "research.md must name the IEEE citation style"
    assert re.search(r"(?:never|do not) invent", flat), "research.md must forbid invented sources"
    assert "verifiable" in flat, "research.md must require every entry to be verifiable"


def test_plan_reference_mirrors_the_teachers_rubric() -> None:
    """T6 rule 3: one criterion per rubric item, mapped to the section that satisfies it."""
    flat = re.sub(r"\s+", " ", read(SKILL_ROOT / "references" / "plan.md")).lower()
    assert "one criterion per rubric item" in flat
    assert "mapped to the body section" in flat, (
        "plan.md must map every criterion to the body section that satisfies it"
    )


def test_draft_reference_states_the_writing_style_contract() -> None:
    """T6 rule 4: the draft covers the rubric and reads like the user, not like a bot."""
    flat = re.sub(r"\s+", " ", read(SKILL_ROOT / "references" / "draft.md")).lower()
    assert "every rubric criterion" in flat
    assert "proposed figures" in flat
    assert "natural" in flat, "draft.md must ask for human, natural prose"
    assert re.search(r"flattering|obsequious", flat), "draft.md must forbid flattering prose"
    assert "how the user writes" in flat, "draft.md must model the tone on the user's writing"
    assert "stock ai phrasing" in flat, "draft.md must forbid stock AI phrasing"
    assert "starting point" in flat, "draft.md must call the draft a starting point for review"


def test_approval_reference_applies_user_text_verbatim() -> None:
    """T6 rule 5: edit orders are applied verbatim and editing re-opens approval."""
    flat = re.sub(r"\s+", " ", read(SKILL_ROOT / "references" / "approval.md")).lower()
    assert "edit orders" in flat, "approval.md must describe the literal edit-order loop"
    assert "verbatim" in flat, "approval.md must apply the user's text verbatim"
    assert "polish" in flat and "rephrase" in flat, (
        "approval.md must forbid polishing or rephrasing user-authored text"
    )
    assert "stale" in flat and "pending" in flat, (
        "approval.md must return an edited-after-approval route to approval as pending"
    )


def test_verify_reference_reports_findings_and_never_rewrites() -> None:
    """T6 rule 6: the content check reports findings; the user fixes them."""
    flat = re.sub(r"\s+", " ", read(SKILL_ROOT / "references" / "verify.md")).lower()
    assert re.search(r"never rewrites? `?body\.md", flat), "verify.md must forbid rewriting body.md"
    for status in ("cumple", "flojo", "falta"):
        assert status in flat, f"verify.md must name the `{status}` judgment status"
    assert "edit orders" in flat, "verify.md must route fixes through the user's edit orders"
    assert "confusing" in flat, "verify.md must report confusing paragraphs"
    assert re.search(r"figures? (?:that |which )?serves? no criterion", flat), (
        "verify.md must report figures that serve no criterion"
    )


def test_format_reference_is_one_question_with_the_ape_sections() -> None:
    """T6 rule 7: one question, per-format metadata, and the fixed APE sections."""
    flat = re.sub(r"\s+", " ", read(SKILL_ROOT / "references" / "format.md")).lower()
    assert "one question" in flat, "format.md must ask exactly one question"
    for token in ("ape", "aa", "libre", "ieee", "format_spec"):
        assert token in flat, f"format.md must name `{token}`"
    for section in (
        "objetivo",
        "materiales",
        "procedimiento",
        "resultados",
        "preguntas de control",
        "conclusiones",
        "recomendaciones",
        "anexos",
    ):
        assert section in flat, f"format.md must name the fixed APE section `{section}`"
    assert "bibliografía" in flat or "referencias" in flat
    assert "identification" in flat, "format.md must name the APE identification fields"
    assert "teacher's guide" in flat, "format.md must extract identification fields from the guide"


def test_review_reference_gates_delivery_on_an_explicit_pdf_ok() -> None:
    """T6 rule 8: the final human review binds the exact PDF; delivery waits for it."""
    flat = re.sub(r"\s+", " ", read(SKILL_ROOT / "references" / "review.md")).lower()
    assert "final-review.yml" in flat
    assert "pdf_sha256" in flat
    assert "explicit" in flat, "review.md must require an explicit OK"
    assert "silence" in flat, "review.md must refuse silence as consent"
    assert re.search(r"deliver\w*[^.]{0,60}only after", flat), (
        "review.md must gate delivery on the review"
    )
