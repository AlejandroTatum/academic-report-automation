# Academic Report Automation

Academic report automation toolkit built with Python. It helps generate structured university-style reports, validate deliverables, manage references, and create reproducible visual assets.

> This public version is sanitized for portfolio use. It contains generic templates and sample data only.

## Why this project exists

Academic reports often require consistent formatting, metadata, figures, references, and PDF/DOCX delivery. This toolkit automates the repetitive parts while keeping the student's reasoning and final review as the most important part of the process.

## Features

- Markdown/YAML based report content.
- HTML and PDF generation helpers.
- Academic formatting templates.
- IEEE reference validation helpers.
- Report quality validation checks.
- Visual asset generation with Mermaid, Vega-Lite, ECharts and HTML screenshots.
- Sample report for local testing.
- Clean project structure prepared for public GitHub use.

## Tech Stack

- Python 3
- Markdown
- WeasyPrint
- python-docx
- BeautifulSoup
- Matplotlib / Altair / Plotly
- Mermaid CLI / Playwright / ECharts for optional visuals

## Project Structure

```txt
academic-report-automation/
├── examples/
│   ├── placeholder.svg
│   └── sample_report.md
├── templates/
│   ├── academic_format.yml
│   ├── report.css
│   └── university-report.tex
├── tools/
│   ├── build_report.py
│   ├── build_latex_report.py
│   ├── report_config.py
│   ├── validate_ieee_refs.py
│   ├── validate_report.py
│   └── visual_builder.py
├── assets/generated/
├── outputs/
├── requirements.txt
└── package.json
```

## Quick Start

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Python dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 3. Generate sample HTML

```bash
python3 tools/build_report.py examples/sample_report.md --html outputs/sample_report.html
```

### 4. Generate sample PDF

```bash
python3 tools/build_report.py examples/sample_report.md --pdf outputs/sample_report.pdf
```

## Running the tests

The suite needs `pytest`, which is not part of the runtime dependencies:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest tools/ tests/
```

## Agent skills

`skills/` holds the agent skill definitions and is the single source of truth
for them. The agent runtimes — `~/.claude/skills/` and
`~/.config/opencode/skills/` — are mirrors. Edit here and sync outward; a file
edited directly in a runtime directory is overwritten on the next sync.

Sync by hand:

```bash
./scripts/sync_skills.sh          # dry run — shows what would change
./scripts/sync_skills.sh --apply  # write the changes
```

The sync is gated on the skill contract tests, so a skill that fails its own
routing contract never reaches a runtime.

### Syncing automatically on pull

Install the versioned hooks once per clone:

```bash
./scripts/install_hooks.sh
```

This sets `core.hooksPath` to `.githooks/`, which is needed because `.git/hooks/`
is not versioned — the hooks travel with the repository, but each clone has to be
told where to look.

After that, `post-merge`, `post-rewrite` and `post-checkout` re-sync the runtimes
whenever the repository changes. All three are covered because a plain `git pull`
fires `post-merge` while `git pull --rebase` fires `post-rewrite` instead, and a
branch switch fires neither.

The hook fingerprints the tracked contents of `skills/` and exits immediately when
nothing changed, so an ordinary pull costs nothing. When a sync fails it says so
and deliberately leaves the fingerprint unwritten, so the next pull retries rather
than silently skipping a pending update. Git ignores the exit code of `post-*`
hooks, so this can never block a pull.

## Visual Builder

The toolkit includes a visual builder for reproducible diagrams and charts.

```bash
python3 tools/visual_builder.py --help
```

Supported visual workflows include:

- Mermaid diagrams
- Vega-Lite charts
- ECharts visuals
- HTML screenshots through Playwright
- Generated asset validation

## Portfolio Notes

This project demonstrates:

- Python scripting for automation.
- File organization and output routing.
- Template-based document generation.
- Validation-oriented thinking.
- Report rendering workflows.
- Reproducible academic visuals.

## Important Principle

Automation should support understanding, structure, formatting and review. It should not replace the student's technical reasoning, source evaluation or final responsibility for the content.

## Author

Alejandro Padilla

- GitHub: [AlejandroTatum](https://github.com/AlejandroTatum)
- LinkedIn: [Alejandro Emanuel Padilla Espinoza](https://www.linkedin.com/in/alejandro-emanuel-padilla-espinoza-58003b408/)
