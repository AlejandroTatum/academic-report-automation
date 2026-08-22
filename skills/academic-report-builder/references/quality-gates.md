# Report quality gates

Apply these gates to the rendered PDF or exported DOCX-to-PDF before human review. Script summaries are hints only: inspect the contact sheet directly and open full-size pages where thumbnails cannot prove the check.

These gates apply to every route. Route-conditional checks are marked as such.

## Evidence gates

1. Record the artifact hash and page count before inspection.
2. Run `validate_report.py` and `visual_pdf_auditor.py`; retain their reports and `contact_sheet.png` as precheck evidence.
3. Inspect every contact-sheet page directly. Do not infer success from `0 warnings`, `PASS`, or `visual_qa.md`.
4. Read back rendered content: verify headings, paragraphs, captions, bibliography, tables, and figure labels are present, legible, and semantically equivalent to the intended source.
5. Open every page containing diagrams, figures, captions, or tables at readable size and apply the checks below.

## Blocking visual checks

- **Academic route only**: cover page occupies page 1; body starts on page 2; the UNL logo is present. Do not apply this check to project documentation, professional reports, or technical documents.
- Reject headings without substantial following content, orphan headings, clipped images, overfull boxes, accidental blank pages, pages below 20% meaningful-content density, and unexplained half-empty pages created by table pagination.
- For practice reports, keep each exercise self-contained: data/content first,
  process/evidence after it, with tables and figures near their explanation.
- Conclusions must not start with formulaic `Se concluye` phrasing. Validate the
  rendered IEEE bibliography, not only `.bib` or `.tex`.
- Tables must render as real grids with visible rules, distinct headers, aligned columns, and readable padding. Reject raw Markdown pipes, separator rows, or table source rendered as plain text.
- For each diagram or figure page, verify the lower border clears the footer, all terminal nodes are complete, no node or connector is clipped/overlapped, and the full caption is visible and associated with the correct asset.
- Verify captions and labels are complete at normal reading zoom; thumbnails alone cannot prove fine text or edge clearance.

## Orphan headings

After a heading, the same page must fit at least one of:

- Two lines of body text.
- A full table header plus one data row.
- A complete figure together with its introduction.

If none fits, the heading moves to the next page. A heading rendered alone at the bottom of a page is a blocking defect, not a stylistic detail.

### Automated detection — blank-tail signature

`visual_pdf_auditor.py::check_orphan_heading()` scans the whole page below
~15% of page height down to the bottom, excluding only the bottom 10%
footer band (page numbers, institution text) from the blank-space check. It
flags a page where a short, heading-shaped ink strip (0.06–0.45 inch tall,
DPI-normalized) is followed by a blank tail reaching at least 20% of page
height — the signature of a heading whose body content was pushed to the
next page. A full table, a multi-line paragraph, or a natural page end
(content simply stops with normal trailing margin) are rejected by the same
guards: they either fail the blank-tail threshold or merge into a strip far
taller than a heading.

Two pages are exempted by index rather than by image analysis — `audit_pdf`
calls `check_orphan_heading(img, dpi=dpi, is_cover=(page_num == 1),
is_last_page=(page_num == n_pages))`, and either flag short-circuits to
`(False, None)` without inspecting pixels:

- **The cover (page 1)** is decorative and sparse by design.
- **The last page** cannot strand a heading at all. An orphan means the
  heading's content was pushed onto the *following* page; the final page has
  no following page, so trailing blank space there is simply where the
  document ends.

Both exemptions are deterministic and DPI-independent. Neither uses
`has_full_bleed_background()`, which returns `True` for ordinary and even
blank pages and therefore cannot serve as a guard.

Orphan findings are always **warnings**, never errors, in
`visual_pdf_validation()` — they never fail the automated build or block a
PDF from being produced. The blocking classification above (line 35) is a
**human visual-QA** rule applied during manual page-by-page review; it is
independent from the automated warning severity. Recall is favored over
precision on interior pages: a short line preceded by generous trailing
whitespace can legitimately warn even when it is not a rendering defect —
inspect it visually before treating any single orphan warning as a
build-blocking issue.

