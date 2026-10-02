# UNL institutional shell

## Cover page from Alejandro's shared image

Default cover structure:

- Top centered UNL logo/brand area.
- Institution block, centered and uppercase:
  - UNIVERSIDAD NACIONAL DE LOJA
  - FACULTAD DE LA ENERGÍA, LAS INDUSTRIAS Y LOS RECURSOS NATURALES NO RENOVABLES
  - CARRERA COMPUTACIÓN
- Main activity title, centered:
  - `Aprendizaje Autónomo` when the assignment type matches autonomous learning.
  - `Actividad Nro. X` when activity number is known.
- Metadata table with left labels and right values:
  - Asignatura
  - Título
  - Tipo
  - Docente
  - Estudiante
  - Paralelo
  - Período Académico
  - Fecha
- Bottom centered italic text:
  - `Ciudad Universitaria "Guillermo Falconí Espinosa"`
  - `Universidad Nacional de Loja`

Student default:
- Alejandro Emanuel Padilla Espinoza
- Paralelo: A por defecto. Nunca se pregunta al usuario; si el encargo fija otro
  paralelo, se declara en `metadata.parallel` de report.yml y ese valor explícito
  prevalece sobre A.

Period default when no override is given:
- Marzo – Agosto 2026

## Header/footer for body pages

When no teacher-specific template overrides it:
- Use a compact institutional header with UNL identity and assignment/course metadata.
- Use a footer with student name and/or page number if present in the teacher's sample.
- If the provided template has a different header/footer, mirror the provided template.

## Formatting posture

- Professional academic layout.
- Do not overfit margins/font unless the teacher's template demands it.
- Keep PDF/DOCX readability above visual imitation.

## AA1 visual profile to preserve

When the teacher does not provide a conflicting template, match Alejandro's 10/10 `U1_AA1_AEPADILLA.pdf` style:

- Font family: formal serif — the original AA1 used DejaVu Serif, and the current automation pipeline defaults to **Times New Roman**.
  - LaTeX canonical chain: Times New Roman → TeX Gyre Termes.
  - Linux / WeasyPrint / render fallback may use Liberation Serif separately where configured.
  - Do **not** present Times → TeX Gyre → Liberation as one single LaTeX chain.
- Heading color: black only; do **not** use Word's default blue heading styles.
- Body text: justified, readable, academic; avoid oversized colored titles.
- Cover metadata table: black borders, light-gray label column, bold labels, clean padding.
- Body comparative tables: black borders, light-gray header row, compact text, no decorative colors.
- Body pages: logo at left in header, centered institution block, right boxed `CARRERA DE / COMPUTACIÓN / HE-CIS-2022`, horizontal rule under header.
- Footer: right-aligned italic `Educamos para Transformar`, with `Transformar` bold.
- Cover page should not repeat the body header/footer.

The automation pipeline expects two logo variants in `assets/`:
- `unl-logo-aa1.png` — plain logo (original AA1 reference).
- `unl-logo-aa1-transparent.png` — transparent variant used by the LaTeX pipeline (referenced via `{{LOGO_PATH}}`).

If the teacher provides a higher-resolution official logo/template, prefer that official source.
