"""Tests for the ACD report template (aa-acd-templates T2, S1/S3/S4/S5/S6).

`format: acd` ("Aprendizaje en Contacto con el Docente") renders the approved
ACD-B session record sheet: IBM Plex Sans with IBM Plex Mono spaced-caps
labels, graphite and brick red accents, a header with the faculty logo and the
record identification, a generated session block, the fixed ACD sections and
annexes after the IEEE bibliography.

These tests pin:
  1. the template file, its placeholders and the approved design facts;
  2. render_tex output: session block (row order, escaping, topic, date,
     group members), the ACD label, and the annexes-after-bibliography slot;
  3. selection: the default template for `format: acd` and the metadata and
     section validation behind `ReportConfig.load` / `metadata_validation`;
  4. S6: APE selection and annex placement stay exactly as they were.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import build_latex_report  # noqa: E402
import course_profile  # noqa: E402
from report_config import ReportConfig  # noqa: E402
from validate_report import metadata_validation  # noqa: E402

ACD_TEMPLATE = ROOT / "templates" / "acd-report.tex"
APE_TEMPLATE = ROOT / "templates" / "ape-report.tex"

ACD_PLACEHOLDERS = (
    "{{ACD_LABEL}}",
    "{{ACD_SESSION_BLOCK}}",
    "{{ACD_FOOTER}}",
    "{{APE_LOGO_PATH}}",
    "{{BODY}}",
    "{{BIBLATEX_OPTIONS}}",
    "{{BIB_FILE}}",
    "{{HAS_BIB}}",
    "{{PRINT_BIBLIOGRAPHY}}",
    "{{AFTER_BIBLIOGRAPHY}}",
    "{{FRONT_MATTER}}",
    "{{AI_DECLARATION}}",
)

# The session block cells, in the approved mockup's reading order:
# (label printed above the value, metadata key that fills it).
SESSION_CELLS = (
    ("Tema de la sesión", "title"),
    ("Fecha de la sesión", "date"),
    ("Horario", "schedule"),
    ("Lugar", "place"),
    ("Asignatura", "subject"),
    ("Ciclo / paralelo", "cycle"),
    ("Unidad", "unit"),
    ("Docente", "teacher"),
    ("Estudiante(s)", "student"),
    ("ACD Nro. · tiempo en sílabo", "planned_time"),
    ("Resultado de aprendizaje de la unidad", "learning_outcome"),
)

ACD_HEADINGS = (
    "Objetivo(s)",
    "Síntesis de contenidos abordados",
    "Actividades desarrolladas en clase",
    "Análisis / reflexión",
    "Conclusiones",
)

BASE_RAW = {
    "type": "technical_report",
    "backend": "latex",
    "output": "pdf",
    "pdf": "build/report.pdf",
    "body": "body.md",
    "format": "acd",
}

SOURCE_BIB = """@book{fuente2026,
  author = {Autor, Ana},
  title = {Fundamentos de APIs REST},
  publisher = {Editorial Universitaria},
  year = {2026},
}
"""


def full_acd_metadata() -> dict:
    return {
        "title": "Diseño de APIs REST con FastAPI",
        "subject": "Desarrollo Basado en Plataformas",
        "teacher": "Ing. Marcela Ríos",
        "student": "Camila Jaramillo",
        "date": "Martes 6 de octubre de 2026",
        "cycle": "Quinto",
        "unit": "Unidad 2: Servicios web",
        "learning_outcome": "Diseña servicios web REST",
        "practice_number": "4",
        "schedule": "10:00 – 11:40 · 100 min",
        "place": "Laboratorio de Cómputo 3",
        "planned_time": "2 horas",
    }


def default_acd_body() -> str:
    parts = [f"# {heading}\n\nContenido de {heading}.\n" for heading in ACD_HEADINGS]
    # A citation so the IEEE bibliography actually prints (emission is
    # citation-driven, #26).
    parts.insert(1, "\nSegún la literatura [@fuente2026].\n")
    parts.append("# Anexos\n\nContenido de anexos.\n")
    return "\n".join(parts)


def make_render_config(
    tmp_path: Path,
    raw: dict | None = None,
    body: str | None = None,
    metadata: dict | None = None,
) -> ReportConfig:
    folder = tmp_path / "r"
    folder.mkdir(parents=True, exist_ok=True)
    written = dict(BASE_RAW)
    written.update(raw or {})
    written["metadata"] = metadata if metadata is not None else full_acd_metadata()
    (folder / "report.yml").write_text(yaml.safe_dump(written), encoding="utf-8")
    (folder / "body.md").write_text(
        body if body is not None else default_acd_body(), encoding="utf-8"
    )
    (folder / "sources.bib").write_text(SOURCE_BIB, encoding="utf-8")
    return ReportConfig.load(folder)


def render(tmp_path: Path, **kwargs) -> str:
    return build_latex_report.render_tex(make_render_config(tmp_path, **kwargs))


def cell_of(tex: str, label: str) -> str:
    """The generated ``\\acdcell{label}{value}`` text, from its label to the cell end."""
    start = tex.index(rf"\acdcell{{{label}}}")
    return tex[start: start + 400]


# ---------------------------------------------------------------------------
# The template itself
# ---------------------------------------------------------------------------


def test_acd_template_exists() -> None:
    assert ACD_TEMPLATE.is_file(), "templates/acd-report.tex must exist"


@pytest.fixture(scope="module")
def acd_template() -> str:
    return ACD_TEMPLATE.read_text(encoding="utf-8")


@pytest.mark.parametrize("placeholder", ACD_PLACEHOLDERS)
def test_acd_template_exposes_placeholder(acd_template: str, placeholder: str) -> None:
    assert placeholder in acd_template, f"acd template must expose {placeholder}"


@pytest.mark.parametrize("snippet", ["hyperref", "Needspace", "onehalfspacing", "parindent"])
def test_acd_template_satisfies_latex_validator(acd_template: str, snippet: str) -> None:
    assert snippet in acd_template, (
        f"validate_report.py greps the generated .tex for {snippet!r}"
    )


def test_acd_template_has_no_cover_page(acd_template: str) -> None:
    assert "titlepage" not in acd_template, "the session sheet has no cover page"


def test_acd_template_carries_the_approved_design(acd_template: str) -> None:
    assert "IBMPlexSans" in acd_template and "IBMPlexMono" in acd_template
    assert "9C2F2A" in acd_template, "brick red accent from the faculty crest"
    assert "20242A" in acd_template, "graphite ink"
    assert "FEIRNNR · CARRERA DE COMPUTACIÓN" in acd_template
    assert "REGISTRO DE SESIÓN" in acd_template
    assert "Aprendizaje en Contacto" in acd_template
    assert "fancyhdr" in acd_template, "header and running footer repeat on every page"
    assert r"\pageref{LastPage}" in acd_template, "footer shows page n / total"


def test_acd_template_falls_back_when_plex_is_not_installed(acd_template: str) -> None:
    """Like ape-report.tex: a missing face degrades to TeX Gyre, never a hard error."""
    assert r"\IfFontExistsTF" in acd_template
    assert "TeX Gyre Heros" in acd_template, "sans fallback shared with the other templates"
    assert "TeX Gyre Cursor" in acd_template, "monospace fallback for the labels"


def test_acd_template_keeps_ieee_citations(acd_template: str, tmp_path: Path) -> None:
    assert "{{BIBLATEX_OPTIONS}}" in acd_template
    assert "style=ieee" in render(tmp_path), "every format cites IEEE by default"


def test_acd_template_alias_resolves_to_the_acd_template() -> None:
    assert build_latex_report.TEMPLATE_ALIASES["acd"] == ACD_TEMPLATE
    assert build_latex_report.TEMPLATE_ALIASES["acd_report"] == ACD_TEMPLATE


def test_acd_bibliography_title() -> None:
    assert build_latex_report.BIBLIOGRAPHY_TITLES["acd"] == "Referencias"
    assert build_latex_report.BIBLIOGRAPHY_TITLES["acd_report"] == "Referencias"


# ---------------------------------------------------------------------------
# render_tex output
# ---------------------------------------------------------------------------


def test_acd_render_leaves_no_placeholder_unfilled(tmp_path: Path) -> None:
    tex = render(tmp_path)
    assert not re.findall(r"\{\{[A-Z_]+\}\}", tex), "every placeholder of the template is filled"


def test_acd_render_prints_the_acd_label(tmp_path: Path) -> None:
    tex = render(tmp_path)
    assert "ACD-4" in tex.split(r"\begin{document}")[0], "the header carries ACD-N"
    assert "ACD-4" in tex.split(r"\begin{document}")[1], "the kicker carries ACD-N"


def test_acd_render_label_does_not_double_an_authored_prefix(tmp_path: Path) -> None:
    tex = render(tmp_path, metadata={**full_acd_metadata(), "practice_number": "ACD-4"})
    assert "ACD-4" in tex and "ACD-ACD" not in tex


def test_acd_render_session_block_cells_in_order(tmp_path: Path) -> None:
    tex = render(tmp_path)
    positions = [tex.index(rf"\acdcell{{{label}}}") for label, _key in SESSION_CELLS]
    assert positions == sorted(positions), "the mockup's reading order is fixed"
    identification = tex.index(r"\section{Datos de identificación}")
    assert identification < positions[0], "the generated section is numbered first"
    assert positions[-1] < tex.index(r"\section{Objetivo(s)}"), "the block precedes the body"
    meta = full_acd_metadata()
    for label, key in SESSION_CELLS:
        assert meta[key] in cell_of(tex, label), f"{key} must fill the '{label}' cell"


def test_acd_render_prints_the_session_topic_and_date(tmp_path: Path) -> None:
    tex = render(tmp_path)
    assert "Diseño de APIs REST con FastAPI" in cell_of(tex, "Tema de la sesión")
    assert "Martes 6 de octubre de 2026" in cell_of(tex, "Fecha de la sesión")


def test_acd_render_joins_cycle_parallel_and_acd_number(tmp_path: Path) -> None:
    tex = render(tmp_path, metadata={**full_acd_metadata(), "parallel": "B"})
    assert "Quinto · B" in cell_of(tex, "Ciclo / paralelo")
    assert "ACD-4 · 2 horas" in cell_of(tex, "ACD Nro. · tiempo en sílabo")


def test_acd_render_session_block_escapes_latex_specials(tmp_path: Path) -> None:
    metadata = full_acd_metadata()
    metadata["student"] = "Ana & Beto_100%"
    metadata["place"] = "Lab #2 (norte)"
    metadata["title"] = "Tarifas $5 y {llaves}"
    tex = render(tmp_path, metadata=metadata)
    assert r"Ana \& Beto\_100\%" in tex
    assert r"Lab \#2 (norte)" in tex
    assert r"Tarifas \$5 y \{llaves\}" in tex


def test_acd_render_flattens_multiline_values(tmp_path: Path) -> None:
    metadata = full_acd_metadata()
    metadata["learning_outcome"] = "Diseña servicios\nweb REST"
    tex = render(tmp_path, metadata=metadata)
    assert "Diseña servicios web REST" in cell_of(tex, "Resultado de aprendizaje de la unidad")


def test_acd_group_report_lists_every_member(tmp_path: Path) -> None:
    members = ["Ana Pérez", "Luis Mora", "Camila Jaramillo"]
    tex = render(tmp_path, metadata={**full_acd_metadata(), "members": members})
    cell = cell_of(tex, "Estudiante(s)")
    assert all(name in cell for name in members), "a group report names every member"


def test_acd_individual_report_keeps_the_student(tmp_path: Path) -> None:
    tex = render(tmp_path)
    assert "Camila Jaramillo" in cell_of(tex, "Estudiante(s)")


def test_acd_footer_names_the_student_and_the_subject(tmp_path: Path) -> None:
    tex = render(tmp_path)
    footer = tex[tex.index(r"\fancyfoot[L]"):].split("\n")[0]
    assert "Camila Jaramillo" in footer and "Desarrollo Basado en Plataformas" in footer


def test_acd_render_fills_the_logo_path(tmp_path: Path) -> None:
    assert build_latex_report.APE_LOGO_FILENAME in render(tmp_path)


def test_acd_render_annexes_move_after_the_bibliography(tmp_path: Path) -> None:
    tex = render(tmp_path)
    last_section = tex.index("Contenido de Conclusiones")
    bibliography = tex.index(r"\printbibliography[title={Referencias}]")
    annexes = tex.index("Contenido de anexos")
    assert last_section < bibliography < annexes, "Anexos must render after the bibliography"
    assert tex.index(r"\section{Anexos}") > bibliography


def test_acd_render_without_annexes_keeps_the_body_whole(tmp_path: Path) -> None:
    """Anexos is optional for ACD: nothing to relocate, nothing invented."""
    body = default_acd_body().split("# Anexos")[0]
    tex = render(tmp_path, body=body)
    assert "Contenido de Conclusiones" in tex
    assert r"\section{Anexos}" not in tex


def test_acd_render_renders_markdown_tables_for_the_activity_log(tmp_path: Path) -> None:
    body = default_acd_body().replace(
        "Contenido de Actividades desarrolladas en clase.",
        "| Min. | Actividad | Modalidad | Producto |\n|---|---|---|---|\n"
        "| 0–10 | Exposición del docente | Expositiva | Apuntes |\n",
    )
    tex = render(tmp_path, body=body)
    assert "Exposición del docente" in tex and r"\begin{xltabular}" in tex


# ---------------------------------------------------------------------------
# Label column: Pandoc definition lists (opt-in per template)
# ---------------------------------------------------------------------------

DEFINITIONS = """General
: Aplicar los principios de *REST* & más.

