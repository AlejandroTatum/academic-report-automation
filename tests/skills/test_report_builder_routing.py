"""Static contract tests for the academic-report-builder skill.

These tests read the skill markdown as data. They do not run the report
pipeline. Their only job is to prove that the routing contract cannot
silently regress back to "every document is a UNL assignment".
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "academic-report-builder"
REFERENCES = SKILL_ROOT / "references"

SKILL_MD = SKILL_ROOT / "SKILL.md"
INTAKE_MD = REFERENCES / "document-intake.md"
ROUTING_MD = REFERENCES / "document-routing.md"
VISUAL_MD = REFERENCES / "visual-directions.md"
GATES_MD = REFERENCES / "quality-gates.md"
UNL_MD = REFERENCES / "unl-shell.md"

ROUTE_SCOPED_FILES = (SKILL_MD, ROUTING_MD)

# Files that must never mention the UNL shell, because they are loaded on
# every route. If unl-shell.md leaks into one of these, a project-doc run
# would pull the institutional cover.
ROUTE_AGNOSTIC_FILES = (INTAKE_MD, VISUAL_MD, GATES_MD)


def read(path: Path) -> str:
    assert path.is_file(), f"missing required skill file: {path}"
    return path.read_text(encoding="utf-8")


def plain(text: str) -> str:
    """Strip markdown emphasis so prose assertions match the rendered wording."""
    return re.sub(r"[*_`]", "", text)


def sections(text: str) -> dict[str, str]:
    """Split a reference file into {heading: body} using its markdown headings."""
    found: dict[str, str] = {}
    heading = "__preamble__"
    buffer: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.*)$", line)
        if match:
            found[heading] = "\n".join(buffer)
            heading = match.group(1).strip()
            buffer = []
        else:
            buffer.append(line)
    found[heading] = "\n".join(buffer)
    return found


@pytest.fixture(scope="module")
def skill() -> str:
    return read(SKILL_MD)


@pytest.fixture(scope="module")
def intake() -> str:
    return read(INTAKE_MD)


@pytest.fixture(scope="module")
def routing() -> str:
    return read(ROUTING_MD)


# --------------------------------------------------------------------------
# Structure
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [SKILL_MD, INTAKE_MD, ROUTING_MD, VISUAL_MD, GATES_MD, UNL_MD],
    ids=lambda p: p.name,
)
def test_required_file_exists(path: Path) -> None:
    assert path.is_file(), f"{path.name} is required by the skill contract"


def test_skill_declares_version_two_or_later(skill: str) -> None:
    match = re.search(r'version:\s*"(\d+)\.(\d+)"', skill)
    assert match, "SKILL.md frontmatter must declare metadata.version"
    major = int(match.group(1))
    assert major >= 2, "multimodal routing landed in version 2.0"


def test_description_is_not_unl_only(skill: str) -> None:
    match = re.search(r'^description:\s*"(.+)"$', skill, re.MULTILINE)
    assert match, "SKILL.md must declare a description"
    description = match.group(1).lower()
    for expected in ("project documentation", "technical document"):
        assert expected in description, (
            f"description must trigger on {expected!r}, not only academic work"
        )


# --------------------------------------------------------------------------
# 8.1 — the document-type gate
# --------------------------------------------------------------------------


def test_document_type_gate_exists(skill: str) -> None:
    assert "Mandatory Intake" in skill
    assert "Prohibition On Inferring Document Type" in skill


DOCUMENT_TYPES = (
    "University academic work",
    "Project documentation",
    "Professional",
    "Technical document",
    "Other",
)


@pytest.mark.parametrize("document_type", DOCUMENT_TYPES)
def test_intake_lists_all_five_document_types(intake: str, document_type: str) -> None:
    assert document_type.lower() in intake.lower(), (
        f"intake must offer {document_type!r} as a document type"
    )


CONFIRMATIONS = (
    "audience",
    "purpose",
    "template",
    "identity",
    "pdf",
    "docx",
    "visual direction",
)


@pytest.mark.parametrize("token", CONFIRMATIONS)
def test_intake_covers_every_confirmation(intake: str, token: str) -> None:
    assert token in intake.lower(), f"intake is missing the {token!r} confirmation"


VISUAL_DIRECTIONS = ("Sober", "Institutional", "Technical", "Executive", "Custom")


@pytest.mark.parametrize("direction", VISUAL_DIRECTIONS)
def test_visual_directions_are_defined(direction: str) -> None:
    intake_text = read(INTAKE_MD)
    visual_text = read(VISUAL_MD)
    assert direction.lower() in intake_text.lower(), (
        f"{direction} must be offered in the intake"
    )
    assert direction.lower() in visual_text.lower(), (
        f"{direction} must have an operational definition"
    )


def test_confirmation_is_required_on_every_execution(skill: str, intake: str) -> None:
    combined = plain(skill + intake).lower()
    assert "every execution" in combined or "every run" in combined
    assert "even when the prompt appears to already contain" in combined, (
        "a prompt that looks complete must still be confirmed"
    )


def test_document_contract_block_is_specified(intake: str) -> None:
    assert "Document Contract" in intake
    for field in ("Type:", "Audience:", "Purpose:", "Outputs:", "Visual direction:"):
        assert field in intake, f"Document Contract block must render {field!r}"


# --------------------------------------------------------------------------
# 8.1 — forbidden behavior
# --------------------------------------------------------------------------


def test_depth_or_length_is_not_a_mandatory_question(intake: str) -> None:
    lowered = intake.lower()
    assert "must not" in lowered
    assert re.search(r"(length|depth|extension)", lowered), (
        "intake must explicitly rule out a mandatory length/depth question"
    )


def test_no_sistemas_operativos_fallback() -> None:
    """The old rule 'Without one, use the Sistemas Operativos format.' is gone.

    The profile file itself may name the course; nothing else may.
    """
    for path in SKILL_ROOT.rglob("*.md"):
        if path.parent.name == "profiles":
            continue
        assert "Sistemas Operativos" not in path.read_text(encoding="utf-8"), (
            f"{path.name} still carries the Sistemas Operativos fallback"
        )


def test_unl_is_not_a_default_or_fallback(skill: str, routing: str) -> None:
    combined = (skill + routing).lower()
    assert "never a silent fallback" in combined or "never fall back" in combined, (
        "Route E must not degrade into the academic route"
    )
    assert "no default document type" in combined


def test_format_request_does_not_imply_academic(skill: str) -> None:
    assert re.search(
        r"pdf or docx is a format signal only", skill, re.IGNORECASE
    ), "asking for PDF/DOCX must never imply a university shell"


@pytest.mark.parametrize("path", ROUTE_AGNOSTIC_FILES, ids=lambda p: p.name)
def test_unl_shell_not_loaded_outside_academic_route(path: Path) -> None:
    text = read(path)
    assert "unl-shell" not in text, (
        f"{path.name} loads on every route and must not reference unl-shell.md"
    )


def test_routing_confines_unl_shell_to_the_academic_section() -> None:
    """In document-routing.md, unl-shell.md may only appear under Route A."""
    for heading, body in sections(read(ROUTING_MD)).items():
        if "unl-shell" not in body:
            continue
        assert re.search(r"route a|academic", heading, re.IGNORECASE), (
            f"unl-shell.md referenced under non-academic section {heading!r}"
        )


def test_skill_unl_references_are_route_qualified(skill: str) -> None:
    """In SKILL.md every unl-shell mention carries an explicit Route A qualifier.

    SKILL.md is a flat operational document with no academic-only section, so
    each individual line has to state the restriction itself.
    """
    for line in skill.splitlines():
        if "unl-shell" not in line:
            continue
        assert re.search(r"route a|academic|only", line, re.IGNORECASE), (
            f"unqualified unl-shell reference in SKILL.md: {line!r}"
        )


# --------------------------------------------------------------------------
# 8.1 — authority boundary
# --------------------------------------------------------------------------


def test_scripts_never_grant_visual_pass(skill: str) -> None:
    assert re.search(
        r"no script,? validator,? or auditor ever grants `?VISUAL_PASS`?",
        skill,
        re.IGNORECASE,
    ), "SKILL.md must state that no script grants VISUAL_PASS"


def test_visible_evidence_overrides_automation() -> None:
    gates = read(GATES_MD)
    assert "Visible evidence overrides automation" in gates


# --------------------------------------------------------------------------
# Hardened composition gates
# --------------------------------------------------------------------------


def test_orphan_heading_rule_is_quantified() -> None:
    gates = read(GATES_MD).lower()
    assert "orphan" in gates
    assert "two lines" in gates, "the orphan-heading rule must be measurable"


def test_whitespace_thresholds_are_quantified() -> None:
    gates = read(GATES_MD)
    assert "20%" in gates, "semi-empty page threshold must be explicit"
    assert "40%" in gates, "lower-page emptiness threshold must be explicit"


def test_wide_table_split_is_documented() -> None:
    gates = read(GATES_MD)
    assert "Acceptance criterion" in gates, (
        "the requirement-table split must be documented to avoid six columns"
    )


def test_diagrams_must_be_module_specific() -> None:
    gates = read(GATES_MD)
    assert "Validación correcta" in gates, (
        "the generic decision node must be named as a rejection criterion"
    )
    for role in ("external service", "retry", "final state"):
        assert role in gates.lower(), (
            f"diagrams must visually differentiate {role!r}"
        )
