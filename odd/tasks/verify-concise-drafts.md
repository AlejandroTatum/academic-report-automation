# Verify instead of judges, concise drafts, APA polish

Feature `verify-concise-drafts`. Branch `feat/verify-concise-drafts`, stacked on the unmerged
`feat/apa-citation-style` @ `0e32203`. Worktree `academic-report-automation-worktrees/pi`.
Engram mirror: `odd/verify-concise-drafts/tasks`, project `academic-report-automation`.

## Specs
- S1 Replace the two judges with one verify: "en general no me gusta como van los jueces, prefiero un verify".
  The verify scores nothing. It produces a requirement → evidence matrix (requirement | location in the
  report | verified evidence | found/missing). It opens links and checks data against the guide. Evidence it
  cannot find is `missing`, never "seems to comply".
- S2 Speed: "se demora mucho para dar un buen resoltado". After an edit, verify and the visual pass cover
  only what changed. One approval packet holds the preview PDF, the verify matrix and the missing items.
- S3 Every guide deliverable becomes a deterministic check in the plan, for example one Wokwi link per part,
  the required tables and the answered questions. Audit evidence: the SD APE1 `informe-entrega` criterion had
  only a heading check, and the missing Part A/D Wokwi links passed both judges.
- S4 No padding: "me esats entregando basura en el borrador, ningun trabajo me pide mas texto, ni un minimo de
  palabras". The skeleton comes from the guide/rubric, and a paragraph that answers no requirement is deleted.
  Each question is answered in its first sentence, with at most 2–3 justification sentences. Data, specs and
  math go in tables or equations. Findings are fixed by shrinking or cutting, never by adding prose.
- S5 No basic concepts: "casi todos los trabajos se exitienden por preguntas basicas, conceptos confusos y por
  esa razon tambien el trabajo demora mas". Theory covers only the concepts the report's decisions use, one
  sentence each. Basic course definitions are forbidden.
- S6 Length budget, never a minimum: the plan assigns each section a word budget from its rubric weight and
  sets a total `max_words`. Going over fails. The body check flags filler phrases and paragraphs of more than
  80 words. The verify lists unmapped paragraphs as deletion candidates.
- S7 APA polish: "otro aspecto es terminal de pulir los documentos generados en formato APA". Known defects
  to reproduce (memory 2026-10-04):
  - a raw multi-key `[@a; @b]` citation
  - no spacing between bibliography entries
  - `@misc` web titles not in italics (use `@online`)
  - Spanish "y" (fixed in cfb9eda; re-check)
  - URLs splitting after "https:" (fixed in 0ee7272; re-check)

## Design T6 (single verify)
- Input file `verification.yml`, schema `academic.verification/v1`, written by ONE independent read-only
  verifier subagent from `content_check.py --verify-brief` (replaces `--judge-brief`):
  - `verifier: {role: independent, inputs: [...]}`, with the same allowed inputs as the old `judge.inputs`.
  - `body_sha256` and `rubric_sha256` bind the current files. The markup-only reuse rule stays.
  - `requirements:` is a list of `{criterion, requirement, status: found|missing, location, evidence}`. Every
    rubric criterion needs at least one requirement. `requirement` quotes the guide/rubric demand.
    `evidence` is an exact quote from body.md and is required when `found`.
  - `unmapped_paragraphs:` is a list of strings: the first words of paragraphs that answer no requirement
    (deletion candidates, reported and non-blocking).
  - `findings:` is a list of strings.
- content_check, deterministically:
  - A `found` requirement whose evidence quote is not in body.md (whitespace-normalized) is downgraded to
    `missing`, with a finding naming it. This is the anti-hallucination rule; it would have caught "Wokwi
    links all present".
  - Per-criterion status: `cumple` when all its requirements are found, `falta` otherwise; no `flojo`.
  - Mechanical `links_resolve` via a new `tools/link_check.py` with an injectable fetcher. Every http(s) URL
    in body.md gets a HEAD request, with GET as fallback and a short timeout. HTTP 404/410/other 4xx/5xx
    FAIL; DNS/timeouts are a warning finding (offline must not block); results are cached per URL in the run.
  - `result: pass` iff every criterion is cumple and every mechanical check is ok.
