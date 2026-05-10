#!/usr/bin/env python3
"""Common, backend-aware validation layer for academic reports."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from report_config import ReportConfig, load_report_config
from output_router import FINAL_EXTENSIONS, GLOBAL_OUTPUTS, infer_subject_for_path
from validate_ieee_refs import ValidationResult, validate_ieee

A4_WIDTH = 595.28
A4_HEIGHT = 841.89


@dataclass
class ReportValidation:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)

    def add(self, name: str, result: ValidationResult) -> None:
        self.checks.append(name)
        self.errors.extend(result.errors)
        self.warnings.extend(result.warnings)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def pdf_text_pages(pdf: Path) -> list[str]:
    if not pdf.exists():
        return []
    result = run(["pdftotext", str(pdf), "-"])
    if result.returncode != 0:
        return []
    return result.stdout.split("\f")


def pdfinfo(pdf: Path) -> dict[str, str]:
    if not pdf.exists():
        return {}
    result = run(["pdfinfo", str(pdf)])
    data: dict[str, str] = {}
    for line in result.stdout.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            data[key.strip()] = value.strip()
    return data


def common_validation(config: ReportConfig) -> ValidationResult:
    result = ValidationResult()
    required_meta = ["title", "subject", "teacher", "student", "date"]
    meta = config.metadata
    missing = [key for key in required_meta if not str(meta.get(key) or "").strip()]
    if missing:
        result.errors.append("Metadata incompleta en report.yml: " + ", ".join(missing))

    if not config.body_path.exists() and config.backend in {"latex", "html"}:
        result.errors.append(f"No existe body.md: {config.body_path}")

    if config.output_format == "pdf" and not config.pdf_path.exists():
        result.errors.append(f"No existe PDF final esperado: {config.pdf_path}")

    outputs = config.folder / "outputs"
    if config.output_format == "pdf" and config.pdf_path.exists() and outputs not in config.pdf_path.parents:
        result.warnings.append("El PDF final no está dentro de outputs/")

    if outputs.exists():
        dirty = [p.name for p in outputs.iterdir() if p.is_file() and p.suffix.lower() not in {".pdf", ".docx"}]
        if dirty:
            result.warnings.append("outputs/ contiene intermedios; deberían ir a backups/ o build/: " + ", ".join(dirty[:8]))

    if config.publish_global and config.output_format == "pdf" and config.pdf_path.exists():
        subject_slug = infer_subject_for_path(config.pdf_path, config.metadata)
        if subject_slug:
            expected_global = GLOBAL_OUTPUTS / subject_slug / config.pdf_path.name
            if not expected_global.exists():
                result.warnings.append(f"No existe copia global filtrada por materia: {expected_global.relative_to(GLOBAL_OUTPUTS.parent)}")
        else:
            result.warnings.append("No pude inferir la materia para publicar en outputs/<materia>/")

    if GLOBAL_OUTPUTS.exists():
        loose_items = [p.name for p in GLOBAL_OUTPUTS.iterdir() if p.is_file() and p.name != ".gitkeep"]
        loose_finals = [name for name in loose_items if Path(name).suffix.lower() in FINAL_EXTENSIONS]
        loose_intermediates = [name for name in loose_items if Path(name).suffix.lower() not in FINAL_EXTENSIONS]
        non_delivery = [
            str(p.relative_to(GLOBAL_OUTPUTS))
            for p in GLOBAL_OUTPUTS.rglob("*")
            if p.is_file() and p.name != ".gitkeep" and p.suffix.lower() not in FINAL_EXTENSIONS
        ]
        if loose_finals:
            result.warnings.append("outputs/ global tiene finales sueltos; deben ir en outputs/<materia>/: " + ", ".join(loose_finals[:8]))
        if loose_intermediates:
            result.warnings.append("outputs/ global tiene intermedios sueltos; deben ir a backups/: " + ", ".join(loose_intermediates[:8]))
        if non_delivery:
            result.warnings.append("outputs/ global contiene archivos que no son PDF/DOCX; deben ir a backups/: " + ", ".join(non_delivery[:8]))

    text = "\n".join(pdf_text_pages(config.pdf_path)) if config.pdf_path.exists() else ""
    banned = config.academic_value("conclusions", "banned_openers", default=["Se concluye", "En conclusión", "En conclusion"])
    found = [item for item in banned if item.lower() in text.lower()]
    if found:
        result.errors.append("Conclusión inicia/usa fórmulas prohibidas: " + ", ".join(found))

    if config.pdf_path.exists():
        pages = pdf_text_pages(config.pdf_path)
        blank_pages = [str(i + 1) for i, page in enumerate(pages) if i < len(pages) - 1 and len(page.strip()) < 20]
        if blank_pages:
            result.errors.append("Posibles páginas vacías accidentales: " + ", ".join(blank_pages))

    return result


def pdf_layout_validation(config: ReportConfig) -> ValidationResult:
    result = ValidationResult()
    if not config.pdf_path.exists():
        result.errors.append(f"No existe PDF para validar layout: {config.pdf_path}")
        return result

    info = pdfinfo(config.pdf_path)
    page_count = int(info.get("Pages", "0") or 0)
    if page_count < 1:
        result.errors.append("PDF sin páginas o pdfinfo no pudo leer conteo")

    page_size = info.get("Page size", "")
    numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", page_size)[:2]]
    if len(numbers) == 2:
        w, h = numbers
        is_a4 = abs(w - A4_WIDTH) < 3 and abs(h - A4_HEIGHT) < 3
        is_a4_landscape = abs(w - A4_HEIGHT) < 3 and abs(h - A4_WIDTH) < 3
        if not (is_a4 or (config.backend == "visual" and is_a4_landscape)):
            result.warnings.append(f"Tamaño de página no parece A4 estándar: {page_size}")

    try:
        images = run(["pdfimages", "-list", str(config.pdf_path)]).stdout.splitlines()
        image_rows = [line for line in images if re.match(r"^\s*\d+\s+\d+\s+image", line)]
        if config.academic_value("cover", "logo_required", default=True) and not image_rows:
            result.errors.append("PDF no parece tener imágenes embebidas; revisar university logo")
    except FileNotFoundError:
        result.warnings.append("pdfimages no disponible; no se validó logo/imágenes")

    pages = pdf_text_pages(config.pdf_path)
    if len(pages) >= 2:
        first = pages[0].lower()
        second = pages[1].lower()
        body_markers = ["introducción", "introduccion", "tema", "antecedentes", "descripción", "descripcion", "desarrollo"]
        marker_pattern = r"\b(" + "|".join(re.escape(marker) for marker in body_markers) + r")\b"
        if re.search(marker_pattern, first) and not config.raw.get("allow_body_on_cover", False):
            result.errors.append("La portada parece mezclada con el cuerpo; el cuerpo debe iniciar en página 2")
        if not re.search(marker_pattern, second) and config.backend == "latex":
            result.warnings.append("No detecté inicio claro del cuerpo en página 2; revisar portada/cuerpo")

        for idx, page in enumerate(pages[:-1], start=1):
            lines = [line.strip() for line in page.splitlines() if line.strip()]
            if not lines:
                continue
            last = lines[-1]
            looks_heading = bool(re.match(r"^(\d+(?:\.\d+)*)?\s*[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ\s]{3,70}$", last)) and not last.endswith((".", ":", ";", ","))
            if looks_heading:
                result.errors.append(f"Posible título huérfano al final de página {idx}: {last}")

    return result


def latex_log_validation(config: ReportConfig) -> ValidationResult:
    result = ValidationResult()
    log = config.log_path.read_text(encoding="utf-8", errors="ignore") if config.log_path.exists() else ""
    tex = config.tex_path.read_text(encoding="utf-8", errors="ignore") if config.tex_path.exists() else ""
    if not config.tex_path.exists():
        result.errors.append(f"No existe main.tex: {config.tex_path}")
        return result

    required_snippets = ["hyperref", "Needspace", "onehalfspacing", "parindent"]
    missing = [snippet for snippet in required_snippets if snippet not in tex]
    if missing:
        result.errors.append("LaTeX template sin reglas obligatorias: " + ", ".join(missing))

    if log:
        fatal_patterns = [
            r"! LaTeX Error",
            r"Undefined control sequence",
            r"Citation `[^']+' undefined",
            r"Reference `[^']+' undefined",
            r"There were undefined (?:references|citations)",
            r"Package biblatex Warning: Please \(re\)run Biber",
        ]
        found = [pattern for pattern in fatal_patterns if re.search(pattern, log)]
        if found:
            result.errors.append("Log LaTeX contiene errores/referencias sin resolver")
        overfull = re.findall(r"Overfull \\hbox \(([^)]+) too wide\)", log)
        if overfull:
            result.warnings.append(f"Hay {len(overfull)} overfull hbox; revisar cortes de línea/tablas")
    else:
        result.warnings.append("No existe log LaTeX todavía; se validó solo el .tex")

    return result


def source_layout_validation(config: ReportConfig) -> ValidationResult:
    result = ValidationResult()
    body = config.body_path.read_text(encoding="utf-8", errors="ignore") if config.body_path.exists() else ""
    bad_bold_titles = [line for line in body.splitlines() if re.match(r"^\s*\*\*[^*]{4,}\*\*\s*$", line)]
    if bad_bold_titles:
        result.errors.append("Usar headings Markdown (#, ##) para títulos, no negrita manual: " + bad_bold_titles[0][:80])
    return result


def visual_validation(config: ReportConfig) -> ValidationResult:
    result = ValidationResult()
    figures_yml = config.folder / "figures" / "figures.yml"
    if not figures_yml.exists():
        figures_yml = config.folder / "figures.yml"
    if not figures_yml.exists():
        result.warnings.append("Trabajo visual sin figures.yml; no se pudo validar captions/fuentes de figuras")
        return result
    data = yaml.safe_load(figures_yml.read_text(encoding="utf-8")) or {}
    figures = data.get("figures") if isinstance(data, dict) else data
    if not isinstance(figures, list) or not figures:
        result.errors.append("figures.yml no contiene lista de figuras")
        return result
    for idx, fig in enumerate(figures, start=1):
        if not isinstance(fig, dict):
            result.errors.append(f"Figura {idx} inválida en figures.yml")
            continue
        for key in ("file", "caption", "source", "renderer"):
            if not fig.get(key):
                result.errors.append(f"Figura {idx} sin {key}")
        file_path = Path(fig.get("file", ""))
        if file_path and not file_path.is_absolute():
            file_path = config.folder / file_path
        if file_path and not file_path.exists():
            result.errors.append(f"Figura {idx} no existe: {file_path}")
        elif file_path and file_path.stat().st_size < 4_000:
            result.warnings.append(f"Figura {idx} parece demasiado pequeña: {file_path}")
    return result


def docx_validation(config: ReportConfig) -> ValidationResult:
    result = ValidationResult()
    if not config.docx_path.exists():
        result.errors.append(f"No existe DOCX final esperado: {config.docx_path}")
        return result
    if config.docx_path.stat().st_size < 10_000:
        result.warnings.append("DOCX demasiado pequeño; revisar que no esté vacío")
    return result


def write_quality_report(config: ReportConfig, validation: ReportValidation) -> None:
    path = config.quality_report_path
    path.parent.mkdir(parents=True, exist_ok=True)
    status = "APROBADO" if not validation.errors else "FALLÓ"
    lines = [
        f"# Quality report — {config.folder.name}",
        "",
        "## Resultado",
        status,
        "",
        "## Validaciones ejecutadas",
    ]
    lines.extend(f"- {check}" for check in validation.checks)
    if validation.errors:
        lines.extend(["", "## Errores", *[f"- {error}" for error in validation.errors]])
    if validation.warnings:
        lines.extend(["", "## Advertencias", *[f"- {warning}" for warning in validation.warnings]])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate(config: ReportConfig) -> ReportValidation:
    validators = config.validators
    validation = ReportValidation()
    if validators.get("common", True):
        validation.add("common", common_validation(config))
    if validators.get("pdf_layout", False):
        validation.add("pdf_layout", pdf_layout_validation(config))
    if validators.get("ieee", True):
        validation.add("ieee", validate_ieee(config))
    if validators.get("latex", False):
        validation.add("source_layout", source_layout_validation(config))
    if validators.get("latex_log", False):
        validation.add("latex_log", latex_log_validation(config))
    if validators.get("visual", False):
        validation.add("visual", visual_validation(config))
    if validators.get("docx", False):
        validation.add("docx", docx_validation(config))
    write_quality_report(config, validation)
    return validation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path, help="Carpeta del reporte con report.yml")
    args = parser.parse_args()
    config = load_report_config(args.folder)
    result = validate(config)
    if result.errors:
        raise SystemExit("VALIDATION FAILED:\n- " + "\n- ".join(result.errors) + f"\n\nReporte: {config.quality_report_path}")
    if result.warnings:
        print("VALIDATION PASSED WITH WARNINGS:\n- " + "\n- ".join(result.warnings))
    else:
        print("VALIDATION PASSED")
    print(f"Reporte: {config.quality_report_path}")


if __name__ == "__main__":
    main()
