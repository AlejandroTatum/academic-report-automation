# Document routing

One route is resolved from Confirmation 1 of `document-intake.md`. Load only that route's references. Never blend routes, never fall back silently.

## Route A — University academic work

The ONLY route that may activate academic institutional machinery.

- Recommended sections: cover, metadata table, `Tema`, `Antecedentes`, `Desarrollo`/`Descripción`, comparative tables or conceptual maps, `Conclusiones`, `Bibliografía`.
- Activates: UNL shell, teacher, subject, parallel, academic period, institutional cover, rubric alignment, IEEE bibliography, teacher profile.
- Forbidden sections: executive summary framed for management decisions, commercial recommendations, sales or proposal language, product changelog.
- Format sources: `unl-shell.md`, the matching file in `profiles/`, the teacher's template or rubric when confirmed.
- Reading priorities: assignment wording first, then rubric, then teacher profile, then unit material, then external sources.
- `unl-shell.md` and `references/profiles/` load ONLY here. No other route may read them, regardless of requested output format.

## Route B — Project documentation

- Recommended sections, in priority order: project name and version, objective, audience, scope, context, modules, requirements, flows, architecture, decisions, risks, traceability, pending items.
- Forbidden — MUST NOT be auto-included: UNL cover, teacher, subject, institutional motto, academic footer, academic section numbering, and any "university submission" language.
- Cover: may be technical and brief, or omitted entirely when it adds no value. Never an institutional academic cover.
- Format sources: the project's own identity when confirmed in Confirmation 3; otherwise a neutral technical layout.
- Reading priorities: existing project artifacts and code, confirmed requirements, decisions already taken, open risks and pending items.

## Route C — Professional/business report

- Recommended sections, in order: executive summary, problem, evidence, analysis, impact, options, recommendation, risks, next steps.
- Headline information comes before technical detail. The reader must be able to decide from the first page.
- Forbidden sections: academic cover and metadata table, rubric alignment, IEEE bibliography as a required section, implementation-level technical appendices in the main flow.
- Format sources: confirmed company or client identity; otherwise sober/executive defaults.
- Reading priorities: business impact, evidence quality, decision options, cost and risk. Technical depth moves to annexes.

## Route D — Technical document

- Recommended sections, in order: purpose, scope, concepts, architecture, contracts, procedures, examples, errors, observability, verification, references.
- Forbidden sections: academic cover and institutional metadata, rubric language, executive persuasion framing, marketing copy.
- Format sources: the project's technical conventions and existing docs; confirmed identity when provided.
- Reading priorities: exact contracts and interfaces, reproducible procedures, real error paths, verification evidence.

## Route E — Other

- Build a specific contract with the user: name the sections, the forbidden content, the format sources, and the reading priorities before generating anything.
- Reuse fragments from other routes only when the user confirms each one.
- MUST NEVER fall silently back to the academic route, or to any other route, when the contract is incomplete. An incomplete Route E contract stops the run.

## Declaring the resolved route

The route is a decision the tooling cannot infer, so write it into `report.yml` before building. Without it every document is validated as university academic work.

| Route | `route:` value | Required metadata |
| --- | --- | --- |
| A | `academic` (or `a`) | `title`, `subject`, `teacher`, `student`, `date` |
| B | `project` (or `b`) | `title`, `student`, `date` |
| C | `business` (or `c`) | `title`, `student`, `date` |
| D | `technical` (or `d`) | `title`, `student`, `date` |
| E | `other` (or `e`) | `title`, `student`, `date` |

- An absent `route:` means Route A. That default exists so reports written before the key keep working; it is never a licence to omit the key on a non-academic document.
- An unrecognised value stops the run naming the accepted ones. There is no silent fallback.
- Declaring `subject` or `teacher` on a non-academic route warns: those fields are academic furniture the route forbids.
- `section_numbering: false` removes numbered headings, which Routes B, C and D forbid. Absent means numbered, so Route A needs nothing.
- These two keys carry the routing contract into the build. A route confirmed with Alejandro but never written to `report.yml` is not a resolved route.
