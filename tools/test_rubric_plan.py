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


@pytest.mark.parametrize("check", [
    {"type": "unknown", "section": "Objetivos"},
    {"type": "contains", "section": "Objetivos"},
    {"type": "matches", "pattern": "["},
    {"type": "ordered_list", "section": "Objetivos", "min_items": 0},
    {"type": "min_citations", "count": True},
    {"type": "figure_referenced", "count": -1},
    {"type": "keywords_from_section", "section": "A", "from_section": "B", "min": 0},
    {"type": "link_present", "pattern": "["},
])
def test_invalid_checks_are_schema_errors(check: dict) -> None:
    data = {"schema": RUBRIC_SCHEMA, "source": "guide", "criteria": [
        dict(DEFAULT_RUBRIC_CRITERIA[0], checks=[check])
    ]}
    assert rubric_plan.validate_rubric(data)


@pytest.mark.parametrize("check", [
    {"type": "min_citations", "count": 5},
    {"type": "min_citations", "count": 2, "section": "Resultados"},
    {"type": "ordered_list", "section": "Procedimiento", "min_items": 3},
    {"type": "keywords_from_section", "section": "C", "from_section": "O", "min": 2},
])
def test_well_formed_numeric_checks_validate(check: dict) -> None:
    data = {"schema": RUBRIC_SCHEMA, "source": "guide", "criteria": [
        dict(DEFAULT_RUBRIC_CRITERIA[0], checks=[check])
    ]}
    assert rubric_plan.validate_rubric(data) == []


def test_checked_criteria_count_and_semantic_backwards_compatibility() -> None:
    criteria = [dict(DEFAULT_RUBRIC_CRITERIA[0], checks=[{"type": "heading_present", "section": "Objetivos"}]),
                dict(DEFAULT_RUBRIC_CRITERIA[1])]
    data = {"schema": RUBRIC_SCHEMA, "source": "guide", "criteria": criteria}
    assert rubric_plan.validate_rubric(data) == []
    assert rubric_plan.count_checked_criteria(criteria) == 1


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


def test_cli_accepts_a_valid_plan(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = tmp_path / "wf"
    _rubric(folder)

    assert rubric_plan.main([str(folder)]) == 0
    assert "OK" in capsys.readouterr().out


def test_cli_reports_problems_and_fails_on_malformed_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = tmp_path / "wf"
    folder.mkdir()
    (folder / "rubric.yml").write_text("schema: nope\ncriteria: []\n", encoding="utf-8")

    assert rubric_plan.main([str(folder)]) == 1
    assert "rubric" in capsys.readouterr().out.lower()


def test_cli_fails_when_the_plan_is_absent(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert rubric_plan.main([str(tmp_path)]) == 1
    assert "rubric.yml" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# max_words: optional word ceilings (verify-concise-drafts T3)
# ---------------------------------------------------------------------------


def _with_budget(total: object = None, criterion: object = None) -> dict:
    data = {
        "schema": RUBRIC_SCHEMA,
        "source": "guia",
        "criteria": [{"id": "objetivo", "title": "Objetivo", "section": "Objetivos"}],
    }
    if total is not None:
        data["max_words"] = total
    if criterion is not None:
        data["criteria"][0]["max_words"] = criterion
    return data


def test_validate_accepts_total_and_criterion_max_words() -> None:
    assert rubric_plan.validate_rubric(_with_budget(total=900, criterion=120)) == []


@pytest.mark.parametrize("value", [0, -5, True, 2.5, "300"])
def test_validate_rejects_non_positive_integer_max_words(value: object) -> None:
    assert any("max_words" in e for e in rubric_plan.validate_rubric(_with_budget(total=value)))
    assert any("max_words" in e for e in rubric_plan.validate_rubric(_with_budget(criterion=value)))


def test_load_max_words_reads_the_total_or_none(tmp_path: Path) -> None:
    path = _rubric(tmp_path)
    assert rubric_plan.load_max_words(tmp_path) is None
    path.write_text(path.read_text(encoding="utf-8") + "max_words: 450\n", encoding="utf-8")
    assert rubric_plan.load_max_words(tmp_path) == 450


# ---------------------------------------------------------------------------
# deliverables: each guide deliverable needs its own check (T5)
# ---------------------------------------------------------------------------


def _with_deliverables(deliverables: object, checks: list[dict]) -> dict:
    return {
        "schema": RUBRIC_SCHEMA,
        "source": "guia",
        "criteria": [
            {
                "id": "entrega",
                "title": "Informe y entrega",
                "section": "Anexos",
                "deliverables": deliverables,
                "checks": checks,
            }
        ],
    }


LINK_A = {"type": "link_present", "pattern": "wokwi.com/projects/1"}
LINK_B = {"type": "link_present", "pattern": "wokwi.com/projects/2"}
HEADING = {"type": "heading_present", "section": "Anexos"}


def test_deliverables_with_one_non_heading_check_each_are_valid() -> None:
    data = _with_deliverables(["Wokwi Parte A", "Wokwi Parte B"], [HEADING, LINK_A, LINK_B])
    assert rubric_plan.validate_rubric(data) == []


def test_deliverables_covered_only_by_a_heading_check_are_rejected() -> None:
    errors = rubric_plan.validate_rubric(_with_deliverables(["Wokwi Parte A"], [HEADING]))
    assert any("1 deliverables" in e and "0 non-heading checks" in e for e in errors), errors


def test_fewer_non_heading_checks_than_deliverables_are_rejected() -> None:
    errors = rubric_plan.validate_rubric(_with_deliverables(["A", "B", "C"], [LINK_A, LINK_B]))
    assert any("3 deliverables" in e and "2 non-heading checks" in e for e in errors), errors


@pytest.mark.parametrize("value", ["Wokwi", [], [""], [3], None])
def test_deliverables_must_be_a_non_empty_list_of_text(value: object) -> None:
    errors = rubric_plan.validate_rubric(_with_deliverables(value, [LINK_A]))
    assert any("deliverables" in e for e in errors), errors
