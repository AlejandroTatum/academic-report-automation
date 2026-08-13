# Clean-delivery contract

Final deliverables are copied to a dedicated user Documents destination that is
separate from sources, intermediates, and audits. Working evidence never leaves
its repo-defined work paths; the delivery folder receives only approved finals.

## Two spaces, never mixed

| Space | Content | Location |
| --- | --- | --- |
| Work paths | sources, manifests, specs, figures, backups, audits, intermediates, build output | Repo-defined: `reports/<work-folder>/`, `visuals/specs/`, `assets/generated/`, `outputs/<materia-slug>/` |
| Delivery folder | only approved final documents (PDF/DOCX) | A dedicated user Documents folder chosen per run |

## Rules

- Copy the approved final file(s) — normally one PDF per run — into the
  delivery folder after all gates pass.
- Never copy manifests, `report.yml`, `body.md`, `sources.bib`, specs, figures,
  audits, contact sheets, logs, or temp files into the delivery folder.
- The delivery folder must contain only clean final documents after the copy.
  Remove or refuse stray non-final files; never leave working evidence behind.
- Destination is explicit and configurable per run. Record the chosen path in
  the run output; do not hardcode one guide's path as a universal default.
- Prefer a fresh subfolder per deliverable (for example
  `~/Documents/Entregas_Academicas/<slug>/`) so different documents never mix.
