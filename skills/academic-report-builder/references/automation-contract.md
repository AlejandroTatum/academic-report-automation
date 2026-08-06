# Report automation contract

This contract applies to every document type: academic work, project documentation, professional/business reports, and technical documents. The commands, gates, and readiness receipts are identical across routes.

Route selection precedes the build. Complete the intake in `document-intake.md`, confirm the Document Contract, and resolve the route in `document-routing.md` before running any command below. Never start a build to "see how it looks" before the route is confirmed.

## Canonical automation

Set one root for every report automation command:

```bash
REPORT_AUTOMATION_ROOT="/home/alejo/devwork/.projects/university/.reports-system/automation"
```

From `$REPORT_AUTOMATION_ROOT`, prefer the router, validator, and visual auditor:

```bash
cd "$REPORT_AUTOMATION_ROOT" && ./.venv/bin/python tools/build_report_auto.py reports/<work-folder>/
cd "$REPORT_AUTOMATION_ROOT" && ./.venv/bin/python tools/validate_report.py reports/<work-folder>/
cd "$REPORT_AUTOMATION_ROOT" && ./.venv/bin/python tools/visual_pdf_auditor.py outputs/<materia-slug>/<final-pdf>.pdf
```

Use `latex` for long textual/mixed reports, `visual` for concept maps, infographics, or design-heavy deliverables, and `docx` only for editable delivery or mandatory DOCX templates. Keep final visible PDF/DOCX files only in `outputs/<materia-slug>/`; keep intermediates in `build/`, `backups/`, or canonical generated-asset folders.

`visual_pdf_auditor.py` is manual unless `report.yml` contains `validators: {visual_pdf: true}`. It produces `visual_qa.md` and `contact_sheet.png`; both are precheck evidence, not approval. Automatic execution inside `validate_report.py` does not change this authority boundary.

Required flow:

`BUILD_PASS -> VALIDATION_PASS -> AUDITOR_PRECHECK -> RENDERED_READBACK -> SEMANTIC_VISUAL_INSPECTION -> VISUAL_PASS -> HUMAN_REVIEW -> READY_TO_SUBMIT`

## Typed pipeline integration

For `/home/alejo/devwork/lab-report-agent`, use:

```bash
uv run python generate_report.py run --config config/<job-pipeline>.yml
uv run python generate_report.py resume --reviewer-id <id>
uv run python generate_report.py status
```

The checked-in `config/academic-pipeline.yml` is only a backend/capability template until it has a typed `job` block. The direct `main` command and ReportLab renderer are legacy compatibility only; they do not prove canonical validation, visual pass, human review, or readiness. Keep receipts in the configured workspace and treat canonical outputs/receipts as authoritative.

## Readiness and command scope

| Gate | Proof |
| --- | --- |
| `BUILD_PASS` | Compilation/export completed without errors. |
| `VALIDATION_PASS` | Active validators pass; rendered semantics and layout remain unproven. |
| `VISUAL_PASS` | Automated prechecks, rendered readback, direct contact-sheet inspection, and applicable full-size checks pass on one immutable artifact. |
| `HUMAN_REVIEW` | Reviewer identity, APPROVE decision, UTC timestamp, gate receipt IDs, and artifact hashes are recorded. |
| `READY_TO_SUBMIT` | Every previous gate passes and approved artifacts remain unchanged. |

`REVIEW_REQUIRED` is a workflow state, not visual approval. Never pair it with `VISUAL_PASS` unless independent semantic inspection passed.

`academic-report-builder` owns full document deliverables on every route, university work included. The `reporte` command is a quick wrapper for lab reports that prepares `report.yml`, `body.md`, and `sources.bib` for the same router. Use the wrapper only when Alejandro invokes `/reporte`; use this skill for profiles, non-lab formats, or more structured work.
