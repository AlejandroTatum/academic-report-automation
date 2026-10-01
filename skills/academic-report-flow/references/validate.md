# Validate phase

Executor: academic-report-flow (`quality-gates.md`) or `gentle-ai review`
Artifact: `reports/<wf>/validation.yml`

Load this reference only when `doc_status` returns `next: validate`. This skill executes
the phase itself, following `quality-gates.md`, or hands the receipt to the native
`gentle-ai review` actor when receipt-driven development is on for the repository.

## Contract

Validation exists to record one pass or fail receipt for the exact final PDF the
generate phase produced. The phase produces exactly one artifact:
`reports/<wf>/validation.yml`, the validation receipt, with this schema:

    schema: academic.doc-validation/v1
    artifact_sha256: <hash of the final PDF that was validated>
    result: pass | fail
    mode: rdd | fallback
    gates: [BUILD_PASS, VALIDATION_PASS, ...]
    recorded_at: <ISO-8601 UTC>
    evidence: backups/quality_report.md | <opaque acknowledged review identifier>
    reason: <optional; why the RDD branch fell through to fallback, when it did>
    bibliography_sha256: <hash of the declared .bib; only when report.yml sets deliver_bibliography: true>

Done means `result: pass` and `artifact_sha256` matches the current final PDF. `result:
fail` is `blocked` (`validation_failed`); a missing receipt or a mismatched hash stays
`pending`. Validation is tied to one immutable artifact hash, so a receipt for stale
bytes never counts as a pass.

When the report declares its bibliography a deliverable (`deliver_bibliography: true`,
source selected by the existing `bibliography:`/`bib:` key), the receipt must also
record `bibliography_sha256`: the exact SHA-256 of the declared `.bib`, written only
after the applicable checks pass, exactly like `artifact_sha256` — there is no
production writer for this receipt, so the executor records both hashes the same way.
A missing, malformed, or stale bibliography hash keeps `validate` pending, and the
deliver gate refuses. Exporting the declared bytes imposes no extra DOI or
citation-style policy.

## Branch selection

Read `gentle-ai review mode status` once, read-only, before choosing a branch. Never
enable, activate, or turn on RDD on the user's behalf: the probe only observes the
repository's existing configuration, and this skill never changes it. An `on` status
selects the RDD branch. An `off` status, an absent `gentle-ai` binary, a non-zero exit,
or unparsable output selects the fallback branch, and an `unknown` status routes to the
fallback chain exactly like `off`, because an unknown state is never a reason to skip,
lower, or defer a gate.

The RDD candidate for a document is `reports/<wf>/**`, binary figures excluded. If the
native review STATUS preflight cannot bind a candidate scoped to that path — for example
it returns `next_transition.reason_code: intended_untracked_selection_required`, or the
returned `next_transition` otherwise cannot be bound to the work folder — fall through to
the fallback branch instead of leaving the phase unreachable, and record why in
`validation.yml` as `reason: <the unbindable condition>`.

## RDD branch (`mode: rdd`)

The native `gentle-ai review` flow performs the applicable check, and its gate verdicts
feed the same gate names the fallback branch reports. The receipt records `mode: rdd`,
and `evidence` holds the opaque acknowledged review identifier that flow returned, never
a paraphrased or self-issued approval. If the review flow cannot produce that
identifier, the run is not a `pass`.

## Fallback branch (`mode: fallback`)

The existing rendered validation chain, in order:

1. `validate_report.py` — `common` is mandatory, and PDF output also requires the
   mandatory `pdf_layout` gate.
2. `visual_pdf_auditor.py` prechecks — retain the report and `contact_sheet.png` as
   precheck evidence.
3. Rendered readback and semantic inspection — verify headings, paragraphs, captions,
   bibliography, tables, and figure labels are present, legible, and semantically
   equivalent to the intended source.

The receipt records `mode: fallback` and `evidence: backups/quality_report.md`.

## Gates

Both branches enforce the identical gate set: `BUILD_PASS`, `VALIDATION_PASS`,
`VISUAL_PASS`, `HUMAN_REVIEW`, `READY_TO_SUBMIT`. The fallback never lowers or skips a
gate reachable under RDD, and neither branch grants a gate it did not verify on the same
immutable artifact. Validation is not approval: an automatic receipt (build and validators alone) does not
grant `VISUAL_PASS`, `HUMAN_REVIEW`, or `READY_TO_SUBMIT`.

`VISUAL_PASS` ownership: the validate phase executor that performed the direct
page-by-page inspection (every page rendered and read back, no blocking defect)
records `VISUAL_PASS` in `validation.yml` `gates:`, and notes the inspection in the
evidence report. A receipt without an inspection never records `VISUAL_PASS`.
`READY_TO_SUBMIT` follows once `HUMAN_REVIEW` (`final-review.yml`) exists for the
same bytes; `deliver_report.py` reports it from the receipt plus that marker.

## Steps

1. Read `gentle-ai review mode status` once and select the branch as above.
2. Run the selected branch's checks against the current final PDF.
3. Write `reports/<wf>/validation.yml` with `artifact_sha256`, `result`, `mode`, `gates`,
   `recorded_at`, and `evidence`.
4. Re-run `doc_status` and report the new current phase.

## Never

- Do not enable, activate, or turn on RDD on the user's behalf, and do not treat an
  unknown status as a pass.
- Do not lower, skip, or rename a gate in either branch; the gate set is identical.
- Do not record a pass for an artifact hash that no longer matches the final PDF.
- Do not claim `VISUAL_PASS`, `HUMAN_REVIEW`, or `READY_TO_SUBMIT` from an automatic
  receipt alone; a receipt without an inspection never records `VISUAL_PASS`.
- Do not write `approval.yml`, `body.md`, or `report.yml`.
