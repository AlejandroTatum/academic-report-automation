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

# `evidence_contract` imports `ValidationResult` from this module at its own
# module scope, so importing it back here at module scope would cycle.
# `validate_ieee` below imports it lazily instead.


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


def malformed_bib_entries(bib_text: str) -> list[str]:
    """BibTeX keys whose entry is missing ``author`` or ``title`` -- the
    minimum an IEEE-rendered bibliography needs (#11 R16)."""
    malformed: list[str] = []
    for match in re.finditer(
        r"@\w+\s*\{\s*([^,\s]+)\s*,(?P<body>.*?)(?=\n@\w+\s*\{|\Z)", bib_text, re.S
    ):
        key = match.group(1)
        body = match.group("body")
        if not re.search(r"\btitle\s*=", body, re.I) or not re.search(r"\bauthor\s*=", body, re.I):
            malformed.append(key)
    return malformed


def claim_support_and_reciprocity(
    claims: list[dict],
    bib_text: str,
    source_text: str,
    justified_unused: set[str] | None = None,
) -> ValidationResult:
    """#11 R15/R16: claim support and citation/bibliography reciprocity.

    Every drafted claim retains an in-text citation that resolves to one
    BibTeX entry (missing ``citation_key``, a key absent from the body/tex,
    or a key absent from BibTeX are each a named failure); every citation
    used in the body resolves to a BibTeX entry; every BibTeX entry is
    either cited or explicitly justified (``justified_unused``); a
    duplicate ``citation_key`` across claims is rejected; a malformed
    BibTeX entry (missing author/title) is rejected.

    A claim entry that is not itself a mapping is a named error, never a
    crash -- ``evidence_contract.validate_evidence_package`` applies the
    same guard to this identical ``claims`` list.

    A justified common-knowledge claim (``use_type == "common_knowledge"``
    with a non-empty ``justification``) legitimately carries no
    ``citation_key`` at all -- ``evidence_contract.validate_claim`` already
    exempts it from every source/locator/identifier requirement for the
    same reason (spec: "Common knowledge MAY omit a source only with
    justification"). Treating its absent citation as "unsupported" here
    would contradict that contract, so it is skipped instead.

    A ``citation_key`` two DIFFERENT claims declare identically is still
    rejected (spec scenario: "duplicate mapping"). This is not about the
    same reference being cited by multiple claims in the rendered document
    -- ordinary IEEE writing does that constantly, and body-level citation
    reuse is untouched. It is about the evidence MATRIX: each row is
    supposed to be its own distinct, individually traceable grounding, so
    two claims sharing one ``citation_key`` signal an under-differentiated
    or duplicated matrix entry rather than two independently verified
    claims -- a research judgment call this validator flags for a human,
    not a crash-worthy defect.
    """
    result = ValidationResult()
    justified_unused = justified_unused or set()
    keys = bib_keys(bib_text)
    cited = cited_keys(source_text)

    seen_citation_keys: dict[str, str] = {}
    for claim in claims:
        if not isinstance(claim, dict):
            result.errors.append("cada claim debe ser un mapeo")
            continue
        claim_id = str(claim.get("claim_id") or "<sin id>")
        use_type = str(claim.get("use_type") or "").strip().lower()
        justified_common_knowledge = use_type == "common_knowledge" and str(
            claim.get("justification") or ""
        ).strip()
        citation_key = str(claim.get("citation_key") or "").strip()
        if not citation_key:
            if justified_common_knowledge:
                continue
            result.errors.append(f"Claim {claim_id}: sin citation_key (unsupported)")
            continue
        if citation_key in seen_citation_keys:
            result.errors.append(
                f"citation_key duplicado entre claims: '{citation_key}' "
                f"({seen_citation_keys[citation_key]} y {claim_id})"
            )
        seen_citation_keys[citation_key] = claim_id
        if citation_key not in cited:
            result.errors.append(
                f"Claim {claim_id}: citation_key '{citation_key}' no aparece citado en el cuerpo"
            )
        if citation_key not in keys:
            result.errors.append(
                f"Claim {claim_id}: citation_key '{citation_key}' no resuelve a una entrada BibTeX"
            )

    missing = sorted(cited - keys)
    if missing:
        result.errors.append("Citas sin entrada BibTeX: " + ", ".join(missing))

    unused = sorted(keys - cited - justified_unused)
    if unused:
        result.errors.append(
            "Entradas de bibliografía no citadas y sin justificación: " + ", ".join(unused)
        )

    malformed = malformed_bib_entries(bib_text)
    if malformed:
        result.errors.append(
            "Entradas BibTeX mal formadas (falta author o title): " + ", ".join(malformed)
        )

    return result


def validate_ieee(config: ReportConfig) -> ValidationResult:
    result = ValidationResult()
    body_text = read_text(config.body_path)
    tex_text = read_text(config.tex_path)
    bib_text = read_text(config.bib_path)
    rendered = pdf_text(config.pdf_path)
    source_text = "\n".join([body_text, tex_text])

    if config.academic_value("citations", "require_bibliography_when_sources_used", default=True) and not config.bib_path and ("[@" in body_text or "\\cite" in tex_text):
        result.errors.append("Hay citas en el cuerpo, pero no existe sources.bib/bibliography configurada")

    # #11 R15/R16: once a report has written research/evidence.yml, claim
    # support and citation/bibliography reciprocity block the build exactly
    # like any other IEEE failure. Lazy import: see the module-cycle note
    # near the top of this file. Presence-gated like every other new gate
    # in this feature -- a report without evidence.yml is untouched.
    from evidence_contract import evidence_gate_engaged, load_evidence_package

    if evidence_gate_engaged(config.folder):
        package = load_evidence_package(config.folder) or {}
        claims = package.get("claims") if isinstance(package, dict) else None
        claims = claims if isinstance(claims, list) else []
        raw_justifications = config.raw.get("bibliography_justifications")
        justified_unused = set(raw_justifications) if isinstance(raw_justifications, list) else set()
        reciprocity = claim_support_and_reciprocity(claims, bib_text, source_text, justified_unused)
        result.errors.extend(reciprocity.errors)

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
