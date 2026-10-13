# AA and ACD templates

Feature `aa-acd-templates`, branch `feat/aa-acd-templates` from `main` @ `1799f6f`. Engram mirror: `odd/aa-acd-templates/tasks`.
Give AA a dedicated template and add ACD as a new format, both from the user-approved independent mockups. APE stays as it is.

## Specs

- **S1 — Approved design source.** The user chose the independent proposals: "me gustan los independientes". The approved mockups are the visual contract:
  - AA: `outputs/template-proposals/aa-b-independiente/main.{tex,pdf}`. Editorial design: Source Serif 4 body, Source Sans 3 headings, green `#1F4E3D`, identification "ficha" in the left margin.
  - ACD: `outputs/template-proposals/acd-b-independiente/main.{tex,pdf}`. Session record sheet: IBM Plex Sans with IBM Plex Mono labels, brick red `#9C2F2A`.
  - The rationale is in `outputs/template-proposals/README.md`. The mockups are git-ignored, so the real templates must carry the design into `templates/`.
- **S2 — AA page 1 only is creative.** User: "el de AA, es creativo pero solo usaria esa creatividad pra la primera pagina".
  - Page 1 has the letterhead, the left-margin identification ficha and the large serif title.
  - Pages 2+ use a full-width layout with inline section numbers.
  - The template must stay correct when page-1 content length varies. Floats, display math or code that would land beside the ficha must be placed below it, never overlapping it.
- **S3 — ACD approved as is.** User: "del ACD me parece bien".
  - ACD becomes a new report format `acd`, selectable like `ape` and `aa`.
  - Its identification block includes the session topic and session date, as in the mockup.
- **S4 — Sections are defined and validated like APE.** User: "la mas solida es la de APE, las de AA y ACD no estan bien definidas". Each format gets a fixed, ordered section list, validated at draft time (content check) and at final validation, as `ape_structure_validation` does for APE.
  - AA: Objetivo(s); Introducción; Desarrollo (free subsections); Conclusiones; Referencias; Anexos (optional); Declaración de uso de IA (optional).
  - ACD: Objetivo(s); Síntesis de contenidos abordados; Actividades desarrolladas en clase; Análisis / reflexión; Conclusiones; Referencias; Anexos (optional).
- **S5 — Selection.** `format: aa` renders the new AA template by default, and `format: acd` renders the ACD template by default. The skill's format question offers APE, AA, ACD or libre.
- **S6 — APE unchanged.** Existing APE rendering, validation and tests keep passing unchanged.
- **S8 — Coverless by format.** User chose "Sí, por formato (recomendado)" to the question "¿Que APE, AA y ACD no lleven portada por defecto según el formato (cambia también APE)?".
  - Formats `ape`, `aa` and `acd` default to no cover, so validation does not require `cover: {required: false}` in report.yml.
  - An explicit cover setting in report.yml still wins.
  - No report that validates today may start failing.
- **S7 — Skill docs.** The `academic-report-flow` references describe the AA and ACD formats, their metadata and their sections; the skill contract tests cover them.

## Tasks

| ID | Specs | Route | Status | Commit |
|---|---|---|---|---|
| T1 | S4, S6 | worker: generalize per-format section structure validation (APE behavior unchanged) and add AA/ACD section lists | done | de53f40 |
| T2 | S1, S3, S4, S5 | worker: `acd` format key, metadata, `templates/acd-report.tex` from the ACD-B mockup, identification block, template default, course profile, tests | done | b5ee140 |
| T3 | S1, S2, S4, S5, S8 | worker: `templates/aa-report.tex` from the AA-B mockup, page-1 ficha from metadata, float/zone safety, `aa` default template, tests | done | 5216c14 |
| T4 | S5, S7 | inline: skill references, format question, conversation cases, contract tests; sync skills | done | d5d02ce |
| T5 | S1-S7 | verify: end-to-end render of sample AA and ACD reports through the real pipeline, visual check, full suite | pending | |

## Log

- **L1** (2026-10-13, user): "mejorar las plantillas para AA, ACD y APE, la mas solida es la de APE, las de AA y ACD no estan bien definidas uan"
- **L2** (user): "no tengo los formatos tengo que crearlos, el actual de AA no me gusta nada"
- **L3** (user): "dame dos propuestas pra cada tipo, una indpendiente y otra basada en APE, de ambas plantillas"
- **L4** (user): "me gustan los independientes, el de AA, es creativo pero solo usaria esa creatividad pra la primera pagina, del ACD me parece bien"
- **L5** (user, after the AA-B page-2+ revision): "aprobado"
- **L6** (evidence): exploration found:
  - `FORMAT_REQUIRED_METADATA` has only `aa`, `ape` and `libre` (`tools/report_config.py:292-301`), and there is no `acd` anywhere.
  - `aa` falls back to `unl-report.tex`.
  - APE structure: `ape_structure_validation` (`tools/validate_report.py:522-598`), `ape_identification_table` (`tools/build_latex_report.py:448`), `tools/test_ape_template.py`.
  - The local machine has no TeX engine; the renderer falls back to docker `texlive/texlive:latest` (lualatex).
