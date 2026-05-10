#!/usr/bin/env python3
"""Build a academic report through a Markdown/YAML/BibTeX -> LaTeX -> PDF pipeline."""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

from output_router import publish_global_output
from report_config import ROOT, ReportConfig, latex_escape, load_report_config

TEMPLATE = ROOT / "templates" / "unl-report.tex"


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check)


def convert_inline(text: str) -> str:
    placeholders: list[tuple[str, str]] = []

    def keep(pattern: str, repl):
        nonlocal text
        def wrapper(match: re.Match[str]) -> str:
            token = f"@@LATEX_KEEP_{len(placeholders)}@@"
            placeholders.append((token, repl(match)))
            return token
        text = re.sub(pattern, wrapper, text)

    keep(r"\[@([A-Za-z0-9_:\-.,; ]+)\]", lambda m: r"\cite{" + re.sub(r"\s+", "", m.group(1)) + "}")
    keep(r"`([^`]+)`", lambda m: r"\texttt{" + latex_escape(m.group(1)) + "}")
    escaped = latex_escape(text)
    escaped = re.sub(r"\*\*([^*]+)\*\*", lambda m: r"\textbf{" + m.group(1) + "}", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", lambda m: r"\emph{" + m.group(1) + "}", escaped)
    for token, value in placeholders:
        escaped = escaped.replace(latex_escape(token), value)
        escaped = escaped.replace(token, value)
    return escaped


def markdown_to_latex(markdown: str) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    paragraph: list[str] = []
    in_list = False

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            output.append(convert_inline(" ".join(item.strip() for item in paragraph)))
            output.append("")
            paragraph = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            output.append(r"\end{itemize}")
            output.append("")
            in_list = False

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            close_list()
            continue

        image = re.match(r"!\[(?P<caption>[^\]]*)\]\((?P<src>[^)]+)\)", stripped)
        if image:
            flush_paragraph(); close_list()
            caption = convert_inline(image.group("caption"))
            src = latex_escape(image.group("src"))
            output.extend([
                r"\begin{figure}[htbp]",
                r"\centering",
                rf"\includegraphics[width=0.86\textwidth]{{{src}}}",
                rf"\caption{{{caption}}}",
                r"\end{figure}",
                "",
            ])
            continue

        heading = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading:
            flush_paragraph(); close_list()
            level = len(heading.group(1))
            title = convert_inline(heading.group(2).strip())
            command = {1: "section", 2: "subsection", 3: "subsubsection"}.get(level, "paragraph")
            output.append(r"\Needspace{4\baselineskip}")
            output.append(rf"\{command}{{{title}}}")
            output.append("")
            continue

        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        if bullet:
            flush_paragraph()
            if not in_list:
                output.append(r"\begin{itemize}")
                in_list = True
            output.append(r"\item " + convert_inline(bullet.group(1)))
            continue

        paragraph.append(stripped)

    flush_paragraph(); close_list()
    return "\n".join(output).strip() + "\n"


def render_tex(config: ReportConfig) -> str:
    if not TEMPLATE.exists():
        raise SystemExit(f"No existe template LaTeX: {TEMPLATE}")
    if not config.body_path.exists():
        raise SystemExit(f"No existe body.md: {config.body_path}")
    template = TEMPLATE.read_text(encoding="utf-8")
    body = markdown_to_latex(config.body_path.read_text(encoding="utf-8"))
    meta = config.metadata
    bib_file = config.bib_path.name if config.bib_path else ""
    replacements = {
        "{{TITLE}}": latex_escape(meta.get("title") or config.raw.get("title") or "Reporte académico"),
        "{{SUBJECT}}": latex_escape(meta.get("subject") or ""),
        "{{TEACHER}}": latex_escape(meta.get("teacher") or ""),
        "{{STUDENT}}": latex_escape(meta.get("student") or ""),
        "{{DATE}}": latex_escape(meta.get("date") or ""),
        "{{CAREER}}": latex_escape(meta.get("career") or "Carrera de Computación"),
        "{{PARALLEL}}": latex_escape(meta.get("parallel") or ""),
        "{{UNIVERSITY}}": latex_escape(meta.get("university") or "Sample University"),
        "{{FACULTY}}": latex_escape(meta.get("faculty") or "Facultad de la Energía, las Industrias y los Recursos Naturales no Renovables"),
        "{{LOGO_PATH}}": latex_escape("unl-logo-aa1-transparent.png"),
        "{{BIB_FILE}}": latex_escape(bib_file),
        "{{HAS_BIB}}": "true" if config.bib_path else "false",
        "{{BODY}}": body,
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template


def compile_latex(config: ReportConfig) -> None:
    build_dir = config.tex_path.parent
    build_dir.mkdir(parents=True, exist_ok=True)
    if config.bib_path:
        shutil.copy2(config.bib_path, build_dir / config.bib_path.name)
    logo = ROOT / "assets" / "unl-logo-aa1-transparent.png"
    if logo.exists():
        shutil.copy2(logo, build_dir / logo.name)
    engine = shutil.which("latexmk")
    latex_engine = shutil.which("lualatex") or shutil.which("xelatex") or shutil.which("pdflatex")
    if engine:
        run([engine, "-lualatex", "-interaction=nonstopmode", "-halt-on-error", config.tex_path.name], cwd=build_dir, check=False)
    elif latex_engine:
        for command in ([latex_engine, "-interaction=nonstopmode", "-halt-on-error", config.tex_path.name],):
            run(list(command), cwd=build_dir, check=False)
        if config.bib_path and shutil.which("biber"):
            run(["biber", config.tex_path.stem], cwd=build_dir, check=False)
        elif config.bib_path and shutil.which("bibtex"):
            run(["bibtex", config.tex_path.stem], cwd=build_dir, check=False)
        run([latex_engine, "-interaction=nonstopmode", "-halt-on-error", config.tex_path.name], cwd=build_dir, check=False)
        run([latex_engine, "-interaction=nonstopmode", "-halt-on-error", config.tex_path.name], cwd=build_dir, check=False)
    elif shutil.which("docker"):
        run([
            "docker", "run", "--rm",
            "-u", f"{os.getuid()}:{os.getgid()}",
            "-v", f"{config.folder}:/work",
            "-w", f"/work/{config.tex_path.parent.relative_to(config.folder)}",
            "texlive/texlive:latest",
            "sh", "-lc",
            f"lualatex -interaction=nonstopmode -halt-on-error {config.tex_path.name}; "
            f"(biber {config.tex_path.stem} || bibtex {config.tex_path.stem} || true); "
            f"lualatex -interaction=nonstopmode -halt-on-error {config.tex_path.name}; "
            f"lualatex -interaction=nonstopmode -halt-on-error {config.tex_path.name}",
        ], cwd=config.folder, check=False)
    else:
        raise SystemExit("No hay pdflatex/latexmk ni Docker para compilar LaTeX")

    built_pdf = build_dir / f"{config.tex_path.stem}.pdf"
    if not built_pdf.exists():
        raise SystemExit(f"La compilación no generó PDF: {built_pdf}")
    config.pdf_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built_pdf, config.pdf_path)
    if config.publish_global:
        global_pdf = publish_global_output(config.pdf_path, config.metadata)
        if global_pdf:
            print(f"PDF publicado por materia: {global_pdf}")
        else:
            print("Aviso: no pude inferir la materia; no se publicó copia global en outputs/<materia>/")


def build(folder: Path, compile_pdf: bool = True) -> ReportConfig:
    config = load_report_config(folder)
    if config.backend != "latex":
        raise SystemExit(f"build_latex_report solo aplica a backend=latex; actual: {config.backend}")
    config.tex_path.parent.mkdir(parents=True, exist_ok=True)
    config.tex_path.write_text(render_tex(config), encoding="utf-8")
    print(f"LaTeX generado: {config.tex_path}")
    if compile_pdf:
        compile_latex(config)
        print(f"PDF generado: {config.pdf_path}")
    return config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path, help="Carpeta del reporte con report.yml")
    parser.add_argument("--tex-only", action="store_true", help="Solo genera build/main.tex")
    args = parser.parse_args()
    build(args.folder, compile_pdf=not args.tex_only)


if __name__ == "__main__":
    main()
