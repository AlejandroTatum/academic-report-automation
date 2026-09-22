#!/usr/bin/env python3
"""Deliver a validated report PDF into the user's versioned Documents library.

The deliver-phase entrypoint (#22): generation (``build_report_auto.py``) no
longer publishes, so delivery is explicit. This module is a thin gate-checker on
top of the existing guarded publisher (``publish_validated_pdf``), not a second
publication system. It adds exactly one check the publisher does not own -- the
validation receipt ``validation.yml`` (schema ``academic.doc-validation/v1``)
must record ``result: pass`` for the exact bytes of the final PDF -- and then
delegates to the publisher, which enforces the current human approval marker and
performs the atomic, versioned, hash-verified copy.

No new states, gates or approvals are introduced: a refusal is a non-zero exit
with the named missing evidence, and a rerun after fixing it is the only exit.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from approval_marker import sha256_file
from publish_pdf import PublicationError, publish_validated_pdf
from report_config import load_report_config, read_yaml

VALIDATION_RECEIPT = "validation.yml"

# The full gate vocabulary the validate phase can grant, in the order
# ``skills/document-workflow/references/validate.md`` names them. The
# delivery message below reports exactly which of these the receipt
# actually names, never a fixed phrase.
KNOWN_GATES = ("BUILD_PASS", "VALIDATION_PASS", "VISUAL_PASS", "HUMAN_REVIEW", "READY_TO_SUBMIT")


def _refuse(reason: str) -> int:
    """Print the refusal with its named missing evidence and fail the run."""
    print(f"DELIVERY REFUSED: {reason}", file=sys.stderr)
    print("No se publicó nada. Resolvé lo indicado y volvé a ejecutar deliver_report.py.", file=sys.stderr)
    return 1


def deliver(folder: Path, documents_root: Path | None = None) -> int:
    """Gate and publish the final PDF of ``folder``; return 0 or 1."""
    try:
        config = load_report_config(folder)
    except SystemExit as exc:
        return _refuse(f"report.yml inválido: {exc}")

    pdf = config.pdf_path
    if not pdf.is_file():
        return _refuse(f"falta el PDF final: {pdf}. Ejecutá primero la fase generate.")

    receipt_path = folder / VALIDATION_RECEIPT
    if not receipt_path.is_file():
        return _refuse(
            f"falta {VALIDATION_RECEIPT} en {folder}. Ejecutá primero la fase validate."
        )
    try:
        receipt = read_yaml(receipt_path)
    except Exception:
        return _refuse(f"{VALIDATION_RECEIPT} no es YAML válido en {folder}.")

    result = str(receipt.get("result") or "").strip().lower()
    if result != "pass":
        return _refuse(
            f"{VALIDATION_RECEIPT} no registra result: pass (registró: {result or 'nada'})."
        )

    pdf_hash = sha256_file(pdf)
    recorded = str(receipt.get("artifact_sha256") or "").strip().lower()
    if recorded != pdf_hash:
        return _refuse(
            f"{VALIDATION_RECEIPT} artifact_sha256 no coincide con los bytes actuales de "
            f"{pdf.name}; la evidencia está obsoleta. Volvé a validar."
        )

    try:
        category = config.publication_category
        slug = config.document_slug
    except (KeyError, ValueError):
        return _refuse("identidad de publicación (categoría/slug) no disponible en report.yml.")

    try:
        publication = publish_validated_pdf(
            pdf,
            category,
            slug,
            documents_root=documents_root,
            work_folder=folder,
            expected_sha256=pdf_hash,
        )
    except PublicationError as exc:
        return _refuse(str(exc))

    action = "ENTREGADO" if publication.created else "REUTILIZADO"
    granted = [gate for gate in KNOWN_GATES if gate in (receipt.get("gates") or [])]
    missing = [gate for gate in KNOWN_GATES if gate not in granted]
    status_note = f"gates otorgados: {', '.join(granted) if granted else 'ninguno'}"
    if missing:
        status_note += f"; sin {', '.join(missing)}"
    print(
        f"PDF {action}: {publication.path} (SHA-256: {publication.sha256}); "
        f"copia técnicamente validada y aprobada; {status_note}."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Publica el PDF validado y aprobado en ~/Documents (fase deliver)."
    )
    parser.add_argument("folder", type=Path, help="Carpeta del reporte con report.yml")
    parser.add_argument(
        "--documents-root",
        type=Path,
        default=None,
        help="Raíz alternativa de Documents (solo para pruebas; por defecto ~/Documents).",
    )
    args = parser.parse_args(argv)
    return deliver(args.folder, args.documents_root)


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
