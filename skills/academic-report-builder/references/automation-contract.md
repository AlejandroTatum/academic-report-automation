# Report automation contract

This contract applies to every document type: academic work, project documentation, professional/business reports, and technical documents. The commands, gates, and readiness receipts are identical across routes.

Route selection precedes the build. Complete the intake in `document-intake.md`, resolve the route in `document-routing.md`, and have a current human approval marker (`APPROVAL_CURRENT`) before running any command below. The Document Contract is recorded data, not the approval gate. Never start a build to "see how it looks" before the route is confirmed.

## Canonical automation

Code and content live in two separate trees. Code is versioned and shared; content is personal and stays out of the code repository. Three independent choices, never mixed:

- `REPORT_AUTOMATION_ROOT` is the **source/tool root**: the checkout that owns `tools/`, `templates/`, the logo assets and the Node toolchain. A feature worktree (for example `academic-report-automation-worktrees/pi`) is a valid source root.
- `REPORT_PYTHON` is the **dependency-equipped interpreter** the tools run under. It is selected explicitly: it may be the source checkout's `.venv/bin/python` when that exists, but it never has to sit beside `tools/`. A worktree has `tools/` and no `.venv`, so it points `REPORT_PYTHON` at the shared interpreter the repository uses.
- `REPORT_CONTENT_ROOT` is the **content root**: the tree that holds `reports/`, `academic-sources/`, `assets/generated/`, and the `outputs/` symlink. It is never derived from the source root.

Resolve the content root with the same loader the tools use, so the documented value and the running value can never disagree. Never assume a personal path:

```bash
# Source of truth for the tools/ you are running (a feature worktree qualifies).
REPORT_AUTOMATION_ROOT="<absolute path of the checkout that owns tools/>"
# Dependency-equipped interpreter for this repository. The default below is the source
# checkout's own .venv; when it does not exist (worktree, shared environment) set it
# explicitly, e.g. REPORT_PYTHON=/path/to/academic-report-automation/.venv/bin/python
REPORT_PYTHON="${REPORT_PYTHON:-$REPORT_AUTOMATION_ROOT/.venv/bin/python}"
REPORT_CONTENT_ROOT="$("$REPORT_PYTHON" -c 'import sys; sys.path.insert(0, sys.argv[1]); from report_config import CONTENT_ROOT; print(CONTENT_ROOT)' "$REPORT_AUTOMATION_ROOT/tools")"
printf 'REPORT_CONTENT_ROOT=%s\n' "$REPORT_CONTENT_ROOT"
```

The snippet prints the resolved root so a fresh session can see the value the tools will use. `tools/report_config.py` resolves `CONTENT_ROOT` from `REPORT_CONTENT_ROOT` when that environment variable is set, otherwise from its own documented default. Exporting `REPORT_CONTENT_ROOT` only points the tools at a different content tree; the source root never moves with it.

Every command below is absolute and runs from any working directory: the selected interpreter, the current source tool and the report folder are all named in full, so no `cd` and no assumed current directory is involved. Run the tools from `REPORT_AUTOMATION_ROOT` even when `REPORT_PYTHON` lives elsewhere.

```bash
"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/build_report_auto.py" "$REPORT_CONTENT_ROOT/reports/<work-folder>/"
"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/validate_report.py" "$REPORT_CONTENT_ROOT/reports/<work-folder>/"
"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/visual_pdf_auditor.py" "$REPORT_CONTENT_ROOT/outputs/<materia-slug>/<final-pdf>.pdf"
```

Before the first build, `report.yml` must carry the resolved route as `route:` and, on the routes that forbid numbered headings, `section_numbering: false`. Both are defined in `document-routing.md`. Without `route:` the report is validated as university academic work and will be asked for a teacher and a subject the route forbids.

Use `latex` for long textual/mixed reports, `visual` for concept maps, infographics, or design-heavy deliverables, and `docx` only for editable delivery or mandatory DOCX templates. Keep final visible PDF/DOCX files only in `outputs/<materia-slug>/`; keep intermediates in `build/`, `backups/`, or canonical generated-asset folders.

### Clean delivery to the user's Documents folder

Generation never publishes. `build_report_auto.py` ends at the validated final PDF
under `outputs/<materia-slug>/` and reports its SHA-256; it writes nothing into
`~/Documents`.

Delivery is a separate, explicit phase. With a current `approval.yml` marker
(`APPROVAL_CURRENT`) and a `validation.yml` receipt recording `result: pass` for the
exact final PDF bytes, run:

