"""Static contract tests for the audited academic skill remediations."""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT_SKILL = ROOT / "skills" / "academic-report-builder" / "SKILL.md"
VISUAL_ROOT = ROOT / "skills" / "academic-visual-builder"
VISUAL_SKILL = VISUAL_ROOT / "SKILL.md"
SCHEMA = VISUAL_ROOT / "references" / "figures-yml-schema.md"
STYLE_GUIDE = ROOT / "docs" / "skill-style-guide.md"

REQUIRED_FIELDS = (
    "file", "title", "caption", "source", "renderer", "section",
    "request_id", "result_id", "content_sha256", "license",
    "license_status", "alt_text",
)


def body_tokens(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    body = parts[2] if len(parts) == 3 else text
    return len(re.findall(r"\S+", body))


def test_local_style_guide_exists_and_declares_hard_budget() -> None:
    assert STYLE_GUIDE.is_file()
    text = STYLE_GUIDE.read_text(encoding="utf-8")
    assert "Hard maximum" in text
    assert "1000 tokens" in text


def test_both_skill_bodies_fit_the_normative_budget() -> None:
    assert body_tokens(REPORT_SKILL) <= 1000
    assert body_tokens(VISUAL_SKILL) <= 1000


def test_both_skills_keep_runtime_sections_in_style_order() -> None:
    expected = [
        "Activation Contract", "Hard Rules", "Decision Gates",
        "Execution Steps", "Output Contract", "References",
    ]
    for path in (REPORT_SKILL, VISUAL_SKILL):
        text = path.read_text(encoding="utf-8")
        positions = [text.index(f"## {heading}") for heading in expected]
        assert positions == sorted(positions), path


def test_shared_validator_and_schema_agree_on_metadata_fields() -> None:
    schema = SCHEMA.read_text(encoding="utf-8")
    module = ROOT / "tools" / "visual_metadata.py"
    assert module.is_file(), "both validators must consume the shared implementation"
    implementation = module.read_text(encoding="utf-8")
    for field in REQUIRED_FIELDS:
        assert f"`{field}`" in schema or f'"{field}"' in schema
        assert f'"{field}"' in implementation


def test_both_runtime_validators_use_the_shared_implementation() -> None:
    for filename in ("tools/visual_builder.py", "tools/validate_report.py"):
        text = (ROOT / filename).read_text(encoding="utf-8")
        assert "from visual_metadata import validate_visual_manifest" in text


def test_visual_skill_assigns_auditor_precheck_not_visual_pass() -> None:
    text = VISUAL_SKILL.read_text(encoding="utf-8")
    assert "AUDITOR_PRECHECK" in text
    assert "semantic inspection" in text.lower()
    assert "visual PDF audit" in text
    assert re.search(r"auditor.*does not grant.*VISUAL_PASS", text, re.IGNORECASE | re.DOTALL)
    assert "HUMAN_REVIEW" in text
    assert "READY_TO_SUBMIT" in text


def test_report_skill_keeps_visual_pass_owned_by_direct_semantic_inspection() -> None:
    text = REPORT_SKILL.read_text(encoding="utf-8")
    assert "No script, validator, or auditor ever grants `VISUAL_PASS`" in text
    assert "independent semantic inspection" in text
    assert "HUMAN_REVIEW" in text
    assert "READY_TO_SUBMIT" in text
