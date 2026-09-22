# Gates list check and float barrier (#37, #38)

## Objective
Close the two follow-ups raised by the native review of #36.

## Problem / why
- #37: `deliver_report` treats `validation.yml` `gates:` as a list without checking it; a string or mapping turns membership into substring/key matching and reports gates that were never granted. The gate vocabulary is duplicated.
- #38: figures float with `[tbp]` since #36, but nothing stops them from crossing section boundaries, and placement is untested.

## Scope (authorized 2026-09-22, "dale continua con lo pendiente")
- #37 `tools/deliver_report.py`, shared gate reading/vocabulary with `tools/doc_status.py` if it reads gates.
- #38 shared LaTeX templates (`placeins` with `[section]`) and `tools/test_figure_detection.py`; confirm on one real report rendered in a scratch content root.

## Constraints
- Strict TDD: on (source: user global config). Runner: `.venv/bin/python -m pytest tools/ tests/`.
- Shrink the system: one helper and one vocabulary, no new flags.
- Never write into the real content root; renders go to a scratch copy.
- Delivery: forecast ~80-150 authored lines -> single PR.
- RDD: on (global); assess after the work-unit commits.

## Tasks
- [x] T1 #37 a malformed `gates:` (string or mapping) grants no gate; one helper and one gate vocabulary shared by callers. RED test in `tools/test_deliver_report.py`. Route: delegated writer.
- [x] T2 #38 templates load `placeins` `[section]`; tests assert `[tbp]` is emitted and every figure-capable template loads the barrier; rendered check on a scratch copy of a real report. RED test in `tools/test_figure_detection.py`. Route: delegated writer.

## Acceptance
- Each fix has a test observed RED then GREEN; full suite green; one Conventional Commit per task.
- Rendered PDF of a real report shows no figure placed after the next section heading.

## Progress / evidence
- Route: T1-T2 delegated to one writer (writer trigger: 2+ non-trivial files).

### T1 (#37)
- Decision: a malformed `gates:` grants **no gate** (not a delivery refusal). By the time the message is built, `result: pass` and the artifact hash were already checked and the publisher already copied the PDF — refusing at that point would contradict a completed delivery. `gates:` only feeds the informational grant/missing message.
- Added `_granted_gates()` helper in `tools/deliver_report.py`, the single place that reads `gates:`; `KNOWN_GATES` stays the one vocabulary. `rg` confirmed `tools/doc_status.py` and every other tool never read `gates`, so no sharing beyond this helper was needed.
- RED: `test_delivery_message_grants_no_gate_from_a_string`, `test_delivery_message_grants_no_gate_from_a_mapping` in `tools/test_deliver_report.py` — both failed against the pre-fix substring/key-matching code (string case reported `VISUAL_PASS` as granted; mapping case reported it granted from a dict key).
- GREEN: `tools/test_deliver_report.py` 12 passed.
- Full suite: `.venv/bin/python -m pytest tools/ tests/` → 966 passed.
- Commit: `c8b5ab2 fix(deliver): grant gates only from a list in validation.yml` (2 files changed, 48 insertions(+), 1 deletion(-)).

### T2 (#38)
- Verified `placeins.sty` is available through the project's existing Docker TeX Live fallback (`texlive/texlive:latest`, already pulled locally); no local `pdflatex`/`kpsewhich` in this environment.
- Added `\usepackage[section]{placeins}` right after `\usepackage{float}` in `templates/unl-report.tex`, `templates/plain-report.tex`, `templates/chamba-overleaf.tex` — the only three `.tex` templates the builder can select (`TEMPLATE_ALIASES` in `tools/build_latex_report.py`).
- RED: `test_figure_is_emitted_with_tbp_placement` (already GREEN pre-fix — `[tbp]` shipped in #36) and `test_template_loads_placeins_with_section_barrier`, parametrized over the 3 templates, in `tools/test_figure_detection.py` — the barrier assertion failed on all 3 templates before the fix.
- GREEN: `tools/test_figure_detection.py` 20 passed.
- Full suite: `.venv/bin/python -m pytest tools/ tests/` → 972 passed.
- Rendered check: copied the real `reports/engram-funcionamiento/` (resolved via `report_config.DEFAULT_CONTENT_ROOT`, read-only) into a scratch content root under the session scratchpad, built with `REPORT_CONTENT_ROOT=<scratch>` through `tools/build_report_auto.py` (Docker TeX Live fallback), and inspected the PDF with `pdftotext -layout`: all 4 figure captions (Figura 1–4) land between their own section heading and the next one, none crossed a boundary. Page count: 12 (previous delivered version: 13). `fd -t f --changed-within 1h` against the real content root returned 0 both before and after the build — nothing written there.
- Commit: `fix(latex): keep floating figures inside their section`.

### Native review
- Parent spot check: `.venv/bin/python -m pytest tools/ tests/ -q` -> 972 passed.
- Assessed `high` (7 files, 134 lines). Preflight first stopped with
  `managed_assets_outdated`; the provider-issued `gentle-ai sync --agent claude-code`
  cleared it. Consent granted; lineage `review-1868dc47ca994980`, four lenses,
  approved and acknowledged (gentle-ai 3.6.0).
- Six non-blocking advisory findings, left as follow-up: `placeins` becomes a hard
  TeX dependency (WARNING, `templates/plain-report.tex:19`); malformed `gates:` is
  silent rather than logged (`deliver_report.py:46-48`); untested mixed list/None
  gates; a possibly vacuous `VISUAL_PASS` assertion and misleading inline comment
  (`test_deliver_report.py:94`); template regex would match a commented-out
  `\usepackage` (`test_figure_detection.py:186-188`).

## Next step
Open the PR (Closes #37, #38).
