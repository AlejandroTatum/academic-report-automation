---
match:
  subject: Simulación
report_defaults:
  format: ape
  output: pdf
  uncited_bibliography: true
  figure_placement: here
  cover:
    required: false
delivery_dir_template: "~/Documents/Academicos/simulacion/unidad-{unit}/ape-{practice_number}-{slug}/documento/"
---
# Docente profile: Simulación — Ing. José O. Guamán Q.

Evidence basis: UNL Computación, ciclo 5. These rules were discovered one by one during APE 1 (2026-10-02); each one cost a review round. The front matter above is applied by `tools/course_profile.py` at intake; values already in `report.yml` win.

## Report rules

- Bibliography: only the unit slides. No other sources and no in-text citations (`uncited_bibliography: true`).
- Figures stay where they are written in the body (`figure_placement: here`).
- Document format is APE (`format: ape`); the delivery format is PDF.
- No cover page (`cover.required: false`).

## Delivery

Each APE lands in the course repo, one folder per practice:

`~/Documents/Academicos/simulacion/unidad-<unit>/ape-<practice_number>-<slug>/documento/`

The template resolves only when `metadata.unit`, the practice number (`metadata.practice_number` or the guide) and the title slug are known; otherwise set `delivery_dir:` by hand.

## Course repo layout

- `README`: only the iteration titles, nothing else.
- `referencias.bib`: the course bibliography file.
- `codigo/`: the practice code, MVC structure with Spanish comments.

Align the report with the unit slides before delivery; they are the only permitted source.
