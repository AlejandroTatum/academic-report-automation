"""Tests for automatic PDF publication configuration."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from conftest import _bibliography  # noqa: E402
from output_router import subject_slug  # noqa: E402
from report_config import (  # noqa: E402
    GLOBAL_OUTPUTS,
    ReportConfig,
    load_report_config,
    resolve_documents_root,
    targets_local_outputs,
    versioned_pdf_pattern,
)


def _write_report(folder: Path, route: str, title: str) -> Path:
    folder.mkdir(parents=True)
    (folder / "report.yml").write_text(
        f"route: {route}\ntype: essay\noutput: pdf\nmetadata:\n  title: {title!r}\n",
        encoding="utf-8",
    )
    return folder


@pytest.mark.parametrize(
    ("route", "category"),
    [
        ("technical", "Tecnicos"),
        ("academic", "Academicos"),
        ("project", "Proyectos"),
        ("business", "Profesionales"),
        ("other", "Otros"),
    ],
)
def test_publication_category_is_derived_from_confirmed_route(
    tmp_path: Path, route: str, category: str
) -> None:
    config = load_report_config(_write_report(tmp_path / route, route, "Informe"))

    assert config.publication_category == category


def test_publication_slug_is_stable_ascii_from_confirmed_title(tmp_path: Path) -> None:
    config = load_report_config(
        _write_report(tmp_path / "report", "technical", "Análisis: Gestión Ñandú 2026!")
    )

    assert config.document_slug == "analisis-gestion-nandu-2026"


def test_delivery_pdf_is_not_required_or_interpreted(tmp_path: Path) -> None:
    folder = _write_report(tmp_path / "report", "technical", "Informe")
    (folder / "report.yml").write_text(
        (folder / "report.yml").read_text(encoding="utf-8") + "delivery_pdf: /tmp/ignored.pdf\n",
        encoding="utf-8",
    )

    config = load_report_config(folder)

    assert not hasattr(config, "delivery_pdf")


# ---------------------------------------------------------------------------
# Subject-scoped academic delivery paths (course-deliverables-hierarchy T1)
# ---------------------------------------------------------------------------


def _write_delivery_report(
    folder: Path, route: str, title: str, *, subject: str | None = None, subject_key: str = "subject"
) -> Path:
    """Write a report.yml with a confirmed title and an optional confirmed subject."""
    folder.mkdir(parents=True)
    lines = [f"route: {route}", "type: essay", "output: pdf", "metadata:", f"  title: {title!r}"]
    if subject is not None:
        lines.append(f"  {subject_key}: {subject!r}")
    (folder / "report.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return folder


def test_academic_delivery_folder_inserts_the_canonical_subject_level(tmp_path: Path) -> None:
    """Academic delivery is Academicos/<canonical subject>/<document-slug>/ under the root."""
    folder = _write_delivery_report(tmp_path / "report", "academic", "Informe", subject="Sistemas Operativos")
    config = load_report_config(folder)
    root = tmp_path / "Documents"

    assert config.delivery_folder(root) == root / "Academicos" / "sistemas-operativos" / "informe"
    assert config.delivery_subject_slug == "sistemas-operativos"


def test_canonical_subject_aliases_share_one_delivery_folder(tmp_path: Path) -> None:
    """Alias spellings of the same course must agree on exactly one folder."""
    roots = []
    for name, subject in (
        ("primera", "Sistemas Operativos"),
        ("segunda", "Sistema operativo"),
        ("tercera", "Operating Systems"),
    ):
        folder = _write_delivery_report(tmp_path / name, "academic", "Informe", subject=subject)
        config = load_report_config(folder)
        assert config.delivery_subject_slug == "sistemas-operativos"
        roots.append(config.delivery_folder(tmp_path / "Documents"))

    assert roots[0] == roots[1] == roots[2]


def test_unknown_course_spelling_and_alias_disagree_by_design(tmp_path: Path) -> None:
    """TRIANGULATE: an unregistered spelling is its own course, not the alias.

    Without registration there is no evidence two spellings are one course, so
    the ASCII slug stands on its own instead of guessing an alias.
    """
    folder = _write_delivery_report(tmp_path / "report", "academic", "Informe", subject="sistemas operativos 2")
    config = load_report_config(folder)

    assert config.delivery_subject_slug == "sistemas-operativos-2"
    assert config.delivery_folder(tmp_path / "Documents") == (
        tmp_path / "Documents" / "Academicos" / "sistemas-operativos-2" / "informe"
    )


def test_nonacademic_delivery_keeps_the_flat_category_layout(tmp_path: Path) -> None:
    """A confirmed subject never scopes a non-academic route: Tecnicos/<slug>/ stays."""
    folder = _write_delivery_report(tmp_path / "report", "technical", "Informe", subject="Sistemas Operativos")
    config = load_report_config(folder)
    root = tmp_path / "Documents"

    assert config.delivery_subject_slug is None
    assert config.delivery_folder(root) == root / "Tecnicos" / "informe"


def test_academic_unknown_confirmed_subject_gets_its_own_ascii_slug_level(tmp_path: Path) -> None:
    """A newly named course still gets its own delivery folder.

    The confirmed subject is data: when the shared alias vocabulary does not
    know it, the level is the subject's own stable ASCII slug — never the flat
    legacy location and never an invented generic bucket.
    """
    folder = _write_delivery_report(tmp_path / "report", "academic", "Informe", subject="Fisica")
    config = load_report_config(folder)

    assert config.delivery_subject_slug == "fisica"
    assert config.delivery_folder(tmp_path / "Documents") == (
        tmp_path / "Documents" / "Academicos" / "fisica" / "informe"
    )


def test_academic_ascii_slug_strips_accents_and_case(tmp_path: Path) -> None:
    """TRIANGULATE: the derived level is stable ASCII, like every other slug."""
    folder = _write_delivery_report(tmp_path / "report", "academic", "Informe", subject="Física Cuántica")
    config = load_report_config(folder)

    assert config.delivery_subject_slug == "fisica-cuantica"


def test_academic_without_subject_keeps_flat_and_invents_no_bucket(tmp_path: Path) -> None:
    """Only a missing confirmed subject has no level: no generic fallback folder.

    The academic route's own validation refuses a report without a subject
    before delivery; the delivery API answers flat rather than inventing a
    'General' bucket for that shape.
    """
    folder = _write_delivery_report(tmp_path / "report", "academic", "Informe")
    config = load_report_config(folder)

    assert config.delivery_subject_slug is None
    assert config.delivery_folder(tmp_path / "Documents") == (
        tmp_path / "Documents" / "Academicos" / "informe"
    )


def test_delivery_subject_slug_reads_the_asignatura_alias(tmp_path: Path) -> None:
    """The confirmed subject may be written as `asignatura:`; the slug is the same."""
    folder = _write_delivery_report(
        tmp_path / "report", "academic", "Informe",
        subject="Sistemas Operativos", subject_key="asignatura",
    )
    config = load_report_config(folder)

    assert config.delivery_subject_slug == "sistemas-operativos"


def test_delivery_folder_defaults_to_the_home_documents_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Without an override the delivery root is ~/Documents, exactly as before."""
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    folder = _write_delivery_report(tmp_path / "report", "academic", "Informe", subject="Sistemas Operativos")
    config = load_report_config(folder)

    assert resolve_documents_root(None) == home / "Documents"
    assert config.delivery_folder(None) == home / "Documents" / "Academicos" / "sistemas-operativos" / "informe"
    override = tmp_path / "otra-raiz"
    assert resolve_documents_root(override) == override


