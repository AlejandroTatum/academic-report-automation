"""Tests for ``tools/draft_docx.py``: DOCX draft export and import through pandoc."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

pytest.importorskip("pypandoc")

import draft_docx  # noqa: E402

BODY = "# Informe\n\nLa energia es $x^2$ en el modelo.\n\n## Seccion\n\nTexto de la seccion.\n"


def _folder(tmp_path: Path) -> Path:
    folder = tmp_path / "wf"
    folder.mkdir()
    (folder / "report.yml").write_text("type: essay\nmetadata:\n  title: Mi Informe\n", encoding="utf-8")
    (folder / "body.md").write_text(BODY, encoding="utf-8")
    return folder


def _export(folder: Path) -> Path:
    return draft_docx.export_draft(folder)


def test_export_creates_v01_then_v02_without_overwriting(tmp_path: Path) -> None:
    folder = _folder(tmp_path)
    first = _export(folder)
    first_bytes = first.read_bytes()
    second = _export(folder)

    assert first.parent == folder / "borrador"
    assert first.name == "mi-informe-borrador-v01.docx"
    assert second.name == "mi-informe-borrador-v02.docx"
    assert first.read_bytes() == first_bytes


def test_export_writes_native_equations(tmp_path: Path) -> None:
    docx = _export(_folder(tmp_path))
    with zipfile.ZipFile(docx) as archive:
        assert "m:oMath" in archive.read("word/document.xml").decode("utf-8")


def test_export_refuses_when_a_lock_file_exists(tmp_path: Path) -> None:
    folder = _folder(tmp_path)
    _export(folder)
    (folder / "borrador" / ".~lock.mi-informe-borrador-v01.docx#").write_text("x", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        _export(folder)
    assert exc.value.code == 2
    assert len(list((folder / "borrador").glob("*.docx"))) == 1


def test_import_shows_diff_and_does_not_write_without_apply(tmp_path: Path, capsys) -> None:
    folder = _folder(tmp_path)
    docx = _export(folder)

    assert draft_docx.main(["import", str(folder), str(docx)]) == 0
    out = capsys.readouterr().out
    assert "$x^{2}$" in out
    assert (folder / "body.md").read_text(encoding="utf-8") == BODY
    assert not (folder / "backups").exists()


def test_import_diff_shows_user_edit_and_apply_writes_with_backup(tmp_path: Path, capsys) -> None:
    import docx as python_docx

    folder = _folder(tmp_path)
    path = _export(folder)
    document = python_docx.Document(str(path))
    for paragraph in document.paragraphs:
        if paragraph.text == "Texto de la seccion.":
            paragraph.runs[0].text = "Texto parafraseado por el usuario."
    document.save(str(path))

    assert draft_docx.main(["import", str(folder), str(path)]) == 0
    out = capsys.readouterr().out
    assert "+Texto parafraseado por el usuario." in out
    assert "-Texto de la seccion." in out
    assert (folder / "body.md").read_text(encoding="utf-8") == BODY

    assert draft_docx.main(["import", str(folder), str(path), "--apply"]) == 0
    capsys.readouterr()
    new_body = (folder / "body.md").read_text(encoding="utf-8")
    assert "Texto parafraseado por el usuario." in new_body
    assert "$x^{2}$" in new_body  # pandoc spells the same math with braces
    assert new_body.startswith("# Informe")
    backups = list((folder / "backups").glob("body-*.md"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == BODY


def test_import_refuses_when_the_docx_is_locked(tmp_path: Path) -> None:
    folder = _folder(tmp_path)
    docx = _export(folder)
    (docx.parent / f".~lock.{docx.name}#").write_text("x", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        draft_docx.main(["import", str(folder), str(docx), "--apply"])
    assert exc.value.code == 2
    assert (folder / "body.md").read_text(encoding="utf-8") == BODY


def test_export_prints_a_file_url(tmp_path: Path, capsys) -> None:
    folder = _folder(tmp_path)
    assert draft_docx.main(["export", str(folder)]) == 0
    assert "file://" in capsys.readouterr().out
