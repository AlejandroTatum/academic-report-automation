# practice-feedback-fixes — lessons from Simulación APE 1

Branch: `fix/skill-practice-feedback` (from `origin/main` @ b15af80).
Worktree: `academic-report-automation-worktrees/claude`.

## Goal

Turn the friction observed while producing Simulación APE 1 (2026-10-02) into tool and
skill fixes, so the next APE for this course starts configured and needs no extra
approval rounds. Also closes #59 and #60.

## Evidence

- `tools/guide_facts.py` on `guia-ape-1.txt` returns `{'planned_time': '24 horas',
  'conflicts': {'practice_number': ['01', '1']}}`: family missed (`experimental\b` vs
  "Experimentales"), `01`/`1` treated as a conflict, planned time taken from exercise
  prose instead of the "Tiempo planificado en el Sílabo 3" row.
- `content_check.body_check_results` does not run `ape_structure_validation`; APE titles
  fail only at validate, after approval.
- `parse_judgments` rejects `findings` items that are mappings; judges also emitted
  unquoted `: ` notes.
- No `report.yml` key sets the delivery folder (default `~/Documents/Academicos/<subject>/<slug>/`).
- `scripts/sync_skills.sh` does not target `~/.pi/agent/skills`.
- DOCX export writes equations as LaTeX text; the working draft used pandoc ad hoc.

## Tasks

- [x] 1. guide_facts: detect APE guides, normalize practice numbers, read planned time from its labeled row.
- [x] 2. Body check enforces the fixed APE headings when `format: ape`.
- [x] 3. Judges: brief carries an exact quoted YAML example; parser accepts finding mappings.
- [x] 4. `report.yml` delivery folder override for the publisher, keeping the version register.
- [x] 5. Simulación course profile (Guamán) applied by intake on subject match.
- [x] 6. DOCX draft round-trip: export with native equations, import with diff, refuse locked files.
- [x] 7. Approval gate: fresh preview required (#59) and clickable links before the prompt (#60).
- [x] 8. `sync_skills.sh` also syncs `~/.pi/agent/skills`.
- [x] 9. Rubric checks are document-wide unless a section is explicitly bound.

## Evidence log
- Task 1 (guide_facts): 18663ed — tools/test_guide_facts.py 8 passed (RED: 3 failed before implementation).
- Task 2 (APE headings in body check): see commit subject 'fix(tools): check fixed APE headings at draft time' — test_content_check.py 142 passed (RED: 2 failed before); with test_guide_facts, test_validate_report_connector_wiring, test_ape_template: 194 passed.
- Task 3 (robust judges): see commit subject 'fix(tools): accept structured judge findings and show a quoted example' — tools/test_content_check.py 147 passed (RED: 2 failed before implementation).
- Task 4 (delivery_dir override): see commit subject 'feat(tools): let report.yml set the delivery folder' — test_report_config.py + test_pdf_publication.py + test_deliver_report.py 123 passed (RED: 15 failed before implementation).
- Task 8 (sync to Pi): see commit subject 'fix(scripts): sync skills into the Pi runtime too' — tests/skills/test_sync_skills.py 4 passed (RED: 2 failed before implementation).
- Task 9 (document-wide rubric checks): see commit subject 'fix(tools): run rubric checks over the whole document unless bound' — test_rubric_checks.py + test_rubric_plan.py + test_content_check.py + tests/skills green (RED: 2 failed before implementation).
- Task 5 (Simulación profile): see commit subject 'feat(skill): add Simulación course profile applied on subject match' — tools/test_course_profile.py 9 passed (RED: collection error, module missing) + tests/skills green.
- Task 7 (approval gate, closes #59/#60): see commit subject 'fix(skill): require a fresh rendered draft and links at the approval gate' — test_doc_status_approval.py + test_build_report_auto.py + test_approval_marker.py + tests/skills green (RED: 6 tool tests failed before implementation, 1 contract test before the docs edit).
- Task 6 (DOCX draft round-trip): see commit subject 'feat(tools): add DOCX draft export and import for paraphrasing' — tools/test_draft_docx.py 7 passed (RED: collection error, module missing) + tests/skills green.
