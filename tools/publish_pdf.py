#!/usr/bin/env python3
"""Publish validated PDFs into the user's versioned Documents library."""
from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from approval_marker import ApprovalState, approval_state, sha256_file


class PublicationError(RuntimeError):
    """A validated PDF could not be safely published."""


@dataclass(frozen=True)
class Publication:
    path: Path
    sha256: str
    created: bool


def _require_pdf_file(path: Path) -> None:
    if path.suffix.lower() != ".pdf" or not path.is_file():
        raise PublicationError(f"El PDF validado no existe o no es un PDF: {path}")


def _approval_refusal(state: ApprovalState, work_folder: Path) -> str:
    """Map an approval state onto the user-facing refusal message."""
    if state.state == "stale":
        return (
            "La aprobación está obsoleta: preview_sha256 y/o body_sha256 de "
            f"approval.yml no coinciden con preview.md y body.md en {work_folder}. "
            "Volvé a aprobar el preview y el cuerpo actuales; no se publica nada."
        )
    if state.state == "malformed":
        return (
            f"approval.yml es inválido en {work_folder}: {state.detail}. "
            "No se publica nada y el marcador nunca se repara automáticamente."
        )
    return (
        "Falta la aprobación humana: no existe approval.yml en "
        f"{work_folder}. Ejecutá la fase de aprobación después de revisar preview.md "
        "y body.md; no se publica nada. La validación técnica pasó; falta únicamente "
        "la aprobación humana."
    )


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
    work_folder: Path,
    expected_sha256: str | None = None,
) -> Publication:
    """Atomically publish a validated PDF, reusing identical hashes by version.

    Publication requires both configured technical validation AND a current human
    approval marker: ``work_folder/approval.yml`` must hash the exact bytes of
    both ``work_folder/preview.md`` and ``work_folder/body.md``. ``work_folder``
    is required keyword-only, so a caller cannot skip the guard by omission. The
    check runs before any hash, directory or temporary file, so a refused
    publication creates nothing.

    It remains a technical-copy operation: it never grants ``VISUAL_PASS``,
    ``HUMAN_REVIEW``, or ``READY_TO_SUBMIT``.
    """
    source = Path(source)
    work_folder = Path(work_folder)
    _require_pdf_file(source)
    if not category or not slug:
        raise PublicationError("La categoría y el slug del documento son obligatorios")

    state = approval_state(work_folder)
    if state.state != "current":
        raise PublicationError(_approval_refusal(state, work_folder))

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
