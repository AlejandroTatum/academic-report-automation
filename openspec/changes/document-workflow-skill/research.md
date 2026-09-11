# gentle-ai.sdd-research/v1

```yaml
schema: gentle-ai.sdd-research/v1
change: document-workflow-skill
project: academic-report-automation
phase: sdd-research
revision: 1
status: done
outcome: done
```

## Research Question

How should the `document-workflow` skill's user-facing status output be shaped so it reads clearly to a human in an agent chat/terminal (Claude Code, Codex, OpenCode, Pi): the compact route line, current phase, what was completed, what happens next, pending human gate, and active cross-skill handoff — given these surfaces render model-relayed markdown text, not a raw TTY.

## Admission / Grants

- Declared source classes: `documentation`, `open-web`.
- Tools used: `WebSearch`, `WebFetch` (both grants satisfied).
- No repository, Engram, or local skill files were read; this collector has no filesystem read tool. `~/.claude/skills/_shared/sdd-status-contract.md` (local precedent requested by the orchestrator) was **not** accessible from this role — flagged as a gap below, not fabricated.
- No persistence or mutation performed.

## Executive Summary (≤200 words)

Established CLI guidance (clig.dev) favors human-first, hierarchical, sparing-symbol output: use bold/heading-like structure for scannability, use color/animation only when the stream is an interactive TTY (never assume one), use emoji/symbols sparingly and only where they remove ambiguity, put the most important information last, and always narrate state changes explicitly. Precedents (`gh pr status`, `kubectl rollout status`) confirm a pattern of short section headers plus one-line-per-item plain status text rather than dense tables. This matters directly because primary-source bug reports show Claude Code's terminal renderer supports only ~60% of GFM (headers h2–h6, task checkboxes, and nested blockquotes are silently flattened to bold or stripped), and Codex CLI's TUI does not render markdown pipe tables at all — both render tables and deep structure unreliably. Box-drawing and non-ASCII symbol glyphs are unicode/font-dependent and unsafe to assume everywhere. NN Group's usability-heuristics research grounds the need for a compact "current state at a glance" line (visibility of system status) plus a scannable, F-pattern-friendly layout (short first lines, key facts left-aligned, details progressively disclosed below). No source directly documents OpenCode's or Pi's markdown fidelity in enough detail to state a supported-feature list with confidence; that remains an evidenced gap.

## Sources

