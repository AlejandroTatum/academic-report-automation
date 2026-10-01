# Intake phase

Executor: academic-report-flow
Artifact: `reports/<wf>/report.yml`

Load this reference when `doc_status` returns `next: intake`, and on every execution of
the standalone full route (no work folder), before designing, structuring, drafting, or generating anything.
This skill executes the phase itself. Intake turns a request into the one
machine-readable record the whole route derives from: `reports/<wf>/report.yml`.

A prompt statement, prior document, template, or memory is a proposal, not a
confirmation: run the intake even when the prompt appears to already contain the answers,
and treat nothing from them as confirmed data.

## Content-first intake

Default when a work folder is driven by `doc_status`. Ask only the content-first
minimum: route, title, student, the teacher's guide and rubric material, teacher
explanation.

- Route: when the request or supplied material names an academic assignment (a
  subject or course, teacher, APE, AA, exercise/ejercicio, homework/tarea,
  practice/práctica, guide or rubric), record `route: academic` without asking and
  state it in the intake summary. Ask the route only when signals are absent or
  conflicting. This derivation exists only here: the standalone full route
  never infers the document type.
- `metadata.title` and `metadata.student` are the identity this phase is done on.
  A student identity the user explicitly saved as permanent (persistent memory or
  preference such as "use this name for all future sessions") counts as confirmed:
  intake records it without asking. Without such a saved preference, suggest the
  default student Alejandro Padilla through ask_user_choice as a single-choice
  confirmation, and never auto-fill without the user's answer. Never invent a name.
- Free-text sanity: a title (or any free-text identity answer) that holds
  commentary, a question or a complaint instead of a title is not accepted. Show
  the cleaned candidate and ask for a one-line confirmation.
- Guide material: intake always requests the teacher's guide, rubric and any
  teacher explanation when not already supplied, in the same single compact
  question batch as any other missing field. Never a second round, unless an
  answer is unusable.
- The teacher's guide and rubric material, plus any teacher explanation, stay as
  inputs for the `plan` phase; record the folder-relative `guide:` path in
  `report.yml`, run `tools/guide_facts.py <folder>` and, when it detects a family,
  record `format_hint: ape` or `format_hint: aa` for planning (not `format:`).
- `guide_facts.py` reports only what the guide states explicitly, and it never
  guesses. When one fact key carries several distinct explicit values (say, an
  APE guide that also says "aprendizaje autónomo", or two different "Semana N"
  numbers), the key moves to a `conflicts:` mapping that lists the conflicting
  explicit values, and the fact is omitted from the facts themselves: no value
  is picked, and a conflicted family produces no `format_hint` at all. Any fact
  the conflicts leave unresolved is asked through the existing structured
  question policy (`ask_user_choice`); it is never inferred from context. This
  contract is existing behavior, proven by `tools/test_guide_facts.py`.
- `metadata.date` and the optional record keys `metadata.audience`,
  `metadata.purpose`, `metadata.visual_direction`, top-level `template:`, `cover:`,
  and `output:` - fill them from supplied material when it names them, and never
  interrogate the user for them here.
- When the supplied requirement names the `.bib` as a submitted artifact, record
  `deliver_bibliography: true` (plus `bibliography:` when the file is not
  `sources.bib`) in `report.yml`: intake records the request, it never asks for
  it and never adds an approval gate for it.
- Group work (`metadata.practice_type: Grupal` and `metadata.members`) is decided
  at format, not intake. `metadata.subject` and `metadata.teacher` are recorded
  when the guide names them; the `format` phase completes whatever its chosen
  format still requires.
- Never ask formatting questions at intake (template, identity tables, cover,
  visual direction, output look, the document format APE, AA or libre, and the
  delivery format PDF or DOCX): the `format` phase owns every formatting decision,
  after the content is approved. Intake never asks the delivery format.
- Full-route confirmations that do not apply in content-first: audience and purpose
  (derived from supplied material and recorded, never asked), template and identity,
  delivery format (PDF or DOCX, asked by the `format` phase), and visual direction.
  Confirmations 2 to 5 below do not apply in content-first; Confirmation 1 is
  replaced by the route rule above.

## Full-route confirmations

Standalone run with no work folder. Stop after asking: do not pre-build, do not
draft "while waiting", do not produce a provisional structure.

### Confirmation 1 — Document type

Ask which domain the document belongs to:

