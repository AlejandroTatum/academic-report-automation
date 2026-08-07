"""Tests for pre-flight figure validation and compiler-failure diagnostics.

Two silent-failure defects are pinned here:

* the LaTeX compiler's output was captured and thrown away, so a fatal
  ``! Package luatex.def Error: File ... not found`` was replaced by a bare
  ``La compilación no generó PDF``;
* figure paths referenced from ``body.md`` were never checked, so a missing
  file — or an absolute host path that cannot exist inside the Docker bind
  mount — only surfaced as that same swallowed fatal error.
"""

from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import build_latex_report  # noqa: E402

LUATEX_FAILURE = "\n".join(
    ["This is LuaHBTeX, Version 1.18.0"]
    + [f"[{n}]" for n in range(1, 200)]
    + [
        "! Package luatex.def Error: File `/host/assets/flujo-prompting.png' not found",
        "See the luatex.def package documentation for explanation.",
        "!  ==> Fatal error occurred, no output PDF file produced!",
    ]
)


def _config(tmp_path: Path, body: str = "# Titulo\n\nTexto.\n") -> types.SimpleNamespace:
    folder = tmp_path / "report"
    build_dir = folder / "build"
    build_dir.mkdir(parents=True)
    body_path = folder / "body.md"
    body_path.write_text(body, encoding="utf-8")
    (build_dir / "main.tex").write_text("% tex", encoding="utf-8")
    return types.SimpleNamespace(
        folder=folder,
        body_path=body_path,
        tex_path=build_dir / "main.tex",
        pdf_path=folder / "outputs" / "main.pdf",
        bib_path=None,
        publish_global=False,
        metadata={},
    )


# ---------------------------------------------------------------------------
# D-08 — the compiler output must reach the user when there is no PDF
# ---------------------------------------------------------------------------


def test_failure_message_names_the_missing_pdf_and_the_log() -> None:
    message = build_latex_report.compilation_failure_message(
        Path("/x/build/main.pdf"), Path("/x/build/main.log"), LUATEX_FAILURE
    )
    assert "/x/build/main.pdf" in message
    assert "/x/build/main.log" in message


def test_failure_message_surfaces_the_latex_error_line() -> None:
    message = build_latex_report.compilation_failure_message(
        Path("/x/build/main.pdf"), Path("/x/build/main.log"), LUATEX_FAILURE
    )
    assert "flujo-prompting.png' not found" in message
    assert "Fatal error occurred" in message


def test_failure_message_does_not_dump_the_whole_transcript() -> None:
    message = build_latex_report.compilation_failure_message(
        Path("/x/build/main.pdf"), Path("/x/build/main.log"), LUATEX_FAILURE
    )
    assert len(message.splitlines()) < 80
    assert "[1]" not in message


def test_failure_message_without_captured_output_still_points_at_the_log() -> None:
    message = build_latex_report.compilation_failure_message(
        Path("/x/build/main.pdf"), Path("/x/build/main.log"), ""
    )
    assert "/x/build/main.log" in message


def test_compile_latex_reports_the_compiler_output_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        build_latex_report.shutil,
        "which",
        lambda name: "/usr/bin/docker" if name == "docker" else None,
    )
    monkeypatch.setattr(
        build_latex_report,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            args=list(a[0]), returncode=1, stdout=LUATEX_FAILURE
        ),
    )
    with pytest.raises(SystemExit) as excinfo:
        build_latex_report.compile_latex(config)
    message = str(excinfo.value)
    assert "flujo-prompting.png' not found" in message
    assert "main.log" in message


def test_successful_compile_stays_quiet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = _config(tmp_path)
    build_dir = config.tex_path.parent

    def fake_run(*args, **kwargs):
        (build_dir / "main.pdf").write_bytes(b"%PDF-1.5\n")
        return subprocess.CompletedProcess(args=list(args[0]), returncode=0, stdout=LUATEX_FAILURE)

    monkeypatch.setattr(
        build_latex_report.shutil,
        "which",
        lambda name: "/usr/bin/docker" if name == "docker" else None,
    )
    monkeypatch.setattr(build_latex_report, "run", fake_run)
    build_latex_report.compile_latex(config)
    printed = capsys.readouterr().out
    assert "LuaHBTeX" not in printed
    assert "[1]" not in printed


# ---------------------------------------------------------------------------
# D-16 — figure references are resolved before the compiler runs
# ---------------------------------------------------------------------------


def test_missing_relative_figure_is_reported(tmp_path: Path) -> None:
    errors = build_latex_report.validate_figure_paths(
        "![Flujo](../assets/flujo.png)\n", tmp_path / "build"
    )
    assert len(errors) == 1
    assert "flujo.png" in errors[0]


def test_existing_relative_figure_passes(tmp_path: Path) -> None:
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "flujo.png").write_bytes(b"x")
    assert build_latex_report.validate_figure_paths(
        "![Flujo](../assets/flujo.png)\n", build_dir
    ) == []


def test_extensionless_figure_resolves_through_a_known_suffix(tmp_path: Path) -> None:
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "grafico.png").write_bytes(b"x")
    assert build_latex_report.validate_figure_paths("![G](grafico)\n", build_dir) == []


def test_absolute_figure_path_is_rejected_under_the_docker_mount(tmp_path: Path) -> None:
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    figure = tmp_path / "flujo.png"
    figure.write_bytes(b"x")
    errors = build_latex_report.validate_figure_paths(
        f"![Flujo]({figure})\n", build_dir, docker_mount=tmp_path
    )
    assert len(errors) == 1
    assert str(figure) in errors[0]
    assert "absoluta" in errors[0].lower()


def test_absolute_figure_path_is_fine_for_a_local_engine(tmp_path: Path) -> None:
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    figure = tmp_path / "flujo.png"
    figure.write_bytes(b"x")
    assert build_latex_report.validate_figure_paths(f"![Flujo]({figure})\n", build_dir) == []


def test_figure_outside_the_docker_mount_is_reported(tmp_path: Path) -> None:
    mount = tmp_path / "mount"
    build_dir = mount / "report" / "build"
    build_dir.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "flujo.png").write_bytes(b"x")
    errors = build_latex_report.validate_figure_paths(
        "![Flujo](../../../outside/flujo.png)\n", build_dir, docker_mount=mount
    )
    assert len(errors) == 1
    assert "flujo.png" in errors[0]


def test_remote_figure_urls_are_not_checked(tmp_path: Path) -> None:
    assert build_latex_report.validate_figure_paths(
        "![Logo](https://example.org/logo.png)\n", tmp_path
    ) == []


def test_compile_latex_fails_before_running_the_compiler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path, body="# Titulo\n\n![Flujo](../../assets/ausente.png)\n")
    calls: list[list[str]] = []
    monkeypatch.setattr(
        build_latex_report.shutil,
        "which",
        lambda name: "/usr/bin/docker" if name == "docker" else None,
    )
    monkeypatch.setattr(
        build_latex_report,
        "run",
        lambda *a, **k: calls.append(list(a[0]))
        or subprocess.CompletedProcess(args=list(a[0]), returncode=0, stdout=""),
    )
    with pytest.raises(SystemExit) as excinfo:
        build_latex_report.compile_latex(config)
    assert "ausente.png" in str(excinfo.value)
    assert calls == [], "no compiler must run once a figure is known to be unusable"
