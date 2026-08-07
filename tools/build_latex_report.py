#!/usr/bin/env python3
"""Build a UNL academic report through a Markdown/YAML/BibTeX -> LaTeX -> PDF pipeline."""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

from output_router import publish_global_output
from report_config import (
    CONTENT_ROOT,
    ROOT,
    ReportConfig,
    latex_escape,
    load_report_config,
    relative_subpath,
)

DEFAULT_TEMPLATE = ROOT / "templates" / "unl-report.tex"
PLAIN_TEMPLATE = ROOT / "templates" / "plain-report.tex"
TEMPLATE_ALIASES = {
    "default": DEFAULT_TEMPLATE,
    "unl": DEFAULT_TEMPLATE,
    "unl_report": DEFAULT_TEMPLATE,
    "chamba_overleaf": ROOT / "templates" / "chamba-overleaf.tex",
    "overleaf_chamba": ROOT / "templates" / "chamba-overleaf.tex",
    "plain": PLAIN_TEMPLATE,
    "plain_report": PLAIN_TEMPLATE,
}


def normalize_template_key(key: str | None) -> str:
    """Normalize a report.yml template key (case-insensitive, trimmed)."""
    normalized = str(key or "").strip().lower()
    return normalized or "default"


def resolve_template(key: str | None) -> Path:
    """Resolve a template key to its .tex path.

    An empty/absent key keeps the historical academic default. An unknown key
    fails loudly instead of silently rendering the institutional template.
    """
    normalized = normalize_template_key(key)
    template_path = TEMPLATE_ALIASES.get(normalized)
    if template_path is None:
        valid = ", ".join(sorted(TEMPLATE_ALIASES))
        raise SystemExit(
            f"Template LaTeX desconocido: {normalized!r}. Valores válidos: {valid}"
        )
    return template_path


# report.yml key that turns academic section numbering on or off for one
# report. `document-routing.md` forbids auto-included academic section
# numbering on Routes B, C and D, but the templates numbered unconditionally.
#
# The key is intentionally independent of `route:`: numbering is an explicit
# typographic decision, and a routing key that silently restyled a document
# would be surprising. A future change could derive the *default* from the
# route once that key settles.
SECTION_NUMBERING_KEY = "section_numbering"

# Absence of the key means numbered. Every report that exists today declares
# nothing about numbering and must keep rendering exactly as it does now.
SECTION_NUMBERING_DEFAULT = True

_SECTION_NUMBERING_TRUE = {"true", "yes", "on", "si", "sí", "1"}
_SECTION_NUMBERING_FALSE = {"false", "no", "off", "0"}


def section_numbering_enabled(raw: dict) -> bool:
    """Read `section_numbering:` from a report.yml mapping.

    Returns the historical default when the key is absent. An unrecognised
    value fails loudly rather than picking a side: guessing would silently
    renumber — or unnumber — a whole document over a typo.
    """
    if SECTION_NUMBERING_KEY not in raw:
        return SECTION_NUMBERING_DEFAULT
    value = raw.get(SECTION_NUMBERING_KEY)
    if isinstance(value, bool):
        return value
    written = str(value if value is not None else "").strip().lower()
    if written in _SECTION_NUMBERING_TRUE:
        return True
    if written in _SECTION_NUMBERING_FALSE:
        return False
    raise SystemExit(
        f"Valor no válido para '{SECTION_NUMBERING_KEY}' en report.yml: "
        f"{value!r}. Valores aceptados: true, false (también sí/no, on/off). "
        "Sin la clave, las secciones se numeran como hasta ahora."
    )


# Asset constants — single source of truth for expected filenames.
ASSETS_DIR = ROOT / "assets"
# Markdown image syntax. Only ever matched against Markdown source, never
# against a body that markdown_to_latex() has already converted.
MARKDOWN_IMAGE_RE = re.compile(r"!\[.*\]\(.*\)")


def cover_field(value: str | None) -> str:
    r"""Escape an optional cover field, never returning an empty string.

    Cover templates render these on their own line as ``{\large {{FIELD}}}\\``.
    An empty substitution leaves ``{\large }\\``, which LaTeX rejects outright
    with ``There's no line here to end.`` — a fatal error whose message points
    at the title page rather than at the metadata field nobody set.

    ``\strut`` is an invisible box with the height and depth of a normal line,
    so the line exists for LaTeX to end while the reader sees nothing, and the
    cover's vertical rhythm stays exactly as designed.
    """
    text = (value or "").strip()
    return latex_escape(text) if text else r"\strut"
