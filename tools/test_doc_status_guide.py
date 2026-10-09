"""Guide-aware status guidance contracts."""
import shlex
import sys
from pathlib import Path

import doc_status
from doc_status import _guidance
from report_config import ReportConfig


def test_intake_suggests_but_does_not_fill_student(tmp_path: Path):
    config = ReportConfig(tmp_path, {"metadata": {"title": "Example"}})
    assert "Alejandro Padilla" in _guidance("intake", tmp_path, config)
    assert "single-choice" in _guidance("intake", tmp_path, config)
    assert "student" not in config.raw["metadata"]


def test_intake_guidance_honours_a_saved_permanent_student_and_never_invents(tmp_path: Path):
    config = ReportConfig(tmp_path, {"metadata": {"title": "Example"}})
    guidance = _guidance("intake", tmp_path, config)
    assert "saved as permanent" in guidance
    assert "record it without asking" in guidance
    assert "otherwise" in guidance and "never invent" in guidance


def test_intake_guidance_skips_the_student_suggestion_once_recorded(tmp_path: Path):
    config = ReportConfig(tmp_path, {"metadata": {"student": "Ana Perez"}})
    assert "Alejandro Padilla" not in _guidance("intake", tmp_path, config)


def test_format_guidance_discloses_facts_and_remaining_gaps(tmp_path: Path):
    (tmp_path / "guide.txt").write_text("APE Semana 1. Entrega grupal. Tiempo planificado 4 horas", encoding="utf-8")
    config = ReportConfig(tmp_path, {"guide": "guide.txt", "format_hint": "ape"})
    guidance = _guidance("format", tmp_path, config)
    for fragment in ("ask_user_choice", "family", "ape", "practice_number=1", "practice_type=Grupal", "planned_time=4 horas", "remaining gaps: cycle", "members"):
        if fragment == "family":
            continue
        assert fragment in guidance
    assert "practice_number, " not in guidance


def test_review_opens_the_exact_pdf_for_the_user(tmp_path):
    folder = tmp_path / "my report"
    config = ReportConfig(folder, {"pdf": str(folder / "author's [final] $copy.pdf")})
    guidance = _guidance("review", folder, config)
    expected = shlex.join([sys.executable, str(doc_status.ROOT / "tools" / "pdf_viewer.py"),
                           str(folder / "author's [final] $copy.pdf")])
    assert "open the PDF for the user (never screenshots): " + expected in guidance
    assert "brave" not in guidance


def test_generate_guidance_opens_nothing(tmp_path):
    folder = Path.home() / "reports" / "sample"
    config = ReportConfig(folder, {"pdf": str(folder / "report-final.pdf")})
    guidance = _guidance("generate", folder, config)
    assert "pdf_viewer.py" not in guidance and "brave" not in guidance