def test_versioned_pdf_pattern_is_the_shared_version_contract() -> None:
    """Publisher and doc_status must match the exact same <slug>-vNNN.pdf names."""
    pattern = versioned_pdf_pattern("informe")

    assert pattern.match("informe-v001.pdf")
    assert pattern.match("informe-v012.pdf")
    assert not pattern.match("informe.pdf")
    assert not pattern.match("informe-v1.pdf")
    assert not pattern.match("otro-v001.pdf")
    assert pattern.match("informe-v002.pdf").group(1) == "002"


# ---------------------------------------------------------------------------
# Declared bibliography delivery (course-deliverables-hierarchy T2)
# ---------------------------------------------------------------------------


def _write_optin_report(folder: Path, option: object = True, bib_line: str | None = None) -> Path:
    """Write an academic report with the deliver_bibliography option set verbatim."""
    folder = _write_delivery_report(folder, "academic", "Informe")
    lines = [f"deliver_bibliography: {option}"]
    if bib_line:
        lines.append(bib_line)
    report = folder / "report.yml"
    report.write_text(report.read_text(encoding="utf-8") + "\n".join(lines) + "\n", encoding="utf-8")
    return folder


def test_deliver_bibliography_defaults_to_false(tmp_path: Path) -> None:
    """Without the opt-in key the bibliography is never a declared deliverable."""
    folder = _write_delivery_report(tmp_path / "report", "academic", "Informe")
    config = load_report_config(folder)

    assert config.deliver_bibliography is False
    assert config.delivery_bibliography() is None


