"""Validate/deliver-phase tests for ``tools/doc_status.py`` (slice 2b-iii).

Slice 2b-iii ships the last two derivations. Validate is ``done`` when
``validation.yml`` records ``result: pass`` for the exact bytes of the final PDF,
``blocked`` with ``validation_failed`` when it records a fail, and ``pending`` when
the receipt is missing or its hash no longer matches. Deliver is ``done`` when a
``<slug>-vNNN.pdf`` under the Documents root hash-matches the final PDF and
``pending`` otherwise. Like the 2a/2b-i/2b-ii suites these tests call the handlers
directly and assert the raw token, detail and blocked reason -- ``derive``, the
renderers and the CLI are slice 2c. Artifact shapes come from ``tools/conftest.py``.
"""
from __future__ import annotations

from pathlib import Path

import doc_status
from conftest import _config, _pdf, _published, _report, _validation

CATEGORY = "Academicos"
SLUG = "informe-de-laboratorio"


def _final_pdf(folder: Path) -> Path:
    """Build the default report and its configured final PDF; return the PDF path."""
    _report(folder)
    return _pdf(folder)


# ---------------------------------------------------------------------------
# 2.12 validate
# ---------------------------------------------------------------------------


def test_validate_pass_with_matching_hash_is_done(tmp_path: Path) -> None:
    """A pass receipt bound to the current PDF bytes is the validate artifact."""
    folder = tmp_path / "wf"
    pdf = _final_pdf(folder)
    _validation(folder, pdf=pdf)

    phase = doc_status._phase_validate(folder, _config(folder), None)

    assert phase.name == "validate"
    assert phase.state == doc_status.DONE
    assert phase.blocked_reason == ""
    assert pdf.name in phase.detail


def test_validate_pass_with_mismatched_hash_is_pending(tmp_path: Path) -> None:
    """A receipt for other bytes does not validate this PDF; rerun validation."""
    folder = tmp_path / "wf"
    pdf = _final_pdf(folder)
    _validation(folder, pdf=pdf, artifact_sha256="0" * 64)

    phase = doc_status._phase_validate(folder, _config(folder), None)

    assert phase.state == doc_status.PENDING
    assert phase.blocked_reason == ""
    assert phase.state != doc_status.DONE


def test_validate_result_fail_is_blocked_with_validation_failed(tmp_path: Path) -> None:
    """A recorded failure stops the route instead of advancing to delivery."""
    folder = tmp_path / "wf"
    pdf = _final_pdf(folder)
    _validation(folder, pdf=pdf, result="fail")

    phase = doc_status._phase_validate(folder, _config(folder), None)

    assert phase.state == doc_status.BLOCKED
    assert phase.blocked_reason == "validation_failed"
    assert phase.state != doc_status.DONE


def test_validate_missing_receipt_is_pending(tmp_path: Path) -> None:
    """TRIANGULATE: a folder that was never validated waits at validate."""
    folder = tmp_path / "wf"
    _final_pdf(folder)

    phase = doc_status._phase_validate(folder, _config(folder), None)

    assert phase.state == doc_status.PENDING
    assert phase.blocked_reason == ""
    assert "validation.yml" in phase.detail


def test_validate_missing_final_pdf_is_pending(tmp_path: Path) -> None:
    """TRIANGULATE: a receipt cannot bind to a PDF that no longer exists."""
    folder = tmp_path / "wf"
    pdf = _final_pdf(folder)
    _validation(folder, pdf=pdf)
    pdf.unlink()

    phase = doc_status._phase_validate(folder, _config(folder), None)

    assert phase.state == doc_status.PENDING
    assert phase.blocked_reason == ""
    assert phase.state != doc_status.DONE


def test_validate_unparsable_receipt_is_pending_not_done(tmp_path: Path) -> None:
    """TRIANGULATE: a corrupt receipt is never read as a pass."""
    folder = tmp_path / "wf"
    _final_pdf(folder)
    (folder / "validation.yml").write_text("artifact_sha256: [unclosed\n", encoding="utf-8")

    phase = doc_status._phase_validate(folder, _config(folder), None)

    assert phase.state == doc_status.PENDING
    assert phase.blocked_reason == ""
    assert phase.state != doc_status.DONE


# ---------------------------------------------------------------------------
# 2.14 deliver
# ---------------------------------------------------------------------------


def test_deliver_hash_matched_published_pdf_is_done(tmp_path: Path) -> None:
    """A published version whose bytes match the final PDF is the delivery."""
    folder = tmp_path / "wf"
    pdf = _final_pdf(folder)
    root = tmp_path / "Documents"
    published = _published(root, category=CATEGORY, slug=SLUG, source=pdf)

    phase = doc_status._phase_deliver(folder, _config(folder), root)

    assert phase.name == "deliver"
    assert phase.state == doc_status.DONE
    assert phase.blocked_reason == ""
    assert published.name in phase.detail


def test_deliver_absent_published_pdf_is_pending(tmp_path: Path) -> None:
    """Nothing published for this report keeps delivery pending."""
    folder = tmp_path / "wf"
    _final_pdf(folder)
    root = tmp_path / "Documents"

    phase = doc_status._phase_deliver(folder, _config(folder), root)

    assert phase.state == doc_status.PENDING
    assert phase.blocked_reason == ""
    assert phase.state != doc_status.DONE


def test_deliver_published_copy_with_other_bytes_is_pending(tmp_path: Path) -> None:
    """TRIANGULATE: a same-named version with different bytes is not a delivery."""
    folder = tmp_path / "wf"
    _final_pdf(folder)
    root = tmp_path / "Documents"
    _published(root, category=CATEGORY, slug=SLUG, content=b"%PDF-1.4\nOTHER\n%%EOF\n")

    phase = doc_status._phase_deliver(folder, _config(folder), root)

    assert phase.state == doc_status.PENDING


def test_deliver_scans_every_version_for_a_hash_match(tmp_path: Path) -> None:
    """TRIANGULATE: an older mismatched version does not hide the matching v002."""
    folder = tmp_path / "wf"
    pdf = _final_pdf(folder)
    root = tmp_path / "Documents"
    _published(root, category=CATEGORY, slug=SLUG, content=b"%PDF-1.4\nSTALE\n%%EOF\n", version=1)
    matched = _published(root, category=CATEGORY, slug=SLUG, source=pdf, version=2)

    phase = doc_status._phase_deliver(folder, _config(folder), root)

    assert phase.state == doc_status.DONE
    assert matched.name in phase.detail


def test_deliver_defaults_to_home_documents(tmp_path: Path, monkeypatch) -> None:
    """TRIANGULATE: without an explicit root the phase reads ``~/Documents``."""
    folder = tmp_path / "wf"
    pdf = _final_pdf(folder)
    root = tmp_path / "home" / "Documents"
    published = _published(root, category=CATEGORY, slug=SLUG, source=pdf)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))

    phase = doc_status._phase_deliver(folder, _config(folder), None)

    assert phase.state == doc_status.DONE
    assert published.name in phase.detail


# ---------------------------------------------------------------------------
# purity
# ---------------------------------------------------------------------------


def test_validate_and_deliver_derivations_never_write(tmp_path: Path) -> None:
    """Both late handlers only read: the folder listing is byte-identical after."""
    folder = tmp_path / "wf"
    pdf = _final_pdf(folder)
    _validation(folder, pdf=pdf)
    root = tmp_path / "Documents"
    _published(root, category=CATEGORY, slug=SLUG, source=pdf)
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    config = _config(folder)

    doc_status._phase_validate(folder, config, root)
    doc_status._phase_deliver(folder, config, root)

    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    assert after == before
