# Code listing style

Goal: render fenced code blocks as elegant, full-width, page-breakable listings
(light background, side rule, line numbers, syntax highlighting for known languages)
instead of bare `verbatim`, so code sections stop leaving dead space.

Motivation: reports/metodos-numericos-ejercicio-1-5 "Código modificado" looked plain
and left half the page width empty.

## Tasks

- [ ] 1. Builder emits a styled `lstlisting` for fenced blocks (language mapped from the fence word), every LaTeX template loads the style, tests updated (RED → GREEN), real build checked.
- [ ] 2. Rebuild the ejercicio 1.5 PDF, re-validate, and present for final review.