No fixture PNGs are committed to this repository to test the detector — it
is a sanitized public toolkit and the real fixture PDF carries private
content. Detector tests build synthetic images (`tools/test_orphan_detection.py`),
parametrized over `dpi in (150, 300)`, calibrated to page geometry measured
on the real fixture.

## Whitespace classification

Whitespace is never judged by size alone. Classify every large empty region:

| Class | Verdict |
| --- | --- |
| Intentional space (deliberate composition) | Approvable with justification |
| Natural section close (section genuinely ends) | Approvable |
| Accidental space from a page break | Defect |
| Space forced by an indivisible table | Defect unless the table is genuinely unsplittable and the split was attempted |
| Nearly-empty page holding an isolated title | Defect |

Large space is approvable ONLY with an explicit visual justification recorded in the inspection output. "It looks fine" is not a justification.

Inspection must record every page with:

- Under 20% meaningful content.
- Over 40% of the lower page empty with no natural section close.
- A heading followed by a new page.
- A whole table displaced to the following page.

## Tables

- Render as real grids with visible rules and a distinguishable header.
- Font size must stay legible; shrinking type to fit columns is a defect.
- Remove unnecessary columns before compressing any column.
- Split a table into grouped tables when a horizontal layout is too wide for the page.

### Breakable-table contract

`render_table()` in `build_latex_report.py` emits page-breakable tables, not
atomic floats: `xltabular` for more than 2 columns, `longtable` for 2 or
fewer columns — never `\begin{table}[H]` + `tabularx`/`tabular`. A table too
tall for the remaining page space now flows onto the next page instead of
jumping whole, which is what used to strand the heading above it. Every
emitted table follows this shape:

- `\Needspace{4\baselineskip}` (not `15\baselineskip`) reserves just enough
  room to avoid a bare header row at the page foot, without forcing an early
  page break that itself causes stranding.
- `\begingroup ... \endgroup` wraps the font-size (`\footnotesize`/`\small`),
  `\arraystretch`, `\tabcolsep`, and the table environment — required because
  a non-float table provides no group of its own.
- `\endhead` sits immediately after the header row's closing `\hline` and
  before the first data row, so the (optionally gray-shaded) header repeats
  on every continuation page.
- No `\endfirsthead` (longtable/xltabular reuse `\endhead` for the first
  page) and no `\endfoot` (every data row already emits its own trailing
  `\hline`).

All three templates (`unl-report.tex`, `plain-report.tex`,
`chamba-overleaf.tex`) declare `\usepackage{xltabular}` after `tabularx`.
With this contract, "a whole table displaced to the following page" and
"space forced by an indivisible table" (see the whitespace table below)
should no longer occur for any table long enough to need a real split —
verify tables that DO break across a page boundary still show the repeated
header and an unbroken bottom rule on every chunk.

Recommended split for wide requirement tables — avoid six compressed columns by using two tables sharing the same code:

```
| Code | Actor | Requirement | Priority |
```

```
| Code | Acceptance criterion |
```

## Diagrams

Legibility is necessary but not sufficient. Each diagram must represent the real decisions of its module and must visually differentiate:

- User
- System
- Internal module
- External service
- Validation
- Error
- Retry
- Final state

Reject:

- The same template repeated across all modules.
- Generic decisions such as `¿Validación correcta?`.
- Flows that model no real alternatives.
- Diagrams that merely restate the surrounding text.
- Clipped terminal nodes.
- Detached captions.
- Ambiguous arrows.

## Contradiction and regression gates

- Visible evidence overrides automation. Any visible blocking defect produces `VISUAL_FAIL`, even when all scripts report PASS or zero warnings.
- After any correction, rebuild the whole artifact and rerun validators, readback, contact-sheet inspection, and applicable full-size checks. Never validate only changed pages.
- Compare page count before and after correction. Investigate every material increase or decrease for table reflow, orphan headings, blank/semivacant pages, lost content, or altered section boundaries; record the explanation.
- Grant `VISUAL_PASS` only when all applicable checks pass on the same immutable artifact. If inspection is incomplete, report `REVIEW_REQUIRED` without visual approval. A prior automatic versioned PDF publication may be reported as a technically validated copy, never as human-approved final delivery.
