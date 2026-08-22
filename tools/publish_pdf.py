#!/usr/bin/env python3
"""Publish validated PDFs into the user's versioned Documents library."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path


class PublicationError(RuntimeError):
    """A validated PDF could not be safely published."""


@dataclass(frozen=True)
class Publication:
    path: Path
    sha256: str
    created: bool


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_pdf_file(path: Path) -> None:
    if path.suffix.lower() != ".pdf" or not path.is_file():
        raise PublicationError(f"El PDF validado no existe o no es un PDF: {path}")


def _existing_versions(folder: Path, slug: str) -> list[tuple[int, Path]]:
    if not folder.exists():
        return []
    non_pdfs = [path for path in folder.iterdir() if not path.is_file() or path.suffix.lower() != ".pdf"]
    if non_pdfs:
        raise PublicationError(f"La carpeta de entrega solo puede contener PDFs: {folder}")
    pattern = re.compile(rf"^{re.escape(slug)}-v(\d{{3,}})\.pdf$")
    versions: list[tuple[int, Path]] = []
    for path in folder.iterdir():
        match = pattern.match(path.name)
        if match:
            versions.append((int(match.group(1)), path))
    return versions


def publish_validated_pdf(
    source: Path,
    category: str,
    slug: str,
    documents_root: Path | None = None,
    *,
    expected_sha256: str | None = None,
) -> Publication:
    """Atomically publish a validated PDF, reusing identical hashes by version.

    Publication is deliberately a technical-copy operation: callers invoke it only
    after configured validation has passed; it never grants visual or human review.
    """
    source = Path(source)
    _require_pdf_file(source)
    if not category or not slug:
        raise PublicationError("La categoría y el slug del documento son obligatorios")

    root = Path.home() / "Documents" if documents_root is None else Path(documents_root)
    folder = root / category / slug
    source_hash = sha256_file(source)
    if expected_sha256 is not None and source_hash != expected_sha256:
        raise PublicationError("El PDF cambió desde la validación técnica")
    folder.mkdir(parents=True, exist_ok=True)

    while True:
        existing = _existing_versions(folder, slug)
        for _, path in existing:
            if sha256_file(path) == source_hash:
                return Publication(path=path, sha256=source_hash, created=False)

        next_version = max((version for version, _ in existing), default=0) + 1
        destination = folder / f"{slug}-v{next_version:03d}.pdf"
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=f".{destination.name}.", suffix=".tmp", dir=folder, delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                with source.open("rb") as input_stream:
                    shutil.copyfileobj(input_stream, temporary)
                temporary.flush()
                os.fsync(temporary.fileno())
            # link(2) atomically claims the version and refuses to overwrite an
            # already claimed name. A concurrent publisher therefore retries with
            # a fresh version scan instead of replacing another artifact.
            os.link(temporary_path, destination)
            temporary_path.unlink()
        except FileExistsError:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            continue
        except OSError as exc:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise PublicationError(f"No se pudo publicar el PDF en {destination}: {exc}") from exc

        destination_hash = sha256_file(destination)
        if destination_hash != source_hash:
            raise PublicationError(f"SHA-256 no coincide después de publicar {destination}")
        return Publication(path=destination, sha256=source_hash, created=True)
