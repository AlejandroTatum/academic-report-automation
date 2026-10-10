"""Static contract tests for the audited academic skill remediations."""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT_SKILL = ROOT / "skills" / "academic-report-flow" / "SKILL.md"
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


def test_visual_assets_never_reach_the_delivery_folder() -> None:
    text = VISUAL_SKILL.read_text(encoding="utf-8")
    assert "delivery folder" in text.lower(), (
        "the visual skill must keep assets out of the user's delivery folder"
    )
    assert "delivery.md" in text, (
        "the visual skill must point at the report skill's delivery contract"
    )


def test_visual_workflow_keeps_assets_in_repo_work_paths() -> None:
    workflow = (VISUAL_ROOT / "references" / "visual-workflow.md").read_text(
        encoding="utf-8"
    )
    normalized = re.sub(r"\s+", " ", workflow.lower())
    assert "never copied to the user's documents delivery folder" in normalized


def test_visual_skill_documents_automated_connector_gate() -> None:
    """Issue #10: the connector geometry gate is documented as automated
    AUDITOR_PRECHECK/blocking evidence, never as the VISUAL_PASS grant itself."""
    text = VISUAL_SKILL.read_text(encoding="utf-8")
    assert "connector" in text.lower()
    assert "0.80" in text
    assert re.search(r"auditor.*does not grant.*VISUAL_PASS", text, re.IGNORECASE | re.DOTALL)


def test_visual_workflow_replaces_eyeball_instruction_with_automated_gate() -> None:
    """The old manual-eyeball-only readability paragraph is replaced by the
    automated connector_geometry/connector_pdf_stage gate: isolated precheck
    vs mandatory final-size blocking, with the 0.80 SVG-unit clearance rule
    and its final-print-scale equivalent both documented."""
    workflow = (VISUAL_ROOT / "references" / "visual-workflow.md").read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", workflow.lower())
    assert "connector_geometry" in normalized
    assert "connector_pdf_stage" in normalized
    assert "0.80" in workflow
    assert "precheck" in normalized and "final" in normalized and "block" in normalized


def test_visual_skill_defaults_to_the_editorial_style() -> None:
    """#63: one documented house style with layouts and a print-size check, not a vague aesthetic."""
    skill = VISUAL_SKILL.read_text(encoding="utf-8")
    style = (VISUAL_ROOT / "references" / "editorial-style.md").read_text(encoding="utf-8")
    workflow = (VISUAL_ROOT / "references" / "visual-workflow.md").read_text(encoding="utf-8")
    assert "references/editorial-style.md" in skill and "editorial_svg.py check" in skill
    for phrase in ("actor_map", "concept_map", "5.5 pt", "860 SVG units", "## Never", "rsvg-convert"):
        assert phrase in style, phrase
    assert "approved conceptual-map aesthetic" not in workflow
    assert (ROOT / "tools" / "editorial_svg.py").is_file()


# --- Bauhaus técnico maps: the default for concept and process maps ---------

BAUHAUS_REFERENCE = VISUAL_ROOT / "references" / "bauhaus-maps.md"
EXAMPLES = VISUAL_ROOT / "assets" / "examples"
BAUHAUS_TOOL = ROOT / "tools" / "bauhaus_maps.py"


def _tool_module(name: str):
    import importlib
    import sys

    if str(ROOT / "tools") not in sys.path:
        sys.path.insert(0, str(ROOT / "tools"))
    return importlib.import_module(name)


def test_visual_skill_makes_bauhaus_the_default_for_concept_and_process_maps() -> None:
    skill = VISUAL_SKILL.read_text(encoding="utf-8")
    for phrase in ("references/bauhaus-maps.md", "tools/bauhaus_maps.py", "concept_map", "process_map", "Bauhaus"):
        assert phrase in skill, phrase
    # The editorial layouts stay documented for the actor map and the hand-written fallback.
    assert "actor_map" in skill and "references/editorial-style.md" in skill and "editorial_svg.py check" in skill
    assert "Concept map or process map" in skill, "the decision gate routes maps to the Bauhaus renderer"
    assert BAUHAUS_TOOL.is_file()


def test_bauhaus_reference_documents_both_schemas_the_limit_and_the_png_route() -> None:
    reference = BAUHAUS_REFERENCE.read_text(encoding="utf-8")
    for phrase in ("concept_map", "process_map", "spine", "cross", "families", "artifact_lane", "decision",
                   "860 SVG units", "5.5 pt", "never shrunk", "--png", "assets/fonts", "Space Grotesk",
                   "SpecError", "exit code 2", "## Never", "assets/examples/"):
        assert phrase in reference, phrase


def test_bauhaus_reference_tokens_match_the_renderer() -> None:
    reference = BAUHAUS_REFERENCE.read_text(encoding="utf-8")
    maps = _tool_module("bauhaus_maps")
    for token in (maps.BG, maps.INK, maps.MUTED, maps.SAFFRON, *maps.MEANING_COLOURS.values()):
        assert token in reference, token
    assert str(maps.MAX_WIDTH) in reference


def test_style_and_workflow_references_point_maps_to_the_bauhaus_reference() -> None:
    style = (VISUAL_ROOT / "references" / "editorial-style.md").read_text(encoding="utf-8")
    workflow = (VISUAL_ROOT / "references" / "visual-workflow.md").read_text(encoding="utf-8")
    assert "bauhaus-maps.md" in style and "actor_map" in style
    assert "bauhaus_maps.py" in workflow and "bauhaus-maps.md" in workflow


def test_example_specs_cover_the_features_the_reference_teaches() -> None:
    import yaml

    concept = yaml.safe_load((EXAMPLES / "concept-map-sdd.yml").read_text(encoding="utf-8"))
    process = yaml.safe_load((EXAMPLES / "process-map-spec-kit.yml").read_text(encoding="utf-8"))
    assert concept["kind"] == "concept_map" and process["kind"] == "process_map"
    assert concept["spine"] and any(link.get("cross") for link in concept["links"])
    assert {c.get("level") for c in concept["concepts"]} >= {"key", None}
    assert any(step.get("decision") for step in process["steps"]) and process["artifact_lane"]
    row = {step["id"]: index for index, step in enumerate(process["steps"])}
    assert any(row[f["to"]] < row[f["from"]] for f in process["flow"]), "a back edge"
    assert any(row[f["to"]] > row[f["from"]] + 1 for f in process["flow"]), "an edge that skips rows"


def test_example_specs_render_and_pass_the_print_size_check(tmp_path: Path) -> None:
    import shutil
    import subprocess
    import sys

    import pytest

    if shutil.which("dot") is None:
        pytest.skip("Graphviz dot is not installed")
    editorial = _tool_module("editorial_svg")
    for name in ("concept-map-sdd", "process-map-spec-kit"):
        out = tmp_path / f"{name}.svg"
        done = subprocess.run([sys.executable, str(BAUHAUS_TOOL), "render", str(EXAMPLES / f"{name}.yml"), "--out", str(out)],
                              capture_output=True, text=True)
        assert done.returncode == 0, done.stderr
        svg = out.read_text(encoding="utf-8")
        assert editorial.check(svg) == [], name
        assert float(re.search(r'width="([\d.]+)"', svg).group(1)) <= 860
