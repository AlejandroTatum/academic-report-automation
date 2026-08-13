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

## Document Contract

Render this block with the confirmed values before generating anything:

```
Document Contract

Type: Project documentation
Audience: Technical team and project reviewers
Purpose: Define implementation scope and expected behavior
Template/identity: KIPU visual identity; no UNL shell
Outputs: PDF and DOCX
Visual direction: Technical
```

Generation begins only after the user confirms this block. Any change to a confirmed field re-renders the block and requires confirmation again.
