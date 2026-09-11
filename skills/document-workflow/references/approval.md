# Approval phase

Artifact: `reports/<wf>/approval.yml`

Load this reference only when `doc_status` returns `next: approval`. This phase is the
human gate: no executor is delegated, the orchestrator presents the lossless prompt,
and only the human's explicit answer may produce the marker. This skill never decides
for the human and never writes the marker on an inferred answer.

## Contract

Approval exists to bind the exact preview bytes to a named human decision before any
build. The phase produces exactly one artifact: `reports/<wf>/approval.yml`, the
approval marker, with this schema:

    schema: academic.doc-approval/v1
    preview_sha256: <64 lowercase hex of the exact preview.md bytes>
    approved_at: <ISO-8601 UTC, e.g. 2026-09-10T14:03:11Z>
    approved_by: <non-empty human identity>

The marker is the only record of consent. Silence, an inferred yes, a restated plan,
or an agent decision never produce `approval.yml`; a decline writes nothing. Approval
happens only after an explicit human answer to the lossless gate prompt, and this
skill's own judgement is never that answer.

The gate prompt is lossless and blocking: it states the complete decision, its
consequences, and the exact allowed answers, with no silent default. It says plainly
that generation happens only after this approval, and it never proceeds on silence, a
non-answer, or an agent-invented yes.

Done means `approval.yml` exists and its `preview_sha256` matches the current
`preview.md`. An absent marker is `pending`; a mismatch or a malformed marker is
`blocked` (`approval_marker_stale`, `approval_marker_malformed`). Once the preview
changes, any earlier marker goes stale and the one gate is presented again for the new
bytes.

## Steps

1. Present the lossless gate prompt with the complete decision and the exact allowed
   answers.
2. Write `reports/<wf>/approval.yml` only on the human's explicit affirmative answer,
   recording `preview_sha256`, `approved_at`, and `approved_by`.
3. On any other answer, write nothing and report approval as `pending`.
4. Re-run `doc_status` and report the new current phase.

## Never

- Do not infer consent from silence, a restated plan, a prior answer, or your own
  judgement: none of these ever produce `approval.yml`.
- Do not create, repair, or refresh the marker on an absent, stale, or malformed
  state; only a fresh explicit human approval produces a new one.
- Do not build, publish, or validate anything: approval produces exactly one artifact
  and grants no build or delivery.
