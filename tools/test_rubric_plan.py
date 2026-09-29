"""Unit tests for ``tools/rubric_plan.py`` (new-report-flow T3).

The plan phase artifact: ``rubric.yml`` turns the teacher's rubric into the
one-criterion-one-task plan the draft and content check follow. These tests pin
``validate_rubric`` (schema key, non-empty ``source``, criterion shapes: slug
ids, non-empty title/section, positive numeric weight), the folder-level
``rubric_state`` predicate (``absent|malformed|valid``, never raising for bad
files), and the ``load_rubric`` loader. Artifact shapes come from
``tools/conftest.py``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import rubric_plan
from conftest import DEFAULT_RUBRIC_CRITERIA, RUBRIC_SCHEMA, _rubric


# ---------------------------------------------------------------------------
# validate_rubric: accepted shapes
# ---------------------------------------------------------------------------


def test_schema_constant_is_pinned() -> None:
    assert rubric_plan.RUBRIC_NAME == "rubric.yml"
    assert rubric_plan.RUBRIC_SCHEMA == "academic.rubric/v1"
    assert RUBRIC_SCHEMA == rubric_plan.RUBRIC_SCHEMA


def test_validate_accepts_minimal_valid_rubric() -> None:
    data = {
        "schema": RUBRIC_SCHEMA,
        "source": "guia de la catedra",
        "criteria": [{"id": "objetivo", "title": "Objetivo claro", "section": "Objetivos"}],
    }

    assert rubric_plan.validate_rubric(data) == []


def test_validate_accepts_optional_description_and_weight() -> None:
    data = {
        "schema": RUBRIC_SCHEMA,
        "source": "teacher explanation",
        "criteria": [
            {
                "id": "metodologia",
                "title": "Metodologia descrita",
                "section": "Metodologia",
                "description": "Describe instruments and procedure.",
                "weight": 2.5,
            }
        ],
    }

    assert rubric_plan.validate_rubric(data) == []


# ---------------------------------------------------------------------------
# validate_rubric: rejected shapes
# ---------------------------------------------------------------------------


def test_validate_rejects_non_mapping() -> None:
    assert rubric_plan.validate_rubric(["not", "a", "mapping"]) != []
    assert rubric_plan.validate_rubric("just a string") != []


@pytest.mark.parametrize("schema", [None, "", "academic.rubric/v2", 7])
def test_validate_rejects_missing_or_foreign_schema(schema: object) -> None:
    data = {"schema": schema, "source": "guia", "criteria": [dict(DEFAULT_RUBRIC_CRITERIA[0])]}

    assert rubric_plan.validate_rubric(data) != []


@pytest.mark.parametrize("source", [None, "", "   "])
def test_validate_rejects_missing_or_blank_source(source: object) -> None:
    data = {"schema": RUBRIC_SCHEMA, "source": source, "criteria": [dict(DEFAULT_RUBRIC_CRITERIA[0])]}

    assert rubric_plan.validate_rubric(data) != []


@pytest.mark.parametrize("criteria", [None, [], "nope", {"id": "objetivo"}])
def test_validate_rejects_empty_or_non_list_criteria(criteria: object) -> None:
    data = {"schema": RUBRIC_SCHEMA, "source": "guia", "criteria": criteria}

    assert rubric_plan.validate_rubric(data) != []


def test_validate_rejects_non_mapping_criterion() -> None:
    data = {"schema": RUBRIC_SCHEMA, "source": "guia", "criteria": ["objetivo"]}

    assert rubric_plan.validate_rubric(data) != []


@pytest.mark.parametrize("drop", [("title",), ("section",), ("id",)])
def test_validate_rejects_criterion_missing_required_keys(drop: tuple[str, ...]) -> None:
    criterion = dict(DEFAULT_RUBRIC_CRITERIA[0])
    for key in drop:
        criterion.pop(key)  # type: ignore[arg-type]
    data = {"schema": RUBRIC_SCHEMA, "source": "guia", "criteria": [criterion]}

    assert rubric_plan.validate_rubric(data) != []


@pytest.mark.parametrize("title", [None, "", "   "])
def test_validate_rejects_blank_title(title: object) -> None:
    criterion = dict(DEFAULT_RUBRIC_CRITERIA[0], title=title)
    data = {"schema": RUBRIC_SCHEMA, "source": "guia", "criteria": [criterion]}

    assert rubric_plan.validate_rubric(data) != []


@pytest.mark.parametrize("bad_id", ["Objetivo", "con espacios", "", "anio_2026", "sueño"])
def test_validate_rejects_non_slug_ids(bad_id: str) -> None:
    criterion = dict(DEFAULT_RUBRIC_CRITERIA[0], id=bad_id)
    data = {"schema": RUBRIC_SCHEMA, "source": "guia", "criteria": [criterion]}

    assert rubric_plan.validate_rubric(data) != []


def test_validate_rejects_duplicate_ids() -> None:
    criterion = dict(DEFAULT_RUBRIC_CRITERIA[0])
    data = {"schema": RUBRIC_SCHEMA, "source": "guia", "criteria": [criterion, dict(criterion)]}

    assert rubric_plan.validate_rubric(data) != []


@pytest.mark.parametrize("weight", [0, -1, "heavy", True])
def test_validate_rejects_non_positive_or_non_numeric_weight(weight: object) -> None:
    criterion = dict(DEFAULT_RUBRIC_CRITERIA[0], weight=weight)
    data = {"schema": RUBRIC_SCHEMA, "source": "guia", "criteria": [criterion]}

    assert rubric_plan.validate_rubric(data) != []


# ---------------------------------------------------------------------------
# rubric_state and load_rubric: folder-level predicate, never raises
# ---------------------------------------------------------------------------


def test_rubric_state_absent(tmp_path: Path) -> None:
    assert rubric_plan.rubric_state(tmp_path / "wf") == "absent"


def test_rubric_state_valid(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _rubric(folder)

    assert rubric_plan.rubric_state(folder) == "valid"


def test_rubric_state_malformed_for_invalid_shapes(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _rubric(folder, criteria=())

    assert rubric_plan.rubric_state(folder) == "malformed"


def test_rubric_state_malformed_for_broken_yaml(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    folder.mkdir()
    (folder / "rubric.yml").write_text("schema: [unclosed\n", encoding="utf-8")

    assert rubric_plan.rubric_state(folder) == "malformed"


def test_rubric_state_malformed_for_non_mapping_yaml(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    folder.mkdir()
    (folder / "rubric.yml").write_text("just a top-level string\n", encoding="utf-8")

    assert rubric_plan.rubric_state(folder) == "malformed"


def test_rubric_state_malformed_for_non_utf8(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    folder.mkdir()
    (folder / "rubric.yml").write_bytes(b"schema: \xff\xfe not utf-8\n")

    assert rubric_plan.rubric_state(folder) == "malformed"


def test_rubric_state_malformed_for_unreadable_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "wf"
    _rubric(folder)

    def _boom(self: object, *args: object, **kwargs: object) -> str:
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "read_text", _boom)

    assert rubric_plan.rubric_state(folder) == "malformed"


def test_load_rubric_returns_criteria_for_valid_plan(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _rubric(folder)

    criteria = rubric_plan.load_rubric(folder)

    assert [c["id"] for c in criteria] == ["objetivo", "metodologia"]


def test_load_rubric_returns_empty_for_absent_and_malformed(tmp_path: Path) -> None:
    absent = tmp_path / "absent"
    assert rubric_plan.load_rubric(absent) == []

    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "rubric.yml").write_bytes(b"\xff\xfe")

    assert rubric_plan.load_rubric(broken) == []
