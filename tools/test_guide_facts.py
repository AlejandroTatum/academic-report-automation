"""Guide extraction and safe loading contracts."""
import subprocess
import sys
from pathlib import Path

from guide_facts import extract_guide_facts, load_guide_facts


def test_spanish_variants_and_accents():
    assert extract_guide_facts("Práctico experimental. Semana 1. Entrega individual (4 horas)") == {
        "family": "ape", "practice_number": "1", "practice_type": "Individual", "planned_time": "4 horas",
    }
    assert extract_guide_facts("APRENDIZAJE AUTÓNOMO; Práctica Nro. 12; en grupo; 2 horas") == {
        "family": "aa", "practice_number": "12", "practice_type": "Grupal", "planned_time": "2 horas",
    }
    assert extract_guide_facts("practico-experimental Práctica 3 grupal") == {
        "family": "ape", "practice_number": "3", "practice_type": "Grupal",
    }


def test_conflicting_explicit_facts_are_not_guessed():
    facts = extract_guide_facts('APE y aprendizaje autónomo. Semana 1; Semana 2. Individual y grupal. 2 horas; 3 horas')
    assert facts == {'conflicts': {
        'family': ['ape', 'aa'], 'practice_number': ['1', '2'],
        'practice_type': ['Individual', 'Grupal'],
        'planned_time': ['2 horas', '3 horas'],
    }}


def test_absent_and_invalid_facts():
    assert extract_guide_facts("No hay datos") == {}
    assert extract_guide_facts(None) == {}


def test_loader_confines_guide_to_folder(tmp_path):
    folder = tmp_path / "report"
    folder.mkdir()
    (folder / "guide.txt").write_text("APE Semana 5", encoding="utf-8")
    assert load_guide_facts(folder, {"guide": "guide.txt"}) == {"family": "ape", "practice_number": "5"}
    assert load_guide_facts(folder, {"guide": "../outside.txt"}) == {}
    assert load_guide_facts(folder, {"guide": "missing.txt"}) == {}
    (folder / "bad.txt").write_bytes(b"\xff")
    assert load_guide_facts(folder, {"guide": "bad.txt"}) == {}


def test_cli_prints_yaml(tmp_path):
    folder = tmp_path / "report"
    folder.mkdir()
    (folder / "report.yml").write_text("guide: guide.txt\n", encoding="utf-8")
    (folder / "guide.txt").write_text("APE Semana 2", encoding="utf-8")
    result = subprocess.run([sys.executable, str(Path(__file__).with_name("guide_facts.py")), str(folder)], capture_output=True, text=True)
    assert result.returncode == 0
    assert "family: ape" in result.stdout
    assert "practice_number: '2'" in result.stdout
