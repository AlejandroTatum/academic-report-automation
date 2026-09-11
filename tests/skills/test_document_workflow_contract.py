"""Static contract tests for the document-workflow orchestration skill.

These tests read the skill markdown as data. They never run the pipeline: they
prove the orchestrator keeps a single route loop, a fixed seven-reference
routing table, and a portable ASCII status template.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = ROOT / "skills" / "document-workflow"
SKILL_MD = SKILL_ROOT / "SKILL.md"

PHASES = ("intake", "research", "preview", "approval", "generate", "validate", "deliver")
STATE_TOKENS = ("done", "current", "pending", "blocked")
EXECUTORS = ("academic-report-builder", "research-workflow")


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

    assert block.splitlines()[0] == (
        "**Gate**: approval pending - generation runs only after you approve "
        "reports/<wf>/preview.md"
    )
    assert block.index("**Gate**:") < block.index("**Summary**"), "gate line must be front-loaded"

    summary = block.split("**Summary**", 1)[1].split("**Next**:", 1)[0]
    bullets = re.findall(r"^- ([a-z]+): ([a-z]+)", summary, re.MULTILINE)
    assert [name for name, _ in bullets] == list(PHASES)
    assert {state for _, state in bullets} <= set(STATE_TOKENS)

    assert re.search(r"^\*\*Next\*\*: [a-z]+", block, re.MULTILINE), "closing Next line missing"
