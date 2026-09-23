"""RED tests for the contextual table style catalog and selector (issue #13).

Covers spec scenarios R1-R4:
  R1 test_issue_13_exact_versioned_catalog
  R2 test_issue_13_catalog_is_runtime_self_contained
  R3 test_issue_13_context_matrix_is_deterministic
  R4 test_issue_13_applicability_and_avoidance
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from table_styles import (  # noqa: E402
    APPROVED_STYLE_IDS,
    REQUIRED_TOKEN_KEYS,
    TableContext,
    eligible_candidates,
    load_catalog,
    select_style,
)

ROOT = TOOLS.parent


def test_issue_13_exact_versioned_catalog() -> None:
    catalog = load_catalog()

    assert catalog.schema_version == 1
    assert isinstance(catalog.catalog_version, str) and catalog.catalog_version.strip()
    assert set(catalog.styles) == APPROVED_STYLE_IDS

    for style_id, style in catalog.styles.items():
        assert style.id == style_id
        assert style.label.strip()
        assert set(style.tokens) == REQUIRED_TOKEN_KEYS
        assert style.applicability is not None
        assert style.avoidance is not None


def test_issue_13_catalog_is_runtime_self_contained() -> None:
    # Neither the loader source nor the catalog file may depend on the
    # private evaluation artifact's absolute path or parse a PDF at runtime.
    source = (TOOLS / "table_styles.py").read_text(encoding="utf-8")
    catalog_text = (ROOT / "templates" / "table_styles.yml").read_text(encoding="utf-8")
    for forbidden in ("reports-system", ".pdf", "PyPDF", "pdfplumber"):
        assert forbidden not in source
        assert forbidden not in catalog_text

    # Selection succeeds without touching any private/content-root path.
    catalog = load_catalog()
    context = TableContext(
        purpose="reference", length="short", density="low", columns=3, rows=5,
        pagination="single",
    )
    result = select_style(context, catalog)
    assert result.style_id in APPROVED_STYLE_IDS


SHORT = TableContext(purpose="reference", length="short", density="low", columns=3, rows=5, pagination="single")
LONG = TableContext(purpose="reference", length="long", density="medium", columns=3, rows=10, pagination="single")
COMPARISON = TableContext(
    purpose="comparison", length="short", density="medium", columns=4, rows=6,
    pagination="single", emphasis="column", meaning="comparison",
)
STATUS = TableContext(
    purpose="status", length="short", density="medium", columns=4, rows=6,
    pagination="single", meaning="status",
)
DENSE = TableContext(purpose="dense", length="long", density="high", columns=6, rows=20, pagination="single")
MULTIPAGE = TableContext(
    purpose="reference", length="long", density="medium", columns=3, rows=40,
    pagination="multipage",
)


def test_issue_13_context_matrix_is_deterministic() -> None:
    catalog = load_catalog()
    expected = {
        "short": ("TAB-CL-01", SHORT),
        "long": ("TAB-ZB-04", LONG),
        "comparison": ("TAB-CE-05", COMPARISON),
        "status": ("TAB-ES-06", STATUS),
        "dense": ("TAB-CC-07", DENSE),
        "multipage": ("TAB-ZB-04", MULTIPAGE),
    }
    for name, (expected_id, context) in expected.items():
        first = select_style(context, catalog)
        second = select_style(context, catalog)
        assert first.style_id == expected_id, name
        assert second.style_id == expected_id, name
        assert first.rationale == second.rationale, name
        assert first.rationale.strip()


def test_issue_13_applicability_and_avoidance() -> None:
    catalog = load_catalog()

    # Avoidance: TAB-CL-01 explicitly avoids high-density contexts.
    high_density_reference = TableContext(
        purpose="reference", length="short", density="high", columns=3, rows=5, pagination="single",
    )
    candidates = eligible_candidates(high_density_reference, catalog)
    assert "TAB-CL-01" not in candidates

    # Applicability: TAB-MN-03 only applies to short tables.
    long_reference = TableContext(
        purpose="reference", length="long", density="low", columns=3, rows=10, pagination="single",
    )
    candidates = eligible_candidates(long_reference, catalog)
    assert "TAB-MN-03" not in candidates

    # Sanity: both exclusions leave at least one eligible style.
    assert eligible_candidates(high_density_reference, catalog)
    assert eligible_candidates(long_reference, catalog)