LOGO_FILENAME = "unl-logo-aa1-transparent.png"
BACKGROUND_FILENAME = "fondo-overleaf-investigacion.png"
# Known extra PNGs in assets/ that are NOT referenced by the LaTeX pipeline.
# These are standalone files (e.g. prompt engineering flow diagrams) used
# directly from report body.md via Markdown image syntax.
KNOWN_EXTRA_ASSETS: set[str] = {"prompting-os-flow.png"}
# Plain logo variant — not used by the LaTeX pipeline directly but referenced
# in unl-shell.md as the original AA1 source asset.
PLAIN_LOGO_FILENAME = "unl-logo-aa1.png"

EXPECTED_ASSETS: list[tuple[str, str]] = [
    (LOGO_FILENAME, "Logo UNL (transparente, usado por {{LOGO_PATH}})"),
    (BACKGROUND_FILENAME, "Fondo portada (usado por {{BACKGROUND_PATH}})"),
    (PLAIN_LOGO_FILENAME, "Logo UNL original (referencia AA1, no usado por pipeline)"),
]


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check)


# Characters after which an inline-code run may break across lines. Monospace
# fonts carry no hyphenation patterns, so without these explicit penalties a
# path like ``tools/test_content_root.py`` is one unbreakable box: it overflows
# a table column into its neighbour, and in justified prose it forces TeX to
# shrink the surrounding interword glue until the code looks glued to the words
# next to it.
INLINE_CODE_BREAK_AFTER = "/_-.:,=()"


