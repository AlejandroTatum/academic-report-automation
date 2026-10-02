"""Course profiles: front-matter match, default merge, delivery_dir template."""
from pathlib import Path

import pytest
import yaml

import course_profile
from report_config import load_report_config

PROFILE = """---
match:
  subject: Simulación
report_defaults:
  format: ape
  uncited_bibliography: true
  cover:
    required: false
delivery_dir_template: "/tmp/sim/unidad-{unit}/ape-{practice_number}-{slug}/documento/"
---
Prose body.
"""

REPORT = """# my report
route: academic
metadata:
  title: "Modelo de colas"
  subject: simulacion
  unit: "2"
  practice_number: "3"
"""


def _profiles(tmp_path: Path, *texts: str) -> Path:
    directory = tmp_path / "profiles"
    directory.mkdir()
    for index, text in enumerate(texts):
        (directory / f"p{index}.md").write_text(text, encoding="utf-8")
    return directory


def _folder(tmp_path: Path, text: str = REPORT) -> Path:
    folder = tmp_path / "report"
    folder.mkdir()
    (folder / "report.yml").write_text(text, encoding="utf-8")
    return folder


def _run(folder: Path, profiles: Path, *flags: str) -> int:
    return course_profile.main([str(folder), "--profiles", str(profiles), *flags])


def test_applies_defaults_and_delivery_dir_preserving_comments(tmp_path, capsys):
    folder = _folder(tmp_path)
    assert _run(folder, _profiles(tmp_path, PROFILE)) == 0
    text = (folder / "report.yml").read_text(encoding="utf-8")
    assert text.startswith(REPORT)
    data = yaml.safe_load(text)
    assert data["format"] == "ape" and data["uncited_bibliography"] is True
    assert data["cover"] == {"required": False}
    assert data["delivery_dir"] == "/tmp/sim/unidad-2/ape-3-modelo-de-colas/documento/"
    assert "format" in capsys.readouterr().out


def test_numeric_placeholders_use_the_bare_number(tmp_path):
    report = REPORT.replace('unit: "2"', 'unit: "U1: Introducción a la Simulación"').replace(
        'practice_number: "3"', 'practice_number: "01"')
    folder = _folder(tmp_path, report)
    assert _run(folder, _profiles(tmp_path, PROFILE)) == 0
    data = yaml.safe_load((folder / "report.yml").read_text(encoding="utf-8"))
    assert data["delivery_dir"] == "/tmp/sim/unidad-1/ape-1-modelo-de-colas/documento/"


def test_explicit_report_values_win(tmp_path):
    folder = _folder(tmp_path, REPORT + "format: libre\ncover:\n  required: true\ndelivery_dir: /x\n")
    assert _run(folder, _profiles(tmp_path, PROFILE)) == 0
    data = yaml.safe_load((folder / "report.yml").read_text(encoding="utf-8"))
    assert data["format"] == "libre"
    assert data["cover"] == {"required": True}
    assert data["delivery_dir"] == "/x"
    assert data["uncited_bibliography"] is True


def test_nested_default_is_added_to_existing_block(tmp_path):
    folder = _folder(tmp_path, REPORT + "cover:\n  logo_required: false\n")
    assert _run(folder, _profiles(tmp_path, PROFILE)) == 0
    data = yaml.safe_load((folder / "report.yml").read_text(encoding="utf-8"))
    assert data["cover"] == {"logo_required": False, "required": False}


def test_no_match_prints_no_profile_and_leaves_file(tmp_path, capsys):
    folder = _folder(tmp_path, REPORT.replace("simulacion", "Redes"))
    assert _run(folder, _profiles(tmp_path, PROFILE, "no front matter\n")) == 0
    assert "no profile" in capsys.readouterr().out
    assert (folder / "report.yml").read_text(encoding="utf-8") == REPORT.replace("simulacion", "Redes")


def test_several_matches_is_an_error(tmp_path):
    folder = _folder(tmp_path)
    assert _run(folder, _profiles(tmp_path, PROFILE, PROFILE)) == 2


def test_unresolved_placeholder_leaves_delivery_dir_unset(tmp_path, capsys):
    folder = _folder(tmp_path, REPORT.replace('  unit: "2"\n', ""))
    assert _run(folder, _profiles(tmp_path, PROFILE)) == 0
    data = yaml.safe_load((folder / "report.yml").read_text(encoding="utf-8"))
    assert "delivery_dir" not in data and data["format"] == "ape"
    assert "unit" in capsys.readouterr().out


def test_practice_number_falls_back_to_guide_facts(tmp_path):
    text = REPORT.replace('  practice_number: "3"\n', "") + "guide: guia.txt\n"
    folder = _folder(tmp_path, text)
    (folder / "guia.txt").write_text("Práctico experimental. Práctica Nro. 4", encoding="utf-8")
    assert _run(folder, _profiles(tmp_path, PROFILE)) == 0
    data = yaml.safe_load((folder / "report.yml").read_text(encoding="utf-8"))
    assert data["delivery_dir"].endswith("ape-4-modelo-de-colas/documento/")


def test_check_flag_does_not_write(tmp_path, capsys):
    folder = _folder(tmp_path)
    assert _run(folder, _profiles(tmp_path, PROFILE), "--check") == 0
    assert (folder / "report.yml").read_text(encoding="utf-8") == REPORT
    assert "ape" in capsys.readouterr().out


def test_real_simulacion_profile_applies_valid_keys(tmp_path):
    folder = _folder(tmp_path, REPORT.replace("simulacion", "Simulación"))
    assert course_profile.main([str(folder)]) == 0
    (folder / "sources.bib").touch()  # uncited_bibliography needs the file at build time
    config = load_report_config(folder)
    assert config.format == "ape"
    assert config.uncited_bibliography is True
    assert config.figure_placement == "here"
    assert config.output_format == "pdf"
    assert config.cover_value("required") is False
    assert config.delivery_dir == Path(
        "~/Documents/Academicos/simulacion/unidad-2/ape-3-modelo-de-colas/documento/"
    ).expanduser()
