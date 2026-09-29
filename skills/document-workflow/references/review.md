# Review - the final human review

Executor: document-workflow
Artifact: `reports/<wf>/final-review.yml`

Present the validated final PDF to the user; only an explicit OK produces
`final-review.yml`, bound to the PDF bytes through `pdf_sha256`. Silence is
never a yes and the marker is never inferred; a rebuilt PDF goes stale and
must be reviewed again before delivery.
