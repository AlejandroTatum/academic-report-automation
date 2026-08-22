"""Tests for where compile_latex() puts the finished PDF.

The final copy used to assume the build output and the configured ``pdf:``
destination were always distinct files. They are not: once reports were told to
keep final artifacts out of ``reports/<work>/outputs/``, pointing ``pdf:`` at
the build output itself became the obvious thing to write — and
``shutil.copy2`` raises ``SameFileError`` for a self-copy, so the build died
*after* successfully producing the PDF.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import types
from pathlib import Path

import publish_pdf

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import build_latex_report  # noqa: E402


def _config(tmp_path: Path, pdf_path: Path | None = None) -> types.SimpleNamespace:
    folder = tmp_path / "report"
    build_dir = folder / "build"
    build_dir.mkdir(parents=True)
    body_path = folder / "body.md"
    body_path.write_text("# Titulo\n\nTexto.\n", encoding="utf-8")
    (build_dir / "main.tex").write_text("% tex", encoding="utf-8")
    return types.SimpleNamespace(
        folder=folder,
        body_path=body_path,
        tex_path=build_dir / "main.tex",
        pdf_path=pdf_path if pdf_path is not None else folder / "entrega" / "informe.pdf",
        bib_path=None,
        publish_global=False,
        metadata={},
    )


def _compiler_that_writes_the_pdf(build_dir: Path):
    def fake_run(*args, **kwargs):
        (build_dir / "main.pdf").write_bytes(b"%PDF-1.5\ncontenido\n")
        return subprocess.CompletedProcess(args=list(args[0]), returncode=0, stdout="")

    return fake_run


@pytest.fixture
def docker_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        build_latex_report.shutil,
        "which",
        lambda name: "/usr/bin/docker" if name == "docker" else None,
    )


def test_pdf_pointing_at_the_build_output_is_not_a_self_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, docker_engine: None
) -> None:
    """``pdf: build/main.pdf`` must publish, not crash on SameFileError."""
    config = _config(tmp_path)
    build_dir = config.tex_path.parent
    config.pdf_path = build_dir / "main.pdf"
    monkeypatch.setattr(build_latex_report, "run", _compiler_that_writes_the_pdf(build_dir))

    build_latex_report.compile_latex(config)

    assert config.pdf_path.exists()
    assert config.pdf_path.read_bytes().startswith(b"%PDF")


def test_pdf_reached_through_a_symlinked_build_dir_is_still_the_same_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, docker_engine: None
) -> None:
    """Sameness is about the file on disk, not about matching path strings."""
    config = _config(tmp_path)
    build_dir = config.tex_path.parent
    monkeypatch.setattr(build_latex_report, "run", _compiler_that_writes_the_pdf(build_dir))

    link = tmp_path / "atajo"
    link.symlink_to(build_dir, target_is_directory=True)
    config.pdf_path = link / "main.pdf"

    build_latex_report.compile_latex(config)

    assert (build_dir / "main.pdf").read_bytes().startswith(b"%PDF")


def test_distinct_destination_still_receives_a_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, docker_engine: None
) -> None:
    """The ordinary case must keep working: build output copied to pdf_path."""
    config = _config(tmp_path)
    build_dir = config.tex_path.parent
    monkeypatch.setattr(build_latex_report, "run", _compiler_that_writes_the_pdf(build_dir))

    build_latex_report.compile_latex(config)

    assert config.pdf_path.exists()
    assert config.pdf_path != build_dir / "main.pdf"
    assert config.pdf_path.read_bytes() == (build_dir / "main.pdf").read_bytes()


def _validated_pdf(tmp_path: Path, content: bytes = b"%PDF-1.7\nvalidated content\n") -> Path:
    source = tmp_path / "work" / "validated.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(content)
    return source


def test_first_publication_is_v001_pdf_only_and_hash_verified(tmp_path: Path) -> None:
    source = _validated_pdf(tmp_path)
    documents = tmp_path / "Documents"

    published = publish_pdf.publish_validated_pdf(source, "Tecnicos", "informe", documents)

    assert published.path == documents / "Tecnicos" / "informe" / "informe-v001.pdf"
    assert published.created is True
    assert published.path.exists()
    assert published.sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert list(published.path.parent.iterdir()) == [published.path]


def test_unchanged_hash_reuses_existing_version(tmp_path: Path) -> None:
    source = _validated_pdf(tmp_path)
    documents = tmp_path / "Documents"
    first = publish_pdf.publish_validated_pdf(source, "Tecnicos", "informe", documents)

    reused = publish_pdf.publish_validated_pdf(source, "Tecnicos", "informe", documents)

    assert reused.path == first.path
    assert reused.created is False
    assert list(first.path.parent.glob("*.pdf")) == [first.path]


def test_changed_hash_publishes_next_monotonic_version(tmp_path: Path) -> None:
    source = _validated_pdf(tmp_path, b"%PDF-1.7\nfirst\n")
    documents = tmp_path / "Documents"
    publish_pdf.publish_validated_pdf(source, "Academicos", "informe", documents)
    source.write_bytes(b"%PDF-1.7\nsecond\n")

    published = publish_pdf.publish_validated_pdf(source, "Academicos", "informe", documents)

    assert published.path.name == "informe-v002.pdf"
    assert published.path.read_bytes() == source.read_bytes()
    assert {path.name for path in published.path.parent.iterdir()} == {"informe-v001.pdf", "informe-v002.pdf"}


def test_concurrent_version_claim_retries_without_overwriting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _validated_pdf(tmp_path, b"%PDF-1.7\nsecond publisher\n")
    documents = tmp_path / "Documents"
    folder = documents / "Tecnicos" / "informe"
    folder.mkdir(parents=True)
    (folder / "informe-v001.pdf").write_bytes(b"%PDF-1.7\nfirst publisher\n")
    real_link = publish_pdf.os.link
    calls = 0

    def collision_once(source_path, destination_path):
        nonlocal calls
        calls += 1
        if calls == 1:
            Path(destination_path).write_bytes(b"%PDF-1.7\nconcurrent publisher\n")
            raise FileExistsError
        return real_link(source_path, destination_path)

    monkeypatch.setattr(publish_pdf.os, "link", collision_once)

    published = publish_pdf.publish_validated_pdf(source, "Tecnicos", "informe", documents)

    assert published.path.name == "informe-v003.pdf"
    assert (folder / "informe-v002.pdf").read_bytes() == b"%PDF-1.7\nconcurrent publisher\n"


def test_publication_rejects_non_pdf_source_and_non_pdf_output_folder_contents(tmp_path: Path) -> None:
    source = tmp_path / "validated.docx"
    source.write_bytes(b"not a pdf")
    documents = tmp_path / "Documents"

    with pytest.raises(publish_pdf.PublicationError):
        publish_pdf.publish_validated_pdf(source, "Tecnicos", "informe", documents)

    source = _validated_pdf(tmp_path)
    destination = documents / "Tecnicos" / "informe"
    destination.mkdir(parents=True)
    (destination / "audit.txt").write_text("not a PDF", encoding="utf-8")
    with pytest.raises(publish_pdf.PublicationError):
        publish_pdf.publish_validated_pdf(source, "Tecnicos", "informe", documents)


def test_global_publication_still_runs_when_the_pdf_is_the_build_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, docker_engine: None
) -> None:
    """Skipping the copy must not skip publishing the visible per-subject copy."""
    config = _config(tmp_path)
    build_dir = config.tex_path.parent
    config.pdf_path = build_dir / "main.pdf"
    config.publish_global = True
    config.metadata = {"subject": "Sistemas Operativos"}
    monkeypatch.setattr(build_latex_report, "run", _compiler_that_writes_the_pdf(build_dir))

    published: list[Path] = []
    monkeypatch.setattr(
        build_latex_report,
        "publish_global_output",
        lambda pdf, metadata: published.append(Path(pdf)) or Path(pdf),
    )

    build_latex_report.compile_latex(config)

    assert published == [config.pdf_path]
