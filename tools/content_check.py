#!/usr/bin/env python3
"""The hard content check: record the agent's judgments, derive the verdict.

new-report-flow T3 makes the verify phase a two-sided contract. The AI agent
judges every rubric criterion in a judgments file -- a YAML/JSON mapping of
``criteria: [{id, status: cumple|flojo|falta, where, note}]`` plus optional
free-text ``findings`` (confusing paragraphs, figures serving no criterion).
This tool never generates those judgments; it validates them against the plan
(``tools/rubric_plan.py``), adds the deterministic mechanical checks over
``body.md`` and the document bib, and writes ``content-check.yml`` (schema
``academic.content-check/v1``) with the derived ``result``: ``pass`` only when
every criterion is ``cumple`` AND every mechanical check is ok, so the agent
can never declare a pass by itself.

Mechanical checks reuse the repo's existing citation helpers instead of a new
regex: ``validate_ieee_refs.cited_keys``/``bib_keys`` for `[@key]` extraction
and resolution, and ``source_count.eligible_entry_keys``/``MIN_ACADEMIC_SOURCES``
for the at-least-five-eligible-sources-cited gate (T2).

The check reports findings and never rewrites the draft: its only write is
``content-check.yml``. ``body.md`` bytes flow into ``body_sha256`` exactly as
``approval.yml`` binds them, ``rubric.yml`` and the document bib into
``rubric_sha256``/``bib_sha256`` (new-report-flow T5), so
``content_check_state`` can detect any input edited after the check and route
the phase back to ``stale``. A missing or unreadable file is data, never a
crash: ``content_check_state`` never raises. The marker is written atomically
(temp file + ``os.replace``), so a crash can never leave a half-written verdict.

``content_check_state`` also never trusts the recorded ``result`` blindly: it
re-derives the verdict from the recorded criteria (every status ``cumple``),
the recorded mechanical checks (every ``ok``), and the recorded criterion ids
(equal to the current rubric ids) -- a forged ``result: pass`` fails.

CLI: ``python tools/content_check.py <report-folder> --judgments <file>``
exits 0 on pass, 1 on fail, 2 on usage/input error.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import rubric_plan
import rubric_checks
import yaml
from approval_marker import BODY_NAME, sha256_file
from report_config import ReportConfig, read_yaml
from source_count import MIN_ACADEMIC_SOURCES, eligible_entry_keys
from validate_ieee_refs import bib_keys, cited_keys

CONTENT_CHECK_NAME = "content-check.yml"
CONTENT_CHECK_SCHEMA = "academic.content-check/v1"
JUDGMENT_STATUSES = ("cumple", "flojo", "falta")
RESULT_VALUES = ("pass", "fail")
MECHANICAL_NAMES = {"citations_resolve", "eligible_sources_cited", "judgments_match_rubric", "rubric_checks"}

# Keys content-check.yml must carry for content_check_state to trust it; the
# per-check ``mechanical`` entries and ``criteria`` judgment records are
# validated by presence here and by their producers above.
REQUIRED_MARKER_KEYS = (
    "schema",
    "body_sha256",
    "rubric_sha256",
    "bib_sha256",
    "judge",
    "checked_at",
    "criteria",
    "findings",
    "mechanical",
    "result",
)


@dataclass(frozen=True)
class CheckOutcome:
    """The result of one content-check run.

    ``errors`` non-empty means a usage/input error: nothing was written and
    ``result``/``marker`` carry no verdict. Otherwise ``marker`` is the exact
    mapping written to ``content-check.yml``.
    """

    result: str
    marker: dict
    errors: tuple[str, ...]


def _guide_input(folder: Path, config: ReportConfig) -> str | None:
    """Resolve the optional guide once, rejecting paths outside this report."""
    raw = config.raw.get("guide")
    if not raw:
        return None
    relative = Path(str(raw))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("guide must be relative to the report folder")
    root = folder.resolve()
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("guide must remain inside the report folder")
    if not resolved.is_file():
        return None
    return str(resolved.relative_to(root))


def judge_inputs(folder: Path, config: ReportConfig) -> list[str]:
    """Exact report-relative names available to the independent judge."""
    inputs = [rubric_plan.RUBRIC_NAME, BODY_NAME,
              Path(str(config.raw.get("bibliography") or config.raw.get("bib") or "sources.bib")).name]
    guide = _guide_input(folder, config)
    if guide:
        inputs.append(guide)
    return inputs


def judge_brief(folder: Path) -> str:
    """A self-contained, read-only assignment with hashes for the current draft."""
    folder = folder.resolve()
    if rubric_plan.rubric_state(folder) != "valid":
        raise ValueError("rubric.yml missing or malformed")
    for name in (BODY_NAME, rubric_plan.RUBRIC_NAME):
        if not (folder / name).is_file():
            raise ValueError(f"{name} missing or unreadable")
    config = ReportConfig(folder=folder, raw=read_yaml(folder / "report.yml"))
    inputs = judge_inputs(folder, config)
    schema = {
        "judge": {"role": "independent", "inputs": inputs},
        "body_sha256": sha256_file(folder / BODY_NAME),
        "rubric_sha256": sha256_file(folder / rubric_plan.RUBRIC_NAME),
        "criteria": [{"id": "<rubric criterion id>", "status": "cumple|flojo|falta",
                      "where": "<quoted location in body.md>", "note": "<reason>"}],
        "findings": [],
    }
    return ("You are an independent read-only judge. Judge only from these inputs; "
            "do not use the drafting conversation or any other files. Do not edit any file.\n"
            "Citations [@key] in body.md render in IEEE format at build time from sources.bib; citation keys are expected, not a formatting defect. Check that cited keys exist in sources.bib instead.\n"
            "Allowed input paths (absolute):\n"
            + "\n".join(str(folder / name) for name in inputs)
            + "\nReturn only judgments YAML using this schema. Judge every rubric criterion; "
              "allowed statuses: cumple|flojo|falta. Quote where locations.\n"
            + yaml.safe_dump(schema, sort_keys=False))


def parse_judgments(path: Path) -> tuple[list[dict], list[str], dict, str, str, list[str]]:
    """Parse an agent judgments file into ``(judgments, findings, errors)``.

    A judgments file is the agent's *input* contract, so a structural violation
    (bad YAML, non-mapping, missing id, unknown status) is a usage error the
    caller reports with exit code 2 -- unlike an unknown criterion id, which is
    well-formed input that simply fails the mechanical check. ``where`` and
    ``note`` are optional and recorded as plain strings.
    """
    name = Path(path).name
    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [], [], {}, "", "", [f"{name} is not valid UTF-8; save it as UTF-8"]
    except OSError:
        return [], [], {}, "", "", [f"{name} unreadable"]

    try:
        data = yaml.safe_load(text)
    except Exception:
        return [], [], {}, "", "", [f"{name} is not valid YAML"]
    if not isinstance(data, dict):
        return [], [], {}, "", "", [f"{name} must be a YAML mapping"]

    records = data.get("criteria")
    if not isinstance(records, list) or not records:
        return [], [], {}, "", "", [f"{name} criteria must be a non-empty list"]

    errors: list[str] = []
    judgments: list[dict] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            errors.append(f"{name} judgment {index} must be a mapping")
            continue
        cid = record.get("id")
        status = record.get("status")
        if not isinstance(cid, str) or not cid.strip():
            errors.append(f"{name} judgment {index} missing or blank id")
            continue
        if status not in JUDGMENT_STATUSES:
            allowed = ", ".join(JUDGMENT_STATUSES)
            errors.append(f"{name} judgment {index} (id '{cid}') status must be one of: {allowed}")
            continue
        where = record.get("where")
        note = record.get("note")
        judgments.append(
            {
                "id": cid,
                "status": status,
                "where": where if isinstance(where, str) else "",
                "note": note if isinstance(note, str) else "",
            }
        )

    findings = data.get("findings") or []
    if not isinstance(findings, list) or any(not isinstance(f, str) for f in findings):
        errors.append(f"{name} findings must be a list of strings")
        findings = []
    return judgments, findings, data.get("judge"), data.get("body_sha256"), data.get("rubric_sha256"), errors


def mechanical_checks(
    body_text: str, bib_text: str, criteria: list[dict], judgments: list[dict]
) -> list[dict]:
    """Derive the deterministic per-check entries (``check``/``ok``/``detail``).

    (a) every ``[@key]`` citation in body.md resolves to a bib entry;
    (b) at least ``MIN_ACADEMIC_SOURCES`` distinct eligible book/paper entries
        are actually cited in body.md (not merely present in the bib);
    (c) every rubric criterion id has exactly one judgment and no unknown ids.
    """
    cited = cited_keys(body_text)
    known_bib = bib_keys(bib_text)
    eligible = set(eligible_entry_keys(bib_text))
    unresolved = sorted(cited - known_bib)
    eligible_cited = sorted(cited & eligible)

    checks: list[dict] = []

    if cited:
        detail = f"{len(cited) - len(unresolved)}/{len(cited)} cited keys resolve to bib entries"
        if unresolved:
            detail += f"; unresolved: {', '.join(unresolved)}"
    else:
        detail = "no [@key] citations in body.md"
    checks.append({"check": "citations_resolve", "ok": not unresolved, "detail": detail})

    checks.append(
        {
            "check": "eligible_sources_cited",
            "ok": len(eligible_cited) >= MIN_ACADEMIC_SOURCES,
            "detail": (
                f"{len(eligible_cited)}/{MIN_ACADEMIC_SOURCES} eligible book or paper "
                f"sources cited in body.md"
                + (f": {', '.join(eligible_cited)}" if eligible_cited else "")
            ),
        }
    )

    known_ids = [str(criterion.get("id")) for criterion in criteria]
    counts = Counter(str(judgment["id"]) for judgment in judgments)
    problems: list[str] = []
    missing = [cid for cid in known_ids if counts.get(cid, 0) == 0]
    if missing:
        problems.append(f"no judgment for: {', '.join(missing)}")
    unknown = sorted(set(counts) - set(known_ids))
    if unknown:
        problems.append(f"unknown ids: {', '.join(unknown)}")
    duplicated = sorted(cid for cid, count in counts.items() if count > 1)
    if duplicated:
        problems.append(f"duplicate judgments: {', '.join(duplicated)}")
    detail = "; ".join(problems) or f"every criterion judged exactly once ({len(known_ids)} criteria)"
    checks.append({"check": "judgments_match_rubric", "ok": not problems, "detail": detail})

    return checks


def _read_bib(config: ReportConfig) -> str:
    """Read the document bib through ReportConfig.bib_path, tolerating bad files.

    A missing, unreadable or non-UTF-8 bib becomes empty text, so the mechanical
    checks fail closed (unresolved citations, zero eligible sources) instead of
    crashing -- the same tolerance source_count.source_gate applies.
    """
    bib = config.bib_path
    if bib is None:
        return ""
    try:
        return bib.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


def _sha256_or_empty(path: Path | None) -> str:
    """The hex digest of ``path``, or ``""`` when it is absent/unreadable.

    The empty string is the recorded identity of 'this input did not exist when
    the check ran', so a file that appears (or disappears) afterwards changes
    the binding and the state goes stale.
    """
    if path is None:
        return ""
    try:
        return sha256_file(path)
    except OSError:
        return ""


def _write_marker_atomically(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` so readers never see a half-written marker.

    The temp file sits beside the target (same filesystem, so ``os.replace`` is
    atomic) and is removed even when the replace fails, so a crashed check
    never leaves a ``content-check.yml.tmp`` behind for the next run to trip on.
    """
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def run_check(
    folder: Path, judgments_path: Path, config: ReportConfig | None = None
) -> CheckOutcome:
    """Run the content check for a report folder and write content-check.yml.

    The only file this function writes is ``content-check.yml``; ``body.md`` is
    read for hashing and citation extraction and never modified. On a usage or
    input error (missing folder/rubric/body, malformed judgments) nothing is
    written and ``errors`` names the offending file.
    """
    folder = Path(folder)
    if not folder.is_dir():
        return CheckOutcome("", {}, (f"report folder not found: {folder}",))

    if rubric_plan.rubric_state(folder) != "valid":
        return CheckOutcome(
            "", {}, (f"{rubric_plan.RUBRIC_NAME} missing or malformed; run the plan phase first",)
        )

    body_path = folder / BODY_NAME
    try:
        body_text = body_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return CheckOutcome("", {}, (f"{BODY_NAME} is not valid UTF-8",))
    except OSError:
        return CheckOutcome("", {}, (f"{BODY_NAME} missing or unreadable",))

    judgments, findings, judge, judged_body, judged_rubric, errors = parse_judgments(judgments_path)
    if errors:
        return CheckOutcome("", {}, tuple(errors))
    if config is None:
        # Build directly (doc_status's production rule): a missing report.yml is
        # an empty mapping, so the bib default (sources.bib) still applies.
        config = ReportConfig(folder=folder, raw=read_yaml(folder / "report.yml"))

    try:
        expected_inputs = judge_inputs(folder, config)
        criteria = rubric_plan.load_rubric(folder)
        rubric_hash = sha256_file(folder / rubric_plan.RUBRIC_NAME)
    except (OSError, ValueError, TypeError) as exc:
        return CheckOutcome("", {}, (f"rubric or guide missing, malformed or unreadable: {exc}",))
    if not criteria:
        return CheckOutcome("", {}, ("rubric.yml missing or malformed",))
    if not isinstance(judge, dict) or judge.get("role") != "independent":
        errors.append("judge.role must be independent")
    elif judge.get("inputs") != expected_inputs:
        errors.append(f"judge.inputs must list exactly: {', '.join(expected_inputs)}")
    if not isinstance(judged_body, str) or not isinstance(judged_rubric, str):
        errors.append("body_sha256 and rubric_sha256 are required")
    elif judged_body != sha256_file(body_path) or judged_rubric != rubric_hash:
        errors.append("judgments are for a different draft; re-run the judge")
    if errors:
        return CheckOutcome("", {}, tuple(errors))

    checks = mechanical_checks(body_text, _read_bib(config), criteria, judgments)
    rubric_results = [vars(item) for item in rubric_checks.run_checks(folder, criteria, body_text)]
    failed = [item for item in rubric_results if not item["ok"]]
    statuses = {item["id"]: item["status"] for item in judgments}
    detail = "; ".join(
        f"{item['criterion_id']} check {item['check_index']} ({item['type']}): {item['detail']}"
        + (" (judged cumple despite failing check)" if statuses.get(item["criterion_id"]) == "cumple" else "")
        for item in failed
    ) or f"all {len(rubric_results)} rubric checks pass"
    checks.append({"check": "rubric_checks", "ok": not failed, "detail": detail})
    mechanical_ok = all(check["ok"] for check in checks)
    criteria_ok = all(judgment["status"] == "cumple" for judgment in judgments)
    marker = {
        "schema": CONTENT_CHECK_SCHEMA,
        "body_sha256": sha256_file(body_path),
        "rubric_sha256": _sha256_or_empty(folder / rubric_plan.RUBRIC_NAME),
        "bib_sha256": _sha256_or_empty(config.bib_path),
        "judge": judge,
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "criteria": judgments,
        # The agent's free-text findings verbatim, plus every mechanical
        # failure so the human reads one artifact, not two.
        "findings": list(findings)
        + [f"{check['check']}: {check['detail']}" for check in checks if not check["ok"]],
        "mechanical": checks,
        "rubric_check_results": rubric_results,
        "result": "pass" if mechanical_ok and criteria_ok else "fail",
    }
    _write_marker_atomically(
        folder / CONTENT_CHECK_NAME,
        yaml.safe_dump(marker, sort_keys=False, allow_unicode=False),
    )
    return CheckOutcome(str(marker["result"]), marker, ())


