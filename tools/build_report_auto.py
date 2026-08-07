#!/usr/bin/env python3
"""Backend router for academic reports.

Chooses LaTeX/visual/DOCX routing based on report.yml. LaTeX and DOCX both have
a fully generic ``body.md`` builder; visual jobs are still validated with the
shared gates because their builders depend on the specific teacher/template
task.

Unsupported backends fail fast with a non-zero exit and a clear message
instead of silently falling through to validation.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from report_config import load_report_config
from validate_report import validate

# ---------------------------------------------------------------------------
# Backend router — messages for no-op / unsupported backends
# ---------------------------------------------------------------------------

UNSUPPORTED_BUILDER_MESSAGES: dict[str, str] = {
    "visual": (
        "Backend 'visual' no tiene builder genérico en este router. "
        "Usá el builder visual específico de tu tarea "
        "(ej: tools/build_mapa_conceptual_investigacion.py) "
        "y luego ejecutá este router con --validate-only."
    ),
}

# Backends with a generic builder in this router, mapped to their script.
GENERIC_BUILDERS: dict[str, str] = {
    "latex": "build_latex_report.py",
    "docx": "build_docx_report.py",
}


def build_backend(
    config: "ReportConfig",
    args: argparse.Namespace,
) -> None:
    """Run the backend builder for a configured report.

    Args:
        config: ReportConfig with .backend and .folder.
        args: argparse.Namespace with .tex_only and .validate_only.

    Raises:
        SystemExit: on unsupported/no-op backend or subprocess failure.
    """
    if config.backend in GENERIC_BUILDERS:
        script = GENERIC_BUILDERS[config.backend]
        cmd = [sys.executable, str(Path(__file__).with_name(script)), str(config.folder)]
        # --tex-only is a LaTeX-only switch; the DOCX builder has no such stage.
        if args.tex_only and config.backend == "latex":
            cmd.append("--tex-only")
        try:
            proc = subprocess.run(cmd, text=True)
        except FileNotFoundError:
            raise SystemExit(
                "Error: no se encontró el ejecutable de Python o el script "
                f"{script} en la ruta esperada."
            )
        except OSError as exc:
            raise SystemExit(
                f"Error del sistema al ejecutar el builder {config.backend}: {exc}"
            )
        if proc.returncode != 0:
            raise SystemExit(proc.returncode)
    elif config.backend in UNSUPPORTED_BUILDER_MESSAGES:
        raise SystemExit(UNSUPPORTED_BUILDER_MESSAGES[config.backend])
    else:
        raise SystemExit(
            f"Backend no soportado: '{config.backend}'. "
            "Soportados: latex, docx (builders completos), "
            "visual (solo validación con --validate-only tras build manual)."
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path, help="Carpeta del reporte con report.yml")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--tex-only", action="store_true", help="Para backend LaTeX: genera .tex sin compilar PDF")
    args = parser.parse_args()

    config = load_report_config(args.folder)
    print(f"Tipo: {config.type} | backend: {config.backend} | output: {config.output_format}")

    # Build step — skipped when --validate-only
    if not args.validate_only:
        build_backend(config, args)

    if args.tex_only:
        config.raw["output"] = "tex"
        config.raw.setdefault("validators", {})["pdf_layout"] = False
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
