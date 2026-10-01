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
| Delivery folder | only versioned technically validated PDFs | `~/Documents/<automatic-category>/<document-slug>/`; the academic route is scoped one level deeper (below) |

Production never writes into the delivery tree, and the delivery tree never
receives work files: no manifest, no `report.yml`, no `sources.bib`, no specs,
figures, audits, logs, receipts or intermediates.

## Academic subjects scope the delivery tree

- On the academic route, the confirmed subject always scopes the delivery tree
  one level deeper: `~/Documents/Academicos/<subject-slug>/<document-slug>/`.
  The slug is the canonical alias when the shared `output_router` vocabulary
  knows the confirmed subject, so alias spellings of one course deliver into
  one folder; otherwise it is the subject's own stable ASCII slug, so a newly
  named course gets its own Git-ready folder without being registered anywhere.
- Only a report without a confirmed subject has no subject level: the academic
  route's own validation refuses that before delivery, and the tools never
  invent a fallback bucket. Non-academic routes are unchanged: `Tecnicos`,
  `Proyectos`, `Profesionales` and `Otros` keep
  `~/Documents/<automatic-category>/<document-slug>/`.

## Declared bibliography (opt-in)

- The delivery tree is PDF-only by default: a `sources.bib` that exists for
  citations never travels merely because it exists. Only `deliver_bibliography:
  true` in `report.yml` declares the bibliography a final artifact; the file is
  the one the report already selects (`bibliography:`/`bib:`, default
  `sources.bib`) — no new schema for other supplementary files.
- The declared source must be a regular `.bib` inside the work folder
  (traversal, absolute paths and symlink escapes refuse), non-empty, and parse
  as BibTeX. Anything else refuses delivery before anything is created. No DOI
  or citation-style policy is imposed for exporting the declared bytes.
- Evidence binds the exact bytes: `validation.yml` records `bibliography_sha256`
  after the applicable checks, and `final-review.yml` records it after the human
  reviews the declared bibliography alongside the PDF. Missing, stale or
  malformed evidence refuses delivery; the marker is computed only after the
  explicit human OK, never granted automatically.
- The pair ships as `<slug>-vNNN.pdf` plus the same-version `<slug>-vNNN.bib`.
  Reuse compares the complete requested set: the same PDF with a changed
  bibliography claims a new version, and switching between pair and PDF-only
  never reuses the other shape. A partial pair is never a delivery; a failed
  claim cleans only its own files and never overwrites an earlier version.
- Per-document folders hold only properly named versioned artifacts; Git
  metadata stays at the course root, and no work file, log, receipt, or
  unrelated source ever enters.

## Automatic PDF versioning

- No `delivery_pdf:` configuration or user-selected path is needed.
- Category is derived from the confirmed route: `technical -> Tecnicos`,
  `academic -> Academicos`, `project -> Proyectos`, `business -> Profesionales`,
  and `other -> Otros`.
- The document slug is stable ASCII derived from the confirmed title (or confirmed
  document identity). The artifact path is
  `~/Documents/<category>[/<subject-slug>]/<slug>/<slug>-vNNN.pdf`.
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

## The course folder is the user's Git repository, not ours

A course folder (`~/Documents/Academicos/<subject-slug>/`) may be a Git repository
the user owns. The tools respect an existing repository and never run `git init`,
`git add`, `git commit` or `git push`; the user owns every Git operation and every
commit. Git metadata belongs at the course root, above the per-document folders.
Each per-document folder stays PDFs-only, so a course commit contains exactly the
clean final deliverables and nothing else.
