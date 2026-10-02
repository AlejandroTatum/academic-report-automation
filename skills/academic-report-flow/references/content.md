# Content - sources, plan, draft

Stages `research`, `plan`, `draft`; one artifact each. After each: re-run `doc_status`, report the new phase. No stage writes another stage's artifact, `approval.yml` or `validation.yml`.

## Research (executor `research-workflow`, artifact `reports/<wf>/sources.bib`)

Research is mandatory: at least 5 (or the report's `min_sources:`) eligible entries in the document's own BibTeX file (or the `bibliography:`/`bib:` path in `report.yml`): `book`, `inbook`, `incollection`, `article`, `inproceedings`, `conference`, `phdthesis`, `mastersthesis`, `techreport`. Web-only `@misc`/`@online` never count; `doc_status` keeps the phase `pending` until the file holds them. `min_sources: N` (top-level positive integer, invalid values rejected) replaces the minimum only when a requirement limits sources; `min_sources: 0` (no bibliography, nothing to cite or verify, no references section) is accepted only on a non-academic route, and the academic route always needs at least 1.

- Every entry is real and verifiable (author, title, year, publisher/venue): never invent a source, locator, quotation, date, author or finding. Citations are IEEE (biblatex `style=ieee`); no other style exists in this route.
- Protocol: `research-workflow` (`references/research-protocol.md`). Its `research/evidence-matrix.md` (and `evidence.yml`) is pre-document evidence: it never satisfies the phase or chooses type, structure, style or prose.
- Local inspected sources feed the bibliography: `"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/source_library.py" pack --only-inspected <query>` over `$REPORT_CONTENT_ROOT/academic-sources/manifest.yml`. Only `inspected: true` entries are eligible; an uninspected source stays a `lead`, never in `sources.bib`.
- After writing `sources.bib`, run `"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/verify_sources.py" "$REPORT_CONTENT_ROOT/reports/<work-folder>/"`. Finish only when every entry is VERIFIED or VERIFIED_WITH_WARNINGS; fix or replace MISMATCH and NOT_FOUND, give NO_IDENTIFIER entries a DOI or ISBN and verify again.

## Plan (artifact `reports/<wf>/rubric.yml`, schema `academic.rubric/v1`)

A confirmed teacher template is mirrored too: its sections, order and formatting. The plan mirrors the teacher's rubric: one criterion per rubric item (`id`, `title`, optional `weight`), each mapped to the body section that satisfies it. A rubric item no section can satisfy is a gap to raise with the user, never a criterion to drop, merge or invent.

- No teacher rubric: criteria come only from the guide's explicit demands (sections, questions, deliverables it states); never from the agent's idea of a good report. With neither rubric nor explicit demands, ask the user instead of inventing criteria.
- `format_hint: ape`: map criteria and checks to the fixed APE sections (Objetivo(s), Materiales, Procedimiento, Resultados, Preguntas de Control, Conclusiones, Recomendaciones, Bibliografía/Referencias, Anexos); the hint guides planning, never chooses the format.
- Write deterministic `checks:` before the draft exists for every mechanically checkable criterion (rubric TDD: red now, the draft turns them green). Types: `heading_present`, `contains`, `matches`, `verbatim_from_guide`, `ordered_list`, `min_citations`, `figure_referenced`, `link_present`, `keywords_from_section`. Checks are document-wide by default: use `section:` only when the property must live in that section (a heading restructure breaks scoped checks). Purely semantic criteria may have none.
- Run `"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/rubric_plan.py" "$REPORT_CONTENT_ROOT/reports/<work-folder>/"`; it blocks on a malformed rubric (`rubric_malformed`).

## Draft (artifact `reports/<wf>/body.md`)

The draft phase produces exactly one artifact: the full body the user will review, from `rubric.yml` and the researched sources, in the document's language. Cover every rubric criterion in the section the plan mapped, with proposed figures where they genuinely help (built with `academic-visual-builder`, referenced `![caption](relative/path.png)`). Cite with `[@key]` resolved against `sources.bib`; every claim traces to an entry there.

- Style: human and natural, neither overly technical nor flattering or obsequious. Model the tone on how the user writes (their messages in the session). No stock AI phrasing, no padding. The draft is a starting point for the user's review, offered for literal edit orders, not admiration.
- Body format (the template and font depend on it): sections start at `# ` (a body using only `##`/`###` numbers them 0.1.); `##` only for subsections under a `#`. Write sub/superscripts as math, never Unicode: `$c_1$`, `$10^{-5}$`, `m/s$^2$`.
- Presentation defaults (numbering, cover, template) come from `report.yml`, never from the draft.
- Gate before presenting: run `"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/content_check.py" "$REPORT_CONTENT_ROOT/reports/<work-folder>/" --body-check`. It runs the mechanical part (format rules, citations resolve, every rubric check green), exits 1 on any FAIL and writes nothing; `doc_status` runs the same check and keeps `next: draft` until it passes, so approval is never offered early. Fix failures in the draft; the draft never writes judgments.
- Done = `body.md` has non-whitespace content (unreadable is `blocked`). The draft never writes `approval.yml`, never builds, hashes or publishes, and never presents the approval gate. After approval the body changes only through the user's literal edit orders (`approval.md`).