def test_deliver_bibliography_is_a_strict_boolean(tmp_path: Path) -> None:
    """Only YAML true/false is accepted; strings and numbers are config errors."""
    config = ReportConfig(
        folder=tmp_path, raw={"deliver_bibliography": "yes"}, academic_format={}
    )
    with pytest.raises(ValueError, match="deliver_bibliography"):
        _ = config.deliver_bibliography

    folder = _write_optin_report(tmp_path / "report", option='"true"')
    with pytest.raises(SystemExit, match="deliver_bibliography"):
        load_report_config(folder)


def test_delivery_bibliography_resolves_the_declared_source(tmp_path: Path) -> None:
    """The opt-in delivers the bibliography the config already selects."""
    folder = _write_optin_report(tmp_path / "report")
    _bibliography(folder)
    config = load_report_config(folder)

    assert config.delivery_bibliography() == folder / "sources.bib"

    custom = _write_optin_report(tmp_path / "custom", bib_line="bibliography: refs/fuentes.bib")
    _bibliography(custom / "refs", name="fuentes.bib")
    custom_config = load_report_config(custom)

    assert custom_config.delivery_bibliography() == custom / "refs" / "fuentes.bib"


def test_delivery_bibliography_refuses_missing_or_non_bib_source(tmp_path: Path) -> None:
    """A declared source that is missing or not a .bib file is a config refusal."""
    folder = _write_optin_report(tmp_path / "missing")
    config = load_report_config(folder)
    with pytest.raises(ValueError, match="no existe o no es un archivo regular"):
        config.delivery_bibliography()

    wrong = _write_optin_report(tmp_path / "wrong", bib_line="bibliography: notas.txt")
    (wrong / "notas.txt").write_text("notas", encoding="utf-8")
    with pytest.raises(ValueError, match="debe ser un archivo .bib"):
        load_report_config(wrong).delivery_bibliography()


def test_delivery_bibliography_refuses_empty_or_malformed_bib(tmp_path: Path) -> None:
    """An empty file or one with zero BibTeX entries is refused, not exported."""
    empty = _write_optin_report(tmp_path / "empty")
    _bibliography(empty, text="")
    with pytest.raises(ValueError, match="vac"):
        load_report_config(empty).delivery_bibliography()

    malformed = _write_optin_report(tmp_path / "malformed")
    _bibliography(malformed, text="esto no es BibTeX\n")
    with pytest.raises(ValueError, match="no tiene entradas BibTeX"):
        load_report_config(malformed).delivery_bibliography()


