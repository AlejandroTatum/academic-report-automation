# Visual directions

The direction confirmed in Confirmation 5 is an execution parameter, not a label. It must change typography, tables, diagrams, density, color, and composition in the rendered artifact. If the rendered pages would look identical under two directions, the direction was not applied.

## Technical

- Typography: clean, neutral, consistent; monospace for codes, identifiers, paths, and commands.
- Tables: compact, no unnecessary columns, visible header, split into grouped tables instead of compressing many columns.
- Diagrams: precise; represent real decisions, states, and alternatives; visible codes and traceability from requirement to flow to module.
- Density: high but legible. Less ornamentation, no decorative frames or filler graphics.
- Color: functional only — differentiate actor, state, error, external service. Never decorative.
- Composition: predictable grid, figures near the text they support.

## Executive

- Typography: larger hierarchy contrast; short lines; strong section leads.
- Tables: few rows per page, aggregated values, no raw detail dumps.
- Diagrams: impact charts and comparisons, not implementation flows.
- Density: low. Few data points per page; summary before detail.
- Color: restrained accent used to mark impact and recommendation.
- Composition: summary first, recommendations and decisions visibly separated from analysis.

## Institutional

- Typography: the confirmed template's family and hierarchy; formal, consistent across every page.
- Tables: template-consistent styling, bordered, labeled headers.
- Diagrams: formal, aligned to the template's palette and heading levels.
- Density: moderate; consistency over compression.
- Color: confirmed branding only.
- Composition: cover and metadata present, formal heading hierarchy, uniform header/footer, no per-section styling drift.

## Sober

- Typography: highly legible, one serif or one sans, minimal weight variation.
- Tables: plain grids, clear headers, no fills beyond a light header row.
- Diagrams: monochrome or two-tone, shape and label carry the meaning.
- Density: balanced; generous but intentional spacing.
- Color: neutral palette, minimal decoration.
- Composition: balanced margins, calm rhythm, nothing competing for attention.

## Custom

- Requires additional user specification before any generation: typography, palette, table style, diagram style, density, and composition rules.
- Do not infer a custom direction from an example document unless the user confirms that document as the reference.
- An unspecified Custom direction stops the run; it never degrades into Sober or Institutional.
