"""Shared validation for report visual manifests.

The visual builder and report validator must enforce the same manifest contract.
This module owns the field rules, identity checks, section alias handling, asset
existence checks, and raw-byte SHA-256 integrity checks.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


REQUIRED_FIELDS = (
    "file",
    "title",
    "caption",
    "source",
    "renderer",
    "section",
    "request_id",
    "result_id",
    "content_sha256",
    "license",
    "license_status",
    "alt_text",
)
LICENSE_STATUSES = frozenset(
    {"original", "licensed", "public_domain", "permission_granted"}
)
ASSET_SUFFIXES = frozenset({".svg", ".png", ".pdf"})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class VisualMetadataValidation:
    """Validation findings shared by both visual/report entry points."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _asset_path(folder: Path, value: Any) -> Path | None:
    filename = _text(value)
    if not filename:
        return None
    path = Path(filename)
    return path if path.is_absolute() else folder / path


def _manifest_figures(data: Any) -> list[Any] | None:
    if isinstance(data, dict):
        return data.get("figures")
    if isinstance(data, list):
        return data
    return None


def validate_visual_manifest(
    folder: Path,
    manifest_path: Path | None = None,
) -> VisualMetadataValidation:
    """Validate one ``figures.yml`` and the assets it addresses.

    ``content_sha256`` is always interpreted as SHA-256 over the asset's raw
    bytes. If the declared path exists, a mismatch is an error; it is never
    downgraded to a warning or silently repaired.
    """
    folder = Path(folder)
    manifest = manifest_path or folder / "figures.yml"
    outcome = VisualMetadataValidation()
    if not manifest.exists():
        outcome.errors.append(f"falta metadata: {manifest}")
        return outcome

    try:
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        outcome.errors.append(f"figures.yml inválido: {exc}")
        return outcome

    figures = _manifest_figures(data or {})
    if not isinstance(figures, list) or not figures:
        outcome.errors.append("figures.yml no contiene lista de figuras")
        return outcome

    request_ids: dict[str, int] = {}
    result_ids: dict[str, int] = {}
    listed_assets: set[Path] = set()

    for index, figure in enumerate(figures, start=1):
        prefix = f"Figura {index}"
        if not isinstance(figure, dict):
            outcome.errors.append(f"{prefix} inválida en figures.yml")
            continue

        for key in REQUIRED_FIELDS:
            if key == "section":
                continue
            if not _text(figure.get(key)):
                outcome.errors.append(f"{prefix} sin {key}")

        section = _text(figure.get("section"))
        intended_section = _text(figure.get("intended_section"))
        if not section and not intended_section:
            outcome.errors.append(f"{prefix} sin section ni intended_section")
        elif section and intended_section and section != intended_section:
            outcome.errors.append(
                f"{prefix} conflict entre section e intended_section"
            )

        for key, seen in (("request_id", request_ids), ("result_id", result_ids)):
            value = _text(figure.get(key))
            if not value:
                continue
            if value in seen:
                outcome.errors.append(
                    f"{prefix} {key} duplicado (también en Figura {seen[value]})"
                )
            else:
                seen[value] = index

        license_status = _text(figure.get("license_status"))
        if license_status and license_status not in LICENSE_STATUSES:
            allowed = ", ".join(sorted(LICENSE_STATUSES))
            outcome.errors.append(
                f"{prefix} license_status inválido: {license_status!r}; "
                f"valores permitidos: {allowed}"
            )

        declared_hash = _text(figure.get("content_sha256"))
        if declared_hash and not SHA256_RE.fullmatch(declared_hash):
            outcome.errors.append(
                f"{prefix} content_sha256 malformado; debe ser SHA-256 hexadecimal en minúsculas"
            )

        asset = _asset_path(folder, figure.get("file"))
        if asset is None:
            continue
        resolved_asset = asset.resolve()
        listed_assets.add(resolved_asset)
        if not asset.is_file():
            outcome.errors.append(f"{prefix} no existe: {asset}")
            continue

        if declared_hash and SHA256_RE.fullmatch(declared_hash):
            try:
                raw_bytes = asset.read_bytes()
            except OSError as exc:
                outcome.errors.append(f"{prefix} no se puede leer: {asset} ({exc})")
                continue
            actual_hash = hashlib.sha256(raw_bytes).hexdigest()
            if declared_hash != actual_hash:
                outcome.errors.append(
                    f"{prefix} content_sha256 no coincide con los bytes de {asset}"
                )

    for asset in sorted(folder.rglob("*")):
        if asset.is_file() and asset.suffix.lower() in ASSET_SUFFIXES:
            if asset.resolve() not in listed_assets:
                outcome.errors.append(f"Asset no listado en figures.yml: {asset}")

    return outcome