def test_delivery_bibliography_refuses_paths_outside_the_work_folder(tmp_path: Path) -> None:
    """Traversal, absolute paths and symlink escapes never deliver an outside file."""
    escape = tmp_path / "escape.bib"
    _bibliography(tmp_path, name="escape.bib")

    traversal = _write_optin_report(tmp_path / "traversal", bib_line="bibliography: ../escape.bib")
    with pytest.raises(ValueError, match="dentro de la carpeta del reporte"):
        load_report_config(traversal).delivery_bibliography()

    absolute = _write_optin_report(tmp_path / "absolute", bib_line=f"bibliography: {escape}")
    with pytest.raises(ValueError, match="dentro de la carpeta del reporte"):
        load_report_config(absolute).delivery_bibliography()

    symlinked = _write_optin_report(tmp_path / "symlink", bib_line="bibliography: enlace.bib")
    (symlinked / "enlace.bib").symlink_to(escape)
    with pytest.raises(ValueError, match="dentro de la carpeta del reporte"):
        load_report_config(symlinked).delivery_bibliography()


# ---------------------------------------------------------------------------
# Derived default output path (no `pdf:`/`docx:` declared)
# ---------------------------------------------------------------------------


def _write_academic_report(folder: Path, title: str, subject: str) -> Path:
    folder.mkdir(parents=True)
    (folder / "report.yml").write_text(
        "route: academic\ntype: essay\noutput: pdf\n"
        f"metadata:\n  title: {title!r}\n  subject: {subject!r}\n"
        "  teacher: Docente\n  student: Estudiante\n  date: '2026-01-01'\n",
        encoding="utf-8",
    )
    return folder


def test_technical_route_without_pdf_derives_under_its_route_category(tmp_path: Path) -> None:
    config = load_report_config(_write_report(tmp_path / "report", "technical", "Informe Tecnico"))

    assert config.pdf_path == GLOBAL_OUTPUTS / "tecnicos" / "informe-tecnico.pdf"
    assert not targets_local_outputs(config)


def test_technical_route_without_docx_derives_under_its_route_category(tmp_path: Path) -> None:
    config = load_report_config(_write_report(tmp_path / "report", "technical", "Informe Tecnico"))

    assert config.docx_path == GLOBAL_OUTPUTS / "tecnicos" / "informe-tecnico.docx"


def test_academic_route_without_pdf_derives_under_the_known_subject(tmp_path: Path) -> None:
    folder = _write_academic_report(tmp_path / "report", "Informe SO", "Sistemas Operativos")

    config = load_report_config(folder)

    expected_slug = subject_slug("Sistemas Operativos")
    assert expected_slug == "sistemas-operativos"
    assert config.pdf_path == GLOBAL_OUTPUTS / expected_slug / "informe-so.pdf"


def test_academic_route_without_docx_derives_under_the_known_subject(tmp_path: Path) -> None:
    folder = _write_academic_report(tmp_path / "report", "Informe SO", "Sistemas Operativos")

    config = load_report_config(folder)

    assert config.docx_path == GLOBAL_OUTPUTS / "sistemas-operativos" / "informe-so.docx"


def test_explicit_pdf_path_keeps_resolving_relative_to_the_folder(tmp_path: Path) -> None:
    folder = _write_report(tmp_path / "report", "technical", "Informe")
    (folder / "report.yml").write_text(
        (folder / "report.yml").read_text(encoding="utf-8") + "pdf: build/informe.pdf\n",
        encoding="utf-8",
    )

    config = load_report_config(folder)

    assert config.pdf_path == folder.resolve() / "build" / "informe.pdf"


def test_explicit_docx_path_keeps_resolving_relative_to_the_folder(tmp_path: Path) -> None:
    folder = _write_report(tmp_path / "report", "technical", "Informe")
    (folder / "report.yml").write_text(
        (folder / "report.yml").read_text(encoding="utf-8") + "docx: build/informe.docx\n",
        encoding="utf-8",
    )

    config = load_report_config(folder)

    assert config.docx_path == folder.resolve() / "build" / "informe.docx"
