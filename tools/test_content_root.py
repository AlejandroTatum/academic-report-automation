"""Tests for the CODE root / CONTENT root split.

The report automation code now lives in a monorepo while the coursework stayed
behind in its own tree. Everything here guards that boundary:

- CONTENT_ROOT resolves from REPORT_CONTENT_ROOT (or the documented default).
- code paths (templates, logos, node toolchain) keep resolving under ROOT and
  content paths (reports, sources, outputs, backups) under CONTENT_ROOT.
- the relative_to() sites that used to assume "everything lives under one root"
  degrade instead of raising for a path outside their root.
- the Docker LaTeX fallback builds a command for a report anywhere on disk.
- a report folder given as an absolute path outside the code tree still loads.

No Docker, LaTeX, Node or network is required.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

# Make tools/ importable (same pattern as the other test modules here).
TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import build_latex_report  # noqa: E402
import output_router  # noqa: E402
import report_config  # noqa: E402
import source_library  # noqa: E402
import visual_builder  # noqa: E402
from report_config import (  # noqa: E402
    CONTENT_ROOT,
    CONTENT_ROOT_ENV,
    DEFAULT_CONTENT_ROOT,
    ROOT,
    load_report_config,
    relative_label,
    relative_subpath,
    resolve_content_root,
)

DOCUMENTED_DEFAULT = Path("/home/alejo/devwork/.projects/university/.reports-system/automation")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def import_report_config_fresh(name: str = "report_config_fresh"):
    """Import a private copy of report_config, re-running its import-time code.

    A private copy (instead of importlib.reload) keeps the shared module every
    other test relies on untouched, while still exercising the real
    "resolved once, at import" binding.
    """
    path = Path(report_config.__file__)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclass decorator needs the module registered
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def write_report(folder: Path, **extra: object) -> Path:
    """Create a minimal but valid report folder."""
    folder.mkdir(parents=True, exist_ok=True)
    lines = ["type: essay", "title: Reporte de prueba"]
    lines += [f"{key}: {value}" for key, value in extra.items()]
    (folder / "report.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (folder / "body.md").write_text("# Titulo\n\nTexto.\n", encoding="utf-8")
    return folder


# ---------------------------------------------------------------------------
# 1. CONTENT_ROOT default + REPORT_CONTENT_ROOT override
# ---------------------------------------------------------------------------


def test_default_content_root_is_the_documented_path():
    assert DEFAULT_CONTENT_ROOT == DOCUMENTED_DEFAULT


def test_resolve_content_root_falls_back_to_the_default():
    assert resolve_content_root({}) == DEFAULT_CONTENT_ROOT.resolve()


def test_resolve_content_root_honours_the_env_var(tmp_path):
    assert resolve_content_root({CONTENT_ROOT_ENV: str(tmp_path)}) == tmp_path.resolve()


def test_blank_env_var_falls_back_to_the_default():
    assert resolve_content_root({CONTENT_ROOT_ENV: "   "}) == DEFAULT_CONTENT_ROOT.resolve()


def test_content_root_is_absolute_and_resolved():
    assert CONTENT_ROOT.is_absolute()
    assert CONTENT_ROOT == CONTENT_ROOT.resolve()


def test_module_level_content_root_binds_the_env_var_at_import(tmp_path, monkeypatch):
    target = tmp_path / "elsewhere"
    target.mkdir()
    monkeypatch.setenv(CONTENT_ROOT_ENV, str(target))
    fresh = import_report_config_fresh()
    assert fresh.CONTENT_ROOT == target.resolve()
    # ROOT is unaffected by the override: code stays where the code is.
    assert fresh.ROOT == ROOT


def test_module_level_content_root_defaults_without_the_env_var(monkeypatch):
    monkeypatch.delenv(CONTENT_ROOT_ENV, raising=False)
    fresh = import_report_config_fresh()
    assert fresh.CONTENT_ROOT == DEFAULT_CONTENT_ROOT.resolve()


def test_relative_env_value_is_made_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    resolved = resolve_content_root({CONTENT_ROOT_ENV: "relative-content"})
    assert resolved.is_absolute()
    assert resolved == (tmp_path / "relative-content").resolve()


# ---------------------------------------------------------------------------
# 2. ROOT and CONTENT_ROOT are independent
# ---------------------------------------------------------------------------


CODE_PATHS = {
    "DEFAULT_FORMAT": report_config.DEFAULT_FORMAT,
    "DEFAULT_TEMPLATE": build_latex_report.DEFAULT_TEMPLATE,
    "PLAIN_TEMPLATE": build_latex_report.PLAIN_TEMPLATE,
    "ASSETS_DIR": build_latex_report.ASSETS_DIR,
    "NODE_BIN": visual_builder.NODE_BIN,
}

CONTENT_PATHS = {
    "GLOBAL_OUTPUTS": output_router.GLOBAL_OUTPUTS,
    "BACKUPS": output_router.BACKUPS,
    "SOURCE_ROOT": source_library.SOURCE_ROOT,
    "MANIFEST": source_library.MANIFEST,
    "VISUAL_RENDER_BACKUPS": visual_builder.BACKUPS,
}


@pytest.mark.parametrize("name", sorted(CODE_PATHS))
def test_code_paths_resolve_under_the_code_root(name):
    assert CODE_PATHS[name].is_relative_to(ROOT)


@pytest.mark.parametrize("name", sorted(CONTENT_PATHS))
def test_content_paths_resolve_under_the_content_root(name):
    assert CONTENT_PATHS[name].is_relative_to(CONTENT_ROOT)


@pytest.mark.parametrize("name", sorted(CONTENT_PATHS))
def test_content_paths_do_not_leak_into_the_code_root(name):
    if CONTENT_ROOT.is_relative_to(ROOT):
        pytest.skip("content root deliberately nested inside the code root")
    assert not CONTENT_PATHS[name].is_relative_to(ROOT)


def test_every_template_alias_stays_on_the_code_root():
    for key, path in build_latex_report.TEMPLATE_ALIASES.items():
        assert path.is_relative_to(ROOT), key


def test_shipped_code_assets_still_exist_under_the_code_root():
    assert report_config.DEFAULT_FORMAT.exists()
    assert (build_latex_report.ASSETS_DIR / build_latex_report.LOGO_FILENAME).exists()


def test_reports_and_sources_are_looked_up_under_the_content_root(monkeypatch, tmp_path):
    monkeypatch.setattr(output_router, "CONTENT_ROOT", tmp_path)
    monkeypatch.setattr(output_router, "GLOBAL_OUTPUTS", tmp_path / "outputs")
    (tmp_path / "reports" / "demo" / "outputs").mkdir(parents=True)
    (tmp_path / "academic-sources" / "sistemas-operativos").mkdir(parents=True)

    assert tmp_path / "reports" / "demo" / "outputs" in output_router.output_dirs()
    assert "sistemas-operativos" in output_router.known_subject_slugs()


# ---------------------------------------------------------------------------
# 3. relative_to sites no longer raise for a path outside their root
# ---------------------------------------------------------------------------


def test_relative_label_returns_a_relative_string_inside_the_root(tmp_path):
    assert relative_label(tmp_path / "a" / "b.pdf", tmp_path) == str(Path("a/b.pdf"))


def test_relative_label_degrades_to_the_absolute_path_outside_the_root(tmp_path):
    outsider = Path("/definitely/not/under") / tmp_path.name / "x.pdf"
    assert relative_label(outsider, tmp_path) == str(outsider)


def test_relative_subpath_never_escapes_the_target_directory(tmp_path):
    outsider = Path("/etc/passwd")
    relative = relative_subpath(outsider, tmp_path)
    assert not relative.is_absolute()
    assert (tmp_path / "backup" / relative).is_relative_to(tmp_path / "backup")


def test_backup_non_delivery_handles_a_file_outside_the_content_root(tmp_path):
    stray = tmp_path / "stray" / "notes.zip"
    stray.parent.mkdir(parents=True)
    stray.write_text("x", encoding="utf-8")
    backup_root = tmp_path / "backups"

    destination = output_router.backup_non_delivery(stray, backup_root, dry_run=True)

    assert destination.is_relative_to(backup_root)
    assert stray.exists()  # dry run touches nothing


def test_clean_global_outputs_logs_paths_outside_the_content_root(tmp_path, monkeypatch):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "loose_notes.zip").write_text("x", encoding="utf-8")
    (outputs / "ensayo_sistemas_operativos.pdf").write_bytes(b"%PDF-1.4\n")
    (outputs / "sin_materia.pdf").write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(output_router, "CONTENT_ROOT", tmp_path / "content-root-elsewhere")
    monkeypatch.setattr(output_router, "GLOBAL_OUTPUTS", outputs)
    monkeypatch.setattr(output_router, "BACKUPS", tmp_path / "backups")

    actions = output_router.clean_global_outputs(dry_run=True)

    assert actions  # nothing raised, and the run still reported its work
    assert any("loose_notes.zip" in action for action in actions)


def test_source_library_rel_to_root_handles_a_path_outside_the_content_root(tmp_path):
    outsider = tmp_path / "paper.pdf"
    outsider.write_text("x", encoding="utf-8")
    assert source_library.rel_to_root(outsider) == str(outsider.resolve())


def test_source_library_rel_to_root_stays_relative_inside_the_content_root(monkeypatch, tmp_path):
    monkeypatch.setattr(source_library, "CONTENT_ROOT", tmp_path)
    inside = tmp_path / "academic-sources" / "inbox" / "paper.pdf"
    inside.parent.mkdir(parents=True)
    inside.write_text("x", encoding="utf-8")
    assert source_library.rel_to_root(inside) == str(Path("academic-sources/inbox/paper.pdf"))


# ---------------------------------------------------------------------------
# 4. Docker command construction for a report outside the code root
# ---------------------------------------------------------------------------


def docker_flag(command: list[str], flag: str) -> str:
    return command[command.index(flag) + 1]


def test_docker_command_builds_for_a_report_outside_every_known_root(tmp_path):
    folder = write_report(tmp_path / "reports" / "informe_externo")
    config = load_report_config(folder)

    command = build_latex_report.docker_compile_command(config)

    mount = Path(docker_flag(command, "-v").split(":", 1)[0])
    assert folder.resolve().is_relative_to(mount)
    assert config.tex_path.parent.resolve().is_relative_to(mount)
    assert docker_flag(command, "-w") == "/work/build"
    assert command[0] == "docker"
    assert config.tex_path.name in command[-1]


def test_docker_command_mounts_the_content_root_for_a_content_report(tmp_path, monkeypatch):
    # Figure references in body.md escape the report folder
    # (../../../assets/generated/...), so a content report mounts the content
    # root, not just its own folder.
    monkeypatch.setattr(build_latex_report, "CONTENT_ROOT", tmp_path)
    folder = write_report(tmp_path / "reports" / "informe_interno")
    config = load_report_config(folder)

    command = build_latex_report.docker_compile_command(config)

    assert docker_flag(command, "-v") == f"{tmp_path}:/work"
    assert docker_flag(command, "-w") == "/work/reports/informe_interno/build"


def test_docker_command_handles_a_build_dir_outside_the_report_folder(tmp_path):
    workspace = tmp_path / "workspace"
    folder = write_report(workspace / "report", tex=str(workspace / "scratch" / "main.tex"))
    config = load_report_config(folder)

    command = build_latex_report.docker_compile_command(config)

    mount = Path(docker_flag(command, "-v").split(":", 1)[0])
    assert config.tex_path.parent.resolve().is_relative_to(mount)
    assert docker_flag(command, "-w").startswith("/work")


def test_docker_mount_never_degenerates_into_a_filesystem_root(tmp_path):
    folder = write_report(tmp_path / "report", tex="/tmp/isolated-build/main.tex")
    config = load_report_config(folder)

    mount = build_latex_report.docker_mount_root(config)

    assert len(mount.parts) > 2
    assert config.tex_path.parent.resolve().is_relative_to(mount)


def test_compile_latex_docker_path_does_not_touch_the_code_root(tmp_path):
    folder = write_report(tmp_path / "report")
    config = load_report_config(folder)

    mount = build_latex_report.docker_mount_root(config)

    assert not mount == ROOT
    assert mount.is_relative_to(tmp_path)


# ---------------------------------------------------------------------------
# 5. Absolute report folder outside the code tree
# ---------------------------------------------------------------------------


def test_absolute_report_folder_outside_the_code_tree_loads(tmp_path):
    folder = write_report(tmp_path / "reports" / "informe_absoluto")
    assert not folder.is_relative_to(ROOT)

    config = load_report_config(folder.absolute())

    assert config.folder == folder.resolve()
    assert config.backend == "latex"
    assert config.body_path == folder.resolve() / "body.md"
    assert config.body_path.exists()
    assert config.tex_path == folder.resolve() / "build" / "main.tex"
    assert config.pdf_path == folder.resolve() / "outputs" / "report.pdf"
    # Format rules keep coming from the code root, not from the report's tree.
    assert config.academic_format


def test_absolute_report_folder_keeps_absolute_overrides(tmp_path):
    elsewhere = tmp_path / "somewhere-else" / "final.pdf"
    folder = write_report(tmp_path / "reports" / "informe_pdf_externo", pdf=str(elsewhere))

    config = load_report_config(folder)

    assert config.pdf_path == elsewhere


def test_missing_report_yml_still_fails_loudly(tmp_path):
    empty = tmp_path / "no-report"
    empty.mkdir()
    with pytest.raises(SystemExit):
        load_report_config(empty)


# ---------------------------------------------------------------------------
# visual_builder path resolution (code vs content judgement)
# ---------------------------------------------------------------------------


def test_visual_builder_sends_new_outputs_to_the_content_root(monkeypatch, tmp_path):
    content = tmp_path / "content"
    content.mkdir()
    monkeypatch.setattr(visual_builder, "CONTENT_ROOT", content)
    monkeypatch.chdir(tmp_path)

    resolved = visual_builder.resolve_path("assets/generated/materia/figura.png")

    assert resolved == content / "assets" / "generated" / "materia" / "figura.png"


def test_visual_builder_keeps_existing_relative_inputs(monkeypatch, tmp_path):
    monkeypatch.setattr(visual_builder, "CONTENT_ROOT", tmp_path / "content")
    monkeypatch.chdir(tmp_path)
    existing = tmp_path / "spec.html"
    existing.write_text("<html></html>", encoding="utf-8")

    assert visual_builder.resolve_path("spec.html") == existing


def test_visual_builder_keeps_absolute_paths_untouched(tmp_path):
    target = tmp_path / "figure.png"
    assert visual_builder.resolve_path(target) == target


def test_visual_builder_looks_for_chrome_in_both_trees():
    assert visual_builder.LOCAL_CHROME_ROOTS[0].is_relative_to(ROOT)
    assert visual_builder.LOCAL_CHROME_ROOTS[1].is_relative_to(CONTENT_ROOT)


def test_getuid_is_available_for_the_docker_fallback():
    # Guards the assumption baked into docker_compile_command.
    assert isinstance(os.getuid(), int)