| ID | Class | Title | Publisher | URL | Accessed |
|----|-------|-------|-----------|-----|----------|
| S1 | documentation | Command Line Interface Guidelines | clig.dev | https://clig.dev/ | 2026-09-10 |
| S2 | documentation | Visibility of System Status (Usability Heuristic #1) | Nielsen Norman Group | https://www.nngroup.com/articles/visibility-system-status/ | 2026-09-10 |
| S3 | documentation | F-Shaped Pattern For Reading Web Content | Nielsen Norman Group | https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content-discovered/ | 2026-09-10 |
| S4 | open-web | Terminal markdown renderer silently destroys ~40% of GFM features (#26390) | GitHub — anthropics/claude-code | https://github.com/anthropics/claude-code/issues/26390 | 2026-09-10 |
| S5 | open-web | CLI markdown tables are not rendered as readable aligned tables in TUI output (#15449) | GitHub — openai/codex | https://github.com/openai/codex/issues/15449 | 2026-09-10 |
| S6 | documentation | `gh pr status` manual | GitHub CLI (cli.github.com) | https://cli.github.com/manual/gh_pr_status | 2026-09-10 |
| S7 | open-web | `kubectl rollout status` progress text behavior (search-derived; official page not fetched verbatim) | Kubernetes docs / secondary summaries | https://kubernetes.io/docs/reference/kubectl/generated/kubectl_rollout | 2026-09-10 |
| S8 | open-web | Box-drawing characters | Wikipedia | https://en.wikipedia.org/wiki/Box-drawing_characters | 2026-09-10 |

Excerpts (verbatim or tightly paraphrased from fetch/search output above):
- S1: "Bold headings make it much easier to scan" / "These things should disable colors: stdout or stderr is not an interactive terminal (a TTY)" / "Be careful, though — it can be easy to overdo it [symbols/emoji] and make your program look cluttered" / "Put the most important information at the end of the output" / "When a command changes the state of a system, it's especially valuable to explain what has just happened."
- S2: "Ideally, systems should always keep users informed about what is going on, through appropriate feedback within reasonable time."
- S3: Eyetracking shows users scan in an F-shaped pattern; first lines and left-aligned leading words get disproportionate attention; ~79% of users scan rather than read fully.
- S4: Claude Code's terminal renderer supports bold/italic, code spans, fenced code, diff blocks, tables, flat lists, single-level blockquotes; it silently flattens `##`–`######` headers to bold (hierarchy lost), strips task-list checkbox state, and collapses nested blockquotes.
- S5: "Markdown tables in Codex CLI/TUI output are not rendered as readable terminal tables. They are effectively treated as plain markdown text, so column structure is lost."
- S6: `gh pr status` groups output into named sections ("Current branch", "Created by you", "Requesting a code review from you"), each a short list of one-line items with inline status tokens, not a table.
- S7: `kubectl rollout status` streams single-line, self-overwriting progress text ("Waiting for deployment ... to finish: 2 out of 5 new replicas have been updated ...") ending in one explicit terminal success line.
- S8: Box-drawing glyphs require a monospaced font and consistent glyph coverage; several terminal emulators/fonts historically misrender or fail to align them, so they are not universally safe.

## Validated Claims

| # | Claim | Source(s) |
|---|-------|-----------|
| C1 | CLI status output should be human-first and hierarchical, using bold/heading-style emphasis for scanability rather than relying on color or animation that may not render. | S1 |
| C2 | Color and animated indicators must be assumed unavailable/unreliable in a non-interactive or model-relayed stream; the design must not depend on them for meaning. | S1 |
| C3 | Symbols/emoji are acceptable only when they remove ambiguity (e.g., a single unambiguous "done" vs "pending" marker), used sparingly to avoid clutter. | S1 |
| C4 | The most decision-critical information (e.g., what happens next, blocking gate) should be placed where the eye naturally lands last/first depending on layout — surfaced prominently, not buried mid-block. | S1, S3 |
| C5 | Explicit state-change narration ("what just happened") is a core CLI UX expectation whenever a command mutates state. | S1 |
| C6 | Visibility of current system status is a foundational usability requirement; users need brief, understandable, timely feedback on where they are and whether their last action succeeded. | S2 |
| C7 | Users scan rather than read line-by-line; leading words/first lines of each block carry disproportionate attention weight, favoring short lead-line summaries with detail below (progressive disclosure). | S3 |
| C8 | Claude Code's terminal renderer degrades multi-level markdown headers to uniform bold text and strips task-checkbox state and nested blockquote depth — deep heading hierarchies and `- [x]` checklists cannot be relied on to convey structure. | S4 |
| C9 | Claude Code's renderer does support: bold/italic, fenced code blocks, flat bulleted/numbered lists, single-level blockquotes, and tables (tables render correctly in Native UI mode; degrade to flattened key:value lines in raw terminal mode per issue discussion). | S4 |
| C10 | Codex CLI's TUI does not render markdown pipe tables as aligned tables; they appear as raw pipe-delimited text, making tables an unreliable structural choice across these two surfaces. | S5 |
| C11 | Precedent CLIs (`gh pr status`) organize multi-part status into short named sections of one-line items rather than dense tables, which is more portable across renderers than markdown tables. | S6 |
| C12 | Precedent tools (`kubectl rollout status`) render pipeline/step progress as a short sequence of plain-text lines culminating in one unambiguous terminal success/failure line, not a step-counter widget. | S7 |
| C13 | Unicode box-drawing and many decorative glyphs are font/terminal-dependent and can misrender or misalign; a template that must degrade gracefully across unknown renderers should avoid relying on them for structural meaning. | S8, S4, S5 |

## Contradictions / Uncertainty / Freshness

- No direct contradictions found between sources; all point the same direction (favor plain hierarchical text and short lists over tables/box-drawing/deep nesting for portability).
- **Uncertainty — OpenCode markdown fidelity**: only general marketing/GitHub-readme material was found (S: search results, not cited above because no primary rendering-fidelity claim could be extracted); no primary source enumerates OpenCode's supported/unsupported GFM subset. Treat OpenCode as "unknown fidelity, assume the lowest common denominator" rather than "known to support X."
- **Uncertainty — Pi markdown fidelity**: search surfaced `pi-tui`/`pi-markdown-preview`/Rust "FrankenTUI" ecosystem material describing markdown rendering components exist, but nothing confirms which GFM subset is supported inside Pi's own chat pane versus companion preview tools. Not usable as a validated claim; flagged as a gap.
- **Freshness**: S4 and S5 are open, dated bug reports (2026); they describe current known limitations, not guaranteed-permanent ones — a future renderer update could close the gap. The artifact should be revisited if either project ships GFM/table-rendering fixes.
- The local precedent `~/.claude/skills/_shared/sdd-status-contract.md` could not be read in this role; claims about how `gentle-ai sdd-status` itself formats output are **not validated by this research** and must come from the orchestrator's own file access, not from this artifact.

## Gaps

- No primary-source confirmation of OpenCode's exact supported markdown subset in its chat/TUI pane.
- No primary-source confirmation of Pi's exact supported markdown subset in its own conversational rendering surface (as opposed to companion preview tooling).
- `~/.claude/skills/_shared/sdd-status-contract.md` precedent not inspected by this collector (no file-read tool); the orchestrator should read it directly rather than relying on this artifact for that content.

## Risks

- Designing the template assuming table support will silently break on Codex (confirmed, S5) and degrade unpredictably on Claude Code terminal mode (confirmed, S4).
- Relying on deep `###`/`####` heading nesting for phase/step hierarchy will collapse to uniform bold on at least one supported surface (Claude Code, S4), losing intended visual hierarchy.
- Assuming any decorative box-drawing or multi-glyph iconography renders identically risks visual breakage on unknown terminal/font combinations (S8) and adds no functional value per clig.dev's caution against clutter (S1).

## Non-Authoritative Product Choices (for orchestrator confirmation only — not decided here)

These are candidate directions surfaced by the evidence, not selections:

1. **Structure**: one compact route/progress line (plain text, arrows or `>`, no box-drawing) + a single H2-level "Summary" block using flat bullet lists (not nested, not tables) + a single H2-level "Next" line + an explicit, separately labeled gate/handoff line when applicable — mirroring `gh pr status`'s named-section-of-one-liners pattern (S6) and avoiding tables (S4, S5) and deep header nesting (S4).
2. **Symbols**: at most one binary marker convention (e.g., plain-ASCII `[done]` / `[pending]` / `[blocked]` tokens rather than unicode ✓/○/●) to sidestep font/rendering risk (S8) while still meeting "symbols where they remove ambiguity" (S1, S3).
3. **Progress representation**: a `step X/Y` plain counter plus one current-step sentence (kubectl-style single evolving status line, S7) rather than a rendered progress bar or ANSI spinner (unsafe per S1's "disable animation when not a TTY").
4. **Gate/handoff visibility**: since NN Group's status-visibility heuristic (S2) and F-pattern scanning (S3) favor short lead sentences, any pending human gate or active cross-skill handoff should be its own short, front-loaded line rather than buried in a details block.

The orchestrator should confirm or reject these directions with the user before `sdd-design`/`sdd-tasks` fixes the actual template.

## Next Recommended

Have the orchestrator read `~/.claude/skills/_shared/sdd-status-contract.md` directly (file access unavailable to this research role) to capture the exact `gentle-ai sdd-status` precedent fields/format, then reconcile it with the candidate directions above before proposing the `document-workflow` status template.
