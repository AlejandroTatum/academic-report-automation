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
- Grant `VISUAL_PASS` only when all applicable checks pass on the same immutable artifact. If inspection is incomplete, report `REVIEW_REQUIRED` without visual approval and do not expose final delivery paths.
