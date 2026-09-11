"""Renderer and ``--json`` tests for ``tools/doc_status.py`` (slice 2c-ii).

``render_human`` is the portable ASCII human block: an optional front-loaded
``**Gate**`` line, exactly one route line with the current token bracketed, a flat
``**Summary**`` list using only ``done|current|pending|blocked``, and a closing
``**Next**`` line -- no tables, no nested headers. ``render_machine`` mirrors the
``gentle-ai.sdd-status/v2`` shape (``## Document Workflow Status``,
``schema: academic.doc-status/v1``, ``next:``, ``### Summary``,
``### Blocked Reasons``, ``### JSON``) with the fenced payload
``schemaName/schemaVersion/workFolder/phases/current/next/gate/blockedReasons``.
``main`` renders both blocks every time: human then machine on stdout by default,
machine on stdout and human on stderr under ``--json``. Shapes come from ``conftest``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import doc_status
from conftest import (
    _approval,
    _mtime,
    _pdf,
    _preview,
    _published,
    _report,
    _skip_research,
    _validation,
)

CATEGORY = "Academicos"
SLUG = "informe-de-laboratorio"
PAYLOAD_KEYS = {
    "schemaName",
    "schemaVersion",
    "workFolder",
    "phases",
    "current",
    "next",
    "gate",
    "blockedReasons",
}


def _golden_folder(folder: Path) -> Path:
    """The design's documented state: intake+research done, preview waits, no marker."""
    _report(folder)
    _skip_research(folder)
    return folder


def _all_done(tmp_path: Path) -> tuple[Path, Path]:
    """A folder whose every phase is ``done``; returns (folder, Documents root)."""
    folder = tmp_path / "wf"
    _report(folder)
    _skip_research(folder)
    _preview(folder)
    marker = _approval(folder)
    pdf = _pdf(folder)
    _mtime(marker, 1_000_000)
    _mtime(pdf, 2_000_000)
    _validation(folder, pdf=pdf)
    root = tmp_path / "Documents"
    _published(root, category=CATEGORY, slug=SLUG, source=pdf)
    return folder, root


def _assert_human_contract(text: str) -> None:
    """Any human block satisfies the portable output contract."""
    assert all(ord(char) < 128 for char in text)
    assert "|" not in text
    assert not any(line.lstrip().startswith("#") for line in text.splitlines())
    routes = [line for line in text.splitlines() if line.startswith("Route:")]
    assert len(routes) == 1
    bracket = re.findall(r"\[([^\]]+)\]", routes[0])
    assert len(bracket) == 1 and (bracket[0] in doc_status.PHASES or bracket[0] == doc_status.DONE)
    summary = re.findall(r"^- ([a-z]+): (\w+)", text, re.M)
    assert [name for name, _ in summary] == list(doc_status.PHASES)
    assert all(state in doc_status.STATE_TOKENS for _, state in summary)


def _payload_block(text: str) -> dict:
    match = re.search(r"```json\n(.*?)\n```", text, re.S)
    assert match is not None
    return json.loads(match.group(1))


# 2.18 render_human golden + portable contract


def test_render_human_golden(tmp_path: Path) -> None:
    """Acceptance for 2.18: the design's exact block for its documented state."""
    status = doc_status.derive(_golden_folder(tmp_path / "wf"))

    text = doc_status.render_human(status)

    assert text == "\n".join(
        [
            "**Gate**: approval pending - generation runs only after you approve reports/wf/preview.md",
            "Route: intake > research > [preview] > approval > generate > validate > deliver",
            "",
            "**Summary**",
            "- intake: done - route=academic, metadata complete",
            "- research: done - skipped in report.yml",
            "- preview: current - preview.md missing",
            "- approval: pending",
            "- generate: pending",
            "- validate: pending",
            "- deliver: pending",
            "",
            "**Next**: preview - draft reports/wf/preview.md, then re-run doc_status",
        ]
    ) + "\n"
    _assert_human_contract(text)


def test_render_human_omits_gate_when_route_complete(tmp_path: Path) -> None:
    """TRIANGULATE: an all-done route starts directly with the route line."""
    folder, root = _all_done(tmp_path)
    status = doc_status.derive(folder, documents_root=root)

    text = doc_status.render_human(status)

    assert status.current == doc_status.DONE
    assert "**Gate**" not in text and text.startswith("Route:")
    assert text.rstrip().endswith("**Next**: done")
    _assert_human_contract(text)


