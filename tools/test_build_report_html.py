"""Behaviour tests for the HTML/WeasyPrint branch (``tools/build_report.py``).

Every assertion here is made against the produced HTML string, never against
internal helpers, because the defects being guarded are all things a reader of
the rendered document can see:

- D-09: the academic header/metadata block must be opt-in. A document that does
  not declare itself academic must not be stamped with empty institutional
  labels, and a declared field that is absent must not leave an orphan label.
- D-17a: image references are written relative to the Markdown file, so they
  have to be rewritten when the HTML lands in a different directory. A missing
  image must be reported, not shipped as a silently broken page.
- D-17b: this branch has no bibliography engine. Citation syntax must not reach
  the reader as raw noise; it is marked and announced instead.
- D-14: ``---`` means "page break" to the LaTeX branch and "front-matter" to
  this one. Only a real key/value block at the very start counts as metadata;
  anything else renders as an ordinary horizontal rule.
- D-19: the README's project structure must name files that actually exist.

No LaTeX, WeasyPrint, Node or network is required.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

# Make tools/ importable (same pattern as the other test modules here).
TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import build_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "templates" / "ensayo_unl.css"

ACADEMIC_LABELS = ("Nombre:", "Fecha:", "Paralelo:", "Asignatura:", "Docente:")


def write_md(directory: Path, text: str, name: str = "body.md") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


def render(md_path: Path, out_dir: Path | None = None) -> str:
    return build_report.render(md_path, CSS, out_dir or md_path.parent)


def image_sources(html_text: str) -> list[str]:
    return re.findall(r'<img[^>]*\bsrc="([^"]+)"', html_text)


# --------------------------------------------------------------------------
# D-09 — the academic block is opt-in
# --------------------------------------------------------------------------


def test_document_without_frontmatter_has_no_academic_furniture(tmp_path):
    md = write_md(tmp_path, "# Propósito\n\nEspecificar el contrato del router.\n")

    out = render(md)

    for label in ACADEMIC_LABELS:
        assert label not in out, f"orphan academic label leaked: {label}"
    assert 'class="meta"' not in out
    assert 'class="header"' not in out


def test_partial_academic_frontmatter_renders_only_declared_fields(tmp_path):
    md = write_md(
        tmp_path,
        '---\nasignatura: "Sistemas Operativos"\nnombre: "Alejandro Padilla"\n---\n\n# Tema\n\nTexto.\n',
    )

    out = render(md)

    assert "Asignatura:" in out
    assert "Nombre:" in out
    assert "Sistemas Operativos" in out
    # Fields the document never declared must not appear as empty labels.
    assert "Docente:" not in out
    assert "Paralelo:" not in out
    assert "Fecha:" not in out


def test_academic_block_can_be_switched_off_explicitly(tmp_path):
    md = write_md(
        tmp_path,
        '---\nuniversidad: "UNL"\ndocente: "Nombre Docente"\nacademico: false\n'
        'titulo: "Contrato del router"\n---\n\n# Alcance\n\nTexto.\n',
    )

    out = render(md)

    for label in ACADEMIC_LABELS:
        assert label not in out
    assert "UNL" not in out
    # The document title is not institutional furniture, so it survives.
    assert "Contrato del router" in out


def test_full_academic_frontmatter_still_renders_the_block(tmp_path):
    md = write_md(
        tmp_path,
        '---\nuniversidad: "Sample University"\nfacultad: "Faculty of Engineering"\n'
        'carrera: "Computer Science"\nasignatura: "Software Engineering"\n'
        'docente: "Teacher Name"\nnombre: "Student Name"\nfecha: "2026-05-10"\n'
        '---\n\n# Tema\n\nTexto.\n',
    )

    out = render(md)

    for label in ACADEMIC_LABELS[:1] + ACADEMIC_LABELS[3:]:
        assert label in out
    assert "Sample University" in out
    assert 'class="meta"' in out


def test_absent_report_title_leaves_no_empty_element(tmp_path):
    md = write_md(tmp_path, "# Solo cuerpo\n\nTexto.\n")

    out = render(md)

    # The CSS carries a `.report-title` rule, so assert on the element itself.
    assert '<div class="report-title">' not in out


# --------------------------------------------------------------------------
# D-17a — image paths resolve from the HTML output location
# --------------------------------------------------------------------------


def test_image_src_resolves_from_the_output_directory(tmp_path):
    image = tmp_path / "assets" / "generated" / "flujo.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"\x89PNG\r\n\x1a\n")
    md = write_md(
        tmp_path / "content" / "reports" / "doc",
        "# Arquitectura\n\n![Ruta de publicación](../../../assets/generated/flujo.png)\n",
    )
    out_dir = tmp_path / "outputs" / "html"

    out = render(md, out_dir)

    sources = image_sources(out)
    assert sources, "the figure lost its <img>"
    resolved = (out_dir / sources[0]).resolve()
    assert resolved == image.resolve(), f"src {sources[0]!r} does not resolve from {out_dir}"


def test_image_reference_relative_to_the_latex_build_dir_still_resolves(tmp_path):
    # build_latex_report.py resolves figure references from `<report>/build/`,
    # not from body.md, so real bodies carry paths that escape the report from
    # one level deeper. The HTML branch must find those too.
    content = tmp_path / "content"
    image = content / "assets" / "generated" / "flujo.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"\x89PNG\r\n\x1a\n")
    report = content / "reports" / "doc"
    (report / "build").mkdir(parents=True)
    md = write_md(report, "# Arquitectura\n\n![Ruta](../../../assets/generated/flujo.png)\n")
    out_dir = tmp_path / "html"

    out = render(md, out_dir)

    assert "Imagen no encontrada" not in out
    sources = image_sources(out)
    assert sources
    assert (out_dir / sources[0]).resolve() == image.resolve()


def test_absolute_urls_are_left_untouched(tmp_path):
    md = write_md(
        tmp_path,
        "# Figuras\n\n![Remota](https://example.com/a.png)\n\n![Incrustada](data:image/png;base64,AAAA)\n",
    )

    out = render(md, tmp_path / "elsewhere")

    sources = image_sources(out)
    assert "https://example.com/a.png" in sources
    assert "data:image/png;base64,AAAA" in sources


def test_missing_image_is_reported_instead_of_silently_broken(tmp_path):
    md = write_md(tmp_path, "# Arquitectura\n\n![Diagrama](figuras/ausente.png)\n")

    out = render(md, tmp_path / "out")

    assert "Imagen no encontrada" in out
    assert "figuras/ausente.png" in out
    # No <img> may point at a file that is not there.
    assert not [src for src in image_sources(out) if "ausente.png" in src]


# --------------------------------------------------------------------------
# D-17b — citation syntax is announced, never shipped as raw noise
# --------------------------------------------------------------------------


def test_citation_syntax_produces_a_visible_warning(tmp_path):
    md = write_md(
        tmp_path,
        "# Alcance\n\nNo cubre la compilación LaTeX [@padilla2026].\n",
    )

    out = render(md)

    assert "citation-unsupported" in out
    assert "padilla2026" in out
    assert "citas" in out.lower()
    assert "build_report_auto.py" in out


def test_citations_inside_code_fences_are_left_alone(tmp_path):
    md = write_md(tmp_path, "# Ejemplo\n\n```text\nclave = [@literal]\n```\n")

    out = render(md)

    assert "citation-unsupported" not in out
    assert "[@literal]" in out


def test_document_without_citations_has_no_warning_banner(tmp_path):
    md = write_md(tmp_path, "# Alcance\n\nTexto sin citas.\n")

    out = render(md)

    assert "build-warning" not in out


# --------------------------------------------------------------------------
# D-14 — `---` semantics cannot be confused with front-matter
# --------------------------------------------------------------------------


def test_dashes_in_the_middle_render_as_a_horizontal_rule(tmp_path):
    md = write_md(tmp_path, "# Primera\n\nTexto uno.\n\n---\n\n# Segunda\n\nTexto dos.\n")

    out = render(md)

    assert "<hr" in out
    assert 'class="meta"' not in out
    assert "Texto dos." in out


def test_leading_dashes_that_are_not_key_values_are_not_frontmatter(tmp_path):
    # A body.md written for the LaTeX branch, where `---` means \newpage.
    md = write_md(
        tmp_path,
        "---\n\nEsta prosa jamás fue metadata.\nSigue siendo prosa.\n\n---\n\n# Segunda página\n",
    )

    out = render(md)

    assert "Esta prosa jamás fue metadata." in out
    assert 'class="meta"' not in out


def test_real_frontmatter_at_the_start_is_still_parsed(tmp_path):
    md = write_md(tmp_path, '---\ntitulo: "Informe"\n---\n\n# Cuerpo\n\nTexto.\n')

    out = render(md)

    assert "Informe" in out
    assert "titulo:" not in out


# --------------------------------------------------------------------------
# D-19 — the README describes files that exist
# --------------------------------------------------------------------------


def test_readme_project_structure_lists_only_existing_paths():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    block = re.search(r"## Project Structure\s*```txt\n(.*?)```", readme, re.DOTALL)
    assert block, "the README lost its Project Structure block"

    names = set(re.findall(r"[\w.\-]+\.(?:py|css|tex|yml|yaml|md|svg|json|txt|sh)", block.group(1)))
    assert names, "the Project Structure block names no files at all"

    missing = [name for name in sorted(names) if not any(ROOT.rglob(name))]
    assert not missing, f"README names files that do not exist: {missing}"


def test_readme_points_at_the_canonical_pipeline_and_the_node_install():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "build_report_auto.py" in readme
    assert "npm install" in readme


# --------------------------------------------------------------------------
# End to end on the repository's own Quick Start input
# --------------------------------------------------------------------------


def test_sample_report_quick_start_renders_without_orphan_labels(tmp_path):
    md = ROOT / "examples" / "sample_report.md"
    if not md.exists():  # pragma: no cover - guarded by D-19 above
        pytest.skip("examples/sample_report.md is missing")

    out = render(md, tmp_path)

    assert "Sample University" in out
    assert "Student Name" in out
    assert "build-warning" not in out