- **L7** (T1 decisions):
  - Referencias behaves like the APE bibliography: the template prints it, so an authored heading is never required, but an authored one must sit after Conclusiones and before Anexos.
  - Only H1 headings are checked, as in APE.
  - No generic omit knob was added.
  - The draft checks are named `ape_structure`, `aa_structure` and `acd_structure`.
  - RED: ImportError on `section_structure_validation`. GREEN: 280 focused tests and 2391 in the full suite.
  - Consequence: AA drafts with a free structure now block approval until they have the S4 sections.
- **L8** (T1 handoff to T2/T3):
  - `metadata_validation` and `ReportConfig.load` still reject `format: acd`; T2 adds the key and an end-to-end test.
  - Annexes after the bibliography are wired only for APE (`split_annexes_markdown`, `APE_TEMPLATE_KEYS`); the AA and ACD templates need the same slot.
- **L9** (parent steer during T2): keep the ACD label column the user approved. Drive it from standard Markdown definition lists and drop only the minutes strip.
- **L10** (T2 result):
  - `acd` reuses the existing metadata keys: `title` is the session topic, `date` the session date and `practice_number` the ACD number. All 12 are required, with no new keys and no omit knob.
  - `ANNEXES_AFTER_BIBLIOGRAPHY_TEMPLATE_KEYS` now drives annex placement for APE and ACD; T3 adds AA with one entry.
  - `markdown_to_latex(definition_lists=)` is enabled only for `DEFINITION_LIST_TEMPLATE_KEYS` (ACD); other templates' output is unchanged.
  - RED: 31 failed and 21 errors. GREEN: 284 focused tests (parent rerun) and 2459 in the full suite (worker).
  - Real render: `outputs/_acd_scratch/sample-acd/build/acd-sample.pdf`. Page 1 matches the mockup (parent visual check).
  - Polish for T5: grid-style tables instead of the mockup's booktabs look; `\Needspace` leaves a large gap at the end of page 2; the footer shows the full uppercased name.
  - Open decision: `format: acd` (like APE) needs `cover: {required: false}` in report.yml, otherwise validation reports a mixed cover. A format-derived cover default would also change APE behavior.
  - Definition-list converter tests were written after the code, so there is no RED for them.
- **L11** (user, decision): "Sí, por formato (recomendado)". The ape, aa and acd formats default to no cover (S8), added to T3.
- **L12** (incident during T3): standalone probe builds published a scratch PDF to the real `.reports-system/automation/outputs/sistemas-operativos/main.pdf`.
  - Removed with user approval.
  - The new tests are now leak-proof: an autouse fixture monkeypatches `GLOBAL_OUTPUTS`, and probes use `publish_global: false`.
  - A possible T2 leftover in `outputs/desarrollo-basado-en-plataformas/` is kept by user decision ("no lo borres no hay problema").
- **L13** (user): "acabas t3, y paramos t4 en otra sesion". T4 and T5 move to a new session.
- **L14** (T3 result):
  - `templates/aa-report.tex`: the page-1 ficha zone narrows prose with `\parshape`. An `env/*/before` hook pushes tables, code and display math below the ficha, and `\suppressfloats[t]` keeps floats off the top of page 1. 10 real-PDF variants passed, and a mutant check confirmed the overlap reappears without the hook.
  - S8: `FORMAT_COVER_DEFAULTS` in `ReportConfig.cover_value`; an explicit `cover:` wins per key.
  - `format: aa` now defaults to `aa-report.tex`, and `template: unl` keeps the old look. Existing tests were adjusted accordingly: the route-defaults and cover-label tests now use `template: unl`, and the parent updated `test_format_choice.py`.
  - Definition lists stay off for AA.
  - RED: 30 failed and 25 errors. GREEN: 343 focused tests (worker) and 2563 in the full suite (parent).
  - Parent visual check of `outputs/_aa_scratch/sample-aa/build/aa-sample.pdf`: page 1 matches the mockup, and an early table drops below the ficha.
  - Polish for T5: the Gantt figure floats to the bottom of page 2, leaving a large gap; the tables use grid style; paragraphs are indented; the sample was not run through the visual auditor.
- **L15** (user, new session): "retoma lo de las plantillas". T4 resumed inline: a single unit with a known scope, so no worker.
- **L16** (T4 result):
  - The format question now reads "APE, AA, ACD or libre" in `doc_status.py` (approval batch, format guidance, unchosen-format detail), `approval.md`, `data.md`, `README.md`, `conversation-cases.md` and the Spanish flow diagram (SVG and PNG regenerated).
  - `approval.md` documents the `aa` (`aa-report.tex`, page-1 ficha, metadata, sections, `template: unl` fallback) and `acd` (`acd-report.tex`, session topic and date, reused APE keys, sections, definition lists) formats, plus the S8 no-cover default and the draft-time structure checks.
  - The three `not in guidance` assertions now check the new wording, so they no longer pass vacuously.
  - RED: 2 failed (missing wording). GREEN: 252 focused tests and 2565 in the full suite (parent). `sync_skills.sh --apply` passed its 188 contract tests and synced to `.claude`, `.codex` and `.pi` (opencode is absent).
  - `guide_facts.py` still detects only APE and AA as `format_hint`. ACD detection was not in scope.
