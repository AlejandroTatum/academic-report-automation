"""Named spec scenarios for #12: confirmed report structure contract.

Combined per-section model (decision #6408): mandatory rubric/content
criteria per section, plus optional quantitative limits. Scenarios R1-R8 map
one-to-one to the spec at ``sdd/academic-structure-and-research-contract``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from report_config import ReportConfig, load_report_config  # noqa: E402
from structure_contract import (  # noqa: E402
    combine_assignment_sources,
    declared_limit,
    has_blocking_conflicts,
    sha256_file,
    structure_confirmation_state,
    validate_structure_schema,
)
from validate_report import structure_validation  # noqa: E402


@pytest.fixture
def temp_report_folder(tmp_path: Path) -> Path:
    (tmp_path / "outputs").mkdir(parents=True, exist_ok=True)
    return tmp_path


def write_academic_report(folder: Path, structure: object | None = None) -> Path:
    data = {
        "type": "essay",
        "route": "academic",
        "metadata": {
            "title": "Informe",
            "subject": "Sistemas Operativos",
            "teacher": "Ing. Hernán",
            "student": "Alejandro Padilla",
            "date": "2026-01-01",
        },
    }
    if structure is not None:
        data["structure"] = structure
    path = folder / "report.yml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# R1 — combine every supplied assignment source
# ---------------------------------------------------------------------------


def test_intake_combines_supplied_assignment_sources() -> None:
    """Requirements from every supplied source are combined with provenance,
    and contradictions between sources block confirmation."""
    rubric = {
        "kind": "rubric",
        "path": "research/rubric.pdf",
        "sections": [
            {
                "title": "Resumen",
                "criteria": ["Summarize objective, method, and results"],
                "limits": {"words": {"max": 250}},
            },
        ],
    }
    brief = {
        "kind": "brief",
        "path": "research/brief.pdf",
        "sections": [
            {
                "title": "Resumen",
                "criteria": ["State the assignment context"],
                "limits": {"words": {"max": 300}},  # contradicts rubric's 250
            },
            {
                "title": "Desarrollo",
                "criteria": ["Explain the implemented solution"],
            },
        ],
    }

    combined = combine_assignment_sources([rubric, brief])

    assert {entry["path"] for entry in combined["provenance"]} == {
        "research/rubric.pdf",
        "research/brief.pdf",
    }

    resumen = next(s for s in combined["sections"] if s["title"] == "Resumen")
    texts = {c["text"] for c in resumen["criteria"]}
    assert texts == {
        "Summarize objective, method, and results",
        "State the assignment context",
    }
    refs = {c["source_ref"] for c in resumen["criteria"]}
    assert refs == {"research/rubric.pdf", "research/brief.pdf"}

    desarrollo = next(s for s in combined["sections"] if s["title"] == "Desarrollo")
    assert desarrollo["criteria"][0]["source_ref"] == "research/brief.pdf"

    assert has_blocking_conflicts(combined), "the words:max contradiction must block confirmation"
    conflict = combined["conflicts"][0]
    assert conflict["section_title"] == "Resumen"
    assert conflict["field"] == "words"
    assert "words" not in resumen["limits"], "a conflicting key is never silently merged"


def test_intake_combine_surfaces_order_conflict() -> None:
    """A source that orders shared sections differently is a conflict too
    (document-intake.md: "a section required by one and forbidden or
    reordered by another blocks confirmation"), not a silently-resolved
    first-source-wins pick."""
    rubric = {
        "kind": "rubric",
        "path": "research/rubric.pdf",
        "sections": [
            {"title": "Resumen", "criteria": ["Summarize"]},
            {"title": "Desarrollo", "criteria": ["Explain the solution"]},
        ],
    }
    brief = {
        "kind": "brief",
        "path": "research/brief.pdf",
        "sections": [
            # Same two sections, reversed order.
            {"title": "Desarrollo", "criteria": ["State the context"]},
            {"title": "Resumen", "criteria": ["State objectives"]},
        ],
    }

    combined = combine_assignment_sources([rubric, brief])

    assert has_blocking_conflicts(combined), "conflicting cross-source order must block confirmation"
    order_conflicts = [c for c in combined["conflicts"] if c.get("type") == "order"]
    assert order_conflicts, "the order disagreement must be named as its own conflict"
    assert order_conflicts[0]["source"] == "research/brief.pdf"


# ---------------------------------------------------------------------------
# R2/R3 — confirmed schema: exact titles, order, criteria, optional limits
# ---------------------------------------------------------------------------


def test_structure_confirms_exact_titles_order_criteria_and_limits() -> None:
    """A well-formed contract freezes exact titles, order, criteria, and limits."""
    structure = {
        "version": 1,
        "sections": [
            {
                "title": "Resumen",
                "criteria": [{"text": "Summarize objectives and results", "source_ref": "rubric.pdf"}],
                "limits": {"words": {"max": 250}},
            },
            {
                "title": "Desarrollo",
                "criteria": [{"text": "Explain the implemented solution", "source_ref": "rubric.pdf"}],
            },
        ],
    }
    result = validate_structure_schema(structure)
    assert result.errors == []
    titles_in_order = [section["title"] for section in structure["sections"]]
    assert titles_in_order == ["Resumen", "Desarrollo"]


def test_structure_omits_unsupplied_quantitative_limits() -> None:
    """No limit was supplied for Desarrollo, so none is inferred or enforced."""
    structure = {
        "version": 1,
        "sections": [
            {
                "title": "Desarrollo",
                "criteria": [{"text": "Explain the implemented solution", "source_ref": "rubric.pdf"}],
            },
        ],
    }
    result = validate_structure_schema(structure)
    assert result.errors == []
    section = structure["sections"][0]
    assert declared_limit(section, "words") is None
    assert declared_limit(section, "pages") is None

    # An unrecognized limit key is rejected explicitly, never silently accepted.
    bad = {
        "version": 1,
        "sections": [
            {
                "title": "Desarrollo",
                "criteria": [{"text": "x", "source_ref": "rubric.pdf"}],
                "limits": {"paragraphs": 3},
            },
        ],
    }
    bad_result = validate_structure_schema(bad)
    assert any("no reconocidos" in e for e in bad_result.errors)

    # A section with no rubric/content criteria at all is rejected -- criteria
    # are mandatory even though limits stay optional (#6408).
    no_criteria = {"version": 1, "sections": [{"title": "Desarrollo", "criteria": []}]}
    no_criteria_result = validate_structure_schema(no_criteria)
    assert any("al menos un criterio" in e for e in no_criteria_result.errors)


def test_structure_rejects_non_numeric_limit_values() -> None:
    """A limit value that is not a number (or a {min, max} of numbers) is a
    schema error, never a crash at final validation time."""
    bad_scalar = {
        "version": 1,
        "sections": [
            {
                "title": "Resumen",
                "criteria": [{"text": "x", "source_ref": "rubric.pdf"}],
                "limits": {"words": "muchas"},
            },
        ],
    }
    result = validate_structure_schema(bad_scalar)
    assert any("words" in e and "Resumen" in e for e in result.errors)

    bad_dict = {
        "version": 1,
        "sections": [
            {
                "title": "Resumen",
                "criteria": [{"text": "x", "source_ref": "rubric.pdf"}],
                "limits": {"words": {"max": "cincuenta"}},
            },
        ],
    }
    dict_result = validate_structure_schema(bad_dict)
    assert any("words" in e and "Resumen" in e for e in dict_result.errors)


def test_structure_rejects_malformed_sources_shape() -> None:
    """A malformed 'sources' value is a schema error, not a crash when
    confirmation state later inspects it for staleness."""
    bad_sources = {
        "version": 1,
        "sources": "rubric.pdf",  # must be a list, not a bare string
        "sections": [
            {"title": "Resumen", "criteria": [{"text": "x", "source_ref": "rubric.pdf"}]},
        ],
    }
    result = validate_structure_schema(bad_sources)
    assert any("sources" in e for e in result.errors)

    bad_entries = {
        "version": 1,
        "sources": ["rubric.pdf"],  # entries must be mappings, not strings
        "sections": [
            {"title": "Resumen", "criteria": [{"text": "x", "source_ref": "rubric.pdf"}]},
        ],
    }
    entries_result = validate_structure_schema(bad_entries)
    assert any("sources" in e for e in entries_result.errors)


# ---------------------------------------------------------------------------
# R4 — proposed structure requires explicit confirmation
# ---------------------------------------------------------------------------


def test_structure_proposal_requires_confirmation(temp_report_folder: Path) -> None:
    """A proposed structure is not confirmed until the user explicitly says so."""
    folder = temp_report_folder
    write_academic_report(folder, structure="proposed")
    config = load_report_config(folder)

    state, detail = structure_confirmation_state(config)
    assert state == "unconfirmed"
    assert "proposed" in detail

    # A report that never engaged the flow at all is a different state:
    # absent, not unconfirmed -- the pre-existing behaviour is untouched.
    folder2 = temp_report_folder / "legacy"
    folder2.mkdir()
    (folder2 / "outputs").mkdir()
    write_academic_report(folder2, structure=None)
    legacy_config = load_report_config(folder2)
    legacy_state, _ = structure_confirmation_state(legacy_config)
    assert legacy_state == "absent"


# ---------------------------------------------------------------------------
# R5 — a changed structure requires reconfirmation
# ---------------------------------------------------------------------------


def test_structure_change_requires_reconfirmation(temp_report_folder: Path) -> None:
    """A confirmed contract goes stale once its recorded source changes."""
    folder = temp_report_folder
    rubric_path = folder / "rubric.pdf"
    rubric_path.write_bytes(b"original rubric bytes")

    structure = {
        "version": 1,
        "sources": [{"kind": "rubric", "path": "rubric.pdf", "sha256": sha256_file(rubric_path)}],
        "sections": [
            {
                "title": "Resumen",
                "criteria": [{"text": "Summarize", "source_ref": "rubric.pdf"}],
            },
        ],
    }
    write_academic_report(folder, structure=structure)
    config = load_report_config(folder)

    state, _ = structure_confirmation_state(config)
    assert state == "confirmed"

    # The teacher revises the rubric after confirmation.
    rubric_path.write_bytes(b"revised rubric bytes -- new requirement added")
    config = load_report_config(folder)
    changed_state, detail = structure_confirmation_state(config)
    assert changed_state == "stale"
    assert "rubric.pdf" in detail


def test_structure_missing_source_file_is_stale_not_confirmed(temp_report_folder: Path) -> None:
    """A recorded source that disappeared from disk must never fail open
    into 'confirmed' -- the teacher's requirement can no longer be
    re-verified, so reconfirmation is required exactly like a changed hash."""
    folder = temp_report_folder
    rubric_path = folder / "rubric.pdf"
    rubric_path.write_bytes(b"original rubric bytes")

    structure = {
        "version": 1,
        "sources": [{"kind": "rubric", "path": "rubric.pdf", "sha256": sha256_file(rubric_path)}],
        "sections": [
            {"title": "Resumen", "criteria": [{"text": "Summarize", "source_ref": "rubric.pdf"}]},
        ],
    }
    write_academic_report(folder, structure=structure)
    config = load_report_config(folder)
    state, _ = structure_confirmation_state(config)
    assert state == "confirmed"

    rubric_path.unlink()
    config = load_report_config(folder)
    state, detail = structure_confirmation_state(config)
    assert state == "stale"
    assert "rubric.pdf" in detail


# ---------------------------------------------------------------------------
# R6 — unconfirmed structure blocks every downstream phase
# ---------------------------------------------------------------------------


def test_unconfirmed_structure_blocks_all_downstream_phases(temp_report_folder: Path) -> None:
    """Once a report engages the structure flow, doc_status locks downstream
    phases until it reports 'confirmed'."""
    import doc_status

    folder = temp_report_folder
    write_academic_report(folder, structure="proposed")

    status = doc_status.derive(folder)
    intake = next(p for p in status.phases if p.name == "intake")
    assert intake.state in ("pending", "current")
    assert "structure" in intake.detail

    downstream = [p for p in status.phases if p.name != "intake"]
    assert all(p.state == "pending" for p in downstream), (
        "every phase after intake must stay locked while structure is unconfirmed"
    )

    # Confirming the structure unlocks intake; downstream phases proceed on
    # their own merits again (no forced 'waiting for an earlier phase').
    structure = {
        "version": 1,
        "sections": [
            {"title": "Resumen", "criteria": [{"text": "Summarize", "source_ref": "rubric.pdf"}]},
        ],
    }
    write_academic_report(folder, structure=structure)
    confirmed_status = doc_status.derive(folder)
    confirmed_intake = next(p for p in confirmed_status.phases if p.name == "intake")
    assert confirmed_intake.state == "done"


# ---------------------------------------------------------------------------
# R7/R8 — final structure validation: presence, names, order, content, limits
# ---------------------------------------------------------------------------

COMPLIANT_STRUCTURE = {
    "version": 1,
    "sections": [
        {
            "title": "Resumen",
            "criteria": [
                {
                    "text": "State objective and results",
                    "source_ref": "rubric.pdf",
                    "content_anchor": "objetivo",
                }
            ],
            "limits": {"words": {"max": 50}},
        },
        {
            "title": "Desarrollo",
            "criteria": [
                {
                    "text": "Explain the implemented solution",
                    "source_ref": "rubric.pdf",
                    "content_anchor": "solucion",
                }
            ],
        },
    ],
}


def _write_structured_report(folder: Path, structure: dict, body: str) -> ReportConfig:
    write_academic_report(folder, structure=structure)
    (folder / "body.md").write_text(body, encoding="utf-8")
    return load_report_config(folder)


def test_final_structure_validation_accepts_compliant_report(temp_report_folder: Path) -> None:
    """A body matching the confirmed contract passes every final check."""
    body = (
        "# Resumen\n\nEl objetivo del trabajo y sus resultados.\n\n"
        "# Desarrollo\n\nLa solucion implementada se explica aqui.\n"
    )
    config = _write_structured_report(temp_report_folder, COMPLIANT_STRUCTURE, body)
    assert structure_validation(config).errors == []


def test_final_structure_validation_rejects_each_mismatch(temp_report_folder: Path) -> None:
    """Missing, renamed, reordered, content-incomplete, and over-limit each fail named."""
    # Missing section: "Desarrollo" never appears.
    missing_folder = temp_report_folder / "missing"
    missing_folder.mkdir()
    (missing_folder / "outputs").mkdir()
    config = _write_structured_report(
        missing_folder, COMPLIANT_STRUCTURE, "# Resumen\n\nEl objetivo y resultados.\n"
    )
    errors = structure_validation(config).errors
    assert any("Desarrollo" in e for e in errors)

    # Renamed section: "Resumen ejecutivo" does not satisfy "Resumen".
    renamed_folder = temp_report_folder / "renamed"
    renamed_folder.mkdir()
    (renamed_folder / "outputs").mkdir()
    config = _write_structured_report(
        renamed_folder,
        COMPLIANT_STRUCTURE,
        "# Resumen ejecutivo\n\nEl objetivo.\n\n# Desarrollo\n\nLa solucion.\n",
    )
    errors = structure_validation(config).errors
    assert any("Resumen" in e for e in errors)

    # Reordered section: Desarrollo renders before Resumen.
    reordered_folder = temp_report_folder / "reordered"
    reordered_folder.mkdir()
    (reordered_folder / "outputs").mkdir()
    config = _write_structured_report(
        reordered_folder,
        COMPLIANT_STRUCTURE,
        "# Desarrollo\n\nLa solucion.\n\n# Resumen\n\nEl objetivo.\n",
    )
    errors = structure_validation(config).errors
    assert any("orden" in e.lower() for e in errors)

    # Content-incomplete: Resumen exists but never states the objective.
    incomplete_folder = temp_report_folder / "incomplete"
    incomplete_folder.mkdir()
    (incomplete_folder / "outputs").mkdir()
    config = _write_structured_report(
        incomplete_folder,
        COMPLIANT_STRUCTURE,
        "# Resumen\n\nSolo una frase sin el contenido pedido.\n\n"
        "# Desarrollo\n\nLa solucion implementada.\n",
    )
    errors = structure_validation(config).errors
    assert any("criterio" in e.lower() and "Resumen" in e for e in errors)

    # Over declared limit: Resumen exceeds its 50-word cap.
    overlimit_folder = temp_report_folder / "overlimit"
    overlimit_folder.mkdir()
    (overlimit_folder / "outputs").mkdir()
    long_body = "# Resumen\n\n" + ("objetivo palabra " * 40) + "\n\n# Desarrollo\n\nLa solucion.\n"
    config = _write_structured_report(overlimit_folder, COMPLIANT_STRUCTURE, long_body)
    errors = structure_validation(config).errors
    assert any("límite de palabras" in e and "Resumen" in e for e in errors)


def test_final_structure_validation_rejects_stale_structure(temp_report_folder: Path) -> None:
    """A confirmed-but-now-stale contract must fail final validation, never
    silently validate the body against a superseded structure."""
    folder = temp_report_folder
    rubric_path = folder / "rubric.pdf"
    rubric_path.write_bytes(b"original rubric bytes")
    structure = {
        "version": 1,
        "sources": [{"kind": "rubric", "path": "rubric.pdf", "sha256": sha256_file(rubric_path)}],
        "sections": [
            {"title": "Resumen", "criteria": [{"text": "Summarize", "source_ref": "rubric.pdf"}]},
        ],
    }
    body = "# Resumen\n\nEl resumen del trabajo.\n"
    config = _write_structured_report(folder, structure, body)
    assert structure_validation(config).errors == []

    # The teacher revises the rubric after confirmation -- the contract is
    # now stale, and final validation must refuse to certify against it.
    rubric_path.write_bytes(b"revised rubric bytes -- new requirement added")
    config = load_report_config(folder)
    errors = structure_validation(config).errors
    assert any("confirmad" in e.lower() or "stale" in e.lower() for e in errors)


def test_final_structure_validation_ignores_subsection_headings(temp_report_folder: Path) -> None:
    """A subsection heading nested under a required section must not split
    that section's text bucket -- content criteria and word counts inside
    the subsection still belong to the enclosing required section."""
    body = (
        "# Resumen\n\n"
        "## Contexto\n\n"
        "El objetivo del trabajo y sus resultados se explican aqui.\n\n"
        "# Desarrollo\n\nLa solucion implementada se explica aqui.\n"
    )
    config = _write_structured_report(temp_report_folder, COMPLIANT_STRUCTURE, body)
    assert structure_validation(config).errors == []
