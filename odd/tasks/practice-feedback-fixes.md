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
- [ ] 2. Body check enforces the fixed APE headings when `format: ape`.
- [ ] 3. Judges: brief carries an exact quoted YAML example; parser accepts finding mappings.
- [ ] 4. `report.yml` delivery folder override for the publisher, keeping the version register.
- [ ] 5. Simulación course profile (Guamán) applied by intake on subject match.
- [ ] 6. DOCX draft round-trip: export with native equations, import with diff, refuse locked files.
- [ ] 7. Approval gate: fresh preview required (#59) and clickable links before the prompt (#60).
- [ ] 8. `sync_skills.sh` also syncs `~/.pi/agent/skills`.
- [ ] 9. Rubric checks are document-wide unless a section is explicitly bound.

## Evidence log
- Task 1 (guide_facts): TBD — tools/test_guide_facts.py 8 passed (RED: 3 failed before implementation).
