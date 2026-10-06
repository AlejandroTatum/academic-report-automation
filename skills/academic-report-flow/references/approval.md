# Approval - Decision 2 (draft approval + format batch)

Phases `approval` (human gate) and `format`. No executor is delegated to the gate: the orchestrator presents the prompt and only the human's explicit answer may produce the marker. `doc_status` offers it only once the body check passes (`content.md`) and the verify passes (`production.md`): verify runs before approval, so the human approves with the requirement matrix in hand.

## Marker

Artifact `reports/<wf>/approval.yml`, binding the exact bytes of `body.md` to a named human decision:

    schema: academic.doc-approval/v1
    body_sha256: <64 lowercase hex of the exact body.md bytes>
    approved_at: <ISO-8601 UTC>
    approved_by: <non-empty human identity>

Silence, an inferred yes, a restated plan, or an agent decision never produces `approval.yml`; a decline writes nothing. Done = marker exists and `body_sha256` matches the current `body.md`; absent or stale is `pending`, malformed is `blocked` (`approval_marker_malformed`). Never create, repair or refresh a marker except from a fresh explicit approval. Approval grants no build or delivery.

The gate prompt is lossless and blocking: complete decision, consequences and exact allowed answers, no silent default. The approver reads `body.md` in full: point to the complete body, never a summary, and say that generation happens only after this approval.

## Preview before asking

Before asking, build a preview with `build_report_auto.py <folder> --no-approval-check` (it records the sha256 of the `body.md` it rendered next to the PDF; `doc_status` keeps the gate closed with "rebuild the draft PDF" while that record is missing or differs from the current `body.md`), render every page and inspect it against the blocking-defect list in `production.md`. Fix layout defects in `body.md` first (re-run the body check), then rebuild. The message immediately before the approval `ask_user_choice` is the approval packet printed by `"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/approval_packet.py" <folder>`, pasted unchanged: clickable Markdown links with absolute `file://` URLs to the preview PDF, `body.md` and the latest DOCX draft, plus the verify result, the requirement matrix, the missing items, the deletion candidates and the findings. It flags a stale preview or verification; never present the gate without them, and never with either stale. The preview is never the final artifact: it predates `approval.yml`, so generate stays `pending` and the final build runs after approval.

## One batch: approval plus format

Ask in ONE batch, the same batch for approval and format, through `ask_user_choice` with suggested options, no free text: (1) approve `body.md` (exact bytes); (2) document format AA, APE or libre (`format_hint:` first when present), delivery format PDF or DOCX (`output:`), `format_spec` when `libre` is chosen (suggested options such as "documento sobrio sin portada" or "con portada"), and the metadata the chosen format still requires (subject, teacher, APE identification fields, group members). Never infer an answer and offer no default. On approval write `approval.yml` and record the answers in `report.yml` at the same time; a decline or edit order records nothing. Approval binds only `body.md` bytes; the format answers are plain `report.yml` data.

## Review loop - literal edit orders

The user answers with literal edit orders ("in paragraph X replace '...' with '...'", "delete section Y", "move this paragraph before that one"). Apply the user's text verbatim: never polish, rephrase or improve user-authored text; polishing forges authorship. Batch all literal edit orders from one reading into one round: apply them all verbatim, rebuild the preview PDF, and only then ask for re-approval with the same links. Every edit changes `body.md`, so the approval goes stale and the route returns to `approval` as `pending`; present the gate again for the new bytes. Each re-approval re-runs verify (fresh independent verifier), generate and validate before final review. The loop repeats until the user explicitly approves.

## Format (phase `format`, artifact `reports/<wf>/report.yml`)

Normally `done` without a stop because the batch already answered it. It is a completeness check plus fallback: when `report.yml` lacks a known `format:`, `output:` or that format's required metadata, ask only the missing fields `doc_status` names and never re-ask what `report.yml` records.

- One question for format selection through `ask_user_choice`: APE, AA, libre (hint first; the hint is not a choice, wait for the answer before recording `format:`). Metadata gaps are separate `ask_user_choice` prompts, never free text and never a second format-selection question.
- Delivery format PDF or DOCX is asked in the same format step, has no default, and is never inferred from the request or material; record it as `output:`.
- `ape`: practical-experimental technical report. Fixed sections: Objetivo(s), Materiales, Procedimiento (steps as a list), Resultados, Preguntas de Control, Conclusiones (tied to the objective), Recomendaciones, Bibliografía/Referencias (IEEE, or APA with `citation_style: apa`), Anexos. Extract its identification fields (cycle, unit, learning outcome, practice number and type, schedule, place, planned time) from the teacher's guide; the user only confirms or fills gaps. When `practice_type` is Grupal, record `metadata.members`.
- `aa`: the UNL academic template (`unl-report.tex`), look unchanged.
- `libre`: wait for the user's own specification and record it verbatim as `format_spec:`; the plain template applies by default.
- Every format cites with IEEE by default; `citation_style: apa` is the opt-in when the guide demands APA, on any route; `ape` and `aa` map to the academic route, `libre` to the plain template. Missing metadata keeps the phase `pending`; an unrecognised value is `blocked`, never a silent fallback. Never fill identification fields on the user's behalf.