1. University academic work
2. Project documentation
3. Professional/business report
4. Technical document
5. Other

- The skill MAY recommend one option, with a one-line reason drawn from the prompt.
- The skill MUST NEVER auto-select it, treat the recommendation as accepted, or continue on silence.
- There is no default type. No prior document, repository, file name, or format request determines it.

### Confirmation 2 — Audience and purpose

Capture **two independent fields**. Never collapse them into one answer.

| Field | Question |
| --- | --- |
| Audience | Who reads this document? |
| Purpose | What must the reader do after reading it? |

Examples of the pairing:

| Audience | Purpose |
| --- | --- |
| Teacher | Evaluate an activity |
| Technical team | Implement a solution |
| Client | Approve a proposal |
| Management | Make a decision |
| End user | Learn a procedure |

Audience and purpose drive structure, tone, and depth. A mismatch between them stops the run.

### Confirmation 3 — Template and identity

Ask whether any of the following applies:

- Mandatory template
- Institutional format
- Visual identity
- Logo
- Palette
- Typography
- Reference document to imitate
- Teacher, client, or company requirements

Rules:

- A template applies ONLY when the user confirms it. A template that is merely mentioned, guessed, inherited from a previous document, or found in the repository does not apply.
- If nothing is confirmed, record `Template/identity: none` and build without institutional shell, logo, or borrowed branding.

### Identity confirmation

Capture concrete author identity before generation:

- Individual report: the author's full name.
- Group report: the complete membership list — every member's full name.

Placeholder values (bracket templates such as `[Nombre del estudiante]`) and
blanks are rejected: they are instructions left in a template, not identity.
Group membership missing from the metadata fails validation and names the
missing members. The skill never prompts the user to choose a Paralelo: the
academic route renders A by default, and only an explicit assignment value
overrides it.

### Structure confirmation (#12)

Ask whether the teacher (or client/company) supplied a mandatory structure —
a rubric, an assignment brief, a template, or a transcribed section list.
Combine requirements from every supplied source; a contradiction between
sources (a section required by one and forbidden or reordered by another)
blocks confirmation until the user resolves it.

For each required section, record its exact title, its order, and at least
one mandatory content/rubric criterion. Quantitative limits (words, pages,
tables, figures, references) stay entirely optional per section: a limit is
recorded only when a source actually supplies it, and no limit is ever
inferred for a section that never declared one.

When no teacher structure exists, propose one structure appropriate to the
confirmed document type, audience, and purpose, then require explicit
confirmation before it is written to `report.yml`. The run never proceeds
with a provisional structure.

The confirmed structure is written to `report.yml` as `structure:` (see
`tools/structure_contract.py`). Downstream phases — research, drafting,
visual planning, generation — stay blocked while `structure:` is present but
not confirmed. A structure changed after confirmation (its recorded source
no longer matches) requires reconfirmation before generation resumes.

### Confirmation 4 — Delivery format

Ask for PDF, DOCX, or both. Always confirmed, never inferred.

A format request never implies a document type, a route, or an institutional shell.

### Confirmation 5 — Visual direction

Ask for one of:

| Direction | Short meaning |
| --- | --- |
| Sober | Neutral, highly legible, minimal decoration |
| Institutional | Confirmed branding, cover and metadata, formal hierarchy |
| Technical | Precise diagrams, traceability, compact tables, functional color |
| Executive | Summary first, few data points per page, impact charts |
| Custom | Requires additional user specification |

The chosen direction must materially change typography, composition, tables, charts, density, and hierarchy. It is never a decorative label, a theme name, or a cosmetic afterthought. Operational definitions live in `visual-directions.md`.

## Question scope

- Length, depth, page count, or extension MUST NOT be asked as a mandatory question. Derive them from audience, purpose, and route; ask only when the user raises them or the route genuinely cannot resolve them.
- No additional permanent questions may be introduced into this intake without explicit approval. Ad-hoc clarifications stay ad-hoc.
- Ask the confirmations compactly; do not turn the intake into an interrogation.
- Intake MAY ask one targeted clarification per missing route-mandatory field, drawn from the known input and configuration. Adaptivity is about data only: it never adds, duplicates, removes, or relocates the single confirmation gate.

## Document Contract

Render this block with the confirmed values. It is a data record of the intake answers: it is written to `report.yml` and does not authorize generation.

