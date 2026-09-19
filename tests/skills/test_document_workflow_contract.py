"""Static contract tests for the document-workflow orchestration skill.

These tests read the skill markdown as data. They never run the pipeline: they
prove the orchestrator keeps a single route loop, a fixed seven-reference
routing table, and a portable ASCII status template.
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

PHASES = ("intake", "research", "preview", "approval", "generate", "validate", "deliver")
STATE_TOKENS = ("done", "current", "pending", "blocked")
EXECUTORS = ("academic-report-builder", "research-workflow")

# Slice 3a-ii owns the five executor references below. `approval.md` and
# `validate.md` belong to Slices 3b-i and 3b-ii and are asserted by their own
# contract tests, never here.
OWNED_REFERENCES = ("intake", "research", "preview", "generate", "deliver")
REFERENCE_EXECUTOR = {
    "intake": "academic-report-builder",
    "research": "research-workflow",
    "preview": "academic-report-builder",
    "generate": "academic-report-builder",
    "deliver": "academic-report-builder",
}
# The single artifact each phase must produce, exactly as its reference declares it.
REFERENCE_ARTIFACT = {
    "intake": "reports/<wf>/report.yml",
    "research": "reports/<wf>/research/evidence-matrix.md",
    "preview": "reports/<wf>/preview.md",
    "generate": "outputs/<materia>/<final>.pdf",
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
        "Route: intake > research > [preview] > approval > generate > validate > deliver"
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

    expected = "preview pending - " + doc_status._guidance("preview", Path("<report-folder>"))

    assert gate_line == f"**Gate**: {expected}"
    assert "approval pending" not in gate_line, "the approval front-load must stay gone"


def test_status_template_next_line_matches_the_tool_guidance() -> None:
    """The documented ``**Next**`` line is the tool's own guidance sentence."""
    doc_status = tool_doc_status()
    block = human_template(read(SKILL_MD))
    next_line = next(line for line in block.splitlines() if line.startswith("**Next**: "))

    assert next_line == (
        "**Next**: preview - " + doc_status._guidance("preview", Path("<report-folder>"))
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
    for key in ("preview_sha256", "approved_at", "approved_by"):
        assert key in text, f"approval.md must name the marker key {key}"
    assert "approval.yml" in text, "approval.md must name the marker file"
    flat = re.sub(r"\s+", " ", text).lower()
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
    reference must state the precondition and forbid acting before it holds.
    """
    text = read(SKILL_ROOT / "references" / "generate.md")
    flat = re.sub(r"\s+", " ", text).lower()
    assert "approval: done" in flat, "generate.md must name the `approval: done` precondition"
    assert "preview_sha256" in flat, "generate.md must name the hash the approval binds to"
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
    keeps reading exactly the path each phase promises.
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


# --------------------------------------------------------------------------
# T7 — instructions sufficient without session context
# --------------------------------------------------------------------------


def test_research_reference_names_local_inspected_evidence_when_skipped() -> None:
    """Skipping research must still cite the local inspected evidence that covers it."""
    text = read(SKILL_ROOT / "references" / "research.md")
    flat = re.sub(r"\s+", " ", text).lower()

    assert "source_library.py" in flat, (
        "a skipped research phase must name the local source inventory the evidence comes from"
    )
    assert "inspected" in flat, "the local evidence must be the inspected kind"
    assert "research: skipped" in flat, "the recorded skip decision must stay"


def test_preview_reference_allows_utf8_and_protects_approved_bytes() -> None:
    """Preview content is UTF-8 (Spanish headings allowed) and frozen once approved."""
    text = read(SKILL_ROOT / "references" / "preview.md")
    flat = re.sub(r"\s+", " ", text).lower()

    assert not re.search(r"\b(?:stays|remains|must be|is)\s+ascii\b", flat), (
        "the preview must not be restricted to ASCII"
    )
    assert "utf-8" in flat, "the preview encoding must be named"
    assert re.search(r"(?:never|do not|must not)\s+(?:be\s+)?rewrit(?:e|ten)", flat), (
        "an approved preview must never be rewritten: the marker binds its exact bytes"
    )
    assert "sha256" in flat or "sha-256" in flat, "the binding hash must be named"


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