- Marker `content-check.yml` keeps its schema name. New markers record `verifier`, `requirements` and
  `unmapped_paragraphs` instead of `judges`/`disagreements`. Existing two-judge markers stay readable and
  valid (delivered reports must not regress); only new runs use the verifier.
- CLI: `--verification <file>` (exactly one) replaces `--judgments` x2; `--verify-brief` replaces
  `--judge-brief`. The brief lists rubric criteria, deliverables, already-run rubric checks and tolerance
  rules (kept from T10), and tells the verifier never to score, to quote evidence exactly, and to mark
  missing when it cannot quote.
- doc_status verify-phase texts say "re-run the verifier"; production.md/SKILL.md/contract tests drop the
  two judges and describe the single verify.

## Tasks
- [x] T1 S7 APA polish: build SD APE1 as APA, list the remaining defects, fix them test-first. Route: inline. Commit: see Log L8
- [x] T2 S4,S5 Drafting rules in the skill (guide skeleton, answer first, theory only as needed, shrink to fix) plus contract tests. Route: inline. Commit: see L9
- [x] T3 S6 Per-section word budget in the rubric plan and a `max_words` failure in validate; no minimum. Route: inline. Commit: see L10
- [x] T4 S6 Filler detector in `--body-check` (filler phrases, paragraphs over 80 words). Route: inline. Commit: see L10
- [x] T5 S3 Rubric plan derives one check per guide deliverable; a criterion with deliverables but only a heading check is rejected. Route: inline. Commit: see L11
- [x] T6 S1 Single verify replaces `judgments-a/b.yml`: matrix file, link fetch, unmapped paragraphs; `content_check`, `doc_status` and skill updated. Contract change: independent verify. Route: worker. Commit: see L12
- [x] T7 S2 Incremental re-verify of changed sections plus visual pass only on changed pages. Route: inline. Commit: see L13
- [ ] T8 S2 Single approval packet (preview PDF + matrix + missing items). Route: inline. Commit: —
- [ ] T9 S1–S7 E2E on the SD APE1 guide: compare words, rounds and time against the delivered v001. Route: inline. Commit: —

## Log
- L1 (2026-10-05) "como vamos con esta skill, el ultimo trabajo entregado no me gusto, en general no me gusta
  como van los jueces, prefiero un verify, asi mismo se demora mucho para dar un buen resoltado, has un analisis
  de los ultimos documentos generados y como podemos ir mejorando tomando en cuentas mis dolencias como usuario"