```bash
"$REPORT_PYTHON" "$REPORT_AUTOMATION_ROOT/tools/deliver_report.py" "$REPORT_CONTENT_ROOT/reports/<work-folder>/"
```

`deliver_report.py` publishes only the confirmed PDF output at
`~/Documents/<automatic-category>/<document-slug>/<document-slug>-vNNN.pdf`.
No `delivery_pdf:` configuration or user-selected path is needed. Category derives
from confirmed route (`technical -> Tecnicos`, `academic -> Academicos`, with
project/professional/other equivalents); slug is stable ASCII from confirmed title
or document identity. The first unique artifact is `v001`; matching SHA-256 reuses
an existing version, while changed content atomically creates the next monotonic
version without overwriting a concurrent publisher and verifies hash equality. The
PDF hash before validation must match the hash immediately before publication:
`deliver_report.py` re-checks the receipt hash against the current bytes and hands
the pre-publication hash to the guarded publisher, which verifies the copy
byte-for-byte. A missing or stale approval, or a receipt not bound to the current
bytes, refuses delivery before anything is created. The
delivery folder contains PDFs only: no
manifests, sources, audits, or intermediates. Publication is technical-copy status,
not `VISUAL_PASS`, `HUMAN_REVIEW`, or `READY_TO_SUBMIT`. See `clean-delivery.md`.

`visual_pdf_auditor.py` is manual unless `report.yml` contains `validators: {visual_pdf: true}`. It produces `visual_qa.md` and `contact_sheet.png`; both are precheck evidence, not approval. Automatic execution inside `validate_report.py` does not change this authority boundary.

Required flow:

`BUILD_PASS -> VALIDATION_PASS -> VERSIONED_PDF_PUBLISHED_OR_REUSED`

The last transition is the explicit deliver phase (`tools/deliver_report.py`),
never an automatic side effect of generation.

Preconditions: `APPROVAL_CURRENT` (a current `approval.yml` whose `preview_sha256`
matches the exact preview bytes) before the build, and unchanged artifact hashes
across validation.

`BUILD_PASS -> VALIDATION_PASS -> AUDITOR_PRECHECK -> RENDERED_READBACK -> SEMANTIC_VISUAL_INSPECTION -> VISUAL_PASS -> HUMAN_REVIEW -> READY_TO_SUBMIT`

## Typed pipeline integration

For the typed lab-report pipeline (its own checkout and job configs, not this repository), run from that checkout:

```bash
uv run python generate_report.py run --config config/<job-pipeline>.yml
uv run python generate_report.py resume --reviewer-id <id>
uv run python generate_report.py status
```

The checked-in `config/academic-pipeline.yml` is only a backend/capability template until it has a typed `job` block. The direct `main` command and ReportLab renderer are legacy compatibility only; they do not prove canonical validation, visual pass, human review, or readiness. Keep receipts in the configured workspace and treat canonical outputs/receipts as authoritative.

## Readiness and command scope

| Gate | Proof |
| --- | --- |
| `APPROVAL_CURRENT` | A current `approval.yml` exists: its `preview_sha256` matches the exact `preview.md` bytes and no later preview edit has staled it. |
| `BUILD_PASS` | Compilation/export completed without errors. |
| `VALIDATION_PASS` | Active validators pass; rendered semantics and layout remain unproven. |
| `VERSIONED_PDF_PUBLISHED_OR_REUSED` | Precondition `APPROVAL_CURRENT`: the automatic PDF-only Documents version was atomically published (or hash-matched and reused) after technical validation and a current approval marker; it is not approval. |
| `VISUAL_PASS` | Automated prechecks, rendered readback, direct contact-sheet inspection, and applicable full-size checks pass on one immutable artifact. |
| `HUMAN_REVIEW` | Reviewer identity, APPROVE decision, UTC timestamp, gate receipt IDs, and artifact hashes are recorded. |
| `READY_TO_SUBMIT` | Every previous gate passes and approved artifacts remain unchanged. |

`REVIEW_REQUIRED` is a workflow state, not visual approval. Never pair it with `VISUAL_PASS` unless independent semantic inspection passed.

`academic-report-builder` owns full document deliverables on every route, university work included. The `reporte` command is a quick wrapper for lab reports that prepares `report.yml`, `body.md`, and `sources.bib` for the same router. Use the wrapper only when Alejandro invokes `/reporte`; use this skill for profiles, non-lab formats, or more structured work.
