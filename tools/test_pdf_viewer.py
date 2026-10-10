"""Open the review PDF for the human automatically at each gate."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pdf_viewer
import pytest


class _Spawn:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], dict]] = []

    def __call__(self, cmd, **kwargs):
        self.calls.append((list(cmd), kwargs))
        return object()


@pytest.fixture
def spawn(monkeypatch) -> _Spawn:
    fake = _Spawn()
    monkeypatch.setattr(pdf_viewer.subprocess, "Popen", fake)
    return fake


def _pdf(tmp_path: Path) -> Path:
    pdf = tmp_path / "informe final.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    return pdf


def test_opens_the_pdf_detached_in_the_default_viewer(tmp_path: Path, spawn: _Spawn, monkeypatch) -> None:
    monkeypatch.delenv(pdf_viewer.VIEWER_ENV, raising=False)
    monkeypatch.setattr(pdf_viewer.shutil, "which", lambda name: f"/usr/bin/{name}")
    pdf = _pdf(tmp_path)
    assert pdf_viewer.open_pdf(pdf) is None
    (cmd, kwargs), = spawn.calls
    assert cmd == ["/usr/bin/brave", str(pdf.resolve())]
    assert kwargs["start_new_session"] is True
    assert kwargs["stdout"] is subprocess.DEVNULL and kwargs["stderr"] is subprocess.DEVNULL


def test_falls_back_to_xdg_open_when_brave_is_missing(tmp_path: Path, spawn: _Spawn, monkeypatch) -> None:
    monkeypatch.delenv(pdf_viewer.VIEWER_ENV, raising=False)
    monkeypatch.setattr(pdf_viewer.shutil, "which", lambda name: "/usr/bin/xdg-open" if name == "xdg-open" else None)
    pdf = _pdf(tmp_path)
    assert pdf_viewer.open_pdf(pdf) is None
    assert spawn.calls[0][0] == ["/usr/bin/xdg-open", str(pdf.resolve())]


def test_viewer_env_overrides_the_default(tmp_path: Path, spawn: _Spawn, monkeypatch) -> None:
    monkeypatch.setenv(pdf_viewer.VIEWER_ENV, "okular --unique")
    monkeypatch.setattr(pdf_viewer.shutil, "which", lambda name: f"/opt/{name}")
    pdf = _pdf(tmp_path)
    assert pdf_viewer.open_pdf(pdf) is None
    assert spawn.calls[0][0] == ["/opt/okular", "--unique", str(pdf.resolve())]


def test_no_viewer_reports_an_error_and_spawns_nothing(tmp_path: Path, spawn: _Spawn, monkeypatch) -> None:
    monkeypatch.delenv(pdf_viewer.VIEWER_ENV, raising=False)
    monkeypatch.setattr(pdf_viewer.shutil, "which", lambda name: None)
    assert "no PDF viewer found" in pdf_viewer.open_pdf(_pdf(tmp_path))
    assert spawn.calls == []


def test_missing_pdf_is_not_opened(tmp_path: Path, spawn: _Spawn) -> None:
    assert "PDF not found" in pdf_viewer.open_pdf(tmp_path / "nope.pdf")
    assert spawn.calls == []


def test_cli_exit_codes_and_messages(tmp_path: Path, spawn: _Spawn, monkeypatch, capsys) -> None:
    monkeypatch.delenv(pdf_viewer.VIEWER_ENV, raising=False)
    monkeypatch.setattr(pdf_viewer.shutil, "which", lambda name: f"/usr/bin/{name}")
    pdf = _pdf(tmp_path)
    assert pdf_viewer.main([str(pdf)]) == 0
    assert capsys.readouterr().out == f"opened {pdf.resolve()}\n"
    assert pdf_viewer.main([str(tmp_path / "nope.pdf")]) == 2
    assert "PDF not found" in capsys.readouterr().err
    monkeypatch.setattr(pdf_viewer.shutil, "which", lambda name: None)
    assert pdf_viewer.main([str(pdf)]) == 1
    assert "no PDF viewer found" in capsys.readouterr().err
    assert len(spawn.calls) == 1
