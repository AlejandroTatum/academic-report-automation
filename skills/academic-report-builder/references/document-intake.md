# Document intake

Run this intake on **every** execution, before designing, structuring, drafting, or generating anything. Run it even when the prompt appears to already contain the answers: a prompt statement is a proposal, not a confirmation.

Stop after asking. Do not pre-build, do not draft "while waiting", do not produce a provisional structure.

## Confirmation 1 — Document type

Ask which domain the document belongs to:

1. University academic work
2. Project documentation
3. Professional/business report
4. Technical document
5. Other

- The skill MAY recommend one option, with a one-line reason drawn from the prompt.
- The skill MUST NEVER auto-select it, treat the recommendation as accepted, or continue on silence.
- There is no default type. No prior document, repository, file name, or format request determines it.

## Confirmation 2 — Audience and purpose

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

## Confirmation 3 — Template and identity

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

## Identity confirmation

Capture concrete author identity before generation:

- Individual report: the author's full name.
- Group report: the complete membership list — every member's full name.

Placeholder values (bracket templates such as `[Nombre del estudiante]`) and
blanks are rejected: they are instructions left in a template, not identity.
Group membership missing from the metadata fails validation and names the
missing members. The skill never prompts the user to choose a Paralelo: the
academic route renders A by default, and only an explicit assignment value
overrides it.

## Structure confirmation (#12)

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

## Confirmation 4 — Delivery format

Ask for PDF, DOCX, or both. Always confirmed, never inferred.

A format request never implies a document type, a route, or an institutional shell.

## Confirmation 5 — Visual direction

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
- No other key is added for these meanings: there is no top-level `audience:`, no
  `document_type:`, and no `visual_direction:` outside `metadata:`.

The single confirmation gate does not live here. Intake records data only and never asks for approval to generate. Generation starts only after the one post-preview confirmation in `document-workflow/references/approval.md`.