def content_check_state(report_dir: Path) -> str:
    """Derive the verify-phase state of a report folder without touching it.

    Exactly one of ``absent|malformed|stale|fail|pass``. A marker that cannot
    be read or is missing required keys is ``malformed``; a marker whose
    ``body_sha256``, ``rubric_sha256`` or ``bib_sha256`` no longer matches the
    folder is ``stale`` (the draft, the rubric or the bib changed since the
    check). The recorded ``result`` is never trusted blindly: the verdict is
    re-derived from the recorded criteria (every status ``cumple``), the
    recorded mechanical checks (every ``ok``) and the recorded criterion ids
    (equal to the current rubric ids), so a forged ``result: pass`` fails.
    Never raises, never writes.
    """
    folder = Path(report_dir)
    path = folder / CONTENT_CHECK_NAME
    if not path.is_file():
        return "absent"

    try:
        data = read_yaml(path)
    except Exception:
        return "malformed"
    if not isinstance(data, dict):
        return "malformed"
    if data.get("schema") == CONTENT_CHECK_SCHEMA and ("judge" not in data or "rubric_sha256" not in data):
        return "stale"
    for key in REQUIRED_MARKER_KEYS:
        if data.get(key) is None:
            return "malformed"
    if not isinstance(data["judge"], dict) or data["judge"].get("role") != "independent":
        return "malformed"
    if data["schema"] != CONTENT_CHECK_SCHEMA:
        return "malformed"
    if data["result"] not in RESULT_VALUES:
        return "malformed"
    if not isinstance(data["criteria"], list) or not data["criteria"]:
        return "malformed"
    mechanical = data["mechanical"]
    if (not isinstance(mechanical, list)
            or len(mechanical) != len(MECHANICAL_NAMES)
            or any(not isinstance(entry, dict) or type(entry.get("ok")) is not bool
                   for entry in mechanical)
            or {entry["check"] for entry in mechanical if isinstance(entry.get("check"), str)} != MECHANICAL_NAMES):
        return "malformed"

    body_path = folder / BODY_NAME
    if not body_path.is_file():
        return "malformed"
    try:
        body_hash = sha256_file(body_path)
    except OSError:
        return "malformed"
    if str(data["body_sha256"]).strip().lower() != body_hash:
        return "stale"

    rubric_path = folder / rubric_plan.RUBRIC_NAME
    rubric_hash = _sha256_or_empty(rubric_path if rubric_path.is_file() else None)
    if str(data["rubric_sha256"]).strip().lower() != rubric_hash:
        return "stale"

    try:
        config = ReportConfig(folder=folder, raw=read_yaml(folder / "report.yml"))
        bib_path = config.bib_path
    except Exception:
        bib_path = None
    if str(data["bib_sha256"]).strip().lower() != _sha256_or_empty(bib_path):
        return "stale"

    criteria = data["criteria"]
    criteria_ok = all(
        isinstance(record, dict) and record.get("status") == "cumple" for record in criteria
    )
    mechanical_ok = all(
        isinstance(entry, dict) and entry.get("ok") is True for entry in data["mechanical"]
    )
    try:
        planned = rubric_plan.load_rubric(folder)
        if not planned or rubric_plan.rubric_state(folder) != "valid":
            return "malformed"
    except Exception:
        return "malformed"
    if rubric_plan.count_checked_criteria(planned):
        recorded = data.get("rubric_check_results")
        expected = [(c["id"], index, check["type"])
                    for c in planned for index, check in enumerate(c.get("checks", []), start=1)]
        if not isinstance(recorded, list) or [
            (item.get("criterion_id"), item.get("check_index"), item.get("type"))
            for item in recorded if isinstance(item, dict)
        ] != expected or len(recorded) != len(expected) or any(
            not isinstance(item, dict) or item.get("ok") is not True for item in recorded
        ) or not any(
            isinstance(entry, dict) and entry.get("check") == "rubric_checks" and entry.get("ok") is True
            for entry in data["mechanical"]
        ):
            mechanical_ok = False
    recorded_ids = [str(record.get("id")) for record in criteria if isinstance(record, dict)]
    current_ids = [str(criterion.get("id")) for criterion in planned]
    ids_match = len(recorded_ids) == len(current_ids) and set(recorded_ids) == set(current_ids)
    return "pass" if criteria_ok and mechanical_ok and ids_match else "fail"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the hard content check for a report folder (never edits body.md)."
    )
    parser.add_argument("folder", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--judgments", type=Path)
    mode.add_argument("--judge-brief", action="store_true")
    args = parser.parse_args(argv)
    if args.judge_brief:
        try:
            print(judge_brief(args.folder))
        except (ValueError, OSError) as exc:
            print(f"content check input error: {exc}", file=sys.stderr)
            return 2
        return 0

    outcome = run_check(args.folder, args.judgments)
    if outcome.errors:
        for error in outcome.errors:
            print(f"content check input error: {error}", file=sys.stderr)
        return 2

    print(f"content check: {outcome.result}")
    for check in outcome.marker["mechanical"]:
        mark = "ok" if check["ok"] else "FAIL"
        print(f"  [{mark}] {check['check']}: {check['detail']}")
    for finding in outcome.marker["findings"]:
        print(f"  finding: {finding}")
    return 0 if outcome.result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
