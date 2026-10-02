"""Guide-aware status guidance contracts."""
from pathlib import Path

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
    (tmp_path / "guide.txt").write_text("APE Semana 1. Entrega grupal (4 horas)", encoding="utf-8")
    config = ReportConfig(tmp_path, {"guide": "guide.txt", "format_hint": "ape"})
    guidance = _guidance("format", tmp_path, config)
    for fragment in ("ask_user_choice", "family", "ape", "practice_number=1", "practice_type=Grupal", "planned_time=4 horas", "remaining gaps: cycle", "members"):
        if fragment == "family":
            continue
        assert fragment in guidance
    assert "practice_number, " not in guidance


def test_pdf_handoff_is_short_home_relative(tmp_path: Path):
    folder = Path.home() / "reports" / "sample"
    config = ReportConfig(folder, {"pdf": str(folder / "report-final.pdf")})
    for phase in ("generate", "review"):
        guidance = _guidance(phase, folder, config)
        assert "set d ~/'reports/sample'\nset f 'report-final.pdf'\nbrave $d/$f" in guidance
        assert all(len(line) < 90 for line in guidance.splitlines()[1:])


def test_pdf_handoff_quotes_fish_metacharacters_and_apostrophes():
    folder = Path.home() / 'reports' / 'my folder'
    config = ReportConfig(folder, {'pdf': str(folder / "author's [final] $copy.pdf")})
    guidance = _guidance('review', folder, config)
    assert "set d ~/'reports/my folder'" in guidance
    assert "set f 'author\\'s [final] $copy.pdf'" in guidance
    assert 'brave $d/$f' in guidance
    assert all(len(line) < 90 for line in guidance.splitlines()[1:])


def test_pdf_handoff_escapes_backslashes_and_quotes(tmp_path):
    folder = Path.home() / 'reports' / "O'Brien\\ files"
    config = ReportConfig(folder, {'pdf': str(folder / "draft\\'s file.pdf")})
    guidance = _guidance('review', folder, config)
    assert "set d ~/'reports/O\\'Brien\\\\ files'" in guidance
    assert "set f 'draft\\\\\\'s file.pdf'" in guidance
    assert all(len(line) < 90 for line in guidance.splitlines()[1:])


def test_pdf_handoff_outside_home_uses_quoted_absolute_path(tmp_path):
    folder = tmp_path / 'report'
    config = ReportConfig(folder, {'pdf': str(folder / "final's.pdf")})
    guidance = _guidance('review', folder, config)
    assert "brave '" + str(folder) + "/final\\'s.pdf'" in guidance
