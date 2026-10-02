# APA citation style (opt-in)

Branch: `feat/apa-citation-style` (worktree `academic-report-automation-worktrees/pi`)

Goal: an opt-in top-level `citation_style: apa` in `report.yml` renders APA 7 in-text
citations `(Author, year)` and an APA reference list. Default stays `ieee`; every
existing report renders unchanged.

Trigger: Sistemas Digitales APE 1 guide requires "Referencias en formato APA"; the
pipeline hard-codes `style=ieee`.

Evidence: `texlive/texlive:latest` ships `apa.bbx`, `apa.cbx`, `csquotes.sty`.

Non-goals: APA in DOCX output (rejected with a clear error), CSL/pandoc citeproc,
renaming `validate_ieee` or the `ieee` validator key.

## Tasks

- [x] 1. `report_config`: `citation_style` strict enum (`ieee` default, `apa`), load-time check, tests.
- [x] 2. LaTeX build: `{{BIBLATEX_OPTIONS}}` placeholder in the four templates; APA uses `style=apa`, `sorting=nyt`, `\parencite`, Spanish APA mapping; tests.
- [x] 3. `validate_ieee_refs`: APA branch (author-year citations required, numeric `[n]` checks skipped, `s. f.` allowed); tests.
- [ ] 4. DOCX builder: reject `citation_style: apa` with a clear error; test.
- [ ] 5. Skill docs + contract test + `content_check` wording: document the opt-in.
- [ ] 6. Real build check: compile a sample report with `citation_style: apa` in Docker and inspect the PDF.

## Evidence log
- Task 1 `a282bc7`: RED 9 failed (test_citation_style_*), GREEN tools/test_report_config.py 73 passed.
- Task 2 `1b6a290`: RED 12 failed/4 passed (tools/test_citation_style_latex.py), GREEN 16 passed; tools/ suite 1754 passed.
- Task 3 `f1f0c65`: RED 4 failed (test_apa_* in tools/test_validate_ieee_refs.py), GREEN 19 passed.
