"""Tests for tools/deliver_report.py — the explicit deliver-phase entrypoint (#22).

Generation no longer publishes; delivery does, through the existing guarded
publisher (``publish_validated_pdf``). Delivery is thin: it adds the validation
receipt gate (``validation.yml`` with ``result: pass`` bound to the exact final
PDF bytes) on top of the publisher's approval gate, preserves hash continuity
across checking and copying, and creates no new states or human approvals.

Artifact shapes come from ``tools/conftest.py``; the Documents root is always a
temporary directory, never the real ``~/Documents``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from conftest import _approval, _pdf, _report, _sha256, _validation  # noqa: E402
from deliver_report import main  # noqa: E402

CATEGORY = "Academicos"
SLUG = "informe-de-laboratorio"


def _ready_folder(tmp_path: Path) -> tuple[Path, Path]:
    """A work folder with report, approved preview, final PDF and a passing receipt."""
    folder = tmp_path / "wf"
    _report(folder)
    _approval(folder)
    pdf = _pdf(folder)
    _validation(folder, pdf=pdf)
    return folder, pdf


def _run(folder: Path, documents_root: Path) -> int:
    return main([str(folder), "--documents-root", str(documents_root)])


# -- Happy path ---------------------------------------------------------------


def test_delivery_publishes_the_validated_bytes_once(tmp_path: Path) -> None:
    """A fully gated folder delivers the exact PDF bytes as v001."""
    folder, pdf = _ready_folder(tmp_path)
    documents_root = tmp_path / "docs"

    assert _run(folder, documents_root) == 0

    published = documents_root / CATEGORY / SLUG / f"{SLUG}-v001.pdf"
    assert published.is_file()
    assert _sha256(published) == _sha256(pdf)


def test_delivery_is_idempotent_for_identical_bytes(tmp_path: Path, capsys) -> None:
    """A second delivery of the same bytes reuses the version, not a new one."""
    folder, _ = _ready_folder(tmp_path)
    documents_root = tmp_path / "docs"

    assert _run(folder, documents_root) == 0
    assert _run(folder, documents_root) == 0

    published = documents_root / CATEGORY / SLUG
    assert len(list(published.iterdir())) == 1
    assert "REUTILIZADO" in capsys.readouterr().out


# -- Validation receipt gate ----------------------------------------------------


def test_delivery_refuses_missing_validation_receipt(tmp_path: Path, capsys) -> None:
    """No validation.yml means no delivery, and nothing is created."""
    folder, _ = tmp_path / "wf", None
    _report(folder)
    _approval(folder)
    _pdf(folder)
    documents_root = tmp_path / "docs"

    assert _run(folder, documents_root) == 1

    captured = capsys.readouterr()
    assert "validation.yml" in captured.err
    assert not (documents_root / CATEGORY).exists()


def test_delivery_refuses_failed_validation_receipt(tmp_path: Path) -> None:
    """A recorded ``result: fail`` is a refusal, never a delivery."""
    folder, _ = _ready_folder(tmp_path)
    _validation(folder, result="fail")
    documents_root = tmp_path / "docs"

    assert _run(folder, documents_root) == 1
    assert not (documents_root / CATEGORY).exists()


def test_delivery_refuses_receipt_bound_to_other_bytes(tmp_path: Path) -> None:
    """The receipt's artifact_sha256 must match the current final PDF bytes."""
    folder, _ = _ready_folder(tmp_path)
    _validation(folder, artifact_sha256="0" * 64)
    documents_root = tmp_path / "docs"

    assert _run(folder, documents_root) == 1
    assert not (documents_root / CATEGORY).exists()


def test_delivery_refuses_pdf_changed_after_validation(tmp_path: Path) -> None:
    """Editing the PDF after the receipt stales the evidence: delivery refuses."""
    folder, pdf = _ready_folder(tmp_path)
    pdf.write_bytes(b"%PDF-1.4\n%%EOF\nedited after validation\n")
    documents_root = tmp_path / "docs"

    assert _run(folder, documents_root) == 1
    assert not (documents_root / CATEGORY).exists()


# -- Approval gate (enforced by the shared publisher) ---------------------------


def test_delivery_refuses_without_current_approval(tmp_path: Path, capsys) -> None:
    """Without a current approval.yml the publisher refuses and nothing appears."""
    folder = tmp_path / "wf"
    _report(folder)
    _pdf(folder)
    _validation(folder)
    documents_root = tmp_path / "docs"

    assert _run(folder, documents_root) == 1

    captured = capsys.readouterr()
    assert "aprobación" in captured.err
    assert not (documents_root / CATEGORY).exists()


def test_delivery_refuses_stale_approval(tmp_path: Path) -> None:
    """A stale marker (edited preview) is refused by the publisher."""
    folder = tmp_path / "wf"
    _report(folder)
    _approval(folder)
    _pdf(folder)
    _validation(folder)
    (folder / "preview.md").write_text("edited after approval\n", encoding="utf-8")
    documents_root = tmp_path / "docs"

    assert _run(folder, documents_root) == 1
    assert not (documents_root / CATEGORY).exists()


# -- Basic input checks ---------------------------------------------------------


def test_delivery_refuses_missing_final_pdf(tmp_path: Path) -> None:
    """No final PDF, no delivery."""
    folder = tmp_path / "wf"
    _report(folder)
    _approval(folder)
    # Receipt bound to some bytes; the final PDF itself is absent.
    stray = tmp_path / "elsewhere.pdf"
    stray.write_bytes(b"%PDF-1.4\n%%EOF\n")
    _validation(folder, pdf=stray)
    documents_root = tmp_path / "docs"

    assert _run(folder, documents_root) == 1
    assert not (documents_root / CATEGORY).exists()
