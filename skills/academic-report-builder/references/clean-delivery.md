# Clean-delivery contract

Generation never publishes. The build ends at the validated final PDF under
`outputs/<materia-slug>/` and reports its SHA-256; it writes nothing into
`~/Documents`. Delivery is a separate, explicit step run through
`tools/deliver_report.py`, which is the only publication route.

Delivery requires a current `approval.yml` marker (`APPROVAL_CURRENT`) and a
`validation.yml` receipt recording `result: pass` for the exact final PDF bytes.
`deliver_report.py` re-checks the receipt against the current bytes and the
publisher re-checks the marker; a missing or stale marker, or a receipt bound to
other bytes, refuses delivery before anything is created. When both hold, the
validated artifact is published in the user's Documents library. Publication is a
technical-copy status, not human approval.

## Two spaces, never mixed

| Space | Content | Location |
| --- | --- | --- |
| Work paths | sources, manifests, specs, figures, backups, audits, intermediates, build output | Repo-defined: `reports/<work-folder>/`, `visuals/specs/`, `assets/generated/`, `outputs/<materia-slug>/` |
| Delivery folder | only versioned technically validated PDFs | `~/Documents/<automatic-category>/<document-slug>/` |

## Automatic PDF versioning

- No `delivery_pdf:` configuration or user-selected path is needed.
- Category is derived from the confirmed route: `technical -> Tecnicos`,
  `academic -> Academicos`, `project -> Proyectos`, `business -> Profesionales`,
  and `other -> Otros`.
- The document slug is stable ASCII derived from the confirmed title (or confirmed
  document identity). The artifact path is
  `~/Documents/<category>/<slug>/<slug>-vNNN.pdf`.
- The first unique validated artifact is `v001`. Compare its hash before validation
  with the hash immediately before publication; publish only when they match. If its
  SHA-256 matches any existing version for that document, report and reuse that
  version. Otherwise atomically claim the next monotonic version without overwriting
  a concurrent publication, then verify destination hash equality.
- Never publish after build, configuration, or configured technical-validation
  failure.
- The document delivery folder contains PDFs only. Never copy manifests,
  `report.yml`, `body.md`, `sources.bib`, specs, figures, audits, contact sheets,
  logs, temporary files, or intermediates into it.
- Automatic publication never grants `VISUAL_PASS`, `HUMAN_REVIEW`, or
  `READY_TO_SUBMIT`; semantic and human review remain distinct evidence.
