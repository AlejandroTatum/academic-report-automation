# Delivery - Decision 3 (final review) and publication

Phases `review` (human gate) and `deliver`. Generation never publishes: the build ends at the validated PDF under `outputs/<materia-slug>/`, writing nothing into `~/Documents`.

## Review (`next: review`, artifact `reports/<wf>/final-review.yml`)

Present the exact PDF the `validate` phase recorded, opened in full, never a summary. When `report.yml` sets `deliver_bibliography: true`, present the declared `.bib` alongside the PDF: the human OK covers both artifacts or neither. Only an explicit OK of that exact set produces the marker, binding `pdf_sha256` (plus `bibliography_sha256` when declared, computed from the `.bib` bytes only after that explicit OK), `reviewed_at`, `reviewed_by`. A review is never granted automatically; silence is never a yes and the marker is never inferred; a decline or any other answer writes nothing and review stays `pending`. A rebuilt PDF or changed declared `.bib` stales the marker and returns the route to `review`. Delivery runs only after this gate is `done`; never refresh a stale marker without a fresh explicit OK.

PDF handoff: present the PDF with the exact short fish command from `doc_status` guidance: `set d <folder>`, `set f <exact PDF filename>`, `brave $d/$f`. Copy its quoting exactly; never glob or truncate the filename. Never send screenshots; the user reviews the PDF itself. The default viewer zathura does not follow internal links.

## Deliver (`next: deliver`)

Artifact: `~/Documents/<category>/[<subject-slug>/]<slug>/<slug>-vNNN.pdf` (plus the same-version `<slug>-vNNN.bib` only when `deliver_bibliography: true`). Never copy or version by hand:

```bash
"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/deliver_report.py" "$REPORT_CONTENT_ROOT/reports/<work-folder>/"
```

`tools/deliver_report.py` is the only publication route. It requires a `validation.yml` receipt with `result: pass` for the exact PDF bytes and a current `final-review.yml` whose `pdf_sha256` matches them; the publisher re-checks `approval.yml` and `final-review.yml` and refuses an absent, stale or malformed marker before creating anything. The hash before validation must match the hash immediately before publication. Publish only the confirmed PDF output.

- Destination: no `delivery_pdf:` or user-selected path: `~/Documents/<automatic-category>/<slug>/<slug>-vNNN.pdf`, category from the confirmed route (`Academicos`, `Proyectos`, `Profesionales`, `Tecnicos`, `Otros`), `<slug>` the stable ASCII slug of the confirmed title.
- Academic route: the confirmed subject scopes one level deeper, `~/Documents/Academicos/<subject-slug>/<slug>/`: the canonical alias when the shared `output_router` vocabulary knows it, otherwise the subject's own stable ASCII slug, so a newly named course gets its own folder; only a missing subject has no level (academic validation refuses it before delivery), and the tools never invent a fallback bucket. Non-academic routes are unchanged.
- Versioning: first unique artifact is `v001`; a matching SHA-256 reuses that version; changed content atomically claims the next monotonic version without overwriting a concurrent publisher, then verifies hash equality. Done = a published `<slug>-vNNN.pdf` hashes equal to the final PDF; delivery has no failure state (absent or non-matching is `pending`).
- Declared bibliography (opt-in): only `deliver_bibliography: true` ships the `.bib` the report already selects (`bibliography:`/`bib:`, default `sources.bib`); a `sources.bib` for citations never travels merely because it exists. It must be a regular non-empty `.bib` inside the work folder that parses (traversal, absolute paths and symlink escapes refuse). `validation.yml` and `final-review.yml` must both record its `bibliography_sha256`. The pair ships as `<slug>-vNNN.pdf` plus `<slug>-vNNN.bib`; reuse compares the complete set, so the same PDF with a changed `.bib` claims a new version, a partial pair is never a delivery, and a failed claim cleans only its own files.
- Delivery folders are PDFs only (plus the declared versioned `.bib`): never a manifest, `report.yml`, `body.md`, `sources.bib` (undeclared), spec, figure, audit, contact sheet, log, receipt or intermediate.
- Git: a course folder (`~/Documents/Academicos/<subject-slug>/`) may be the user's repository. Do not run any Git command (`git init`, `git add`, `git commit`, `git push`) in the delivery tree; the user owns every Git operation, Git metadata stays at the course root, and each per-document folder stays PDFs-only. Do not write any file other than the versioned PDF (and the declared `.bib` pair).
- Never create, repair or refresh `approval.yml` or `final-review.yml` to make publication pass. Publication is not approval and grants no `VISUAL_PASS`, `HUMAN_REVIEW` or `READY_TO_SUBMIT`; do not report a run as `READY_TO_SUBMIT` from publication alone. Report the published path and version, say the receipts are unchanged, re-run `doc_status` (all `done` reports `next: done`).
