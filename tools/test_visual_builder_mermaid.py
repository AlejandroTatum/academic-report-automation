"""Mermaid scale passthrough for the visual builder CLI.

#27: the mermaid subcommand had no way to request a higher raster scale, so
small-diagram text rendered blurry when scaled up later. The contract pinned
here:

1. ``--scale`` must reach the actual ``mmdc`` invocation (``-s``).
2. Omitting ``--scale`` preserves the native default exactly: no ``-s`` flag is
   passed at all, so mmdc keeps its own behavior.
3. A nonpositive or nonfinite scale is rejected explicitly — never silently
   ignored or silently fallen back to a default.

Everything runs without mmdc, node, or a browser: the subprocess boundary and
the toolchain lookups are stubbed and the test inspects the command that *would*
run.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import visual_builder  # noqa: E402


def capture_run(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []

    def fake_run(cmd, *, cwd=None, env=None):
        calls.append([str(c) for c in cmd])
        return None

    monkeypatch.setattr(visual_builder, "run", fake_run)
    return calls


@pytest.fixture
def hermetic_toolchain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    mmdc = tmp_path / "mmdc"
    mmdc.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(visual_builder, "mmdc_bin", lambda: mmdc)
    monkeypatch.setattr(visual_builder, "puppeteer_config", lambda: tmp_path / "pptr.json")
    return mmdc


def mermaid_args(src: Path, out: Path, scale: float | None = None) -> argparse.Namespace:
    return argparse.Namespace(
        input=str(src),
        out=str(out),
        width=1400,
        height=900,
        background="white",
        theme="neutral",
        css_file=None,
        scale=scale,
    )


@pytest.fixture
def mermaid_spec(tmp_path: Path) -> Path:
    src = tmp_path / "diagram.mmd"
    src.write_text("graph TD\nA --> B\n", encoding="utf-8")
    return src


def test_scale_is_passed_through_to_mmdc(tmp_path, monkeypatch, mermaid_spec, hermetic_toolchain):
    calls = capture_run(monkeypatch)

    visual_builder.command_mermaid(
        mermaid_args(mermaid_spec, tmp_path / "out.png", scale=3.0)
    )

    cmd = calls[0]
    assert "-s" in cmd, f"scale flag missing from the mmdc invocation: {cmd}"
    assert cmd[cmd.index("-s") + 1] == "3.0"


def test_omitted_scale_preserves_native_default(tmp_path, monkeypatch, mermaid_spec, hermetic_toolchain):
    """No --scale means no -s flag at all: mmdc keeps its own default."""
    calls = capture_run(monkeypatch)

    visual_builder.command_mermaid(mermaid_args(mermaid_spec, tmp_path / "out.svg"))

    cmd = calls[0]
    assert "-s" not in cmd
    # The rest of the invocation is unchanged from the pre-scale contract.
    assert cmd[1:7] == [
        "-i", str(mermaid_spec),
        "-o", str(tmp_path / "out.svg"),
        "-w", "1400",
    ]


@pytest.mark.parametrize("scale", [0, -1, -0.5])
def test_nonpositive_scale_is_rejected_explicitly(
    tmp_path, monkeypatch, mermaid_spec, hermetic_toolchain, scale
):
    calls = capture_run(monkeypatch)

    with pytest.raises(SystemExit) as excinfo:
        visual_builder.command_mermaid(
            mermaid_args(mermaid_spec, tmp_path / "out.png", scale=scale)
        )

    assert "--scale" in str(excinfo.value)
    assert calls == [], "nothing may run for an invalid scale"


@pytest.mark.parametrize("scale", [float("inf"), float("-inf"), float("nan")])
def test_nonfinite_scale_is_rejected_explicitly(
    tmp_path, monkeypatch, mermaid_spec, hermetic_toolchain, scale
):
    calls = capture_run(monkeypatch)

    with pytest.raises(SystemExit) as excinfo:
        visual_builder.command_mermaid(
            mermaid_args(mermaid_spec, tmp_path / "out.png", scale=scale)
        )

    assert "--scale" in str(excinfo.value)
    assert calls == []


def test_scale_option_appears_in_cli_help(capsys):
    argv = sys.argv
    sys.argv = ["visual_builder.py", "mermaid", "--help"]
    try:
        with pytest.raises(SystemExit) as excinfo:
            visual_builder.main()
    finally:
        sys.argv = argv
    assert excinfo.value.code == 0
    assert "--scale" in capsys.readouterr().out
