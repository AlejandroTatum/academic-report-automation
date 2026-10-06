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

## Tasks
- [x] T1 S7 APA polish: build SD APE1 as APA, list the remaining defects, fix them test-first. Route: inline. Commit: see Log L8
- [x] T2 S4,S5 Drafting rules in the skill (guide skeleton, answer first, theory only as needed, shrink to fix) plus contract tests. Route: inline. Commit: see L9
- [ ] T3 S6 Per-section word budget in the rubric plan and a `max_words` failure in validate; no minimum. Route: inline. Commit: —
- [ ] T4 S6 Filler detector in `--body-check` (filler phrases, paragraphs over 80 words). Route: inline. Commit: —
- [ ] T5 S3 Rubric plan derives one check per guide deliverable; a criterion with deliverables but only a heading check is rejected. Route: inline. Commit: —
- [ ] T6 S1 Single verify replaces `judgments-a/b.yml`: matrix file, link fetch, unmapped paragraphs; `content_check`, `doc_status` and skill updated. Contract change: independent verify. Route: worker. Commit: —
- [ ] T7 S2 Incremental re-verify of changed sections plus visual pass only on changed pages. Route: inline. Commit: —
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
