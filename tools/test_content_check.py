"""Unit and CLI tests for ``tools/content_check.py`` (new-report-flow T3/T5).

The verify phase: after the user approves the draft, the AI agent judges every
rubric criterion (``cumple|flojo|falta`` + ``where``) in a judgments file, and
the tool records those judgments, adds the deterministic mechanical checks over
``body.md`` and the document bib, and derives the pass/fail verdict -- the agent
can never declare a pass by itself. These tests pin the mechanical checks
(citations resolve, >= MIN_ACADEMIC_SOURCES eligible sources cited, judgments
cover every criterion exactly once), the derived ``result``, the CLI exit codes
(0 pass / 1 fail / 2 usage or input error), the ``content_check_state``
predicate (``absent|malformed|stale|fail|pass``), the T5 bindings (the marker
records ``rubric_sha256``/``bib_sha256``, goes stale when either changes, and
re-derives the verdict instead of trusting the recorded ``result``), the atomic
marker write, and the guarantee that the check never touches ``body.md``.
Artifact shapes come from ``tools/conftest.py``.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

import content_check
import rubric_checks
import source_count
from conftest import (
    CONTENT_CHECK_SCHEMA,
    DEFAULT_CITED_BODY,
    DEFAULT_RUBRIC_CRITERIA,
    _body,
    _cited_body,
    _content_check,
    _judgments,
    _report,
    _rubric,
    _sources_bib,
)

# ---------------------------------------------------------------------------
# Working folder: reaches the mechanical checks (report, bib, rubric, body).
# ---------------------------------------------------------------------------


def _verify_folder(folder: Path) -> Path:
    _report(folder)
    _sources_bib(folder)
    _rubric(folder)
    _cited_body(folder)
    return folder


def _run(folder: Path, judgments: Path | None = None) -> int:
    """Run the check the way the CLI does and return its exit code."""
    path = judgments if judgments is not None else _judgments(folder)
    other = _judgments(folder, name="second.yml", findings=["Second independent review"])
    return content_check.main([str(folder), "--judgments", str(path), "--judgments", str(other)])


def test_two_judges_merge_strictest_and_dedupe_findings(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    first = _judgments(folder, name="a.yml", findings=["shared", "first"])
    second = _judgments(folder, name="b.yml", findings=["shared", "second"], criteria=[
        {"id": "objetivo", "status": "falta", "where": "missing", "note": "gap"},
        {"id": "metodologia", "status": "cumple", "where": "Metodologia", "note": "ok"},
    ])
    assert content_check.main([str(folder), "--judgments", str(first), "--judgments", str(second)]) == 1
    marker = _marker(folder)
    assert len(marker["judges"]) == 2
    assert marker["criteria"][0] == {"id": "objetivo", "status": "falta", "where": "missing", "note": "gap"}
    assert marker["disagreements"] == [{"id": "objetivo", "statuses": ["cumple", "falta"]}]
    assert marker["findings"][:3] == ["shared", "first", "second"]
    assert "judges disagreed on objetivo: cumple vs falta" in marker["findings"]


@pytest.mark.parametrize("count", [1, 3])
def test_exactly_two_judgments_required(tmp_path: Path, capsys: pytest.CaptureFixture[str], count: int) -> None:
    folder = _verify_folder(tmp_path / "wf")
    args = [str(folder)]
    for index in range(count):
        args.extend(["--judgments", str(_judgments(folder, name=f"{index}.yml"))])
    assert content_check.main(args) == 2
    assert "two independent judges required" in capsys.readouterr().err


def test_identical_judgments_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = _verify_folder(tmp_path / "wf")
    a = _judgments(folder, name="a.yml")
    b = _judgments(folder, name="b.yml")
    assert content_check.main([str(folder), "--judgments", str(a), "--judgments", str(b)]) == 2
    assert "two independent judges required" in capsys.readouterr().err


def test_single_judge_marker_is_stale(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    _content_check(folder, judges=[{"role": "independent", "inputs": ["rubric.yml", "body.md", "sources.bib"]}])
    assert content_check.content_check_state(folder) == "stale"


def _marker(folder: Path) -> dict:
    import yaml

    return yaml.safe_load((folder / "content-check.yml").read_text(encoding="utf-8"))


def _mechanical(marker: dict, check: str) -> dict:
    return next(entry for entry in marker["mechanical"] if entry["check"] == check)


# ---------------------------------------------------------------------------
# Contract constants
# ---------------------------------------------------------------------------


def test_contract_constants_are_pinned() -> None:
    assert content_check.CONTENT_CHECK_NAME == "content-check.yml"
    assert content_check.CONTENT_CHECK_SCHEMA == "academic.content-check/v1"
    assert CONTENT_CHECK_SCHEMA == content_check.CONTENT_CHECK_SCHEMA
    assert content_check.JUDGMENT_STATUSES == ("cumple", "flojo", "falta")
    assert content_check.MIN_ACADEMIC_SOURCES == source_count.MIN_ACADEMIC_SOURCES == 5


# ---------------------------------------------------------------------------
# End-to-end runs through main(): exit codes and the written marker
# ---------------------------------------------------------------------------


def test_rejects_unbound_or_nonindependent_judgments(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import yaml

    folder = _verify_folder(tmp_path / "wf")
    path = _judgments(folder)
    original = yaml.safe_load(path.read_text())
    for change, message in (
        ({"judge": None}, "judge"),
        ({"judge": {"role": "drafter", "inputs": original["judge"]["inputs"]}}, "independent"),
        ({"judge": {"role": "independent", "inputs": original["judge"]["inputs"] + ["conversation"]}}, "inputs"),
        ({"body_sha256": "0" * 64}, "judgments are for a different draft; re-run the judge"),
        ({"rubric_sha256": "0" * 64}, "judgments are for a different draft; re-run the judge"),
    ):
        path.write_text(yaml.safe_dump(dict(original, **change)))
        assert _run(folder, path) == 2
        assert message in capsys.readouterr().err
        assert not (folder / "content-check.yml").exists()


def test_judge_brief_is_bound_and_read_only(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = _verify_folder(tmp_path / "wf")
    assert content_check.main([str(folder), "--judge-brief"]) == 0
    brief = capsys.readouterr().out
    for name in ("rubric.yml", "body.md", "sources.bib"):
        assert str(folder / name) in brief
    assert _sha(folder / "body.md") in brief
    assert _sha(folder / "rubric.yml") in brief
    assert "independent" in brief and "cumple|flojo|falta" in brief
    assert "Do not edit" in brief and "where" in brief
    assert "[@key]" in brief and "IEEE" in brief and "sources.bib" in brief
    assert "not a formatting defect" in brief


def test_pass_case_writes_marker_and_exits_zero(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")

    assert _run(folder) == 0

    marker = _marker(folder)
    assert marker["schema"] == CONTENT_CHECK_SCHEMA
    assert marker["result"] == "pass"
    assert marker["body_sha256"]
    assert marker["checked_at"]
    assert [c["id"] for c in marker["criteria"]] == ["objetivo", "metodologia"]
    assert all(c["status"] == "cumple" for c in marker["criteria"])
    assert all(entry["ok"] for entry in marker["mechanical"])
    assert marker["findings"] == ["Second independent review"]


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_preplanned_checks_start_red_and_turn_green_without_editing_body_by_runner(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder)
    _sources_bib(folder)
    criteria = [dict(DEFAULT_RUBRIC_CRITERIA[0], checks=[
        {"type": "contains", "section": "Objetivos", "text": "learning outcome"}
    ]), dict(DEFAULT_RUBRIC_CRITERIA[1])]
    _rubric(folder, criteria=criteria)
    assert not (folder / "body.md").exists()
    _cited_body(folder)
    before = (folder / "body.md").read_bytes()
    assert _run(folder) == 1
    marker = _marker(folder)
    assert _mechanical(marker, "rubric_checks")["ok"] is False
    assert "objetivo" in _mechanical(marker, "rubric_checks")["detail"]
    assert "cumple" in _mechanical(marker, "rubric_checks")["detail"]
    assert marker["rubric_check_results"][0]["ok"] is False
    assert (folder / "body.md").read_bytes() == before
    _body(folder, DEFAULT_CITED_BODY + "\n# Objetivos\n\nLearning outcome.\n")
    assert _run(folder) == 0
    assert _mechanical(_marker(folder), "rubric_checks")["ok"] is True
    assert _marker(folder)["rubric_check_results"][0]["ok"] is True


def test_pass_case_binds_the_current_rubric_and_bib(tmp_path: Path) -> None:
    """new-report-flow T5: the marker records rubric_sha256 and bib_sha256."""
    folder = _verify_folder(tmp_path / "wf")

    assert _run(folder) == 0

    marker = _marker(folder)
    assert marker["rubric_sha256"] == _sha(folder / "rubric.yml")
    assert marker["bib_sha256"] == _sha(folder / "sources.bib")
    assert not (folder / "content-check.yml.tmp").exists(), "the write must leave no temp file"


def test_marker_write_is_atomic_and_cleans_up_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed replace never leaves a half-written marker or a stray temp file."""
    folder = _verify_folder(tmp_path / "wf")

    def _boom(src: object, dst: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(content_check.os, "replace", _boom)
    with pytest.raises(OSError):
        content_check.run_check(folder, [_judgments(folder), _judgments(folder, name="second.yml", findings=["second"])])

    assert not (folder / "content-check.yml").exists()
    assert not (folder / "content-check.yml.tmp").exists()


def test_fail_case_exits_one_and_records_result(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    judgments = _judgments(folder, criteria=[dict(DEFAULT_RUBRIC_CRITERIA[0], status="cumple")])

    assert _run(folder, judgments) == 1

    marker = _marker(folder)
    assert marker["result"] == "fail"


def test_flojo_judgment_fails(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    judgments = _judgments(
        folder,
        criteria=[
            {"id": "objetivo", "status": "cumple", "where": "Objetivos", "note": "ok"},
            {"id": "metodologia", "status": "flojo", "where": "Metodologia", "note": "vago"},
        ],
    )

    assert _run(folder, judgments) == 1
    assert _marker(folder)["result"] == "fail"


def test_falta_judgment_fails(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    judgments = _judgments(
        folder,
        criteria=[
            {"id": "objetivo", "status": "cumple", "where": "Objetivos", "note": "ok"},
            {"id": "metodologia", "status": "falta", "where": "", "note": "no existe la seccion"},
        ],
    )

    assert _run(folder, judgments) == 1
    assert _marker(folder)["result"] == "fail"


def test_unresolved_citation_fails(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    _body(folder, DEFAULT_CITED_BODY + "\nReclamo sin fuente [@fantasma].\n")

    assert _run(folder) == 1

    marker = _marker(folder)
    assert _mechanical(marker, "citations_resolve")["ok"] is False
    assert "fantasma" in _mechanical(marker, "citations_resolve")["detail"]
    assert marker["result"] == "fail"


def test_only_four_eligible_cited_sources_fails(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    _body(folder, "# Informe\n\nCuerpo con [@key1], [@key2], [@key3] y [@key4].\n")

    assert _run(folder) == 1

    marker = _marker(folder)
    eligible = _mechanical(marker, "eligible_sources_cited")
    assert eligible["ok"] is False
    assert "4/5" in eligible["detail"]
    assert marker["result"] == "fail"


def test_web_only_cited_sources_do_not_count(tmp_path: Path) -> None:
    """Five cited keys that are all @misc still fail the eligible-source gate."""
    folder = _verify_folder(tmp_path / "wf")
    (folder / "sources.bib").write_text(
        "\n".join(f"@misc{{web{i}, howpublished={{url}}}}" for i in range(1, 6)) + "\n",
        encoding="utf-8",
    )
    _body(folder, "# Informe\n\n" + " ".join(f"[@web{i}]" for i in range(1, 6)) + "\n")

    assert _run(folder) == 1
    assert _mechanical(_marker(folder), "eligible_sources_cited")["ok"] is False


def test_unknown_criterion_id_fails(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    judgments = _judgments(
        folder,
        criteria=[
            {"id": "objetivo", "status": "cumple", "where": "Objetivos", "note": "ok"},
            {"id": "inventado", "status": "cumple", "where": "X", "note": "ok"},
        ],
    )

    assert _run(folder, judgments) == 1

    marker = _marker(folder)
    judgment_check = _mechanical(marker, "judgments_match_rubric")
    assert judgment_check["ok"] is False
    assert "inventado" in judgment_check["detail"]
    assert marker["result"] == "fail"


def test_missing_criterion_judgment_fails(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    judgments = _judgments(
        folder,
        criteria=[{"id": "objetivo", "status": "cumple", "where": "Objetivos", "note": "ok"}],
    )

    assert _run(folder, judgments) == 1
    assert _mechanical(_marker(folder), "judgments_match_rubric")["ok"] is False


def test_duplicate_judgment_for_same_id_fails(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    judgments = _judgments(
        folder,
        criteria=[
            {"id": "objetivo", "status": "cumple", "where": "Objetivos", "note": "ok"},
            {"id": "objetivo", "status": "flojo", "where": "Otro", "note": "?"}
        ]
        + [
            {"id": "metodologia", "status": "cumple", "where": "Metodologia", "note": "ok"},
        ],
    )

    assert _run(folder, judgments) == 1
    assert _mechanical(_marker(folder), "judgments_match_rubric")["ok"] is False


def test_agent_findings_are_recorded_verbatim(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    judgments = _judgments(folder, findings=["El parrafo 2 es confuso"])

    assert _run(folder, judgments) == 0

    marker = _marker(folder)
    assert "El parrafo 2 es confuso" in marker["findings"]
    assert marker["result"] == "pass"


def test_mechanical_failures_become_findings(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    _body(folder, "# Informe\n\nCuerpo con [@key1] y una cita rota [@fantasma].\n")

    assert _run(folder) == 1

    findings = "\n".join(_marker(folder)["findings"])
    assert "citations_resolve" in findings or "fantasma" in findings


def test_body_md_bytes_are_never_modified(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    before = (folder / "body.md").read_bytes()

    assert _run(folder) == 0

    assert (folder / "body.md").read_bytes() == before


# ---------------------------------------------------------------------------
# Judge brief: already-run rubric checks, tolerance rules, no-re-judge rule
# ---------------------------------------------------------------------------


def _checked_folder(folder: Path, *, checks: list[dict], body: str, guide: str) -> Path:
    """A verify folder whose first criterion carries deterministic checks + guide."""
    _report(folder)
    _sources_bib(folder)
    criteria = [dict(DEFAULT_RUBRIC_CRITERIA[0], checks=checks), dict(DEFAULT_RUBRIC_CRITERIA[1])]
    _rubric(folder, criteria=criteria)
    _body(folder, body)
    (folder / "guia.txt").write_text(guide, encoding="utf-8")
    (folder / "report.yml").write_text((folder / "report.yml").read_text() + "guide: guia.txt\n")
    return folder


def test_judge_brief_lists_passing_rubric_check(tmp_path: Path) -> None:
    folder = _checked_folder(
        tmp_path / "wf",
        checks=[{"type": "verbatim_from_guide", "section": "Objetivos", "source": "guia.txt",
                 "text": "preparar un informe de laboratorio"}],
        body="# Informe\n\n## Objetivos\n\nPreparar un informe de laboratorio.\n\n## Metodologia\n\nMedimos dos veces.\n",
        guide="La catedra pide: preparar un informe de laboratorio con formato IEEE.\n",
    )
    brief = content_check.judge_brief(folder)
    assert "- objetivo check 1 (verbatim_from_guide): PASS - verbatim text in guide=True, section=True" in brief
    assert brief == content_check.judge_brief(folder)  # deterministic for identical inputs


def test_judge_brief_lists_failing_rubric_check(tmp_path: Path) -> None:
    folder = _checked_folder(
        tmp_path / "wf",
        checks=[{"type": "contains", "section": "Objetivos", "text": "quantum tunneling result"}],
        body="# Informe\n\n## Objetivos\n\nPreparar un informe de laboratorio.\n",
        guide="irrelevant",
    )
    brief = content_check.judge_brief(folder)
    assert "- objetivo check 1 (contains): FAIL - text 'quantum tunneling result' missing" in brief


def test_judge_brief_states_tolerances_and_no_rejudge_rule(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    brief = content_check.judge_brief(folder)
    assert "normalizes whitespace" in brief
    assert "first letter" in brief and "sentence-initial" in brief
    assert "contains is case-insensitive" in brief
    assert "accent-insensitively" in brief
    assert "a PASSING check" in brief and "flojo or falta" in brief
    assert "judge only what the checks do not cover" in brief


def test_judge_brief_states_when_rubric_has_no_checks(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    assert "no deterministic checks" in content_check.judge_brief(folder)
    assert not (folder / "content-check.yml").exists()


# ---------------------------------------------------------------------------
# report-flow-hardening T11: one body.md read, shared tolerance text, and the
# guide bound into the marker
# ---------------------------------------------------------------------------


def _guide_folder(folder: Path) -> Path:
    """A verify folder whose report.yml declares an existing guide input."""
    _verify_folder(folder)
    (folder / "guia.txt").write_text("La catedra pide formato IEEE.\n", encoding="utf-8")
    (folder / "report.yml").write_text((folder / "report.yml").read_text() + "guide: guia.txt\n")
    return folder


def test_judge_brief_reads_body_md_exactly_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The recorded hash and the rubric checks see the same bytes: one read.

    ``read_bytes``/``read_text`` are the logical reads (``sha256_file`` opens
    its own stream), so the spy pins both: exactly one logical read of body.md,
    and no hash call ever touches it again.
    """
    folder = _verify_folder(tmp_path / "wf")
    expected_hash = _sha(folder / "body.md")
    reads: list[str] = []
    real_read_bytes, real_read_text = Path.read_bytes, Path.read_text

    def spy_read_bytes(self: Path, *args: object, **kwargs: object) -> bytes:
        if self.name == "body.md":
            reads.append(f"read_bytes:{self}")
        return real_read_bytes(self, *args, **kwargs)  # type: ignore[arg-type]

    def spy_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self.name == "body.md":
            reads.append(f"read_text:{self}")
        return real_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

    hashed: list[str] = []
    real_sha = content_check.sha256_file

    def spy_sha256_file(path: Path) -> str:
        hashed.append(str(path))
        return real_sha(path)

    monkeypatch.setattr(Path, "read_bytes", spy_read_bytes)
    monkeypatch.setattr(Path, "read_text", spy_read_text)
    monkeypatch.setattr(content_check, "sha256_file", spy_sha256_file)

    brief = content_check.judge_brief(folder)

    assert reads == [f"read_bytes:{folder / 'body.md'}"]
    assert not any(path.endswith("body.md") for path in hashed)
    assert expected_hash in brief


def test_judge_brief_non_utf8_body_is_input_error(tmp_path: Path) -> None:
    """A decode failure is the same input-error shape as a missing body.md."""
    folder = _verify_folder(tmp_path / "wf")
    (folder / "body.md").write_bytes(b"\xff\xfe not utf-8\n")

    with pytest.raises(ValueError, match="body.md missing or unreadable"):
        content_check.judge_brief(folder)


def test_brief_tolerance_text_is_the_rubric_checks_constant(tmp_path: Path) -> None:
    """The brief quotes rubric_checks.TOLERANCE_RULES verbatim: no drift."""
    folder = _verify_folder(tmp_path / "wf")
    brief = content_check.judge_brief(folder)

    assert f"Tolerance rules these checks apply: {rubric_checks.TOLERANCE_RULES}" in brief


def test_marker_binds_guide_sha256_when_report_declares_one(tmp_path: Path) -> None:
    folder = _guide_folder(_verify_folder(tmp_path / "wf"))

    assert _run(folder) == 0

    assert _marker(folder)["guide_sha256"] == _sha(folder / "guia.txt")


def test_marker_has_no_guide_sha256_without_a_guide(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")

    assert _run(folder) == 0

    assert "guide_sha256" not in _marker(folder)


def test_guide_edit_stales_the_marker(tmp_path: Path) -> None:
    folder = _guide_folder(_verify_folder(tmp_path / "wf"))
    assert _run(folder) == 0

    (folder / "guia.txt").write_text("La catedra pide formato IEEE y APA.\n", encoding="utf-8")

    assert content_check.content_check_state(folder) == "stale"


def test_deleted_guide_stales_the_marker(tmp_path: Path) -> None:
    folder = _guide_folder(_verify_folder(tmp_path / "wf"))
    assert _run(folder) == 0

    (folder / "guia.txt").unlink()

    assert content_check.content_check_state(folder) == "stale"


def test_unbound_guide_stales_the_marker(tmp_path: Path) -> None:
    folder = _guide_folder(_verify_folder(tmp_path / "wf"))
    assert _run(folder) == 0

    (folder / "report.yml").write_text(
        (folder / "report.yml").read_text().replace("guide: guia.txt\n", "")
    )

    assert content_check.content_check_state(folder) == "stale"


def test_escaping_guide_binding_stales_the_marker(tmp_path: Path) -> None:
    folder = _guide_folder(_verify_folder(tmp_path / "wf"))
    assert _run(folder) == 0

    (folder / "report.yml").write_text(
        (folder / "report.yml").read_text().replace("guide: guia.txt", "guide: ../outside.md")
    )

    assert content_check.content_check_state(folder) == "stale"


def test_marker_without_guide_sha256_stays_valid_when_guide_appears_later(tmp_path: Path) -> None:
    """Backward compat: pre-guide markers must not change phase."""
    folder = _verify_folder(tmp_path / "wf")
    assert _run(folder) == 0

    (folder / "guia.txt").write_text("guide added after the check\n", encoding="utf-8")
    (folder / "report.yml").write_text((folder / "report.yml").read_text() + "guide: guia.txt\n")

    assert content_check.content_check_state(folder) == "pass"


# ---------------------------------------------------------------------------
# Usage / input errors: exit 2, nothing written
# ---------------------------------------------------------------------------


def test_missing_folder_is_usage_error(tmp_path: Path) -> None:
    folder = tmp_path / "nope"
    judgments = tmp_path / "judgments.yml"

    assert content_check.main([str(folder), "--judgments", str(judgments)]) == 2
    assert not folder.exists()


def test_missing_body_is_usage_error(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder)
    _sources_bib(folder)
    _rubric(folder)

    assert _run(folder) == 2
    assert not (folder / "content-check.yml").exists()


def test_missing_or_malformed_rubric_is_usage_error(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _report(folder)
    _sources_bib(folder)
    _cited_body(folder)

    assert _run(folder) == 2

    _rubric(folder, criteria=())
    assert _run(folder) == 2
    assert not (folder / "content-check.yml").exists()


def test_missing_judgments_file_is_usage_error(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")

    assert content_check.main([str(folder), "--judgments", str(folder / "nope.yml")]) == 2


def test_judgments_not_a_mapping_is_usage_error(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    judgments = folder / "judgments.yml"
    judgments.write_text("- just\n- a\n- list\n", encoding="utf-8")

    assert _run(folder, judgments) == 2


def test_invalid_status_is_usage_error(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    judgments = _judgments(
        folder,
        criteria=[
            {"id": "objetivo", "status": "maso", "where": "Objetivos", "note": ""},
            {"id": "metodologia", "status": "cumple", "where": "Metodologia", "note": "ok"},
        ],
    )

    assert _run(folder, judgments) == 2


@pytest.mark.parametrize(
    "criteria",
    [
        [{"id": "objetivo"}],
        [{"id": "objetivo", "where": "Objetivos", "note": "sin status"}],
        [{"status": "cumple", "where": "Objetivos", "note": "sin id"}],
    ],
)
def test_judgment_missing_id_or_status_is_usage_error(
    tmp_path: Path, criteria: list[dict]
) -> None:
    folder = _verify_folder(tmp_path / "wf")
    judgments = _judgments(folder, criteria=criteria)

    assert _run(folder, judgments) == 2


def test_non_utf8_judgments_is_usage_error(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    judgments = folder / "judgments.yml"
    judgments.write_bytes(b"criteria: \xff\xfe\n")

    assert _run(folder, judgments) == 2


def test_broken_yaml_judgments_is_usage_error(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    judgments = folder / "judgments.yml"
    judgments.write_text("criteria: [unclosed\n", encoding="utf-8")

    assert _run(folder, judgments) == 2


def test_invalid_judgments_file_blocks_merge_and_names_the_file(tmp_path: Path) -> None:
    """One invalid file aborts the merge; the error names that file only."""
    folder = _verify_folder(tmp_path / "wf")
    good = _judgments(folder, name="good.yml", findings=["second"])
    bad = _judgments(folder, name="bad.yml", criteria=[
        {"id": "objetivo", "status": "maso", "where": "Objetivos", "note": "typo status"},
    ])

    outcome = content_check.run_check(folder, [good, bad])

    assert outcome.result == "" and outcome.marker == {}
    assert len(outcome.errors) == 1
    assert outcome.errors[0].startswith("bad.yml")
    assert not any(error.startswith("good.yml") for error in outcome.errors)
    assert not (folder / "content-check.yml").exists()


def test_judge_level_errors_name_the_offending_file(tmp_path: Path) -> None:
    import yaml

    folder = _verify_folder(tmp_path / "wf")
    good = _judgments(folder, name="good.yml", findings=["second"])
    bad = _judgments(folder, name="bad.yml")
    original = yaml.safe_load(bad.read_text())
    inputs = original["judge"]["inputs"]

    for change, message in (
        ({"judge": {"role": "drafter", "inputs": inputs}},
         ("bad.yml: judge.role must be independent",)),
        ({"judge": {"role": "independent", "inputs": inputs + ["conversation"]}},
         ("bad.yml: judge.inputs must list exactly: rubric.yml, body.md, sources.bib",)),
        ({"body_sha256": "0" * 64},
         ("bad.yml: judgments are for a different draft; re-run the judge",
          "good.yml and bad.yml must bind the same body_sha256 and rubric_sha256")),
    ):
        bad.write_text(yaml.safe_dump(dict(original, **change)))
        outcome = content_check.run_check(folder, [good, bad])
        assert outcome.errors == message, change
        assert not (folder / "content-check.yml").exists()


def test_real_cli_subprocess_exit_codes(tmp_path: Path) -> None:
    """The module entry point maps pass->0, fail->1, usage->2 for real."""
    folder = _verify_folder(tmp_path / "wf")
    runner = sys.executable
    script = Path(content_check.__file__)

    passed = subprocess.run(
        [runner, str(script), str(folder), "--judgments", str(_judgments(folder)), "--judgments", str(_judgments(folder, name="second.yml", findings=["second"]))],
        capture_output=True,
        text=True,
    )
    assert passed.returncode == 0, passed.stderr

    broken = _judgments(folder, name="bad.yml", criteria=[{"id": "inventado", "status": "cumple"}])
    failed = subprocess.run(
        [runner, str(script), str(folder), "--judgments", str(broken), "--judgments", str(_judgments(folder, name="second.yml", findings=["second"]))],
        capture_output=True,
        text=True,
    )
    assert failed.returncode == 1, failed.stderr

    missing = subprocess.run(
        [runner, str(script), str(tmp_path / "nope"), "--judgments", str(broken)],
        capture_output=True,
        text=True,
    )
    assert missing.returncode == 2


# ---------------------------------------------------------------------------
# content_check_state: the folder-level predicate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mechanical", [[], [{"check": "citations_resolve", "ok": True}]])
def test_marker_requires_complete_mechanical_set(tmp_path: Path, mechanical: list[dict]) -> None:
    folder = _verify_folder(tmp_path / "wf")
    _content_check(folder, mechanical=mechanical)
    assert content_check.content_check_state(folder) == "malformed"


@pytest.mark.parametrize("ok", [1, "true", None])
def test_marker_requires_boolean_mechanical_results(tmp_path: Path, ok: object) -> None:
    folder = _verify_folder(tmp_path / "wf")
    _content_check(folder)
    import yaml
    marker = _marker(folder)
    marker["mechanical"][0]["ok"] = ok
    (folder / "content-check.yml").write_text(yaml.safe_dump(marker))
    assert content_check.content_check_state(folder) == "malformed"


def test_no_criteria_cannot_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder = _verify_folder(tmp_path / "wf")
    monkeypatch.setattr(content_check.rubric_plan, "load_rubric", lambda _: [])
    assert content_check.run_check(folder, _judgments(folder)).errors


def test_pre_t1_marker_is_stale_before_mechanical_validation(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    _content_check(folder)
    marker = _marker(folder)
    legacy = {key: marker[key] for key in (
        "schema", "body_sha256", "checked_at", "criteria", "findings", "mechanical", "result"
    )}
    legacy["mechanical"] = [entry for entry in marker["mechanical"] if entry["check"] != "rubric_checks"]
    import yaml
    (folder / "content-check.yml").write_text(yaml.safe_dump(legacy))
    assert content_check.content_check_state(folder) == "stale"


def test_pre_judge_marker_with_current_hashes_is_stale(tmp_path: Path) -> None:
    # Shape written between the rubric/bib binding and the independent judge: current
    # rubric and bib hashes, no judge, and no rubric_checks entry (E2E 2026-09-29).
    folder = _verify_folder(tmp_path / "wf")
    _content_check(folder)
    marker = _marker(folder)
    legacy = {key: marker[key] for key in (
        "schema", "body_sha256", "rubric_sha256", "bib_sha256", "checked_at",
        "criteria", "findings", "mechanical", "result",
    )}
    legacy["mechanical"] = [entry for entry in marker["mechanical"] if entry["check"] != "rubric_checks"]
    import yaml
    (folder / "content-check.yml").write_text(yaml.safe_dump(legacy))
    assert content_check.content_check_state(folder) == "stale"


def test_legacy_marker_is_stale_not_malformed(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    _content_check(folder, drop=("judges", "rubric_sha256"))
    assert content_check.content_check_state(folder) == "stale"


@pytest.mark.parametrize("text", ["criteria: [broken", "- not a mapping"])
def test_parse_failure_has_no_binding_cascade(tmp_path: Path, text: str) -> None:
    folder = _verify_folder(tmp_path / "wf")
    path = folder / "judgments.yml"
    path.write_text(text)
    outcome = content_check.run_check(folder, [path, _judgments(folder, name="second.yml", findings=["second"])])
    assert len(outcome.errors) == 1
    assert "judge" not in outcome.errors[0]


def test_invalid_rubric_never_raises_in_state_or_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder = _verify_folder(tmp_path / "wf")
    _content_check(folder)
    monkeypatch.setattr(content_check.rubric_plan, "load_rubric", lambda _: (_ for _ in ()).throw(OSError("denied")))
    assert content_check.content_check_state(folder) == "malformed"
    assert content_check.run_check(folder, _judgments(folder)).errors


@pytest.mark.parametrize("guide", ["../outside.md", "/tmp/outside.md", "escape.md"])
def test_guide_cannot_escape_report(tmp_path: Path, guide: str) -> None:
    folder = _verify_folder(tmp_path / "wf")
    if guide == "escape.md":
        outside = tmp_path / "outside.md"
        outside.write_text("secret")
        (folder / guide).symlink_to(outside)
    (folder / "report.yml").write_text((folder / "report.yml").read_text() + f"guide: {guide}\n")
    assert content_check.main([str(folder), "--judge-brief"]) == 2
    assert content_check.run_check(folder, _judgments(folder)).errors


def test_missing_guide_is_omitted_from_judge_inputs(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    (folder / "report.yml").write_text((folder / "report.yml").read_text() + "guide: missing.md\n")
    assert "missing.md" not in content_check.judge_brief(folder)
    import yaml
    path = _judgments(folder)
    data = yaml.safe_load(path.read_text())
    data["judge"]["inputs"].remove("missing.md")
    path.write_text(yaml.safe_dump(data))
    second = _judgments(folder, name="second.yml", findings=["second"])
    other = yaml.safe_load(second.read_text())
    other["judge"]["inputs"].remove("missing.md")
    second.write_text(yaml.safe_dump(other))
    assert content_check.run_check(folder, [path, second]).result == "pass"


def test_content_check_state_absent(tmp_path: Path) -> None:
    assert content_check.content_check_state(tmp_path / "wf") == "absent"


def test_content_check_state_pass_and_fail(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _body(folder)
    _content_check(folder, result="pass")

    assert content_check.content_check_state(folder) == "pass"

    # An honest fail shape: a recorded criterion below ``cumple``.
    _content_check(
        folder,
        result="fail",
        criteria=[
            {"id": "objetivo", "status": "cumple", "where": "Objetivos", "note": "ok"},
            {"id": "metodologia", "status": "flojo", "where": "Metodologia", "note": "vago"},
        ],
    )

    assert content_check.content_check_state(folder) == "fail"


def test_content_check_state_stale_after_body_edit(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _body(folder)
    _content_check(folder, result="pass")
    _body(folder, "# Informe\n\nCuerpo editado despues del chequeo.\n")

    assert content_check.content_check_state(folder) == "stale"


def test_content_check_state_stale_after_rubric_edit(tmp_path: Path) -> None:
    """new-report-flow T5: the check binds rubric.yml too."""
    folder = tmp_path / "wf"
    _body(folder)
    _rubric(folder)
    _content_check(folder, result="pass")
    _rubric(folder, source="rubrica editada por la catedra")

    assert content_check.content_check_state(folder) == "stale"


def test_content_check_state_stale_after_rubric_deleted(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _body(folder)
    _rubric(folder)
    _content_check(folder, result="pass")
    (folder / "rubric.yml").unlink()

    assert content_check.content_check_state(folder) == "stale"


def test_content_check_state_stale_after_bib_edit(tmp_path: Path) -> None:
    """new-report-flow T5: the check binds the document bib too."""
    folder = tmp_path / "wf"
    _body(folder)
    _sources_bib(folder)
    _content_check(folder, result="pass")
    _sources_bib(folder, count=6)

    assert content_check.content_check_state(folder) == "stale"


def test_content_check_state_ignores_recorded_pass_with_failing_criteria(
    tmp_path: Path,
) -> None:
    """T5: a forged ``result: pass`` is re-derived; a flojo criterion fails it."""
    folder = tmp_path / "wf"
    _body(folder)
    _content_check(
        folder,
        result="pass",
        criteria=[
            {"id": "objetivo", "status": "cumple", "where": "Objetivos", "note": "ok"},
            {"id": "metodologia", "status": "flojo", "where": "Metodologia", "note": "vago"},
        ],
    )

    assert content_check.content_check_state(folder) == "fail"


def test_content_check_state_ignores_recorded_pass_with_failing_mechanical(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "wf"
    _body(folder)
    _content_check(
        folder,
        result="pass",
        mechanical=[{"check": name, "ok": name != "citations_resolve", "detail": "fantasma"} for name in content_check.MECHANICAL_NAMES],
    )

    assert content_check.content_check_state(folder) == "fail"


def test_content_check_state_ignores_recorded_pass_with_unknown_criterion_ids(
    tmp_path: Path,
) -> None:
    """T5: recorded criterion ids must equal the current rubric ids."""
    folder = tmp_path / "wf"
    _body(folder)
    _rubric(folder)
    _content_check(
        folder,
        result="pass",
        criteria=[
            {"id": "objetivo", "status": "cumple", "where": "Objetivos", "note": "ok"},
            {"id": "inventado", "status": "cumple", "where": "X", "note": "ok"},
        ],
    )

    assert content_check.content_check_state(folder) == "fail"


def test_content_check_state_dedupes_id_comparison_not_sets(tmp_path: Path) -> None:
    """TRIANGULATE: duplicated recorded ids are not equal to the rubric ids."""
    folder = tmp_path / "wf"
    _body(folder)
    _rubric(folder)
    _content_check(
        folder,
        result="pass",
        criteria=[
            {"id": "objetivo", "status": "cumple", "where": "Objetivos", "note": "ok"},
            {"id": "objetivo", "status": "cumple", "where": "Otro", "note": "ok"},
        ],
    )

    assert content_check.content_check_state(folder) == "fail"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"drop": ("body_sha256",)},
        {"judges": [{"role": "drafter"}, {"role": "independent"}]},
        {"drop": ("bib_sha256",)},
        {"drop": ("result",)},
        {"drop": ("criteria",)},
        {"result": "tal vez"},
        {"schema": "academic.content-check/v2"},
    ],
)
def test_content_check_state_malformed_for_bad_marker_shapes(
    tmp_path: Path, kwargs: dict
) -> None:
    folder = tmp_path / "wf"
    _body(folder)
    _content_check(folder, **kwargs)

    assert content_check.content_check_state(folder) == "malformed"


def test_content_check_state_malformed_for_bad_files(tmp_path: Path) -> None:
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "content-check.yml").write_text("schema: [unclosed\n", encoding="utf-8")
    assert content_check.content_check_state(broken) == "malformed"

    flat = tmp_path / "flat"
    flat.mkdir()
    (flat / "content-check.yml").write_text("just a string\n", encoding="utf-8")
    assert content_check.content_check_state(flat) == "malformed"

    binary = tmp_path / "binary"
    binary.mkdir()
    (binary / "content-check.yml").write_bytes(b"\xff\xfe")
    assert content_check.content_check_state(binary) == "malformed"


def test_content_check_state_malformed_when_body_md_is_gone(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    _body(folder)
    _content_check(folder)
    (folder / "body.md").unlink()

    assert content_check.content_check_state(folder) == "malformed"


@pytest.mark.parametrize("judges", ["two independent judges", {"role": "independent"}, 7])
def test_non_list_judges_marker_is_stale_not_a_crash(tmp_path: Path, judges: object) -> None:
    """T11: a present-but-non-list ``judges`` field routes to stale, never raises."""
    folder = _verify_folder(tmp_path / "wf")
    _content_check(folder, judges=judges)

    assert content_check.content_check_state(folder) == "stale"


def test_non_list_judges_with_foreign_schema_is_malformed_not_a_crash(tmp_path: Path) -> None:
    """T11: ``len()`` on an unsized ``judges`` value must never raise TypeError."""
    folder = _verify_folder(tmp_path / "wf")
    _content_check(folder, judges=7, schema="academic.content-check/v2")

    assert content_check.content_check_state(folder) == "malformed"


# ---------------------------------------------------------------------------
# report-flow-hardening T14: a judge's single-quoted ``where`` fragments are
# advisory evidence; a fragment missing from body.md warns, never blocks.
# ---------------------------------------------------------------------------


def _quote_warnings(folder: Path) -> list[str]:
    return [f for f in _marker(folder)["findings"] if f.startswith("quote warning")]


def test_missing_quoted_fragment_warns_and_never_blocks(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    body_before = (folder / "body.md").read_bytes()
    first = _judgments(folder, name="a.yml", criteria=[
        {"id": "objetivo", "status": "cumple", "where": "seccion 'Instalacion de LuaLaTeX' del cuerpo", "note": "ok"},
        {"id": "metodologia", "status": "cumple", "where": "Metodologia", "note": "ok"},
    ])

    assert _run(folder, first) == 0

    marker = _marker(folder)
    assert marker["result"] == "pass"
    assert content_check.content_check_state(folder) == "pass"
    assert (folder / "body.md").read_bytes() == body_before
    assert _quote_warnings(folder) == [
        "quote warning: a.yml: criterion 'objetivo': "
        "quoted fragment not found in body.md: 'Instalacion de LuaLaTeX'"
    ]
    assert [c["status"] for c in marker["criteria"]] == ["cumple", "cumple"]
    assert len(marker["mechanical"]) == 4 and all(e["ok"] for e in marker["mechanical"])


def test_missing_quotes_warn_for_each_judge_file_before_merge(tmp_path: Path) -> None:
    """Provenance survives the strictest merge: each warning names its file."""
    folder = _verify_folder(tmp_path / "wf")
    first = _judgments(folder, name="a.yml", criteria=[
        {"id": "objetivo", "status": "cumple", "where": "cite 'fragmento ausente uno' aqui", "note": "ok"},
        {"id": "metodologia", "status": "cumple", "where": "Metodologia", "note": "ok"},
    ])
    second = _judgments(folder, name="b.yml", findings=["second"], criteria=[
        {"id": "objetivo", "status": "cumple", "where": "Objetivos", "note": "ok"},
        {"id": "metodologia", "status": "cumple", "where": "ver 'fragmento ausente dos' abajo", "note": "ok"},
    ])

    assert content_check.main([str(folder), "--judgments", str(first), "--judgments", str(second)]) == 0

    assert _quote_warnings(folder) == [
        "quote warning: a.yml: criterion 'objetivo': quoted fragment not found in body.md: 'fragmento ausente uno'",
        "quote warning: b.yml: criterion 'metodologia': quoted fragment not found in body.md: 'fragmento ausente dos'",
    ]


def test_multiple_missing_fragments_in_one_where_all_warn(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    first = _judgments(folder, name="a.yml", criteria=[
        {"id": "objetivo", "status": "cumple", "where": "'primera ausente' y 'segunda ausente'", "note": "ok"},
        {"id": "metodologia", "status": "cumple", "where": "Metodologia", "note": "ok"},
    ])

    assert _run(folder, first) == 0

    assert [w.split(": ", 4)[-1] for w in _quote_warnings(folder)] == ["'primera ausente'", "'segunda ausente'"]


def test_present_or_whitespace_normalized_quotes_do_not_warn(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    first = _judgments(folder, name="a.yml", criteria=[
        {"id": "objetivo", "status": "cumple", "where": "aparece 'Cuerpo con fuentes' tal cual", "note": "ok"},
        {"id": "metodologia", "status": "cumple", "where": "salto de linea 'Cuerpo\n\tcon   fuentes' normalizado", "note": "ok"},
    ])

    assert _run(folder, first) == 0

    assert _quote_warnings(folder) == []


def test_quoted_fragment_comparison_is_case_sensitive(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    first = _judgments(folder, name="a.yml", criteria=[
        {"id": "objetivo", "status": "cumple", "where": "no existe 'CUERPO con fuentes' en mayusculas", "note": "ok"},
        {"id": "metodologia", "status": "cumple", "where": "Metodologia", "note": "ok"},
    ])

    assert _run(folder, first) == 0

    assert len(_quote_warnings(folder)) == 1
    assert "objetivo" in _quote_warnings(folder)[0]


def test_ordinary_apostrophes_never_masquerade_as_quotes(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    _body(folder, DEFAULT_CITED_BODY + "\nDo not touch the student's own text: don't polish it.\n")
    first = _judgments(folder, name="a.yml", criteria=[
        {"id": "objetivo", "status": "cumple", "where": "don't polish the student's draft", "note": "ok"},
        {"id": "metodologia", "status": "cumple", "where": "citado 'the student's own text' existe", "note": "ok"},
    ])

    assert _run(folder, first) == 0

    assert _quote_warnings(folder) == []


def test_missing_quote_warning_does_not_soften_strictest_merge(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    first = _judgments(folder, name="a.yml")
    second = _judgments(folder, name="b.yml", findings=["second"], criteria=[
        {"id": "objetivo", "status": "falta", "where": "nunca aparece 'paso faltante'", "note": "gap"},
        {"id": "metodologia", "status": "cumple", "where": "Metodologia", "note": "ok"},
    ])

    assert content_check.main([str(folder), "--judgments", str(first), "--judgments", str(second)]) == 1

    marker = _marker(folder)
    assert marker["result"] == "fail"
    assert content_check.content_check_state(folder) == "fail"
    assert [c["status"] for c in marker["criteria"]] == ["falta", "cumple"]
    assert any(f.startswith("quote warning") and "b.yml" in f and "objetivo" in f for f in marker["findings"])


# ---------------------------------------------------------------------------
# report.yml `min_sources` override
# ---------------------------------------------------------------------------


def _min_sources_folder(folder: Path, value: str | None, bib_count: int = 1) -> Path:
    _report(folder)
    if value is not None:
        with (folder / "report.yml").open("a", encoding="utf-8") as handle:
            handle.write(f"min_sources: {value}\n")
    _sources_bib(folder, count=bib_count)
    _rubric(folder)
    _body(folder, "# Informe\n\nCuerpo con [@key1].\n")
    return folder


def test_min_sources_override_one_passes_with_one_cited_source(tmp_path: Path) -> None:
    folder = _min_sources_folder(tmp_path / "wf", "1")

    assert _run(folder) == 0

    eligible = _mechanical(_marker(folder), "eligible_sources_cited")
    assert eligible["ok"] is True
    assert eligible["detail"].startswith("1/1 eligible book or paper sources cited")


def test_absent_min_sources_still_requires_five_cited(tmp_path: Path) -> None:
    folder = _min_sources_folder(tmp_path / "wf", None)

    assert _run(folder) == 1

    eligible = _mechanical(_marker(folder), "eligible_sources_cited")
    assert eligible["ok"] is False
    assert "1/5" in eligible["detail"]


@pytest.mark.parametrize("bad", ["0", "-2", "'3'", "2.5", "true", "null"])
def test_invalid_min_sources_is_input_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], bad: str
) -> None:
    folder = _min_sources_folder(tmp_path / "wf", bad)

    assert _run(folder) == 2

    assert "min_sources" in capsys.readouterr().err
    assert not (folder / "content-check.yml").exists()


# ---------------------------------------------------------------------------
# Body format check (task 8a): level-1 headings and math sub/superscripts
# ---------------------------------------------------------------------------


def _body_problems(text: str) -> list[str]:
    return content_check.body_format_problems(text)


def test_body_without_level_one_heading_fails() -> None:
    problems = _body_problems("## Seccion\n\nTexto.\n\n### Sub\n")
    assert any("level-1" in problem and "# " in problem for problem in problems)


def test_body_with_level_one_heading_passes() -> None:
    assert _body_problems("# Seccion\n\n## Sub\n\nTexto.\n") == []


def test_level_one_heading_inside_a_fence_does_not_count() -> None:
    problems = _body_problems("## Seccion\n\n```\n# comentario\n```\n")
    assert any("level-1" in problem for problem in problems)


@pytest.mark.parametrize("text", ["c\u2081", "v\u2080", "10\u207b\u2075", "m/s\u00b2", "x\u00b3", "a\u2090"])
def test_unicode_sub_and_superscripts_fail_with_line_numbers(text: str) -> None:
    problems = _body_problems(f"# T\n\nlinea ok\nvalor {text} aqui\n")
    joined = " ".join(problems)
    assert "line 4" in joined
    assert "$c_1$" in joined and "$10^{-5}$" in joined and "m/s$^2$" in joined


def test_unicode_scripts_in_code_are_allowed() -> None:
    body = "# T\n\n```\nc\u2081 = 1\n```\n\nUsa `v\u2080` como nombre.\n"
    assert _body_problems(body) == []


def test_run_check_fails_on_format_defects_and_state_is_fail(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    (folder / "body.md").write_text(
        "## Informe\n\nc\u2081 con [@key1] y [@key2], [@key3], [@key4], [@key5].\n", encoding="utf-8"
    )
    assert _run(folder) == 1
    findings = " ".join(_marker(folder)["findings"])
    assert "level-1" in findings and "line 3" in findings


def test_body_check_mode_reports_without_writing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = _verify_folder(tmp_path / "wf")
    (folder / "body.md").write_text("## Informe\n\nTexto con [@key1].\n", encoding="utf-8")
    assert content_check.main([str(folder), "--body-check"]) == 1
    out = capsys.readouterr().out
    assert "level-1" in out
    assert not (folder / "content-check.yml").exists()


def test_body_check_mode_passes_a_clean_draft(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    assert content_check.main([str(folder), "--body-check"]) == 0
    assert not (folder / "content-check.yml").exists()


def test_body_check_results_select_checks_by_name_and_name_format_defects(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    (folder / "body.md").write_text("## Informe\n\nTexto con [@key1].\n", encoding="utf-8")

    results = {item["check"]: item for item in content_check.body_check_results(folder)}

    assert {"citations_resolve", "eligible_sources_cited", "body_format"} <= set(results)
    assert "judgments_match_rubric" not in results
    assert not results["body_format"]["ok"] and "level-1" in results["body_format"]["detail"]
    assert results["citations_resolve"]["ok"]


def test_body_check_output_labels_body_format_defects(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = _verify_folder(tmp_path / "wf")
    (folder / "body.md").write_text("## Informe\n\nTexto con [@key1].\n", encoding="utf-8")

    assert content_check.main([str(folder), "--body-check"]) == 1

    assert "[FAIL] body_format:" in capsys.readouterr().out


def test_marker_keeps_four_mechanical_entries_with_unambiguous_format_text(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    (folder / "body.md").write_text("## Informe\n\nTexto con [@key1].\n", encoding="utf-8")

    assert _run(folder) == 1

    marker = _marker(folder)
    assert [c["check"] for c in marker["mechanical"]][-1] == "rubric_checks"
    assert len(marker["mechanical"]) == 4
    assert "body_format: no level-1 heading" in marker["mechanical"][-1]["detail"]


# ---------------------------------------------------------------------------
# Bold pseudo-headings: the pre-approval check applies validate_report's rule
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    ["**Por el club**", '**Por el club (en adelante, "el club"):**'],
)
def test_body_format_flags_bold_pseudo_headings_with_line_numbers_and_hint(line: str) -> None:
    problems = _body_problems(f"# Contrato\n\n{line}\n\nTexto.\n")

    joined = " ".join(problems)
    assert "line 3" in joined and "##" in joined


def test_body_format_ignores_inline_bold_and_headings() -> None:
    assert _body_problems("# Contrato\n\nTexto con **negrita** inline.\n\n## Por el club\n") == []


def test_body_format_uses_the_validate_report_rule() -> None:
    import validate_report

    assert content_check.bold_pseudo_heading_lines is validate_report.bold_pseudo_heading_lines


def test_body_check_fails_on_bold_pseudo_heading(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = _verify_folder(tmp_path / "wf")
    (folder / "body.md").write_text("# Informe\n\n**Por el club**\n\nTexto con [@key1].\n", encoding="utf-8")

    assert content_check.main([str(folder), "--body-check"]) == 1

    out = capsys.readouterr().out
    assert "[FAIL] body_format:" in out and "line 3" in out


def test_body_check_surfaces_a_section_scope_warning_without_failing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Task 11(e): a contains check scoped to a heading the draft lacks warns, it does not add a failure."""
    folder = _verify_folder(tmp_path / "wf")
    scoped = {"type": "contains", "section": "Seccion inexistente", "text": "Texto"}
    results = content_check.body_check_results(folder)
    assert "rubric_scope" not in {item["check"] for item in results}

    import yaml
    data = yaml.safe_load((folder / "rubric.yml").read_text(encoding="utf-8"))
    data["criteria"][0]["checks"] = [scoped]
    (folder / "rubric.yml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    scope = {i["check"]: i for i in content_check.body_check_results(folder)}["rubric_scope"]
    assert scope["ok"] and "Seccion inexistente" in scope["detail"] and "warning" in scope["detail"].lower()
    content_check.main([str(folder), "--body-check"])
    assert "rubric_scope" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Judgment reuse for markup-only body changes (task 11 f)
# ---------------------------------------------------------------------------

PLAIN_BODY = (
    "# Informe\n\nEl cliente dijo \"entrega inmediata\" con fuentes [@key1], [@key2], "
    "[@key3], [@key4] y [@key5].\n\n- primer punto\n- segundo punto\n\n"
    "| a | b |\n| --- | --- |\n| uno | dos |\n"
)
MARKUP_BODY = (
    "# **Informe**\n\nEl cliente dijo “**entrega inmediata**” con fuentes [@key1], [@key2], "
    "[@key3], [@key4] y [@key5].\n\n* primer punto\n* _segundo_ punto\n\n"
    "| a  | b  |\n|:---|:---|\n| uno | dos |\n"
)


def _judged_pair(folder: Path) -> list[str]:
    """Two judgments files bound to the current body, carrying ``body_text_sha256``."""
    import yaml

    brief = yaml.safe_load(content_check.judge_brief(folder).split("Return only judgments YAML using this schema.")[1].split("\n", 1)[1].split("\nDouble-quote", 1)[0])
    paths = []
    for name, finding in (("a.yml", "first"), ("b.yml", "second")):
        path = _judgments(folder, name=name, findings=[finding])
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["body_text_sha256"] = brief["body_text_sha256"]
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        paths.append(str(path))
    return ["--judgments", paths[0], "--judgments", paths[1]]


def _reuse_folder(folder: Path) -> list[str]:
    _verify_folder(folder)
    _body(folder, PLAIN_BODY)
    return _judged_pair(folder)


def test_judge_brief_carries_the_normalized_text_hash(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    _body(folder, PLAIN_BODY)
    assert f"body_text_sha256: {content_check.body_text_sha256(PLAIN_BODY)}" in content_check.judge_brief(folder)
    assert content_check.body_text_sha256(PLAIN_BODY) == content_check.body_text_sha256(MARKUP_BODY)


def test_markup_only_edit_reuses_judgments(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    args = _reuse_folder(folder)
    _body(folder, MARKUP_BODY)
    assert content_check.main([str(folder), *args]) == 0
    marker = _marker(folder)
    assert "judgments reused: markup-only change" in _mechanical(marker, "judgments_match_rubric")["detail"]
    assert content_check.content_check_state(folder) == "pass"


def test_unchanged_body_has_no_reuse_note(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    args = _reuse_folder(folder)
    assert content_check.main([str(folder), *args]) == 0
    assert "reused" not in _mechanical(_marker(folder), "judgments_match_rubric")["detail"]


def test_one_word_edit_still_needs_new_judgments(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = tmp_path / "wf"
    args = _reuse_folder(folder)
    _body(folder, MARKUP_BODY.replace("primer", "tercer"))
    assert content_check.main([str(folder), *args]) == 2
    assert "judgments are for a different draft; re-run the judge" in capsys.readouterr().err


def test_added_character_still_needs_new_judgments(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    args = _reuse_folder(folder)
    _body(folder, MARKUP_BODY.replace("dos |", "dos. |"))
    assert content_check.main([str(folder), *args]) == 2


def test_rubric_change_blocks_reuse_even_for_markup_only_edit(tmp_path: Path) -> None:
    folder = tmp_path / "wf"
    args = _reuse_folder(folder)
    _body(folder, MARKUP_BODY)
    _rubric(folder, source="otra guia")
    assert content_check.main([str(folder), *args]) == 2


def test_stale_judgments_without_text_hash_are_not_reused(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")
    _body(folder, PLAIN_BODY)
    first, second = _judgments(folder, name="a.yml"), _judgments(folder, name="b.yml", findings=["x"])
    _body(folder, MARKUP_BODY)
    assert content_check.main([str(folder), "--judgments", str(first), "--judgments", str(second)]) == 2


def test_normalize_body_text_keeps_math_operators() -> None:
    """A change inside math is a content change: judgments must not be reused."""
    from content_check import body_text_sha256

    assert body_text_sha256("La masa es $a*b$.") != body_text_sha256("La masa es $ab$.")
    assert body_text_sha256("Vale $x^_$.") != body_text_sha256("Vale $x^$.")
    assert body_text_sha256("**Nota:** $x_1$") == body_text_sha256("Nota: $x_1$")


def _uncited_folder(folder: Path, body: str = "# Informe\n\nSin citas en el texto.\n") -> Path:
    _report(folder)
    with (folder / "report.yml").open("a", encoding="utf-8") as handle:
        handle.write("uncited_bibliography: true\n")
    (folder / "sources.bib").write_text("@misc{slides, title={Slides}}\n", encoding="utf-8")
    _rubric(folder)
    _body(folder, body)
    return folder


def test_uncited_bibliography_passes_without_citations(tmp_path: Path) -> None:
    folder = _uncited_folder(tmp_path / "wf")

    assert _run(folder) == 0

    marker = _marker(folder)
    eligible = _mechanical(marker, "eligible_sources_cited")
    assert eligible["ok"] is True
    assert eligible["detail"] == "uncited bibliography: 1 entry listed, no citations required"
    assert _mechanical(marker, "citations_resolve")["ok"] is True


def test_uncited_bibliography_still_resolves_cited_keys(tmp_path: Path) -> None:
    folder = _uncited_folder(tmp_path / "wf", "# Informe\n\nCita rota [@fantasma].\n")

    assert _run(folder) == 1

    marker = _marker(folder)
    assert _mechanical(marker, "citations_resolve")["ok"] is False
    assert _mechanical(marker, "eligible_sources_cited")["ok"] is True


def test_uncited_bibliography_body_check_passes(tmp_path: Path) -> None:
    folder = _uncited_folder(tmp_path / "wf")

    results = {item["check"]: item for item in content_check.body_check_results(folder)}

    assert results["eligible_sources_cited"]["ok"] is True


def _ape_folder(tmp_path: Path, headings: tuple[str, ...]) -> Path:
    folder = _verify_folder(tmp_path / "wf")
    report = folder / "report.yml"
    report.write_text(report.read_text(encoding="utf-8") + "format: ape\n", encoding="utf-8")
    body = "".join(f"# {title}\n\nTexto con [@key1].\n\n" for title in headings)
    (folder / "body.md").write_text(body, encoding="utf-8")
    return folder


def _ape_check(folder: Path) -> dict | None:
    return {i["check"]: i for i in content_check.body_check_results(folder)}.get("ape_structure")


def test_body_check_fails_ape_body_with_wrong_heading_title(tmp_path: Path) -> None:
    from validate_report import APE_BODY_HEADINGS

    titles = tuple("Materiales y Herramientas" if t.startswith("Materiales") else t for t in APE_BODY_HEADINGS)
    check = _ape_check(_ape_folder(tmp_path, titles))

    assert check is not None and not check["ok"]
    assert "Materiales, Reactivos, Equipos y Herramientas" in check["detail"]


def test_body_check_passes_correct_ape_headings(tmp_path: Path) -> None:
    from validate_report import APE_BODY_HEADINGS

    check = _ape_check(_ape_folder(tmp_path, APE_BODY_HEADINGS))

    assert check is not None and check["ok"]


def test_body_check_skips_ape_structure_for_other_formats(tmp_path: Path) -> None:
    folder = _verify_folder(tmp_path / "wf")

    assert _ape_check(folder) is None


def _brief_example(folder: Path) -> str:
    brief = content_check.judge_brief(folder)
    assert "Double-quote every string value" in brief
    return brief.split("```yaml\n", 1)[1].split("```", 1)[0]


def test_judge_brief_example_parses_with_parse_judgments(tmp_path: Path) -> None:
    folder = _checked_folder(tmp_path / "wf", checks=[], body=PLAIN_BODY, guide="guia\n")
    path = tmp_path / "example.yml"
    path.write_text(_brief_example(folder), encoding="utf-8")
    judgments, findings, _judge, _body_sha, _rubric_sha, errors = content_check.parse_judgments(path)
    assert errors == []
    assert judgments and findings


def _findings_file(tmp_path: Path, findings_yaml: str) -> Path:
    path = tmp_path / "j.yml"
    path.write_text(
        "judge: {role: independent}\ncriteria:\n  - id: a\n    status: cumple\nfindings:\n" + findings_yaml,
        encoding="utf-8",
    )
    return path


def test_parse_judgments_flattens_mapping_findings(tmp_path: Path) -> None:
    path = _findings_file(tmp_path, "  - {severity: WARNING, text: weak intro}\n  - {b: 2, a: x}\n  - plain\n")
    _j, findings, _judge, _b, _r, errors = content_check.parse_judgments(path)
    assert errors == []
    assert findings == ["WARNING: weak intro", "a: x; b: 2", "plain"]


@pytest.mark.parametrize("bad", ["  - 3\n", "  - [a, b]\n", "  - null\n"])
def test_parse_judgments_still_rejects_other_finding_types(tmp_path: Path, bad: str) -> None:
    _j, _f, _judge, _b, _r, errors = content_check.parse_judgments(_findings_file(tmp_path, bad))
    assert any("findings must be a list of strings" in e for e in errors)
