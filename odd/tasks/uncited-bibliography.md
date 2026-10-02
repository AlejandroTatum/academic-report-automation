# Uncited bibliography (academic route)

Branch `feat/uncited-bibliography` from `refactor/academic-report-flow` (f7a429b).

Motivation: a course (Simulación, Ing. José Guamán) requires no in-text citations and a
bibliography listing only the class slides (a `@misc` entry). The academic route today
demands at least one cited book/paper, so `eligible_sources_cited` and the research gate block.

Design: strict-bool `uncited_bibliography: true` in `report.yml` (academic route only, requires a
bibliography file, mutually exclusive with `min_sources`). When on:
- research gate passes with at least 1 entry of any type in the bib;
- `eligible_sources_cited` passes with an explicit detail;
- LaTeX build emits `\nocite{*}` + `\printbibliography` even with zero `\cite`;
- IEEE validation requires the bibliography section in the PDF and does not flag uncited entries.

## Tasks

- [x] 1. Config + source gate + content check (tests first) — commit `feat(tools): add uncited_bibliography opt-in to source gate and content check`
- [ ] 2. LaTeX build `\nocite{*}` + IEEE validation (tests first)
- [ ] 3. Skill reference docs (content, production, routing, data)
- [ ] 4. Apply to APE 1 Simulación report and build the preview
