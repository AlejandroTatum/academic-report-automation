#!/usr/bin/env python3
"""Build UNL-style university reports from Markdown.

Usage:
  python3 tools/build_report.py templates/ensayo_unl.md --html outputs/ensayo.html
  python3 tools/build_report.py templates/ensayo_unl.md --pdf outputs/ensayo.pdf
"""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

import markdown


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    meta: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip('"').strip("'")
        meta[key.strip()] = value
    return meta, body


def normalize_markdown(md: str) -> str:
    # Turn Markdown images into semantic figures with figcaptions.
    pattern = re.compile(r"!\[(?P<caption>[^\]]*)\]\((?P<src>[^)]+)\)")

    def repl(match: re.Match[str]) -> str:
        caption = html.escape(match.group("caption"))
        src = html.escape(match.group("src"))
        return f'<figure><img src="{src}" alt="{caption}"><figcaption>{caption}</figcaption></figure>'

    return pattern.sub(repl, md)


def render(md_path: Path, css_path: Path) -> str:
    source = md_path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(source)
    body = normalize_markdown(body)
    body_html = markdown.markdown(body, extensions=["tables", "fenced_code", "attr_list"])
    css = css_path.read_text(encoding="utf-8")

    def m(key: str, default: str = "") -> str:
        return html.escape(meta.get(key, default))

    title = m("titulo_documento", m("titulo", "Reporte"))
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>{css}</style>
</head>
<body>
  <header class="header">
    <div class="header__university">
      <strong>{m('universidad')}</strong><br>
      {m('facultad')}<br>
      {m('codigo')}
    </div>
    <div class="header__career">{m('carrera')}</div>
  </header>

  <section class="meta">
    <p><strong>Nombre:</strong> {m('nombre')}</p>
    <p><strong>Fecha:</strong> {m('fecha')}</p>
    <p><strong>Paralelo:</strong> {m('paralelo')}</p>
    <p></p>
    <p class="full"><strong>Asignatura:</strong> {m('asignatura')}</p>
    <p class="full"><strong>Docente:</strong> {m('docente')}</p>
  </section>

  <div class="report-title">{m('titulo')}</div>

  <main>
    {body_html}
  </main>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("markdown_file", type=Path)
    parser.add_argument("--css", type=Path, default=Path("templates/ensayo_unl.css"))
    parser.add_argument("--html", type=Path)
    parser.add_argument("--pdf", type=Path)
    args = parser.parse_args()

    base = Path.cwd()
    css_path = args.css if args.css.is_absolute() else base / args.css
    html_text = render(args.markdown_file, css_path)

    if args.html:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(html_text, encoding="utf-8")
        print(f"HTML generado: {args.html}")

    if args.pdf:
        try:
            from weasyprint import HTML
        except ImportError as exc:
            raise SystemExit(
                "Falta WeasyPrint. Instalá en un venv: python3 -m pip install weasyprint"
            ) from exc
        args.pdf.parent.mkdir(parents=True, exist_ok=True)
        HTML(string=html_text, base_url=str(args.markdown_file.parent.resolve())).write_pdf(args.pdf)
        print(f"PDF generado: {args.pdf}")

    if not args.html and not args.pdf:
        print(html_text)


if __name__ == "__main__":
    main()
