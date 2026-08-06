# Conversation cases — academic-report-builder

Behavioral cases for the routing contract. Static tests in
`test_report_builder_routing.py` prove the rules are *written*; these cases prove
they are *followed*. They require a live skill run and are verified by reading the
assistant's first response.

A case passes only when the first response does **all** of the following:

1. Generates nothing — no file, no build, no draft.
2. Asks the document-type confirmation.
3. Reaches the full Document Contract before any generation.

## Positive cases

### Case 1 — project documentation disguised as a format request

Prompt: `Generá un PDF con los requisitos de KIPU.`

| Expectation | Pass condition |
| --- | --- |
| Does not generate immediately | No build command runs |
| Asks document type | The five options are offered |
| May recommend Route B | Recommendation is phrased as a proposal |
| Does not auto-select | Waits for the user's pick even though the intent looks obvious |
| Does not apply UNL | `unl-shell.md` is never loaded |

### Case 2 — academic work that names the format outright

Prompt: `Necesito un trabajo universitario en formato UNL.`

| Expectation | Pass condition |
| --- | --- |
| Still confirms the type | Confirmation 1 is asked despite the explicit statement |
| Then confirms 2–5 | Audience/purpose, template, delivery, visual direction |
| Only then loads Route A | `unl-shell.md` loads after confirmation, not before |

### Case 3 — business report

Prompt: `Prepará un informe ejecutivo para un cliente.`

| Expectation | Pass condition |
| --- | --- |
| Does not apply UNL | No institutional cover, no academic footer |
| Confirms all five | Full intake runs |
| Recommends Route C | Business route proposed, not imposed |

### Case 4 — technical document

Prompt: `Documentá esta API en DOCX.`

| Expectation | Pass condition |
| --- | --- |
| Confirms technical type | Route D proposed |
| Confirms DOCX | Delivery format restated for confirmation |
| No university cover | DOCX never implies an academic shell |

## Negative cases

The skill **fails** the contract if it does any of these. Each is a hard stop.

| # | Failure | Why it is a defect |
| --- | --- | --- |
| N1 | Starts building before the intake is confirmed | The contract is the gate, not a formality |
| N2 | Applies the UNL shell by default | The inference the rewrite exists to remove |
| N3 | Returns final delivery paths without rendered inspection | Paths imply approval that was never earned |
| N4 | Accepts an auditor `PASS` while defects are visible | Visible evidence overrides automation |
| N5 | Leaves an isolated heading at the end of a page | Orphan-heading gate |
| N6 | Renders raw Markdown pipes instead of a real table | Table gate |
| N7 | Reuses one generic diagram across every module | Diagram gate |
| N8 | Asks length or depth as a mandatory question | Out-of-scope permanent question |
| N9 | Falls back to Route A when the type is ambiguous | Route E must never degrade into academic |

## KIPU regression intake

The answers to replay when regenerating the KIPU fixtures:

```
Type:              Project documentation
Audience:          Technical team, project reviewer, and authors
Purpose:           Define context, requirements, and flows for review and implementation
Template/identity: No UNL shell; KIPU's own visual identity
Outputs:           PDF, and DOCX where applicable
Visual direction:  Technical
```
