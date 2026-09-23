"""Strict-TDD test for visual_builder.py's connector-audit exception guard
(issue #10 T4, native-review hardening).

``command_validate`` must report a malformed SVG as a validation finding
(``VALIDATION FAILED`` naming the offending file), never let a parse
exception escape uncaught -- a single bad file in a folder validate run
must not crash the whole invocation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
FIXTURES = TOOLS / "fixtures" / "connector_geometry"

import visual_builder as vb  # noqa: E402


def test_connector_audit_parse_error_becomes_a_reported_finding(tmp_path) -> None:
    bad_svg = tmp_path / "broken.svg"
    # Malformed XML (unclosed tag): xml.etree.ElementTree.ParseError.
    bad_svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">'
        '<g class="node" id="A"><rect x="0" y="0" width="10" height="10"/>',
        encoding="utf-8",
    )
    args = vb.build_parser().parse_args(["validate", str(bad_svg), "--no-metadata"])
    with pytest.raises(SystemExit) as excinfo:
        vb.command_validate(args)
    message = str(excinfo.value)
    assert "VALIDATION FAILED" in message
    assert "broken.svg" in message or str(bad_svg) in message


def test_connector_audit_indexerror_becomes_a_reported_finding(tmp_path) -> None:
    """Same guard, a different exception class (#43 T2): the previous guard
    caught only (ET.ParseError, ValueError, KeyError, TypeError) and let an
    IndexError from corrupted path/point data escape uncaught."""
    bad_svg = tmp_path / "corrupted.svg"
    bad_svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">'
        '<g class="nodes">'
        '<g class="node" id="my-svg-flowchart-A-0"><rect x="0" y="0" width="10" height="10"/></g>'
        '<g class="node" id="my-svg-flowchart-B-0"><rect x="50" y="0" width="10" height="10"/></g>'
        "</g>"
        '<g class="edgePaths"><path data-id="L_A_B_0" d="M 5 5 L 10"/></g></svg>',
        encoding="utf-8",
    )
    args = vb.build_parser().parse_args(["validate", str(bad_svg), "--no-metadata"])
    with pytest.raises(SystemExit) as excinfo:
        vb.command_validate(args)
    message = str(excinfo.value)
    assert "VALIDATION FAILED" in message
    assert "corrupted.svg" in message or str(bad_svg) in message


def test_no_source_informational_finding_is_shown(capsys) -> None:
    """R3-no-source-info-dropped-in-validate (#43, native review): a clean
    SVG with no matching ``.mmd`` still passes validation, but the
    CONNECTOR_DIRECTION_NO_SOURCE informational finding must be visible in
    the command's own output -- not silently dropped because it isn't a
    FAILURE."""
    clean_svg = FIXTURES / "mmdc-touching-clean.svg"
    args = vb.build_parser().parse_args(["validate", str(clean_svg), "--no-metadata"])
    rc = vb.command_validate(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "VALIDATION_OK" in out
    assert "CONNECTOR_DIRECTION_NO_SOURCE" in out
