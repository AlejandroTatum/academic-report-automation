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