def inline_code(value: str) -> str:
    r"""Render inline code as ``\texttt`` with explicit break opportunities.

    ``\allowbreak{}`` is a zero-width penalty: it never adds a hyphen and never
    changes the glyphs, it only tells TeX that a line may end there. The
    trailing separator gets none, since a break at the very end of the run
    would leave the box empty.
    """
    characters = list(value)
    last = len(characters) - 1
    pieces: list[str] = []
    for index, character in enumerate(characters):
        pieces.append(latex_escape(character))
        if character in INLINE_CODE_BREAK_AFTER and index < last:
            pieces.append(r"\allowbreak{}")
    return r"\texttt{" + "".join(pieces) + "}"


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
    keep(r"\$([^$]+)\$", lambda m: "$" + m.group(1) + "$")
    keep(r"`([^`]+)`", lambda m: inline_code(m.group(1)))
    escaped = latex_escape(text)
    escaped = re.sub(r"\*\*([^*]+)\*\*", lambda m: r"\textbf{" + m.group(1) + "}", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", lambda m: r"\emph{" + m.group(1) + "}", escaped)
    for token, value in placeholders:
        escaped = escaped.replace(latex_escape(token), value)
        escaped = escaped.replace(token, value)
    return escaped


# Fenced code blocks: ``` or ~~~ (three or more), with an optional language
# word. Anything between an opening fence and its closing fence is literal.
CODE_FENCE_RE = re.compile(r"^(?P<marker>`{3,}|~{3,})\s*(?P<language>[^`]*)$")
# Headings the templates already print by themselves through \printbibliography.
BIBLIOGRAPHY_HEADINGS = {"bibliografia", "referencias", "references", "bibliography"}


def fold_heading(title: str) -> str:
    """Normalize a heading for case- and accent-insensitive comparison."""
    decomposed = unicodedata.normalize("NFKD", title)
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return stripped.casefold().strip()


def is_bibliography_heading(title: str) -> bool:
    """True for the heading titles ``\\printbibliography`` already prints."""
    return fold_heading(title) in BIBLIOGRAPHY_HEADINGS


def markdown_to_latex(markdown: str) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    paragraph: list[str] = []
    list_env: str | None = None

    def split_table_row(row: str) -> list[str]:
        stripped = row.strip().strip("|")
        return [cell.strip() for cell in stripped.split("|")]

    def is_table_separator(row: str) -> bool:
        cells = split_table_row(row)
        return bool(cells) and all(re.match(r"^:?-{3,}:?$", cell) for cell in cells)

    def render_table(rows: list[list[str]]) -> None:
        if len(rows) < 2:
            return
        columns = max(len(row) for row in rows)
        # Clean bordered grid: visible rows (\hline) and columns (| separators),
        # centered alignment, subtle gray header, consistent padding. Both
        # branches emit a page-breakable environment (xltabular/longtable)
        # instead of an atomic float — a table too tall for the remaining
        # page space must flow onto the next page, not strand the heading
        # above it while the whole table jumps as one block.
        if columns <= 2:
            colspec = " | ".join(["c"] * columns)
            env = "longtable"
            table_open = rf"\begin{{{env}}}{{| {colspec} |}}"
            font_size = r"\small"
        else:
            # Centered grid columns with automatic text wrapping via xltabular
            colspec = " | ".join([r">{\centering\arraybackslash}X"] * columns)
            env = "xltabular"
            table_open = rf"\begin{{{env}}}{{\textwidth}}{{| {colspec} |}}"
            font_size = r"\footnotesize"

        def normalized(row: list[str]) -> list[str]:
            return row + [""] * (columns - len(row))

        header_cells = normalized(rows[0])
        # No \begin{table}[H]/\centering — longtable/xltabular are not floats
        # and center themselves (\LTleft=\LTright=\fill by default). The
        # font-size/spacing declarations need an explicit group since the
        # table environment no longer provides one.
        output.extend([
            r"\Needspace{4\baselineskip}",
            r"\begingroup",
            font_size,
            r"\renewcommand{\arraystretch}{1.2}",
            r"\setlength{\tabcolsep}{3pt}",
            table_open,
            r"\hline",
            r"\rowcolor[gray]{0.92}",
            " & ".join(r"\textbf{" + convert_inline(cell) + "}" for cell in header_cells) + r" \\",
            r"\hline",
            r"\endhead",
        ])
        for idx, row in enumerate(rows[1:]):
            output.append(" & ".join(convert_inline(cell) for cell in normalized(row)) + r" \\")
            output.append(r"\hline")
        output.extend([
            rf"\end{{{env}}}",
            r"\endgroup",
            "",
        ])

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            output.append(convert_inline(" ".join(item.strip() for item in paragraph)))
            output.append("")
            paragraph = []

    def close_list() -> None:
        nonlocal list_env
        if list_env:
            output.append(rf"\end{{{list_env}}}")
            output.append("")
            list_env = None

    def open_list(env: str) -> None:
        """Start ``env``, closing a list of the other kind still open."""
        nonlocal list_env
        if list_env == env:
            return
        close_list()
        output.append(rf"\begin{{{env}}}")
        list_env = env

    def render_code_block(code_lines: list[str]) -> None:
        r"""Emit a fenced block as page-breakable verbatim.

        ``verbatim`` belongs to the LaTeX kernel, so this adds no package the
        templates would have to load, and it breaks between its own lines
        instead of overflowing the page as one atomic box. The content is
        emitted untouched — neither ``latex_escape()`` nor ``convert_inline()``
        may run over it — except for a literal ``\end{verbatim}``, which would
        otherwise close the environment from the inside.
        """
        block = list(code_lines)
        while block and not block[0].strip():
            block.pop(0)
        while block and not block[-1].strip():
            block.pop()
        if not block:
            return
        # verbatim never wraps a long line, so the font size sets the usable
        # column count. \footnotesize fits ~89 monospace columns in the A4
        # text block; \small stops at ~79 and pushes a plain 80-column source
        # line into the margin.
        output.extend([
            r"\begingroup",
            r"\footnotesize",
            r"\begin{verbatim}",
        ])
        output.extend(line.rstrip().replace(r"\end{verbatim}", r"\end {verbatim}") for line in block)
        output.extend([
            r"\end{verbatim}",
            r"\endgroup",
            "",
        ])

    def find_closing_fence(marker: str, start: int) -> int | None:
        """Index of the fence that closes the block opened at ``start - 1``."""
        for index in range(start, len(lines)):
            candidate = lines[index].strip()
            if len(candidate) >= 3 and set(candidate) == {marker}:
                return index
        return None

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            close_list()
            i += 1
            continue

        # Fences come first: a code line may contain anything, including the
        # pipes, hashes and dashes every other block rule keys on.
        fence = CODE_FENCE_RE.match(stripped)
        if fence:
            closing = find_closing_fence(fence.group("marker")[0], i + 1)
            if closing is None:
                # Unterminated fence: drop the stray marker and keep parsing.
                # Consuming everything to EOF would turn the rest of the
                # document — headings, tables, lists — into literal text.
                #
                # Recovering is right; recovering silently is not. The block's
                # lines now reflow as prose, which is precisely the defect
                # fence support exists to prevent, so say where it started.
                print(
                    f"Aviso: cerca de código sin cerrar en la línea {i + 1} "
                    f"({stripped}); su contenido se reflowará como texto "
                    "corriente. Cerrá el bloque para que salga como código.",
                    file=sys.stderr,
                )
                i += 1
                continue
            flush_paragraph(); close_list()
            render_code_block(lines[i + 1 : closing])
            i = closing + 1
            continue

        if "|" in stripped and i + 1 < len(lines) and is_table_separator(lines[i + 1]):
            flush_paragraph(); close_list()
            table_rows = [split_table_row(stripped)]
            i += 2
            while i < len(lines) and "|" in lines[i].strip() and lines[i].strip():
                table_rows.append(split_table_row(lines[i]))
                i += 1
            render_table(table_rows)
            continue

        # finalanswer{...} —→ answerbox environment (before display_math)
        if stripped.startswith("finalanswer{"):
            flush_paragraph(); close_list()
            depth = 0
            content_start = len("finalanswer{")
            i_pos = content_start
            while i_pos < len(stripped) and depth >= 0:
                if stripped[i_pos] == "{":
                    depth += 1
                elif stripped[i_pos] == "}":
                    depth -= 1
                i_pos += 1
            if depth == -1:
                content = stripped[content_start:i_pos-1].strip()
                output.extend([
                    r"\begin{answerbox}",
                    r"\[",
                    content,
                    r"\]",
                    r"\end{answerbox}",
                    "",
                ])
            else:
                # fallback: unmatched braces — treat as plain paragraph
                paragraph.append(stripped)
            i += 1
            continue

        display_math = re.match(r"^\$\$(?P<formula>.+)\$\$$", stripped)
        if display_math:
            flush_paragraph(); close_list()
            output.extend([
                r"\[",
                display_math.group("formula").strip(),
                r"\]",
                "",
            ])
            i += 1
            continue

        image = re.match(r"!\[(?P<caption>[^\]]*)\]\((?P<src>[^)]+)\)", stripped)
        if image:
            flush_paragraph(); close_list()
            caption = convert_inline(image.group("caption"))
            src = latex_escape(image.group("src"))
            width = "0.86"
            raw_src = image.group("src")
            if "merge_sort_visual_example" in raw_src or "merge_sort_recursion" in raw_src:
                width = "0.70"
            elif "comparison_matrix" in raw_src or "method_" in raw_src or "three_method" in raw_src:
                width = "0.94"
            elif "complexity_growth" in raw_src:
                width = "0.90"
            elif "matriz_etica_ia" in raw_src:
                width = "0.94"
            elif "gestion-procesos" in raw_src:
                width = "0.96"
            elif "planificacion-cpu" in raw_src:
                width = "0.96"
            elif "aa1-uml" in raw_src:
                width = "0.96"
            elif "kipu-entregables" in raw_src:
                # Vertical flowcharts need headroom for their caption and page footer.
                width = "0.50"
            elif "manual_ej" in raw_src:
                width = "0.88"
            elif "mini_paginacion" in raw_src or "mini_segmentacion" in raw_src:
                width = "0.88"
            elif "infografia_paginacion_segmentacion" in raw_src:
                width = "0.75"
            output.extend([
                r"\Needspace{6\baselineskip}",
                r"\begin{figure}[H]",
                r"\centering",
                rf"\includegraphics[width={width}\textwidth, keepaspectratio]{{{src}}}",
                rf"\caption{{{caption}}}",
                r"\end{figure}",
                "",
            ])
            i += 1
            continue

        heading = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading:
            flush_paragraph(); close_list()
            level = len(heading.group(1))
            raw_title = heading.group(2).strip()
            if is_bibliography_heading(raw_title) and not any(
                rest.strip() for rest in lines[i + 1 :]
            ):
                # The templates end with \printbibliography, which prints its
                # own title. An empty trailing bibliography heading would show
                # that title twice, once numbered and once not.
                i += 1
                continue
            title = convert_inline(raw_title)
            command = {1: "section", 2: "subsection", 3: "subsubsection"}.get(level, "paragraph")
            if raw_title.casefold() in {"conclusiones", "conclusión", "conclusion"}:
                needspace_lines = 18
            elif level == 1:
                needspace_lines = 16
            elif level == 2:
                needspace_lines = 10
            else:
                needspace_lines = 8
            output.append(rf"\Needspace{{{needspace_lines}\baselineskip}}")
            output.append(rf"\{command}{{{title}}}")
            output.append("")
            i += 1
            continue

        # Raw LaTeX commands passthrough — \newpage, \clearpage
        if stripped in ("\\newpage", "\\clearpage", "\\pagebreak"):
            flush_paragraph()
            close_list()
            output.append(stripped)
            output.append("")
            i += 1
            continue

        # Passthrough for \begin{...} and \end{...} commands
        if re.match(r"^\\(begin|end)\{", stripped):
            flush_paragraph()
            close_list()
            output.append(stripped)
            output.append("")
            i += 1
            continue

        # Horizontal rule —→ \newpage (page break in PDF output)
        if re.match(r"^-{3,}$", stripped):
            flush_paragraph()
            close_list()
            output.append(r"\newpage")
            output.append("")
            i += 1
            continue

        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        if bullet:
            flush_paragraph()
            open_list("itemize")
            output.append(r"\item " + convert_inline(bullet.group(1)))
            i += 1
            continue

        # Ordered lists — "1." and "1)" alike. Without this the numbers stay in
        # the paragraph buffer and the whole procedure renders as one justified
        # run-on line.
        ordered = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if ordered:
            flush_paragraph()
            open_list("enumerate")
            output.append(r"\item " + convert_inline(ordered.group(1)))
            i += 1
            continue

        paragraph.append(stripped)
        i += 1

    flush_paragraph(); close_list()
    return "\n".join(output).strip() + "\n"


def render_tex(config: ReportConfig) -> str:
    template_key = normalize_template_key(config.raw.get("template") or config.raw.get("latex_template"))
    template_path = resolve_template(template_key)
    if not template_path.exists():
        raise SystemExit(f"No existe template LaTeX: {template_path}")
    if not config.body_path.exists():
        raise SystemExit(f"No existe body.md: {config.body_path}")
    template = template_path.read_text(encoding="utf-8")
    markdown_source = config.body_path.read_text(encoding="utf-8")
    body = markdown_to_latex(markdown_source)
    # Figure detection runs against the Markdown source: once converted, images
    # are \includegraphics commands and the Markdown pattern can never match.
    has_figures = bool(MARKDOWN_IMAGE_RE.search(markdown_source))
    meta = config.metadata
    front_matter = ""
    ai_declaration_latex = ""
    ai_signature_latex = ""
    after_bibliography_latex = ""
    ai_declaration = config.raw.get("ai_declaration") or config.raw.get("declaracion_ia")
    student = meta.get("student") or ""
    date = meta.get("date") or ""
    signature_latex = "\n".join([
        r"\thispagestyle{plain}",
        r"\vspace*{1.15cm}",
        r"\begin{flushright}",
        r"\rule{7.3cm}{0.4pt}\\[-0.1cm]",
        rf"{{\bfseries {cover_field(student)}}}\\",
        "Autor",
        r"\end{flushright}",
        r"\newpage",
        "",
    ])
    if ai_declaration:
        if isinstance(ai_declaration, dict):
            declaration_title = str(ai_declaration.get("title") or "Declaración de uso de IA generativa")
            declaration_text = str(ai_declaration.get("text") or "")
        else:
            declaration_title = "Declaración de uso de IA generativa"
            declaration_text = str(ai_declaration)
        declaration_latex = "\n".join([
            r"\Needspace{5\baselineskip}",
            rf"\section*{{{convert_inline(declaration_title)}}}",
            rf"\addcontentsline{{toc}}{{section}}{{{convert_inline(declaration_title)}}}",
            "",
            convert_inline(declaration_text),
            "",
        ])
        if str(config.raw.get("ai_declaration_position") or "").strip().lower() in {
            "after_bibliography",
            "after-bibliography",
            "after_bib",
        }:
            # Strip the trailing \newpage from signature when placed
            # after bibliography — avoids a blank end-page
            sig_no_newpage = signature_latex.rstrip()
            if sig_no_newpage.endswith(r"\newpage"):
                sig_no_newpage = sig_no_newpage[: -len(r"\newpage")].rstrip()
            after_bibliography_latex = declaration_latex + "\n" + sig_no_newpage
        else:
            front_matter = declaration_latex
            ai_declaration_latex = declaration_latex
            ai_signature_latex = signature_latex
    if template_key in {"chamba_overleaf", "overleaf_chamba"} and not ai_declaration_latex and not after_bibliography_latex:
        student = meta.get("student") or ""
        date = meta.get("date") or ""
        ai_declaration_latex = "\n".join([
            r"\section*{Declaración de uso de IA Generativa}",
            r"\addcontentsline{toc}{section}{Declaración de uso de IA Generativa}",
            rf"Yo, \textbf{{{latex_escape(student)}}}, en calidad de autor, declaro de manera transparente y responsable el uso de herramientas de Inteligencia Artificial Generativa (IAG) durante el desarrollo del presente trabajo, en conformidad con los principios de integridad académica, ética investigativa y buenas prácticas en el uso de tecnologías emergentes.",
            "",
            r"\subsection*{1. Alcance del uso de IA generativa}",
            "El uso de herramientas de IAG se ha limitado a funciones de apoyo, sin sustituir el juicio crítico ni la autoría intelectual del autor. En particular, se han utilizado para:",
            r"\begin{itemize}",
            r"\item Mejora de redacción y estilo académico.",
            r"\item Apoyo en la estructuración y conversión del documento a formato LaTeX.",
            r"\item Asistencia técnica para normalizar figuras, referencias y archivo BibTeX.",
            r"\end{itemize}",
            "",
            r"\subsection*{2. Clasificación del uso según GAIDeT}",
            "De acuerdo con la taxonomía GAIDeT, el uso de IA generativa en este trabajo se clasifica en asistencia lingüística, apoyo en organización documental y asistencia técnica de formato.",
            "",
            r"\subsection*{3. Validación y responsabilidad}",
            "Todo contenido asistido por IA ha sido revisado, validado y adaptado por el autor, quien asume la responsabilidad total sobre la calidad, veracidad y originalidad del trabajo.",
            "",
            r"\subsection*{4. Consideraciones éticas}",
            "El uso de IA se realizó respetando principios de honestidad académica, normativas institucionales de la Universidad Nacional de Loja y buenas prácticas internacionales.",
            "",
            rf"\begin{{flushright}}Loja, Ecuador, {latex_escape(date)}\end{{flushright}}",
            "",
        ])
        ai_signature_latex = signature_latex
    bib_file = config.bib_path.name if config.bib_path else ""
    replacements = {
        "{{TITLE}}": latex_escape(meta.get("title") or config.raw.get("title") or "Reporte académico"),
        "{{TITLE_EN}}": cover_field(meta.get("title_en") or config.raw.get("title_en")),
        "{{SUBJECT}}": latex_escape(meta.get("subject") or ""),
        "{{TEACHER}}": cover_field(meta.get("teacher")),
        "{{STUDENT}}": cover_field(meta.get("student")),
        "{{DATE}}": latex_escape(meta.get("date") or ""),
        "{{CAREER}}": latex_escape(meta.get("career") or "Carrera de Computación"),
        "{{PARALLEL}}": latex_escape(meta.get("parallel") or ""),
        "{{ACTIVITY}}": latex_escape(meta.get("activity") or meta.get("tipo") or config.raw.get("activity") or "Informe académico"),
        "{{UNIVERSITY}}": latex_escape(meta.get("university") or "Universidad Nacional de Loja"),
        "{{FACULTY}}": latex_escape(meta.get("faculty") or "Facultad de la Energía, las Industrias y los Recursos Naturales no Renovables"),
        "{{LOGO_PATH}}": latex_escape(LOGO_FILENAME),
        "{{BACKGROUND_PATH}}": latex_escape(BACKGROUND_FILENAME),
        "{{BIB_FILE}}": latex_escape(bib_file),
        "{{HAS_BIB}}": "true" if config.bib_path else "false",
        "{{HAS_FIGURES}}": "true" if has_figures else "false",
        "{{SECTION_NUMBERING}}": "true" if section_numbering_enabled(config.raw) else "false",
        "{{LIST_OF_FIGURES}}": r"\newpage\listoffigures" if has_figures else "",
        "{{FRONT_MATTER}}": front_matter,
        "{{AI_DECLARATION}}": ai_declaration_latex,
        "{{AI_SIGNATURE}}": ai_signature_latex,
        "{{AFTER_BIBLIOGRAPHY}}": after_bibliography_latex,
        "{{BODY}}": body,
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template


def validate_assets_exist() -> list[str]:
    """Check that expected build assets exist under ASSETS_DIR.

    Returns a list of error messages (empty if all assets are present).
    Callers may raise SystemExit or collect warnings.
    """
    errors: list[str] = []
    for filename, description in EXPECTED_ASSETS:
        path = ASSETS_DIR / filename
        if not path.exists():
            errors.append(f"Asset faltante: {description} → {path}")
        elif path.stat().st_size < 1_000:
            errors.append(f"Asset sospechosamente pequeño ({path.stat().st_size} bytes): {path}")
    return errors


# Extensions \includegraphics tries when a reference carries no suffix.
FIGURE_SUFFIXES = (".png", ".pdf", ".jpg", ".jpeg", ".eps")
# Same Markdown image syntax as MARKDOWN_IMAGE_RE, capturing the source path.
MARKDOWN_IMAGE_SRC_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def figure_references(markdown: str) -> list[str]:
    """Return every local image path referenced from a Markdown body.

    Remote sources are skipped: LaTeX cannot fetch them, and reporting them as
    missing files would be misleading.
    """
    references: list[str] = []
    for match in MARKDOWN_IMAGE_SRC_RE.finditer(markdown):
        source = match.group(1).strip().split(" ")[0].strip()
        if not source or source.startswith(("http://", "https://", "data:")):
            continue
        references.append(source)
    return references


def resolve_figure(reference: str, build_dir: Path) -> Path | None:
    r"""Resolve a figure reference the way ``\includegraphics`` will.

    Relative references resolve from the build directory — the documented
    convention (``../../../assets/generated/...``). A reference with no suffix
    matches any of the graphics extensions LaTeX would try on its own.
    """
    candidate = Path(reference)
    base = candidate if candidate.is_absolute() else build_dir / candidate
    if base.suffix:
        return base if base.exists() else None
    for suffix in FIGURE_SUFFIXES:
        with_suffix = base.with_suffix(suffix)
        if with_suffix.exists():
            return with_suffix
    return None


def validate_figure_paths(
    markdown: str, build_dir: Path, docker_mount: Path | None = None
) -> list[str]:
    r"""Check every figure reference before the compiler ever starts.

    ``\includegraphics`` aborts the whole run on a file it cannot open, so an
    unresolvable figure has to be caught here or it becomes a fatal LaTeX error
    buried in the transcript.

    ``docker_mount`` is the host directory bind-mounted at ``/work`` when the
    Docker fallback is the engine. Under Docker an absolute host path simply
    does not exist inside the container, and a relative path that escapes the
    mount is equally invisible — both are rejected up front.

    Returns a list of Spanish error messages (empty when every figure resolves).
    """
    errors: list[str] = []
    for reference in figure_references(markdown):
        if docker_mount is not None and Path(reference).is_absolute():
            errors.append(
                f"Figura con ruta absoluta no utilizable dentro del contenedor Docker: "
                f"{reference}. Use una ruta relativa al directorio de compilación: {build_dir}"
            )
            continue
        resolved = resolve_figure(reference, build_dir)
        if resolved is None:
            errors.append(f"Figura no encontrada: {reference} (resuelta desde {build_dir})")
            continue
        if docker_mount is not None and not is_within(resolved.resolve(), docker_mount.resolve()):
            errors.append(
                f"Figura fuera del directorio montado en Docker ({docker_mount}): "
                f"{reference} → {resolved}"
            )
    return errors


def compilation_failure_message(
    pdf_path: Path, log_path: Path, output: str, max_lines: int = 30
) -> str:
    """Build the failure text for a compilation that produced no PDF.

    The compiler transcript is captured rather than streamed, so a failure used
    to be reported as a bare "no PDF" while the real cause — a missing figure,
    an unavailable package — stayed inside the pipe. This surfaces the lines
    LaTeX itself marks as errors plus the tail of the transcript, and always
    points at the full log for the rest.
    """
    lines = [line.rstrip() for line in (output or "").splitlines()]
    parts = [f"La compilación no generó PDF: {pdf_path}"]
    errors = [line for line in lines if line.startswith("!")]
    if errors:
        parts.extend(["", "Errores reportados por LaTeX:", *errors[:10]])
    tail = [line for line in lines if line.strip()][-max_lines:]
    if tail:
        parts.extend(["", f"Últimas {len(tail)} líneas de la salida del compilador:", *tail])
    parts.extend(["", f"Log completo: {log_path}"])
    return "\n".join(parts)


def is_within(path: Path, base: Path) -> bool:
    """True when ``path`` is ``base`` or lives under it."""
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True


def docker_mount_root(config: ReportConfig) -> Path:
    """Pick the host directory to bind-mount into the LaTeX container.

    The old implementation mounted the single derived root and crashed with
    ValueError for any report outside it. Reports now live in the content tree
    (or anywhere the user points at), so the mount is derived from the report
    itself.

    It cannot simply be the report folder: figure references inside body.md are
    relative to the build dir and routinely escape the report
    (``../../../assets/generated/...``). So prefer the widest known root that
    already contains the report — content root first, then the code root for a
    report living inside the checkout (examples, fixtures) — and otherwise fall
    back to the closest common ancestor of the report folder and its build dir.
    A degenerate ancestor (``/``, ``/home``) is refused: mounting that much of
    the host is worse than a build that cannot see a stray figure.
    """
    build_dir = config.tex_path.parent.resolve()
    folder = config.folder.resolve()
    for base in (CONTENT_ROOT, ROOT):
        if is_within(build_dir, base) and is_within(folder, base):
            return base
    if is_within(build_dir, folder):
        return folder
    common = Path(os.path.commonpath([str(folder), str(build_dir)]))
    if len(common.parts) > 2 and is_within(build_dir, common):
        return common
    return build_dir


def docker_compile_command(config: ReportConfig) -> list[str]:
    """Build the ``docker run`` argv for the TeX Live fallback.

    Split out from compile_latex so the path arithmetic is testable without
    Docker installed.
    """
    mount = docker_mount_root(config)
    build_dir = config.tex_path.parent.resolve()
    workdir_rel = relative_subpath(build_dir, mount)
    workdir = "/work" if str(workdir_rel) == "." else f"/work/{workdir_rel.as_posix()}"
    tex_name = config.tex_path.name
    tex_stem = config.tex_path.stem
    return [
        "docker", "run", "--rm",
        "-u", f"{os.getuid()}:{os.getgid()}",
        "-v", f"{mount}:/work",
        "-w", workdir,
        "texlive/texlive:latest",
        "sh", "-lc",
        f"lualatex -interaction=nonstopmode -halt-on-error {tex_name}; "
        f"(biber {tex_stem} || bibtex {tex_stem} || true); "
        f"lualatex -interaction=nonstopmode -halt-on-error {tex_name}; "
        f"lualatex -interaction=nonstopmode -halt-on-error {tex_name}",
    ]


def is_same_file(built: Path, destination: Path) -> bool:
    """Return True when both paths name the same file on disk.

    The final publication step copies the build output to the configured
    ``pdf:`` destination. Those are usually distinct, but a report is entitled
    to point ``pdf:`` straight at the build output — and since final artifacts
    are barred from ``reports/<work>/outputs/``, that is now the obvious thing
    to write. ``shutil.copy2`` raises ``SameFileError`` for a self-copy, which
    killed the build *after* the PDF had been produced successfully.

    Path equality is not enough: a symlinked build directory reaches the same
    inode through a different path. ``Path.samefile`` compares the actual
    files, and a missing destination simply means it is not the built PDF.
    """
    try:
        return built.samefile(destination)
    except (OSError, ValueError):
        return False


def compile_latex(config: ReportConfig) -> None:
    build_dir = config.tex_path.parent
    build_dir.mkdir(parents=True, exist_ok=True)
    if config.bib_path:
        shutil.copy2(config.bib_path, build_dir / config.bib_path.name)
    asset_errors = validate_assets_exist()
    if asset_errors:
        raise SystemExit("Errores de assets:\n- " + "\n- ".join(asset_errors))
    logo = ASSETS_DIR / LOGO_FILENAME
    if logo.exists():
        shutil.copy2(logo, build_dir / logo.name)
    background = ASSETS_DIR / BACKGROUND_FILENAME
    if background.exists():
        shutil.copy2(background, build_dir / background.name)
    engine = shutil.which("latexmk")
    latex_engine = shutil.which("lualatex") or shutil.which("xelatex") or shutil.which("pdflatex")
    docker_engine = None if (engine or latex_engine) else shutil.which("docker")
    if not (engine or latex_engine or docker_engine):
        raise SystemExit("No hay pdflatex/latexmk ni Docker para compilar LaTeX")

    # Figures are resolved before any compiler starts. A figure LaTeX cannot
    # open is a fatal error, and the Docker fallback cannot see an absolute
    # host path at all — both are far clearer here than inside a transcript.
    if config.body_path.exists():
        figure_errors = validate_figure_paths(
            config.body_path.read_text(encoding="utf-8"),
            build_dir,
            docker_mount=docker_mount_root(config) if docker_engine else None,
        )
        if figure_errors:
            raise SystemExit("Errores de figuras:\n- " + "\n- ".join(figure_errors))

    # The transcript is kept so a failure can show what LaTeX actually said.
    transcripts: list[str] = []

    def compile_step(command: list[str], cwd: Path) -> None:
        completed = run(command, cwd=cwd, check=False)
        transcripts.append(completed.stdout or "")

    if engine:
        compile_step([engine, "-lualatex", "-interaction=nonstopmode", "-halt-on-error", config.tex_path.name], build_dir)
    elif latex_engine:
        compile_step([latex_engine, "-interaction=nonstopmode", "-halt-on-error", config.tex_path.name], build_dir)
        if config.bib_path and shutil.which("biber"):
            compile_step(["biber", config.tex_path.stem], build_dir)
        elif config.bib_path and shutil.which("bibtex"):
            compile_step(["bibtex", config.tex_path.stem], build_dir)
        compile_step([latex_engine, "-interaction=nonstopmode", "-halt-on-error", config.tex_path.name], build_dir)
        compile_step([latex_engine, "-interaction=nonstopmode", "-halt-on-error", config.tex_path.name], build_dir)
    else:
        compile_step(docker_compile_command(config), config.folder)

    built_pdf = build_dir / f"{config.tex_path.stem}.pdf"
    if not built_pdf.exists():
        log_path = build_dir / f"{config.tex_path.stem}.log"
        transcript = "\n".join(part for part in transcripts if part.strip())
        if not transcript.strip() and log_path.exists():
            transcript = log_path.read_text(encoding="utf-8", errors="replace")
        raise SystemExit(compilation_failure_message(built_pdf, log_path, transcript))
    config.pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if not is_same_file(built_pdf, config.pdf_path):
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
