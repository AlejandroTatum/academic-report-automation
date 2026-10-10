# Bauhaus maps

Concept maps and process maps rendered automatically from a YAML spec in the "Bauhaus técnico" style the user chose.
Repo AlejandroTatum/academic-report-automation; worktree academic-report-automation-worktrees/pi; branch feat/bauhaus-maps (base origin/main 4c1d9cd).
Approved look: outputs/visual-prototypes/variante-b-bauhaus.png (concept map) and variante-b-bauhaus-proceso.png (process map); prototype code in outputs/visual-prototypes/{proto.py,themes.py,process_bauhaus.py} (gitignored, reference only).

## Specs

- S1. Scope: "mapas conceptuales, mapas de proceso, en general mapas que cuestan un poco mas realizar. lo que ya estan bien son las graficas que normalmente hace phython". Matplotlib/Python data charts and the existing `editorial_svg.py` `actor_map` stay unchanged.
- S2. Style: "se ven muy genericos, agregar colores, cambiar la tipografia. la estructura me parece correcto, lo que pasa es que se muy generico"; the user picked variant B ("esta me gusto", "si dale, me gusta ese estilo"). Tokens, exactly as in the prototype:
  - Font: Space Grotesk only (`font-family="Space Grotesk, sans-serif"`), weights 400/500/600/700.
  - Background `#F6F4EE`, ink `#121212`, muted `#4A4A4A`. Palette names: `blue` `#2247B5`, `red` `#E0452A`, `green` `#0D8B6C`, `saffron` `#F2B233` (decisions and the core subtitle only).
  - Colour encodes meaning: a concept family (concept map) or an actor lane (process map). Never one colour per node.
  - Header: an uppercase kind label in red with 2.2 letter-spacing ("MAPA CONCEPTUAL" / "MAPA DE PROCESO"), the title in muted beside it, and a hairline below.
  - Legend at the foot: a 4-unit coloured line and a bold uppercase label (+ meaning text for concept families); no chip grid.
- S3. Concept map structure, as in the approved prototype:
  - The core concept is a solid ink box with a white bold title and a saffron uppercase subtitle.
  - Key concepts are solid family colour with white text. Leaves are white with a 3-unit family-coloured border and a 14-unit corner square.
  - Every link carries its linking phrase, coloured by the source family. Cross-links are dashed and drawn with `constraint=false`, so they do not shape the ranks.
  - An optional `spine` list of ids is laid out as a straight central axis (Graphviz `group`). Sibling order follows the spec (`ordering=out`).
- S4. Process map structure, as in the approved prototype:
  - 2 or 3 actor lanes as columns with solid coloured headers and 5 % tinted bodies, plus an optional artifact lane (document shapes with a folded corner, dashed connector from the step).
  - Steps as rows: white box with a 3-unit lane-coloured border and a 30-unit corner square holding the step number. Decisions are saffron diamonds and are not numbered.
  - Flow edges are orthogonal and ink-coloured, with uppercase branch labels (SÍ/NO). No connector crosses a node: an edge that skips rows runs along the free edge of its source lane, and a back edge (to an earlier row) loops on the right of its source box.
- S5. Automatic layout from YAML: the author writes only content (`render <spec.yml> --out <fig.svg> [--png <fig.png>]`). Graphviz (`dot -Tplain`) places concept maps; a deterministic grid places process maps. Malformed specs fail with a `SpecError` naming the field, exit code 2 and no output file written.
- S6. Legibility, the rule from the plan: "Si el mapa no entra con letra de 5.5 pt o más ... en vez de achicar la letra". Every rendered figure passes `editorial_svg.check` at 13.5 cm. A layout wider than 860 units is never shrunk: render fails with a message naming the width and telling the author to split the map or shorten names/details.
- S7. Fonts ship in the repo (`assets/fonts/SpaceGrotesk[wght].ttf` + its `OFL.txt`). `--png` rasterises with `rsvg-convert -z 2` under a generated fontconfig that loads that folder, so a PNG looks the same on any machine. Nothing is installed system-wide.
- S8. The skill makes this the default for maps: `skills/academic-visual-builder` (SKILL.md, a new `references/bauhaus-maps.md` with both spec schemas and examples, `editorial-style.md`/`visual-workflow.md` pointers), plus two example specs from the DBP AA01 content. Update the contract tests in `tests/skills/`.

## Tasks

- T1 (S2, S3, S5, S6, S7) fonts + shared render core + `concept_map` in `tools/bauhaus_maps.py` with `tools/test_bauhaus_maps.py` — route: worker, test-first — commit: T1-HASH (RED 47 failed + 2 already green → GREEN 49 passed)
- T2 (S4, S5, S6) `process_map` — route: worker, test-first — commit: pending
- T3 (S8) skill docs, example specs, contract tests — route: worker — commit: pending
- T4 (all) independent verification, full suite, PR — route: verifier + parent — commit: pending

## Log

- L1 (2026-10-10, user): "si dale, me gusta ese estilo" (go-ahead to build the engine as proposed: YAML specs, automatic layout, Bauhaus render with Space Grotesk in the repo, legibility gate with no shrinking, skill default, tests and PR).
- L2 (user, earlier in the same thread): "ahora quiero mejorar los diargamas, mapas concepturales, las graficas en general, como lo podriamos hacer?" -> "mapas conceptuales, mapas de proceso, en general mapas que cuestan un poco mas realizar. lo que ya estan bien son las graficas que normalmente hace phython" -> prototypes -> "se ven muy genericos, agregar colores, cambiar la tipografia..." -> variant B chosen.
- L3: Graphviz is at /usr/bin/dot. `-Tplain` reports node centres and sizes in inches (multiply by 72 once), edge B-spline points and, when present, a label followed by "xl yl style color" (one-word labels come unquoted). Declare edge fontsize 14 to dot so 12.5 labels get room.
- L4 (T1, worker): RED `tools/test_bauhaus_maps.py` = 47 failed, 2 passed (fonts ship + editorial regression guard were green from the start). GREEN = 49 passed. Full suite 2178 passed, 1 skipped (this tree collects 2129 passed + 1 skipped without the new file, plus 49 new). Commit T1-HASH `feat(visuals): render Bauhaus concept maps from a YAML spec`. Decisions: text is measured with Pillow on the shipped variable font (no per-character estimates); link labels are given to dot as fixed-size HTML cells so the layout does not depend on system fonts; edges are matched to links by (from, to), so a repeated link pair is rejected.
