"""Named spec scenarios for #11: validated provenance handoff to visuals (R17).

Paired case (tasks #6413): the spec's final provenance requirement renders
as two named RED tests, both retained.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from evidence_contract import evidence_package_sha256  # noqa: E402
from visual_metadata import validate_visual_evidence_provenance, validate_visual_manifest  # noqa: E402


def write_evidence(folder: Path, claim_ids: list[str]) -> None:
    (folder / "research").mkdir(parents=True, exist_ok=True)
    claims = [
        {
            "claim_id": cid,
            "section": "Desarrollo",
            "source_id": "smith2024",
            "source_class": "peer_reviewed_article",
            "evidence": "Measured effect.",
            "locator": "p. 3",
            "identifier": "https://doi.org/10.1000/example",
            "access_date": "2026-09-01",
            "citation_key": "smith2024",
            "use_type": "paraphrase",
            "confidence": "high",
        }
        for cid in claim_ids
    ]
    (folder / "research" / "evidence.yml").write_text(
        yaml.dump({"claims": claims}), encoding="utf-8"
    )


def figure_referencing(folder: Path, claim_ids: list[str]) -> dict:
    return {
        "file": "figure.svg",
        "evidence_package_sha256": evidence_package_sha256(folder),
        "claim_ids": claim_ids,
    }


@pytest.fixture
def report_folder(tmp_path: Path) -> Path:
    return tmp_path


def test_builder_visual_handoff_preserves_validated_provenance(report_folder: Path) -> None:
    """Provenance -- evidence-package identity and claim ids -- survives the
    request/result handoff when the figure matches the current package."""
    write_evidence(report_folder, ["C-001", "C-002"])
    figure = figure_referencing(report_folder, ["C-001"])

    outcome = validate_visual_evidence_provenance(report_folder, [figure])
    assert outcome.errors == []


def test_visual_handoff_rejects_invalid_or_mutated_evidence(report_folder: Path) -> None:
    """Unknown claim id, no evidence.yml at all, and a mutated package are
    each rejected and never granted readiness."""
    # No evidence.yml at all, but the figure claims provenance.
    orphan_folder = report_folder / "orphan"
    orphan_folder.mkdir()
    orphan_figure = {
        "file": "figure.svg",
        "evidence_package_sha256": "0" * 64,
        "claim_ids": ["C-001"],
    }
    outcome = validate_visual_evidence_provenance(orphan_folder, [orphan_figure])
    assert outcome.errors

    # Unknown claim_id: evidence.yml exists but never declares it.
    write_evidence(report_folder, ["C-001"])
    unknown_figure = figure_referencing(report_folder, ["C-999"])
    outcome = validate_visual_evidence_provenance(report_folder, [unknown_figure])
    assert any("C-999" in e for e in outcome.errors)

    # Mutated package: the figure's recorded hash no longer matches the
    # current evidence.yml bytes (the package changed after the figure
    # request was made).
    figure = figure_referencing(report_folder, ["C-001"])
    write_evidence(report_folder, ["C-001", "C-003"])  # evidence.yml mutated
    outcome = validate_visual_evidence_provenance(report_folder, [figure])
    assert any("mut" in e.lower() for e in outcome.errors)


# ---------------------------------------------------------------------------
# Integration -- the composed manifest/final gate rejects it too
# ---------------------------------------------------------------------------


def test_validate_visual_manifest_rejects_unknown_claim_id(report_folder: Path) -> None:
    """The gate real callers use (validate_visual_manifest, report_folder
    distinct from the figures folder) surfaces the same rejection."""
    write_evidence(report_folder, ["C-001"])
    figures_folder = report_folder / "figures"
    figures_folder.mkdir()
    asset = figures_folder / "figure.svg"
    asset.write_bytes(b"<svg></svg>")
    import hashlib

    figure_entry = {
        "file": "figure.svg",
        "title": "Diagram",
        "caption": "A diagram",
        "source": "Original work",
        "renderer": "test-renderer",
        "section": "Desarrollo",
        "request_id": "req-1",
        "result_id": "res-1",
        "content_sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
        "license": "Original work",
        "license_status": "original",
        "alt_text": "A diagram",
        "evidence_package_sha256": evidence_package_sha256(report_folder),
        "claim_ids": ["C-999"],
    }
    manifest = figures_folder / "figures.yml"
    manifest.write_text(yaml.dump({"figures": [figure_entry]}), encoding="utf-8")

    outcome = validate_visual_manifest(figures_folder, manifest, report_folder=report_folder)
    assert any("C-999" in e for e in outcome.errors)
