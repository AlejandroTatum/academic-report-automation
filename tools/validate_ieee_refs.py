#!/usr/bin/env python3
"""IEEE bibliography and citation validators for rendered academic reports."""
from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path

from report_config import ReportConfig, load_report_config


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def extend(self, other: "ValidationResult") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


def read_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def pdf_text(pdf: Path) -> str:
    if not pdf.exists():
        return ""
    try:
        result = subprocess.run(["pdftotext", str(pdf), "-"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return result.stdout
    except FileNotFoundError:
        return ""


def pdf_has_links(pdf: Path) -> bool:
    if not pdf.exists():
        return False
    data = pdf.read_bytes()
    haystack = data
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        try:
            haystack += zlib.decompress(match.group(1))
        except Exception:
            continue
    if b"/Subtype/Link" in haystack or b"/Annots" in haystack:
        return True
    try:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pdf_links"
            proc = subprocess.run(
                ["pdftohtml", "-xml", "-i", str(pdf), str(out)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            xml = out.with_suffix(".xml")
            if proc.returncode == 0 and xml.exists():
                return "href=" in xml.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return False
    return False


def bib_keys(bib_text: str) -> set[str]:
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)", bib_text))


def cited_keys(source_text: str) -> set[str]:
    keys: set[str] = set()
    for match in re.finditer(r"\[@([A-Za-z0-9_:\-.,; ]+)\]", source_text):
        keys.update(key.strip() for key in re.split(r"[,;]", match.group(1)) if key.strip())
    for match in re.finditer(r"\\(?:cite|parencite|textcite|autocite)\*?(?:\[[^\]]*\])*\{([^}]+)\}", source_text):
        keys.update(key.strip() for key in match.group(1).split(",") if key.strip())
    return keys


def has_bib_doi(bib_text: str, key: str) -> bool:
    entry = re.search(r"@\w+\s*\{\s*" + re.escape(key) + r"\s*,(?P<body>.*?)(?=\n@\w+\s*\{|\Z)", bib_text, re.S)
    return bool(entry and re.search(r"\bdoi\s*=", entry.group("body"), re.I))


def validate_ieee(config: ReportConfig) -> ValidationResult:
    result = ValidationResult()
    body_text = read_text(config.body_path)
    tex_text = read_text(config.tex_path)
    bib_text = read_text(config.bib_path)
    rendered = pdf_text(config.pdf_path)
    source_text = "\n".join([body_text, tex_text])

    if config.academic_value("citations", "require_bibliography_when_sources_used", default=True) and not config.bib_path and ("[@" in body_text or "\\cite" in tex_text):
        result.errors.append("Hay citas en el cuerpo, pero no existe sources.bib/bibliography configurada")

    keys = bib_keys(bib_text)
    cited = cited_keys(source_text)
    if keys and cited:
        missing = sorted(cited - keys)
        if missing:
            result.errors.append("Citas sin entrada BibTeX: " + ", ".join(missing))
        unused = sorted(keys - cited)
        if unused:
            result.warnings.append("Entradas BibTeX no citadas: " + ", ".join(unused))

    if config.academic_value("citations", "require_bibliography_when_sources_used", default=True) and config.bib_path and config.pdf_path.exists():
        if not re.search(r"\b(Bibliograf[ií]a|Referencias|References)\b", rendered, re.I):
            result.errors.append("El PDF no muestra sección de Bibliografía/Referencias")
        if cited and not re.search(r"\[[0-9]+\]", rendered):
            result.errors.append("El PDF no muestra citas/referencias numéricas IEEE tipo [1]")

    banned_rendered = config.academic_value("citations", "banned_rendered_terms", default=["date of publication", "s. f.", "sin fecha"])
    lower_rendered = rendered.lower()
    found_banned = [item for item in banned_rendered if item in lower_rendered]
    if found_banned:
        result.errors.append("Texto no deseado en bibliografía IEEE renderizada: " + ", ".join(found_banned))

    if re.search(r"\bpp\.\s*\d{1,3}\s\d{3}\b", rendered):
        result.errors.append("Posible rango de páginas con separador de miles en IEEE; usar pp. 73005–73014, no pp. 73 005")

    if re.search(r"\bin\s+referenc(?:e|ia)\s+\[[0-9]+\]", rendered, re.I):
        result.errors.append("IEEE: evitar 'en referencia [n]'; escribir 'en [n]' o reformular")

    if re.search(r"(Fig\.|figura|ecuaci[oó]n|equation).*referenc(?:e|ia)\s+\[[0-9]+\]", rendered, re.I):
        result.errors.append("IEEE: para partes específicas usar [n, Fig. x], [n, eq. (x)], [n, Sec. x]")

    if keys and rendered:
        doi_keys = [key for key in cited if has_bib_doi(bib_text, key)]
        if doi_keys and "doi" not in lower_rendered:
            result.warnings.append("Hay DOI en BibTeX, pero el PDF no parece renderizar DOI; revisar estilo IEEE")

    if config.academic_value("citations", "clickable_citations", default=True) and config.backend == "latex":
        if "hyperref" not in tex_text:
            result.errors.append("LaTeX debe cargar hyperref para citas/referencias clickeables")
        elif config.pdf_path.exists() and not pdf_has_links(config.pdf_path):
            result.warnings.append("No pude confirmar anotaciones de enlace en el PDF; revisar que las citas sean clickeables")

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    config = load_report_config(args.folder)
    result = validate_ieee(config)
    if result.errors:
        raise SystemExit("IEEE validation failed:\n- " + "\n- ".join(result.errors))
    if result.warnings:
        print("IEEE validation warnings:\n- " + "\n- ".join(result.warnings))
    else:
        print("IEEE validation OK")


if __name__ == "__main__":
    main()
