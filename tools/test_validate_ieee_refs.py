"""Named spec scenarios for #11: claim support and citation/bibliography
reciprocity (R15-R16)."""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import yaml

from validate_ieee_refs import claim_support_and_reciprocity, validate_ieee  # noqa: E402
from report_config import load_report_config  # noqa: E402

BIB_OK = """
@article{smith2024,
  author = {Smith, J.},
  title = {A Study of Latency},
  year = {2024},
}
"""

BODY_OK = "The measured latency dropped [@smith2024].\n"


def claim(**overrides: object) -> dict:
    data = {"claim_id": "C-001", "citation_key": "smith2024"}
    data.update(overrides)
    return data


def test_claim_support_and_citation_reciprocity_pass() -> None:
    result = claim_support_and_reciprocity([claim()], BIB_OK, BODY_OK)
    assert result.errors == []


def test_claim_support_or_reciprocity_failure_blocks_build() -> None:
    # Unsupported claim: no citation_key at all.
    unsupported = claim_support_and_reciprocity(
        [claim(claim_id="C-010", citation_key="")], BIB_OK, BODY_OK
    )
    assert any("C-010" in e and "unsupported" in e for e in unsupported.errors)

    # Unresolved citation: the claim cites a key absent from BibTeX.
    unresolved = claim_support_and_reciprocity(
        [claim(claim_id="C-011", citation_key="doe2023")], BIB_OK, BODY_OK
    )
    assert any("C-011" in e and "doe2023" in e for e in unresolved.errors)

    # Uncited, unjustified entry: the bib has an entry never cited anywhere.
    bib_with_extra = BIB_OK + """
@article{unused2020,
  author = {Nobody},
  title = {Never Cited},
  year = {2020},
}
"""
    uncited = claim_support_and_reciprocity([claim()], bib_with_extra, BODY_OK)
    assert any("unused2020" in e for e in uncited.errors)

    # ...but an explicitly justified entry is not an error.
    justified = claim_support_and_reciprocity(
        [claim()], bib_with_extra, BODY_OK, justified_unused={"unused2020"}
    )
    assert not any("unused2020" in e for e in justified.errors)

    # Duplicate mapping: two claims share the same citation_key.
    duplicate = claim_support_and_reciprocity(
        [claim(claim_id="C-020"), claim(claim_id="C-021")], BIB_OK, BODY_OK
    )
    assert any("duplicado" in e and "C-020" in e and "C-021" in e for e in duplicate.errors)

    # Malformed rendered entry: BibTeX entry missing author/title.
    malformed_bib = BIB_OK + """
@article{broken2022,
  year = {2022},
}
"""
    body_with_broken = BODY_OK + "Also see [@broken2022].\n"
    malformed = claim_support_and_reciprocity(
        [claim(), claim(claim_id="C-002", citation_key="broken2022")],
        malformed_bib,
        body_with_broken,
    )
    assert any("broken2022" in e and "mal formad" in e for e in malformed.errors)


# ---------------------------------------------------------------------------
# Integration -- validate_ieee blocks the build once evidence.yml is present
# ---------------------------------------------------------------------------


def _write_academic_report(folder: Path) -> None:
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
    (folder / "report.yml").write_text(yaml.dump(data), encoding="utf-8")


def test_validate_ieee_blocks_build_on_reciprocity_failure(tmp_path: Path) -> None:
    (tmp_path / "outputs").mkdir()
    _write_academic_report(tmp_path)
    (tmp_path / "body.md").write_text(BODY_OK, encoding="utf-8")
    (tmp_path / "sources.bib").write_text(BIB_OK, encoding="utf-8")
    (tmp_path / "research").mkdir()
    # An evidence.yml claim citing a key that never resolves to BibTeX.
    (tmp_path / "research" / "evidence.yml").write_text(
        yaml.dump({"claims": [claim(claim_id="C-099", citation_key="doe2023")]}),
        encoding="utf-8",
    )

    config = load_report_config(tmp_path)
    result = validate_ieee(config)
    assert any("C-099" in e for e in result.errors)
