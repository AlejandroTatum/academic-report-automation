# Approval phase - the human gate on the draft

Artifact: `reports/<wf>/approval.yml`

Load this reference only when `doc_status` returns `next: approval`. This phase is the
human gate: no executor is delegated, the orchestrator presents the lossless prompt,
and only the human's explicit answer may produce the marker. This skill never decides
for the human and never writes the marker on an inferred answer.

## Contract

Approval exists to bind the exact bytes of `body.md` to a named human decision before
any build. The phase produces exactly one artifact: `reports/<wf>/approval.yml`, the
approval marker, with this schema:

    schema: academic.doc-approval/v1
    body_sha256: <64 lowercase hex of the exact body.md bytes>
    approved_at: <ISO-8601 UTC, e.g. 2026-09-10T14:03:11Z>
    approved_by: <non-empty human identity>

The marker is the only record of consent. Silence, an inferred yes, a restated plan,
or an agent decision never produce `approval.yml`; a decline writes nothing. Approval
happens only after an explicit human answer to the lossless gate prompt, and this
skill's own judgement is never that answer.

The gate prompt is lossless and blocking: it states the complete decision, its
consequences, and the exact allowed answers, with no silent default. The approver
reads `body.md` in full, so the orchestrator must present or point to the complete
body, never a summary. It says plainly that generation happens only after this
approval, and it never proceeds on silence, a non-answer, or an agent-invented yes.

## The review loop - literal edit orders

Between drafts the user answers with literal edit orders: "in paragraph X replace
'...' with '...'", "delete section Y", "move this paragraph before that one". Apply
the user's text VERBATIM: never polish, never rephrase, and never improve
user-authored text - the wording is theirs, and polishing it forges authorship.
Batch all literal edit orders from one reading into one round: collect them all,
apply them verbatim, and only then ask for re-approval. Each re-approval re-runs
verify (with a fresh independent judge), generate and validate before final review.
Every applied edit changes `body.md`, which stales the approval and returns the
route to `approval` as `pending`; present the gate again for the new bytes. That
loop is the normal review cycle, not a failure, and it repeats until the user
explicitly approves.

Done means `approval.yml` exists and its `body_sha256` matches the current
`body.md`. An absent marker is `pending`; a body that changed after approval is
`pending` again - the review loop - and the one gate is presented again for the new
bytes; a malformed marker is `blocked` (`approval_marker_malformed`).

## Steps

1. Present the lossless gate prompt with the complete decision and the exact allowed
   answers, pointing the approver to the complete `body.md`.
2. Between answers, apply the user's literal edit orders verbatim and re-present the
   gate for the edited bytes.
3. Write `reports/<wf>/approval.yml` only on the human's explicit affirmative answer,
   recording `body_sha256`, `approved_at`, and `approved_by`.
4. On any other answer, write nothing and report approval as `pending`.
5. Re-run `doc_status` and report the new current phase.

## Never

- Do not infer consent from silence, a restated plan, a prior answer, or your own
  judgement: none of these ever produce `approval.yml`.
- Do not polish, rephrase, or otherwise improve user-authored text while applying
  edit orders: the user's words go in exactly as given.
- Do not create, repair, or refresh the marker on an absent, stale, or malformed
  state; only a fresh explicit human approval produces a new one.
- Do not build, publish, or validate anything: approval produces exactly one artifact
  and grants no build or delivery.