```
Document Contract

Type: Project documentation
Audience: Technical team and project reviewers
Purpose: Define implementation scope and expected behavior
Template/identity: KIPU visual identity; no UNL shell
Outputs: PDF and DOCX
Visual direction: Technical
```

Any change to a recorded field re-renders the block and overwrites the record.

## report.yml record

The Document Contract is written to `reports/<work-folder>/report.yml` as this
record. These are the keys the pipeline and the later phases actually read; do not
invent a parallel key for a meaning that already has one:

```yaml
# reports/<work-folder>/report.yml — the one machine-readable record the route derives from.
type: report                  # backend classification: essay | report | technical_report | visual | docx ...
route: project                # academic | project | business | technical | other
output: pdf                   # pdf | docx
# pdf: ../../outputs/<materia>/<slug>.pdf   # optional override; default is derived (see below)
template: plain               # only when a template was confirmed; omit it otherwise

metadata:
  title: "Manual de despliegue"
  student: "Nombre y apellido"         # author identity; author/nombre are accepted aliases
  # members: ["Nombre 1", "Nombre 2"]  # group reports only: the complete roster
  date: "2026-09-10"
  audience: "Equipo tecnico"            # Confirmation 2
  purpose: "Implementar el despliegue"  # Confirmation 2
  visual_direction: "Technical"         # Confirmation 5

cover:                        # top-level and optional: explicit values win over the route default
  required: true
  logo_required: true
  body_starts_on_page: 2

deliver_bibliography: true    # only when the course requires the .bib as a submitted artifact
bibliography: sources.bib     # the declared .bib to deliver (existing key; default sources.bib)
min_sources: 1                # only when the teacher/requirement limits sources; positive integer, default 5
```

- `pdf:` (and `docx:`) is optional and top-level. Leaving it unset derives the
  final path under the content root's outputs tree: `outputs/<materia>/<slug>.pdf`
  on the academic route when `metadata.subject` names a known subject, otherwise
  `outputs/<route category>/<slug>.pdf` (e.g. `outputs/tecnicos/<slug>.pdf`).
  Writing `pdf:` overrides the derived default.
- `route:` and `output:` are top-level. `metadata:` holds identity and the three
  recorded context fields (`audience`, `purpose`, `visual_direction`); Route A adds
  `subject` and `teacher`, and the other routes must not invent those.
- `cover:` is top-level as well. `cover_value` only reads `report.yml`'s own
  `cover:` key, so a nested `metadata.cover` is read nowhere and would silently
  leave the route default in force.
- Group reports declare the complete roster in `metadata.members` (aliases
  `integrantes`, `miembros`); `metadata.paralelo` stays optional data the intake
  never asks for.
- Route-derived rendering defaults (template, cover, section numbering, list of
  figures) resolve from the confirmed `route:` at build and validation time; an
  explicitly written value always wins. See `document-routing.md`.
- `deliver_bibliography: true` is recorded only when the supplied requirement
  names the bibliography as a submitted artifact: intake records it from the
  material it is given and never adds a question or an approval gate for it.
  The declared `.bib` (existing `bibliography:`/`bib:` selection, default
  `sources.bib`) then ships as a final deliverable whose exact bytes are bound
  by validation and final review. The default is `false`: a `sources.bib` that
  exists only for citations never travels.
- No other key is added for these meanings: there is no top-level `audience:`, no
  `document_type:`, and no `visual_direction:` outside `metadata:`.

The single confirmation gate does not live here. Intake records data only and never asks for approval to generate. Generation starts only after the one post-preview confirmation in `academic-report-flow/references/approval.md`.

## Stop rules

Done means `report.yml` exists, `route:` is a known route, and `metadata.title` and
`metadata.student` are present and real (not bracket templates or fill-in marks).
An unknown `route:` is `blocked` (`unknown_route`); a missing or placeholder
identity leaves intake `pending`, so the route keeps waiting at intake instead of
advancing.

Steps: resolve the route with the user; collect the minimum; write
`reports/<wf>/report.yml` with the confirmed data record; re-run `doc_status` and
report the new current phase.

Never:

- Write `approval.yml`, `rubric.yml`, `sources.bib`, or `validation.yml`, and do
  not build, validate, or publish anything: intake produces exactly one artifact.
- Add schema fields beyond the record above.
- Continue past a question: stop after asking.
