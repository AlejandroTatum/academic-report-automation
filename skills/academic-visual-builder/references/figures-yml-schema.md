# `figures.yml` visual metadata contract

Every visual asset folder must contain a manifest with a `figures:` list. The
shared validator in `tools/visual_metadata.py` is the executable source for
this contract; both visual and report validation call it.

## Required fields

| Field | Type | Contract |
|---|---|---|
| `file` | non-blank string | Asset path, relative to the manifest folder when not absolute. |
| `title` | non-blank string | Short display title. |
| `caption` | non-blank string | Self-contained report caption. |
| `source` | non-blank string | Explicit provenance: spec, requirement, lecture material, or own work. |
| `renderer` | non-blank string | Tool used to render the asset. Open-ended for reproducibility; no closed registry is assumed. |
| `section` | non-blank string | Canonical report section. |
| `request_id` | non-blank string | Stable, unique request identity within the manifest. |
| `result_id` | non-blank string | Stable, unique rendered-result identity within the manifest. |
| `content_sha256` | lowercase 64-character hex string | SHA-256 of the asset's raw bytes. It is checked whenever the asset exists. |
| `license` | non-blank string | Explicit license or permission text; never replace it with the status alone. |
| `license_status` | enum | One of `original`, `licensed`, `public_domain`, `permission_granted`. |
| `alt_text` | non-blank string | Accessibility description for readers who cannot see the asset. |

`source` is the provenance field. `license` preserves the explicit legal or
permission statement, while `license_status` is intentionally a small domain.
Unknown or arbitrary statuses fail validation. Asset files with `.svg`, `.png`,
or `.pdf` extensions in the folder must be listed; unlisted assets fail before
export.

## Section compatibility

`section` is canonical. `intended_section` remains a legacy alias: an entry may
provide either field, or both when their trimmed values are identical. Missing
both fields fails. Conflicting non-blank values fail; the validator never
silently chooses one.

## Valid example

```yaml
figures:
  - file: process.svg
    title: Process lifecycle
    caption: Main states in the process lifecycle.
    source: Original work derived from requirement REQ-012
    renderer: Custom SVG renderer
    section: Process model
    request_id: req-012-visual
    result_id: render-012-v1
    content_sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
    license: Original work created for this report
    license_status: original
    alt_text: Flow from intake to completion through three process states.
```

## Validation checklist

- [ ] Required fields are present and non-blank.
- [ ] Request and result IDs are unique.
- [ ] Hash syntax is valid and matches raw asset bytes when available.
- [ ] Section aliases are compatible.
- [ ] Every listed asset exists and every asset in the folder is listed.
- [ ] Caption, provenance, license text, status, and accessibility text are retained.
