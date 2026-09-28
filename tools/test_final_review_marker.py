"""Tests for the final human review marker in ``tools/final_review_marker.py``.

``final_review_state()`` is the predicate behind the delivery gate: the
publisher (``publish_pdf``) and the deliver entrypoint (``deliver_report``)
both refuse to publish unless a ``final-review.yml`` marker binds the exact
bytes of the PDF being published. Like the approval marker, the predicate is a
pure read: it never writes, never creates a directory, and never raises for a
bad marker -- every invalid shape is ``malformed`` data the caller can report.
A stale marker means the reviewed bytes are gone: the PDF is missing or its
hash no longer matches, so the human must review the current PDF again.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import final_review_marker

PDF_BYTES = b"%PDF-1.7\nfinal reviewed content\n"
OTHER_PDF_BYTES = b"%PDF-1.7\nrebuilt after review\n"


def _write_pdf(folder: Path, content: bytes = PDF_BYTES) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    pdf = folder / "final" / "report.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(content)
    return pdf


def _write_marker(folder: Path, body: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    marker = folder / "final-review.yml"
    marker.write_text(body, encoding="utf-8")
    return marker


def _marker_body(pdf: Path, *, pdf_sha: str | None = None) -> str:
    if pdf_sha is None:
        pdf_sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    return (
        "schema: academic.doc-final-review/v1\n"
        f"pdf_sha256: {pdf_sha}\n"
        "reviewed_at: 2026-09-10T16:30:00Z\n"
        "reviewed_by: Alejandro\n"
    )


def _snapshot(folder: Path) -> list[tuple[str, int, bool]]:
    return sorted(
        (path.name, path.stat().st_size, path.is_dir()) for path in folder.iterdir()
    )


def test_marker_constants_are_declared() -> None:
    """The marker contract is a stable, importable surface for both consumers."""
    assert final_review_marker.MARKER_NAME == "final-review.yml"
    assert final_review_marker.MARKER_SCHEMA == "academic.doc-final-review/v1"
    assert final_review_marker.REQUIRED_KEYS == (
        "pdf_sha256",
        "reviewed_at",
        "reviewed_by",
    )


def test_state_absent_current_and_stale(tmp_path: Path) -> None:
    """The bounded state vocabulary, derived read-only from disk."""
    # absent — there is no marker at all
    pdf_only = tmp_path / "pdf-only"
    _write_pdf(pdf_only)
    absent = final_review_marker.final_review_state(pdf_only, pdf_only / "final" / "report.pdf")
    assert absent.state == "absent"
    assert absent.reason == "final_review_marker_absent"
    assert "final-review.yml" in absent.detail
    assert absent.detail.isascii()

    # current — the marker hash equals the exact PDF bytes
    current_folder = tmp_path / "current"
    pdf = _write_pdf(current_folder)
    _write_marker(current_folder, _marker_body(pdf))
    current = final_review_marker.final_review_state(current_folder, pdf)
    assert current.state == "current"
    assert current.reason == ""
    assert current.detail == ""

    # stale — the PDF was rebuilt after the human reviewed it
    stale_folder = tmp_path / "stale"
    stale_pdf = _write_pdf(stale_folder)
    _write_marker(stale_folder, _marker_body(stale_pdf))
    stale_pdf.write_bytes(OTHER_PDF_BYTES)
    stale = final_review_marker.final_review_state(stale_folder, stale_pdf)
    assert stale.state == "stale"
    assert stale.reason == "final_review_marker_stale"
    assert "pdf_sha256" in stale.detail
    assert stale.detail.isascii()


def test_pdf_missing_after_review_is_stale_not_malformed(tmp_path: Path) -> None:
    """Reviewed bytes that disappeared are a stale review, not a broken marker."""
    folder = tmp_path / "pdf-gone"
    pdf = _write_pdf(folder)
    _write_marker(folder, _marker_body(pdf))
    pdf.unlink()

    state = final_review_marker.final_review_state(folder, pdf)

    assert state.state == "stale"
    assert state.reason == "final_review_marker_stale"
    assert state.detail.isascii()


def test_pdf_hash_override_produces_stale(tmp_path: Path) -> None:
    """TRIANGULATE: a recorded hash that never matched the bytes is stale too."""
    folder = tmp_path / "override"
    pdf = _write_pdf(folder)
    _write_marker(folder, _marker_body(pdf, pdf_sha="0" * 64))

    state = final_review_marker.final_review_state(folder, pdf)

    assert state.state == "stale"
    assert state.reason == "final_review_marker_stale"


def test_malformed_shapes_name_the_offender(tmp_path: Path) -> None:
    """Every invalid marker is malformed with a bounded, ASCII detail."""
    pdf = _write_pdf(tmp_path)
    good_sha = hashlib.sha256(PDF_BYTES).hexdigest()
    reviewed_at = "2026-09-10T16:30:00Z"

    def case(name: str) -> Path:
        folder = tmp_path / name
        folder.mkdir()
        return folder

    bad_yaml = case("bad-yaml")
    _write_marker(bad_yaml, "pdf_sha256: [unclosed\nreviewed_at: x\n")

    missing_sha = case("missing-sha")
    _write_marker(missing_sha, f"reviewed_at: {reviewed_at}\nreviewed_by: Alejandro\n")

    missing_at = case("missing-at")
    _write_marker(missing_at, f"pdf_sha256: {good_sha}\nreviewed_by: Alejandro\n")

    missing_by = case("missing-by")
    _write_marker(missing_by, f"pdf_sha256: {good_sha}\nreviewed_at: {reviewed_at}\n")

    blank_by = case("blank-by")
    _write_marker(
        blank_by,
        f"pdf_sha256: {good_sha}\nreviewed_at: {reviewed_at}\nreviewed_by: \"   \"\n",
    )

    for folder in (bad_yaml, missing_sha, missing_at, missing_by, blank_by):
        state = final_review_marker.final_review_state(folder, pdf)
        assert state.state == "malformed", f"{folder.name}: {state}"
        assert state.reason == "final_review_marker_malformed", folder.name
        assert state.detail.isascii(), folder.name

    bad_yaml_state = final_review_marker.final_review_state(bad_yaml, pdf)
    assert "final-review.yml" in bad_yaml_state.detail
    missing_sha_state = final_review_marker.final_review_state(missing_sha, pdf)
    assert "pdf_sha256" in missing_sha_state.detail


def test_extra_keys_are_ignored(tmp_path: Path) -> None:
    """Extra recorded data never invalidates a marker whose bound hash matches."""
    folder = tmp_path / "extra"
    pdf = _write_pdf(folder)
    _write_marker(folder, _marker_body(pdf) + "notes: looked good\n")

    state = final_review_marker.final_review_state(folder, pdf)

    assert state.state == "current"


def test_state_is_read_only_and_never_raises(tmp_path: Path) -> None:
    """A bad marker is data, not a crash, and nothing on disk is created."""
    folder = tmp_path / "read-only"
    pdf = _write_pdf(folder)
    _write_marker(folder, "pdf_sha256: [unclosed\n")
    before = _snapshot(folder)

    for _ in range(2):
        state = final_review_marker.final_review_state(folder, pdf)
        assert state.state == "malformed"
        assert _snapshot(folder) == before

    missing = tmp_path / "missing"
    missing.mkdir()
    assert final_review_marker.final_review_state(missing, pdf).state == "absent"
    assert sorted(path.name for path in missing.iterdir()) == []