def test_render_human_gate_falls_to_focus_after_approval(tmp_path: Path) -> None:
    """TRIANGULATE: once approval passes the gate names the waiting focus."""
    folder = tmp_path / "wf"
    _report(folder)
    _skip_research(folder)
    _approval(folder)

    status = doc_status.derive(folder)

    states = {phase.name: phase.state for phase in status.phases}
    assert states["approval"] == doc_status.DONE
    assert status.current == "generate"
    assert "**Gate**: generate " in doc_status.render_human(status)
    _assert_human_contract(doc_status.render_human(status))


def test_render_human_gate_reports_blocked_approval(tmp_path: Path) -> None:
    """TRIANGULATE: a stale marker keeps the front-loaded gate on approval."""
    folder = _golden_folder(tmp_path / "wf")
    _approval(folder, preview_sha256="0" * 64)

    status = doc_status.derive(folder)
    text = doc_status.render_human(status)

    assert status.current == "approval"
    assert "**Gate**: approval blocked - " in text
    _assert_human_contract(text)


def test_gate_and_guidance_helpers_are_ascii_and_folder_bound(tmp_path: Path) -> None:
    """``_gate``/``_guidance`` name the real work folder and stay ASCII."""
    folder = _golden_folder(tmp_path / "wf")
    status = doc_status.derive(folder)

    gate = doc_status._gate(status)

    assert gate.startswith("approval pending - ") and "reports/wf/preview.md" in gate
    assert doc_status._guidance("preview", folder) == (
        "draft reports/wf/preview.md, then re-run doc_status"
    )
    assert doc_status._guidance("approval", folder) == (
        "generation runs only after you approve reports/wf/preview.md"
    )
    assert all(ord(char) < 128 for char in gate + doc_status._guidance("intake", folder))


# 2.19 render_machine schema + --json routing


def test_render_machine_schema_and_payload(tmp_path: Path) -> None:
    """Acceptance for 2.19: machine shape and the exact JSON payload keys."""
    status = doc_status.derive(_golden_folder(tmp_path / "wf"))

    text = doc_status.render_machine(status)
    payload = _payload_block(text)

    assert text.startswith("## Document Workflow Status\n")
    assert "schema: academic.doc-status/v1" in text
    assert f"next: {status.next_token}" in text
    assert "### Summary" in text and "### Blocked Reasons" in text and "### JSON" in text
    assert set(payload) == PAYLOAD_KEYS
    assert payload["schemaName"] == "academic.doc-status" and payload["schemaVersion"] == 1
    assert payload["workFolder"] == str(status.work_folder)
    assert [phase["name"] for phase in payload["phases"]] == list(doc_status.PHASES)
    assert payload["current"] == status.current and payload["next"] == status.next_token
    assert payload["gate"] == status.gate
    assert payload["blockedReasons"] == list(status.blocked_reasons)
    assert doc_status._payload(status) == payload


def test_render_machine_lists_blocked_reasons(tmp_path: Path) -> None:
    """TRIANGULATE: a blocked route surfaces its bounded reason token."""
    folder = _golden_folder(tmp_path / "wf")
    _approval(folder, preview_sha256="0" * 64)

    text = doc_status.render_machine(doc_status.derive(folder))

    assert "approval_marker_stale" in text
    assert _payload_block(text)["blockedReasons"] == ["approval_marker_stale"]


def test_main_json_routes_machine_to_stdout_and_human_to_stderr(tmp_path: Path, capsys) -> None:
    """Acceptance for 2.19: ``--json`` still renders both blocks."""
    folder = _golden_folder(tmp_path / "wf")

    rc = doc_status.main([str(folder), "--json"])

    captured = capsys.readouterr()
    assert rc == 0
    assert "## Document Workflow Status" in captured.out and "### JSON" in captured.out
    assert "**Summary**" not in captured.out
    assert "**Summary**" in captured.err and "Route:" in captured.err and "**Gate**" in captured.err


def test_main_default_renders_both_blocks_on_stdout(tmp_path: Path, capsys) -> None:
    """TRIANGULATE: without ``--json`` both blocks stay on stdout; stderr is empty."""
    folder = _golden_folder(tmp_path / "wf")

    rc = doc_status.main([str(folder)])

    captured = capsys.readouterr()
    assert rc == 0 and captured.err == ""
    assert captured.out.index("Route:") < captured.out.index("## Document Workflow Status")
    assert "**Summary**" in captured.out and "### Summary" in captured.out
