"""Tests for the Node-backed half of the visual builder.

Two defects are pinned here:

1. Generated ``.cjs`` scripts used to be written under ``CONTENT_ROOT``. Node
   resolves ``require('playwright')`` by walking UP from the script's own
   directory, so a script parked in the content tree can never reach
   ``ROOT/node_modules`` — the very directory ``NODE_BIN`` already assumes.
   ``npm install`` in this repository could not fix ``html-shot``, ever.
2. ``newest_local_chrome()`` only knew the puppeteer browser layout while
   ``package.json`` declares ``playwright``, which parks its browsers in
   ``~/.cache/ms-playwright``. The printed instruction installed a browser the
   declared toolchain does not manage.

Everything here runs without Node, without node_modules and without a browser:
the subprocess boundary is monkeypatched and the property under test is *where*
the script lands relative to a ``node_modules`` Node would actually find.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pytest

# Make tools/ importable (same pattern as the other test modules here).
TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import visual_builder  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def node_module_dirs(start: Path) -> list[Path]:
    """Every ``node_modules`` Node would consult for a require from ``start``.

    Deliberately reimplemented from the Node resolution algorithm instead of
    calling the production helper, so the test fails if the module's own idea
    of resolution ever drifts from Node's.
    """
    return [parent / "node_modules" for parent in (start, *start.parents)]


def make_fake_toolchain(tmp_path: Path, *packages: str) -> Path:
    """Build a fake code root carrying an installed node_modules."""
    root = tmp_path / "code-root"
    for package in packages:
        (root / "node_modules" / package).mkdir(parents=True)
    return root


def bind_root(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """Point the module at a throwaway code root, scratch directory included."""
    monkeypatch.setattr(visual_builder, "ROOT", root)
    monkeypatch.setattr(visual_builder, "NODE_SCRATCH", root / ".cache" / "visual-renders")


def capture_run(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    """Record every subprocess launch, including whether the script existed."""
    calls: list[dict[str, object]] = []

    def fake_run(cmd, *, cwd=None, env=None):
        script = Path(str(cmd[1]))
        calls.append({
            "cmd": [str(c) for c in cmd],
            "script": script,
            "script_existed": script.exists(),
            "cwd": cwd,
            "env": env,
        })
        return None

    monkeypatch.setattr(visual_builder, "run", fake_run)
    return calls


def html_shot_args(src: Path, out: Path) -> argparse.Namespace:
    return argparse.Namespace(input=str(src), out=str(out), width=1400, height=900, selector="page")


def echarts_args(src: Path, out: Path) -> argparse.Namespace:
    return argparse.Namespace(input=str(src), out=str(out), width=1400, height=900)


@pytest.fixture
def html_input(tmp_path: Path) -> Path:
    src = tmp_path / "card.html"
    src.write_text("<html><body>card</body></html>", encoding="utf-8")
    return src


@pytest.fixture
def echarts_input(tmp_path: Path) -> Path:
    src = tmp_path / "option.json"
    src.write_text("{}", encoding="utf-8")
    return src


@pytest.fixture
def fake_chrome(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    chrome = tmp_path / "chrome"
    chrome.write_text("#!/bin/sh\n", encoding="utf-8")
    chrome.chmod(0o755)
    monkeypatch.setattr(visual_builder, "newest_local_chrome", lambda: chrome)
    return chrome


# ---------------------------------------------------------------------------
# 1. Generated scripts land where Node can resolve the declared dependencies
# ---------------------------------------------------------------------------


def test_scratch_dir_lets_node_reach_the_repository_node_modules():
    """The scratch directory must sit under the same root ``NODE_BIN`` assumes."""
    assert visual_builder.ROOT / "node_modules" in node_module_dirs(visual_builder.NODE_SCRATCH)
    assert visual_builder.NODE_SCRATCH.is_relative_to(visual_builder.ROOT)


def test_the_old_content_side_scratch_could_never_reach_node_modules():
    """Regression marker: scripts used to be written on the content tree.

    The old location is spelled out here rather than imported, because the
    constant that held it is gone from the module. Naming a dead path in a
    test documents the defect; leaving it defined in the module would have
    left a plausible-looking scratch directory sitting there for the next
    reader to reach for.
    """
    old_scratch = visual_builder.CONTENT_ROOT / "backups" / "visual-renders"
    if visual_builder.CONTENT_ROOT.is_relative_to(visual_builder.ROOT):
        pytest.skip("content root deliberately nested inside the code root")
    assert visual_builder.ROOT / "node_modules" not in node_module_dirs(old_scratch)


def test_html_shot_writes_its_script_where_node_resolves_playwright(
    tmp_path, monkeypatch, html_input, fake_chrome
):
    root = make_fake_toolchain(tmp_path, "playwright")
    bind_root(monkeypatch, root)
    calls = capture_run(monkeypatch)

    visual_builder.command_html_shot(html_shot_args(html_input, tmp_path / "out.png"))

    script = calls[0]["script"]
    assert calls[0]["script_existed"], "the script must still exist when node runs"
    assert script.suffix == ".cjs"
    assert root / "node_modules" in node_module_dirs(script.parent)


def test_echarts_writes_its_script_where_node_resolves_echarts(
    tmp_path, monkeypatch, echarts_input
):
    root = make_fake_toolchain(tmp_path, "echarts")
    bind_root(monkeypatch, root)
    calls = capture_run(monkeypatch)

    visual_builder.command_echarts(echarts_args(echarts_input, tmp_path / "out.svg"))

    script = calls[0]["script"]
    assert calls[0]["script_existed"]
    assert root / "node_modules" in node_module_dirs(script.parent)


@pytest.mark.parametrize("command", ["html-shot", "echarts"])
def test_generated_scripts_are_cleaned_up_after_the_run(
    command, tmp_path, monkeypatch, html_input, echarts_input, fake_chrome
):
    root = make_fake_toolchain(tmp_path, "playwright", "echarts")
    bind_root(monkeypatch, root)
    calls = capture_run(monkeypatch)

    if command == "html-shot":
        visual_builder.command_html_shot(html_shot_args(html_input, tmp_path / "out.png"))
    else:
        visual_builder.command_echarts(echarts_args(echarts_input, tmp_path / "out.svg"))

    assert not calls[0]["script"].exists(), "temp script must be unlinked afterwards"


@pytest.mark.parametrize("command", ["html-shot", "echarts"])
def test_generated_scripts_survive_a_failing_node_run_no_longer_than_needed(
    command, tmp_path, monkeypatch, html_input, echarts_input, fake_chrome
):
    """A failing render must not leave scratch scripts behind either."""
    root = make_fake_toolchain(tmp_path, "playwright", "echarts")
    bind_root(monkeypatch, root)
    seen: list[Path] = []

    def exploding_run(cmd, *, cwd=None, env=None):
        seen.append(Path(str(cmd[1])))
        raise SystemExit("FAILED")

    monkeypatch.setattr(visual_builder, "run", exploding_run)

    with pytest.raises(SystemExit):
        if command == "html-shot":
            visual_builder.command_html_shot(html_shot_args(html_input, tmp_path / "out.png"))
        else:
            visual_builder.command_echarts(echarts_args(echarts_input, tmp_path / "out.svg"))

    assert not seen[0].exists()


def test_puppeteer_config_lands_with_the_node_toolchain(tmp_path, monkeypatch, fake_chrome):
    root = make_fake_toolchain(tmp_path, "@mermaid-js")
    bind_root(monkeypatch, root)

    config = visual_builder.puppeteer_config()

    assert config.is_relative_to(root)
    assert root / "node_modules" in node_module_dirs(config.parent)
    assert str(fake_chrome) in config.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 2. A genuinely missing dependency fails with Spanish guidance, not a trace
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("command", "package"),
    [("html-shot", "playwright"), ("echarts", "echarts")],
)
def test_missing_node_modules_fails_before_spawning_node(
    command, package, tmp_path, monkeypatch, html_input, echarts_input, fake_chrome
):
    root = tmp_path / "code-root"  # no node_modules at all
    root.mkdir()
    bind_root(monkeypatch, root)
    calls = capture_run(monkeypatch)

    with pytest.raises(SystemExit) as excinfo:
        if command == "html-shot":
            visual_builder.command_html_shot(html_shot_args(html_input, tmp_path / "out.png"))
        else:
            visual_builder.command_echarts(echarts_args(echarts_input, tmp_path / "out.svg"))

    message = str(excinfo.value)
    assert calls == [], "node must not be spawned when the dependency is missing"
    assert package in message
    assert str(root) in message, "the message must name this repository"
    assert "npm install" in message
    assert "no encontrada" in message


def test_missing_node_binary_is_reported_in_spanish(tmp_path, monkeypatch, echarts_input):
    root = make_fake_toolchain(tmp_path, "echarts")
    bind_root(monkeypatch, root)
    monkeypatch.setattr(visual_builder.shutil, "which", lambda name: None)
    capture_run(monkeypatch)

    with pytest.raises(SystemExit) as excinfo:
        visual_builder.command_echarts(echarts_args(echarts_input, tmp_path / "out.svg"))

    assert "Node" in str(excinfo.value)
    assert "no encontrado" in str(excinfo.value)


def test_installed_dependency_passes_the_preflight(tmp_path, monkeypatch):
    root = make_fake_toolchain(tmp_path, "playwright")
    bind_root(monkeypatch, root)
    # Must not raise.
    visual_builder.require_node_package("playwright")


# ---------------------------------------------------------------------------
# 3. Both browser managers are searched; the declared one is advertised
# ---------------------------------------------------------------------------


def write_chrome(path: Path, *, mtime: float | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n", encoding="utf-8")
    path.chmod(0o755)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    monkeypatch.setattr(visual_builder, "LOCAL_CHROME_ROOTS", ())
    return home


def test_newest_local_chrome_finds_the_playwright_managed_browser(isolated_home):
    chrome = write_chrome(
        isolated_home / ".cache" / "ms-playwright" / "chromium-1234" / "chrome-linux64" / "chrome"
    )
    assert visual_builder.newest_local_chrome() == chrome


def test_newest_playwright_build_wins(isolated_home):
    cache = isolated_home / ".cache" / "ms-playwright"
    write_chrome(cache / "chromium-1228" / "chrome-linux64" / "chrome", mtime=1_000_000)
    newer = write_chrome(cache / "chromium-1234" / "chrome-linux64" / "chrome", mtime=2_000_000)
    assert visual_builder.newest_local_chrome() == newer


def test_playwright_browsers_path_override_is_honoured(isolated_home, tmp_path, monkeypatch):
    elsewhere = tmp_path / "browsers"
    chrome = write_chrome(elsewhere / "chromium-1234" / "chrome-linux64" / "chrome")
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(elsewhere))
    assert visual_builder.newest_local_chrome() == chrome


def test_an_existing_puppeteer_install_still_wins(isolated_home, tmp_path, monkeypatch):
    """Add, do not break: a configured puppeteer root keeps its priority."""
    puppeteer_root = tmp_path / "content" / ".cache" / "puppeteer" / "chrome"
    puppeteer_chrome = write_chrome(
        puppeteer_root / "linux-140" / "chrome-linux64" / "chrome", mtime=1_000_000
    )
    write_chrome(
        isolated_home / ".cache" / "ms-playwright" / "chromium-1234" / "chrome-linux64" / "chrome",
        mtime=9_000_000,
    )
    monkeypatch.setattr(visual_builder, "LOCAL_CHROME_ROOTS", (puppeteer_root,))
    assert visual_builder.newest_local_chrome() == puppeteer_chrome


def test_home_puppeteer_layout_is_still_searched(isolated_home):
    chrome = write_chrome(
        isolated_home / ".cache" / "puppeteer" / "chrome" / "linux-140" / "chrome-linux64" / "chrome"
    )
    assert visual_builder.newest_local_chrome() == chrome


def test_missing_browser_advertises_the_declared_toolchain(isolated_home, monkeypatch):
    with pytest.raises(SystemExit) as excinfo:
        visual_builder.require_chrome()

    message = str(excinfo.value)
    assert "playwright install" in message
    assert "puppeteer/browsers" not in message, "must not advertise an unmanaged browser"


@pytest.mark.skipif(
    not (Path.home() / ".cache" / "ms-playwright").is_dir(),
    reason="no Playwright browser cache on this machine",
)
def test_real_playwright_cache_on_this_machine_is_discovered(monkeypatch):
    monkeypatch.setattr(visual_builder, "LOCAL_CHROME_ROOTS", ())
    found = visual_builder.newest_local_chrome()
    assert found is not None
    assert found.is_relative_to(Path.home() / ".cache" / "ms-playwright")
    assert os.access(found, os.X_OK)