- L2 Audit of 4 runs (Engram #9880). Judge findings: 3 real gaps, 2 false positives, 2 that caused bloat,
  2 real defects missed. Judge disagreements were [] in all 4 runs. SD took about 35 h over 2 approval cycles.
- L3 User accepted the 5-point verify proposal: "si".
- L4 "si y aparte del cambio a verify, tambien me esats entregando basura en el borrador, ningun trabajo me pide
  mas texto, ni un minimo de palabras, y casi todos los trabajos se exitienden por preguntas basicas, conceptos
  confusos y por esa razon tambien el trabajo demora mas, que podemos hacer por esa parte"
- L5 "si sumalo al plan"
- L6 "otro aspecto es terminal de pulir los documentos generados en formato APA"
- L8 T1 evidence. The SD APE1 rebuild (scratch copy) showed the multi-key cite, "y", entry spacing, italics
  and URLs already correct. Two defects remained: `sorting=nyt` listed "(s.f.)" after the dated work by the
  same author (APA 7, 9.47), and the wording read "Consultado el … desde". Fixed with biblatex-apa sorting and
  the strings "Recuperado el … de". RED: 6 failed. GREEN: 31 focused tests and 1955 in the full suite.
  The real PDF shows the fix.
- L7 "si dale arranca y culmina el plan completo, luego haces pruebas sobre este tema tipos de simulaciones"
- L9 T2 evidence: concision block in content.md Draft plus a SKILL.md hard rule. RED: 2 contract tests failed.
  GREEN: 1957 passed. Passive skill prose with static tests, so no native review.
- L10 T3+T4 evidence, one work unit since they share the new `tools/concision.py`.
  - Rubric gains optional total and per-criterion `max_words`, with a weight-share fallback.
  - The body check adds `word_budget`, `filler_phrases` and `long_paragraphs`, and all three fail the gate.
  - The budget lives in the pre-approval body check, not in validate, because it must block before the
    user reads the draft.
  - RED: collection error plus 9 failures. GREEN: 1980 passed.
  - Calibration on real bodies: SD flagged its three bloated "Resultado y justificación" paragraphs (99,
    120 and 146 words), Métodos 1, Simulación and CataClub 0. No filler false positives.
- L10b T3/T4 review `review-bc764463694c4ade`. One CRITICAL (an unclosed `$$` hid the rest of the body, so the
  gate failed open) was corrected in `bd22d59`: unclosed blocks count as prose. Targeted validation approved;
  acknowledged and burned. Advisories (informational): filler list readability, multi-line HTML comments
  counted, an unmatched budget section is silently ok.
- L11 T5 evidence: criterion `deliverables:` (non-empty list of strings). `rubric_plan` rejects a criterion
  with fewer non-heading checks than deliverables; content.md documents it. RED: 8 failed. GREEN: 1993
  passed. With this rule, the SD APE1 rubric (`informe-entrega`, a heading check only) would have been
  rejected at plan time.
- L11b T5 review `review-6e736a75efc17537`: approved, acknowledged and burned; advisories informational.
- L12 T6 evidence.
  - Route: worker `muw8lvbf-2-rh79`. RED: 9 failing tests plus 2 uncollectable modules. GREEN reported as
    2026; the parent re-ran it: 2026 passed.
  - Legacy two-judge markers of the 4 delivered reports still read `pass` (same as HEAD).
  - Parent fixes: `routing.md` verify row; the brief splits plural demands into one requirement per item.
  - Real E2E on an SD APE1 scratch copy: one verifier ran from `--verify-brief`. It found real gaps the
    two judges missed: the general objective omits "Reconocer la arquitectura", there is no cover sheet,
    and table numbering diverges from the guide. It listed 3 deletion candidates.
  - It still marked "Enlaces públicos de Wokwi" found on Part B alone, hence the split rule above and T5
    deliverables.
  - `content_check --verification` on a subset: `links_resolve` checked 10 real links, all resolve;
    result fail (exit 1) on the missing requirements, as designed.
- L12b T6 review `review-ae4035a4a2cb7b3d`. One CRITICAL (R4-002): `link_check` let a `ValueError` from an
  unparseable URL escape and abort verify without a marker. Fixed test-first in d16f0d9 (11 lines); the
  targeted validator approved; acknowledged and burned. The facade cannot pass `baseRef` in this harness, so
  STATUS, the correction plan and the validator capture ran through the provider CLI with the user's consent.
  Follow-ups (advisory): `http.client.HTTPException` subclasses still escape `_check_one`; the docstring
  omits the `ValueError` path.
- L13 T7 evidence. 367722e: `content_check --verify-brief --since <previous verification.yml>` records
  `section_sha256` per criterion (markup-normalized `concision.section_text`), re-checks only criteria whose
  section changed and embeds the carried requirements to copy verbatim; a rubric change forces a full verify;
  carried quotes are still re-checked by run_check. RED 9, GREEN 10. 769269e: `visual_pdf_auditor` writes
  `page_hashes.json` (pixel hashes, DPI-bound); a later audit in the same folder lists **Changed pages** in
  visual_qa.md and draws `changed_contact_sheet.png`; production.md now inspects only changed pages after a
  correction. RED 6, GREEN 6. Full suite: 2042 passed.
