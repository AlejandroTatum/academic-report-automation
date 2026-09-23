"""RED tests for table style override precedence and evidence receipts (issue #13).

Covers spec scenarios R5-R8:
  R5 test_issue_13_override_precedence
  R6 test_issue_13_invalid_override_rejection
  R7 test_issue_13_unsupported_context_blocks
  R8 test_issue_13_selection_evidence_receipt
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from table_model import (  # noqa: E402
    OverrideRejectedError,
    TableRequest,
    TableStylesContext,
    resolve_table_style,
)
from table_styles import TableContext, UnsupportedContextError, load_catalog  # noqa: E402

CATALOG = load_catalog()

SHORT_REFERENCE = TableContext(
    purpose="reference", length="short", density="low", columns=3, rows=5, pagination="single",
)


def _request(**overrides: object) -> TableRequest:
    fields: dict[str, object] = {
        "table_key": "results-summary",
        "context": SHORT_REFERENCE,
        "teacher_override": None,
        "institution_override": None,
    }
    fields.update(overrides)
    return TableRequest(**fields)  # type: ignore[arg-type]


def test_issue_13_override_precedence() -> None:
    # Teacher wins over institution.
    both = _request(teacher_override="TAB-MN-03", institution_override="TAB-TC-02")
    receipt = resolve_table_style(both, CATALOG)
    assert receipt.style_id == "TAB-MN-03"
    assert receipt.precedence_source == "teacher"

    # Institution wins over automatic when there is no teacher override.
    institution_only = _request(teacher_override=None, institution_override="TAB-TC-02")
    receipt = resolve_table_style(institution_only, CATALOG)
    assert receipt.style_id == "TAB-TC-02"
    assert receipt.precedence_source == "institution"

    # Automatic selection applies when neither override is set.
    automatic = _request(teacher_override=None, institution_override=None)
    receipt = resolve_table_style(automatic, CATALOG)
    assert receipt.style_id == "TAB-CL-01"
    assert receipt.precedence_source == "automatic"


@pytest.mark.parametrize(
    ("override_kwargs", "expected_id", "expected_reason_fragment"),
    [
        ({"teacher_override": "TAB-XX-99"}, "TAB-XX-99", "unapproved"),
        ({"teacher_override": ""}, "", "missing"),
        (
            # TAB-MN-03 only applies to short tables (max_columns 3); a
            # 6-column comparison table is context-incompatible.
            {"teacher_override": "TAB-MN-03", "context": TableContext(
                purpose="comparison", length="short", density="medium",
                columns=6, rows=6, pagination="single", emphasis="column", meaning="comparison",
            )},
            "TAB-MN-03",
            "incompatible",
        ),
        (
            # TAB-ZB-04's applicability (purpose=reference, length=long)
            # matches this context on its own, but its avoidance explicitly
            # excludes column-emphasis contexts -- an override must be
            # rejected by avoidance too, not applicability alone (T1+T2
            # review R3-override-ignores-avoidance).
            {"teacher_override": "TAB-ZB-04", "context": TableContext(
                purpose="reference", length="long", density="medium",
                columns=3, rows=10, pagination="single", emphasis="column",
            )},
            "TAB-ZB-04",
            "incompatible",
        ),
    ],
)
def test_issue_13_invalid_override_rejection(override_kwargs, expected_id, expected_reason_fragment) -> None:
    request = _request(**override_kwargs)
    with pytest.raises(OverrideRejectedError) as excinfo:
        resolve_table_style(request, CATALOG)
    assert excinfo.value.rejected_id == expected_id
    assert expected_reason_fragment in excinfo.value.reason


def test_issue_13_deprecated_override_rejection() -> None:
    deprecated_catalog = CATALOG.__class__(
        schema_version=CATALOG.schema_version,
        catalog_version=CATALOG.catalog_version,
        styles={
            **CATALOG.styles,
            "TAB-CL-01": CATALOG.styles["TAB-CL-01"].__class__(
                **{**CATALOG.styles["TAB-CL-01"].__dict__, "deprecated": True}
            ),
        },
        status_indicators=CATALOG.status_indicators,
        source_path=CATALOG.source_path,
    )
    request = _request(teacher_override="TAB-CL-01")
    with pytest.raises(OverrideRejectedError) as excinfo:
        resolve_table_style(request, deprecated_catalog)
    assert excinfo.value.rejected_id == "TAB-CL-01"
    assert "deprecated" in excinfo.value.reason


def test_issue_13_unsupported_context_blocks() -> None:
    # No approved style is applicable to a table with an incoherent
    # "dense" purpose but low density: automatic selection has no candidate.
    unsupported = TableContext(
        purpose="dense", length="short", density="low", columns=6, rows=6, pagination="single",
    )
    request = _request(context=unsupported, teacher_override=None, institution_override=None)
    with pytest.raises(UnsupportedContextError) as excinfo:
        resolve_table_style(request, CATALOG)
    message = str(excinfo.value)
    assert "purpose" in message
    assert "density" in message


def test_table_styles_context_request_for_applies_teacher_then_institution() -> None:
    styles_context = TableStylesContext(
        catalog=CATALOG,
        teacher_overrides={"results-summary": "TAB-MN-03"},
        institution_override="TAB-TC-02",
    )
    with_teacher = styles_context.request_for("results-summary", SHORT_REFERENCE)
    assert with_teacher.teacher_override == "TAB-MN-03"
    assert with_teacher.institution_override == "TAB-TC-02"

    without_teacher = styles_context.request_for("other-table", SHORT_REFERENCE)
    assert without_teacher.teacher_override is None
    assert without_teacher.institution_override == "TAB-TC-02"


def test_issue_13_selection_evidence_receipt() -> None:
    receipt = resolve_table_style(_request(), CATALOG)

    assert receipt.table_key == "results-summary"
    assert receipt.style_id in CATALOG.styles
    assert receipt.catalog_version == CATALOG.catalog_version
    assert receipt.context == SHORT_REFERENCE
    assert receipt.precedence_source == "automatic"
    assert receipt.rationale.strip()

    for field_value in (receipt.table_key, receipt.style_id, receipt.catalog_version, receipt.rationale):
        assert "/home/" not in field_value
        assert str(CATALOG.source_path) not in field_value
