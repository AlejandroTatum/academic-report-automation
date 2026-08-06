# figures.yml schema

Every figure folder must include a `figures.yml` for traceability. Each figure is an entry under `figures:`.

## Required fields

| Field | Type | Description |
|-------|------|-------------|
| `file` | string | Filename of the rendered asset (e.g. `diagrama-estados.svg`) |
| `title` | string | Short display title of the figure |
| `caption` | string | Full caption as it will appear under the figure in the report |
| `source` | string | Provenance — what spec, requirement, lecture slide, or domain model the figure derives from |
| `renderer` | string | Tool/script used to generate the figure (e.g. `Custom PIL renderer`, `Mermaid`, `Vega-Lite`, `HTML + Playwright`) |
| `section` | string (canonical) | Report section where the figure should be inserted |
| `intended_section` | string (alias) | Accepted as a backward-compatible alias for `section`. New entries should use `section`. |

## Traceability rule

Every figure MUST have traceable metadata before insertion into a report. A figure with no `source` or no `section`/`intended_section` must not be included in the final PDF/DOCX.

## Example

```yaml
figures:
  - file: diagrama-estados.svg
    source: "Derivado del caso de uso CU012 y modelo de dominio"
    renderer: "Custom PIL renderer"
    title: "Diagrama de estado: Comprobante de pago"
    caption: "Estados principales del comprobante de pago: pendiente, aprobado y rechazado."
    section: "Diseño de comportamiento - Diagrama de estados"
```

### Legacy example (still valid)

```yaml
figures:
  - file: proceso-vm.svg
    source: "Clase 5 — Máquinas virtuales"
    renderer: "Mermaid"
    title: "Proceso de creación de VM"
    caption: "Flujo de creación de una máquina virtual en VirtualBox."
    intended_section: "Virtualización - Procesos"
```

## Validation checklist

Before export, verify:

- [ ] Every figure listed in `figures.yml` exists at the declared `file` path
- [ ] `title` is short and descriptive
- [ ] `caption` is meaningful without surrounding report text
- [ ] `source` is non-empty and traces back to a requirement, spec, or domain source
- [ ] `renderer` matches the tool used (so regeneration is reproducible)
- [ ] `section` (or `intended_section` for legacy entries) exists in the current report outline
- [ ] No figure references remain in the report body without a matching `figures.yml` entry