Específico 1
: Identificar recursos
  y asignarles URIs.
Específico 2
: Elegir el verbo HTTP.
"""


def test_definition_lists_become_description_items_when_enabled() -> None:
    tex = build_latex_report.markdown_to_latex(DEFINITIONS, definition_lists=True)
    assert tex.count(r"\begin{description}") == 1, "one run of items is one environment"
    assert r"\item[{General}] Aplicar los principios de \emph{REST} \& más." in tex
    assert r"\item[{Específico 1}] Identificar recursos y asignarles URIs." in tex
    assert r"\item[{Específico 2}] Elegir el verbo HTTP." in tex
    assert tex.rstrip().endswith(r"\end{description}")


def test_definition_lists_keep_other_output_unchanged_by_default() -> None:
    """Without the opt-in the same lines render exactly as before: one paragraph."""
    default = build_latex_report.markdown_to_latex(DEFINITIONS)
    assert default == build_latex_report.markdown_to_latex(DEFINITIONS, definition_lists=False)
    assert "description" not in default
    assert "General : Aplicar" in default


def test_definition_lists_support_a_blank_line_between_term_and_definition() -> None:
    tex = build_latex_report.markdown_to_latex("Recursos\n\n: Sustantivos en plural.\n", definition_lists=True)
    assert r"\item[{Recursos}] Sustantivos en plural." in tex


def test_definition_lists_gather_several_definitions_of_one_term() -> None:
    tex = build_latex_report.markdown_to_latex("Verbo\n: GET\n: POST\n", definition_lists=True)
    assert tex.count(r"\item[") == 1 and "GET" in tex and "POST" in tex


def test_definition_lists_leave_plain_paragraphs_and_blocks_alone() -> None:
    source = "Un párrafo normal.\n\n- una lista\n\n# Título\n\nOtro párrafo\ncon dos líneas.\n"
    assert build_latex_report.markdown_to_latex(source, definition_lists=True) == (
        build_latex_report.markdown_to_latex(source)
    )


def test_definition_lists_escape_the_term() -> None:
    tex = build_latex_report.markdown_to_latex("100% [1] _x_\n: Valor.\n", definition_lists=True)
    assert r"\item[{100\% [1] \_x\_}] Valor." in tex


def test_acd_template_styles_the_description_as_a_label_column(acd_template: str) -> None:
    assert r"\setlist[description]" in acd_template
    assert "labelwidth" in acd_template and "labelsep" in acd_template


def test_acd_render_turns_definition_lists_into_the_label_column(tmp_path: Path) -> None:
    body = default_acd_body().replace("Contenido de Objetivo(s).", DEFINITIONS)
    tex = render(tmp_path, body=body)
    assert r"\item[{General}] Aplicar los principios de" in tex
    assert tex.index(r"\section{Objetivo(s)}") < tex.index(r"\begin{description}")


def test_acd_annexes_also_render_definition_lists(tmp_path: Path) -> None:
    body = default_acd_body().replace("Contenido de anexos.", "Anexo A\n: Código del taller.")
    tex = render(tmp_path, body=body)
    assert tex.index(r"\printbibliography") < tex.index(r"\item[{Anexo A}]")


def test_other_templates_do_not_get_definition_lists(tmp_path: Path) -> None:
    body = default_acd_body().replace("Contenido de Objetivo(s).", DEFINITIONS)
    tex = render(tmp_path, raw={"format": "aa"}, body=body)
    assert r"\item[{General}]" not in tex and "General : Aplicar" in tex


# ---------------------------------------------------------------------------
# Selection and validation
# ---------------------------------------------------------------------------


def rendered_template_name(config: ReportConfig) -> str:
    return build_latex_report.resolve_template(
        build_latex_report.template_key_for(config)
    ).name


def test_acd_format_defaults_to_the_acd_template(tmp_path: Path) -> None:
    assert rendered_template_name(make_render_config(tmp_path)) == ACD_TEMPLATE.name


def test_explicit_template_still_beats_the_acd_default(tmp_path: Path) -> None:
    config = make_render_config(tmp_path, raw={"template": "plain"})
    assert rendered_template_name(config) == "plain-report.tex"


def test_report_config_accepts_the_acd_format(tmp_path: Path) -> None:
    config = make_render_config(tmp_path)
    assert config.format == "acd" and config.format_is_known
    assert set(SESSION_CELLS_KEYS) <= set(config.format_required_metadata)


SESSION_CELLS_KEYS = tuple(key for _label, key in SESSION_CELLS) + ("practice_number",)


def test_acd_requires_the_session_fields_and_no_omit_knob(tmp_path: Path) -> None:
    config = make_render_config(tmp_path, raw={"ape_omit_fields": ["place"]})
    assert "place" in config.format_required_metadata, "ape_omit_fields belongs to APE only"


def test_acd_metadata_aliases_resolve_the_session_fields(tmp_path: Path) -> None:
    config = make_render_config(
        tmp_path,
        metadata={
            "tema": "Diseño de APIs REST",
            "asignatura": "Plataformas",
            "docente": "Ing. Ríos",
            "estudiante": "Camila",
            "fecha": "6 de octubre",
            "ciclo": "Quinto",
            "unidad": "Unidad 2",
            "resultado_aprendizaje": "Diseña APIs",
            "practica_numero": "4",
            "horario": "10:00",
            "lugar": "Lab 3",
            "tiempo_planificado": "2 horas",
        },
    )
    assert metadata_validation(config).errors == []


def test_acd_complete_report_validates_clean(tmp_path: Path) -> None:
    result = metadata_validation(make_render_config(tmp_path))
    assert result.errors == []


def test_acd_missing_session_fields_are_reported(tmp_path: Path) -> None:
    metadata = full_acd_metadata()
    for key in ("schedule", "place", "practice_number", "planned_time"):
        del metadata[key]
    errors = metadata_validation(make_render_config(tmp_path, metadata=metadata)).errors
    assert any(
        "Metadata incompleta para el formato 'acd'" in error
        and all(key in error for key in ("schedule", "place", "practice_number", "planned_time"))
        for error in errors
    ), errors


def test_acd_placeholder_values_count_as_missing(tmp_path: Path) -> None:
    """The session block prints the fields verbatim, so a fill-in mark is a gap."""
    metadata = {**full_acd_metadata(), "place": "XXX", "schedule": "[...]"}
    errors = metadata_validation(make_render_config(tmp_path, metadata=metadata)).errors
    assert any(
        "Metadata incompleta para el formato 'acd'" in error and "place" in error and "schedule" in error
        for error in errors
    ), errors


def test_acd_wrong_section_order_is_reported(tmp_path: Path) -> None:
    headings = list(ACD_HEADINGS)
    headings[1], headings[2] = headings[2], headings[1]
    body = "\n".join(f"# {h}\n\nContenido.\n" for h in headings)
    errors = metadata_validation(make_render_config(tmp_path, body=body)).errors
    assert any("fuera del orden requerido por el formato ACD" in error for error in errors), errors


def test_acd_missing_sections_are_reported(tmp_path: Path) -> None:
    body = "# Objetivo(s)\n\nContenido.\n"
    errors = metadata_validation(make_render_config(tmp_path, body=body)).errors
    assert any("Faltan secciones del formato ACD" in error for error in errors), errors


def test_acd_is_a_practice_format_for_the_course_folder() -> None:
    assert "acd" in course_profile.PRACTICE_FORMATS


# ---------------------------------------------------------------------------
# S6: APE is unchanged
# ---------------------------------------------------------------------------


def ape_body() -> str:
    headings = (
        "Objetivo(s) de la Práctica",
        "Materiales, Reactivos, Equipos y Herramientas",
        "Procedimiento / Metodología Ejecutada",
        "Resultados",
        "Preguntas de Control",
        "Conclusiones",
        "Recomendaciones",
    )
    parts = [f"# {heading}\n\nContenido de {heading}.\n" for heading in headings]
    parts.insert(1, "\nSegún la literatura [@fuente2026].\n")
    parts.append("# Anexos\n\nContenido de anexos.\n")
    return "\n".join(parts)


def test_ape_keeps_its_template_and_annex_placement(tmp_path: Path) -> None:
    metadata = {
        **full_acd_metadata(),
        "practice_type": "Experimental",
        "title": "Simulación de una fila de espera",
    }
    config = make_render_config(tmp_path, raw={"format": "ape"}, body=ape_body(), metadata=metadata)
    assert rendered_template_name(config) == APE_TEMPLATE.name
    tex = build_latex_report.render_tex(config)
    assert "Reporte Técnico de Actividades Práctico-Experimentales Nro. 4" in tex
    last_section = tex.index("Contenido de Recomendaciones")
    bibliography = tex.index(r"\printbibliography[title={Bibliografía / Referencias}]")
    annexes = tex.index("Contenido de anexos")
    assert last_section < bibliography < annexes
    assert r"\acdcell{" not in tex and "REGISTRO DE SESIÓN" not in tex, "no ACD machinery leaks into APE"


def test_non_annex_templates_still_receive_the_whole_body(tmp_path: Path) -> None:
    config = make_render_config(tmp_path, raw={"format": "aa"})
    assert rendered_template_name(config) == "unl-report.tex"
    tex = build_latex_report.render_tex(config)
    assert tex.index("Contenido de anexos") < tex.index(r"\printbibliography"), (
        "the AA/UNL template keeps the annexes in body order until T3 gives it a slot"
    )
