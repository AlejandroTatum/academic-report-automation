#!/usr/bin/env python3
"""
Visual PDF Auditor — heuristic page-image analysis for academic reports.

Renders PDF pages to PNG via pdftoppm (no PyMuPDF required), then analyzes
each page for common visual risks in academic PDF output:

  - Near-blank pages / excessive whitespace
  - Ink/tone blocks touching page edges (possible clipping)
  - Possible orphan headings near page bottom
  - Suspiciously low content density
  - Table-like regions (grid/banding patterns)

Output artifacts:
  - Rendered page PNGs in <outdir>/rendered/page-*.png
  - Contact sheet (thumbnail grid) at <outdir>/contact_sheet.png
  - Report at <outdir>/visual_qa.md
  - Optional JSON output with --json

Exit codes:
  0 = PASS or PASS_WITH_WARNINGS
  1 = FAIL (probable defects)
  2 = fatal error (PDF not found, render failed, etc.)

Dependencies:
  - pdftoppm (from poppler-utils)
  - Pillow (PIL)

Integration note:
  This tool can be called from validate_report.py by adding a 'visual_pdf'
  validator. See pdf_layout_validation() in validate_report.py — the visual
  auditor complements that text-based check by analyzing page images.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from PIL import Image, ImageFilter, ImageStat

from report_config import CONTENT_ROOT


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DPI = 150  # ~0.17 mm/px — good balance for heuristics
BOTTOM_ORPHAN_FRAC = 0.12  # bottom 12 % of page for orphan heading check
EDGE_MARGIN_PX = 5  # threshold from page edge to check for clipping
MIN_CONTENT_FRAC = 0.005  # ink fraction below this → WARNING
VERY_LOW_FRAC = 0.001  # ink fraction below this → FAIL (near-blank)
TABLE_EDGE_THRESHOLD = 0.004  # edge-pixel fraction to suspect a table


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class PageFinding:
    page: int
    near_blank: bool = False
    blank_reason: Optional[str] = None
    orphan_heading: bool = False
    orphan_confidence: Optional[float] = None
    edge_clipping: bool = False
    edge_side: Optional[str] = None
    low_density: bool = False
    density_frac: Optional[float] = None
    table_suspect: bool = False
    table_confidence: Optional[float] = None
    ink_center_of_mass_y: Optional[float] = None
    note: str = ""


@dataclass
class AuditResult:
    pdf_path: str
    total_pages: int = 0
    page_width_px: int = 0
    page_height_px: int = 0
    findings: list = field(default_factory=list)
    contact_sheet: str = ""
    artifacts_dir: str = ""
    render_success: bool = True
    severity: str = "PASS"  # PASS | PASS_WITH_WARNINGS | FAIL
    summary: str = ""


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_pdf_to_pngs(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = DEFAULT_DPI,
) -> tuple[list[Path], int, int, int]:
    """Render PDF pages to grayscale PNG images via pdftoppm.

    Returns (png_paths, width_px, height_px, num_pages).
    """
    # Clean stale images from previous audit runs — prevents duplicate
    # page-1.png vs page-01.png collisions in the glob.
    for stale in output_dir.glob("page-*.png"):
        stale.unlink(missing_ok=True)

    # pdftoppm outputs prefix-1.png, prefix-2.png, …
    prefix = output_dir / "page"

    cmd = [
        "pdftoppm",
        "-png",
        "-r", str(dpi),
        "-gray",           # render as grayscale — saves I/O, enough for heuristics
        "-aa", "yes",
        "-aaVector", "yes",
        str(pdf_path),
        str(prefix),
    ]

    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=180,
    )

    if proc.returncode != 0:
        raise RuntimeError(
            f"pdftoppm failed (exit {proc.returncode}): "
            f"{proc.stderr.strip() or '(no stderr)'}"
        )

    pngs = sorted(
        output_dir.glob("page-*.png"),
        key=lambda p: int(re.search(r"page-(\d+)", p.stem).group(1)),
    )

    if not pngs:
        raise RuntimeError("pdftoppm produced no output PNGs")

    # Collect dimensions from the first page
    with Image.open(pngs[0]) as img:
        w, h = img.size

    return pngs, w, h, len(pngs)


# ---------------------------------------------------------------------------
# Image-analysis helpers
# ---------------------------------------------------------------------------


def _pixels(img: Image.Image) -> list:
    """Return flat pixel list — compatible when ``getdata()`` is removed."""
    # getdata() is deprecated in Pillow 12; try the replacement first.
    try:
        return list(img.get_flattened_data())
    except AttributeError:
        return list(img.getdata())


def _grayscale(img: Image.Image) -> Image.Image:
    return img if img.mode == "L" else img.convert("L")


def ink_fraction(img: Image.Image, threshold: int = 240) -> float:
    """Proportion of pixels darker than *threshold* (i.e. ink/toner)."""
    gs = _grayscale(img)
    pixels = _pixels(gs)
    dark = sum(1 for p in pixels if p < threshold)
    return dark / len(pixels) if pixels else 0.0




def variance(img: Image.Image) -> float:
    """Normalised standard deviation of pixel intensities (0..1)."""
    stat = ImageStat.Stat(_grayscale(img))
    return stat.stddev[0] / 255.0 if stat.stddev[0] else 0.0


def edge_pixel_fraction(img: Image.Image) -> float:
    """Fraction of pixels that are strong edges (FIND_EDGES filter)."""
    gs = _grayscale(img)
    edges = gs.filter(ImageFilter.FIND_EDGES)
    stat = ImageStat.Stat(edges)
    mean = stat.mean[0]
    threshold = max(30, mean * 2.5)
    pixels = _pixels(edges)
    n_edge = sum(1 for p in pixels if p > threshold)
    return n_edge / len(pixels) if pixels else 0.0


def center_of_mass_y(img: Image.Image) -> float:
    """Vertical centroid of ink (0 = top, 1 = bottom)."""
    gs = _grayscale(img)
    h = gs.height
    total_dark = 0
    weighted = 0
    for y in range(h):
        for x in range(gs.width):
            if gs.getpixel((x, y)) < 240:
                total_dark += 1
                weighted += y
    if total_dark == 0:
        return 0.5
    return weighted / total_dark / h


# ---------------------------------------------------------------------------
# Heuristic checks (per page)
# ---------------------------------------------------------------------------


def check_near_blank(img: Image.Image) -> tuple[bool, Optional[str]]:
    """Return (is_near_blank, reason)."""
    gs = _grayscale(img)
    pixels = _pixels(gs)
    n_ink = sum(1 for p in pixels if p < 240)
    frac = n_ink / len(pixels)

    if frac < VERY_LOW_FRAC:
        return True, f"density={frac:.6f} (below VERY_LOW_FRAC={VERY_LOW_FRAC})"
    if frac < MIN_CONTENT_FRAC and variance(img) < 0.03:
        return True, f"density={frac:.6f}, variance too low"

    return False, None


def has_full_bleed_background(img: Image.Image, margin: int = 8) -> bool:
    """Detect if a page has a cover-like background image reaching the edges.

    Unlike a strict "full-bleed" check that requires all 4 sides, this detects
    also partial-bleed decorative backgrounds (common in UNL cover pages):

      Criteria (must meet at least two):
        (A) Top edge near a corner has >15 % dark pixels (header decoration)
        (B) Right edge near top has >15 % dark pixels (side decoration)
        (C) Left edge is clean (<2 % dark) throughout — distinguishes
            background corner decoration from full-width content clipping
        (D) Bottom edge is clean (<2 % dark)
        (E) Ink on the right edge is concentrated in the top 15 % and/or
            bottom 15 % of the page (corner decorations), not spanning
            the full page height

    Returns True when the page has background-like edge ink characteristic
    of a decorative cover, as opposed to content accidentally clipping.
    """
    w, h = img.size
    gs = _grayscale(img)

    # Right-edge per-band analysis
    right_full = gs.crop((w - margin, 0, w, h))
    rpx = _pixels(right_full)
    r_h = len(rpx) // margin  # approximate pixel rows
    r_dark_total = sum(1 for p in rpx if p < 200) / len(rpx) if rpx else 0.0

    # Right edge top 15 % band
    r_top_h = max(1, int(h * 0.15))
    right_top = gs.crop((w - margin, 0, w, r_top_h))
    rtp = _pixels(right_top)
    r_top_frac = sum(1 for p in rtp if p < 200) / len(rtp) if rtp else 0.0

    # Right edge bottom 15 % band
    r_bot = gs.crop((w - margin, h - r_top_h, w, h))
    rbp = _pixels(r_bot)
    r_bot_frac = sum(1 for p in rbp if p < 200) / len(rbp) if rbp else 0.0

    # Top edge left corner (first 15 % of width)
    t_left_w = max(1, int(w * 0.15))
    top_left = gs.crop((0, 0, t_left_w, margin))
    tlp = _pixels(top_left)
    top_left_frac = sum(1 for p in tlp if p < 200) / len(tlp) if tlp else 0.0

    # Top edge right corner (last 15 % of width)
    top_right = gs.crop((w - t_left_w, 0, w, margin))
    trp = _pixels(top_right)
    top_right_frac = sum(1 for p in trp if p < 200) / len(trp) if trp else 0.0

    # Left edge (should be clean for a decorated cover)
    left_edge = gs.crop((0, 0, margin, h))
    lep = _pixels(left_edge)
    left_frac = sum(1 for p in lep if p < 200) / len(lep) if lep else 0.0

    # Bottom edge (should be clean)
    bottom_edge = gs.crop((0, h - margin, w, h))
    bep = _pixels(bottom_edge)
    bot_frac = sum(1 for p in bep if p < 200) / len(bep) if bep else 0.0

    # Criteria
    crit_a = top_left_frac > 0.15 or top_right_frac > 0.15
    crit_b = r_top_frac > 0.15
    crit_c = left_frac < 0.02
    crit_d = bot_frac < 0.02
    # Right-edge ink is NOT spanning full height — it's concentrated
    # in top and/or bottom corners
    if r_dark_total > 0.02:
        r_mid_h = gs.crop((w - margin, int(h * 0.25), w, int(h * 0.75)))
        rmp = _pixels(r_mid_h)
        r_mid_frac = sum(1 for p in rmp if p < 200) / len(rmp) if rmp else 0.0
        crit_e = r_mid_frac < 0.01
    else:
        crit_e = True  # No right-edge ink at all — trivially satisfied

    # Score: need at least 2 positive criteria
    score = sum([crit_a, crit_b, crit_c, crit_d, crit_e])
    return score >= 2


def check_edge_clipping(
    img: Image.Image, margin: int = EDGE_MARGIN_PX,
) -> Optional[str]:
    """Return edge name if ink touches page edge, else None.

    Pages with a full-bleed background (detected by *has_full_bleed_background*)
    are skipped — the background image is expected to reach the paper edge
    and is NOT actual content clipping.
    """
    if has_full_bleed_background(img):
        return None

    w, h = img.size
    gs = _grayscale(img)
    zones = {
        "left": gs.crop((0, 0, margin, h)),
        "right": gs.crop((w - margin, 0, w, h)),
        "top": gs.crop((0, 0, w, margin)),
        "bottom": gs.crop((0, h - margin, w, h)),
    }
    for side, strip in zones.items():
        px = _pixels(strip)
        dark = sum(1 for p in px if p < 200)
        if dark / len(px) > 0.02:
            return side
    return None


# NOTE: an earlier duplicate definition of check_orphan_heading() used to sit
# here and was silently replaced by the one below, so its cover-page guard
# never ran. The guard is deliberately NOT reinstated: has_full_bleed_background()
# returns True for an ordinary body page and even for a blank one (three of its
# five criteria are satisfied by clean edges alone), so calling it here would
# suppress orphan detection on every page instead of only on covers.
def check_orphan_heading(img: Image.Image) -> tuple[bool, Optional[float]]:
    """Check for a possible orphan heading at the bottom of the page.

    Heuristic: the bottom band has a short (few-row) strip of ink that
    does *not* span the full page width — resembling a heading/title
    with no body content after it.
    """
    w, h = img.size
    bottom_start = int(h * (1 - BOTTOM_ORPHAN_FRAC))
    bottom_band = img.crop((0, bottom_start, w, h))
    gs = _grayscale(bottom_band)
    rows: list[float] = []
    for y in range(gs.height):
        row_dark = sum(
            1 for x in range(gs.width) if gs.getpixel((x, y)) < 240
        )
        rows.append(row_dark / gs.width)

    # Find contiguous ink strips
    strips: list[tuple[int, int]] = []
    in_strip = False
    start = 0
    for y, frac in enumerate(rows):
        if frac > 0.02 and not in_strip:
            start = y
            in_strip = True
        elif frac <= 0.001 and in_strip:
            strips.append((start, y - 1))
            in_strip = False
    if in_strip:
        strips.append((start, len(rows) - 1))

    if not strips:
        return False, None

    for s, e in strips:
        strip_height = e - s + 1
        # A heading should be a few lines at most
        if strip_height > 12:
            continue
        # Should not occupy a large fraction of the bottom band
        if strip_height / gs.height > 0.3:
            continue

        max_row_frac = max(rows[s : e + 1])
        # Heading rows do not span full width
        if max_row_frac >= 0.5:
            continue
        # Very sparse strips (e.g. page numbers, section numbering)
        # are not orphan headings — require at least some substance
        if max_row_frac < 0.04:
            continue

        # Skip strips in the bottom 40 % of the bottom band — they're likely
        # footer elements (page numbers, institution text) rather than
        # orphan headings. Also skip when near the absolute page bottom.
        if s > gs.height * 0.5 or (bottom_start + s + strip_height) > h * 0.96:
            continue

        # There should be a noticeable gap above the strip
        gap_above = s >= 4

        # The area above the bottom band should have normal content
        main_area = img.crop((0, int(h * 0.15), w, bottom_start))
        if ink_fraction(main_area) < 0.005:
            continue

        if gap_above:
            conf = round(min(1.0, (0.5 - max_row_frac) / 0.4), 2)
            if conf > 0.2:
                return True, conf

    return False, None


def check_low_density(img: Image.Image) -> tuple[bool, float]:
    """Return (is_low_density, ink_fraction)."""
    frac = ink_fraction(img)
    return frac < MIN_CONTENT_FRAC, round(frac, 6)


def check_table_like(img: Image.Image) -> tuple[bool, Optional[float]]:
    """Detect likely table regions via edge density + row-band transitions."""
    gs = _grayscale(img)
    edges = gs.filter(ImageFilter.FIND_EDGES)
    stat = ImageStat.Stat(edges)

    if (stat.mean[0] or 0) < 5:
        return False, None

    epf = edge_pixel_fraction(img)
    if epf < TABLE_EDGE_THRESHOLD:
        return False, None

    # Build horizontal projection
    px_data = _pixels(gs)
    row_ink = []
    for y in range(gs.height):
        row = px_data[y * gs.width : (y + 1) * gs.width]
        row_ink.append(sum(1 for p in row if p < 200) / len(row))

    transitions = sum(
        1 for i in range(1, len(row_ink))
        if (row_ink[i] > 0.02) != (row_ink[i - 1] > 0.02)
    )

    if transitions > 30:
        conf = round(min(1.0, (transitions - 30) / 80), 2)
        return True, conf

    return False, None


# ---------------------------------------------------------------------------
# Contact sheet
# ---------------------------------------------------------------------------


def create_contact_sheet(
    png_paths: list[Path],
    output_path: Path,
    cols: int = 4,
    thumb_size: tuple[int, int] = (300, 424),
) -> Path:
    """Build a grid thumbnail of all pages and save as PNG.

    Each thumbnail is labelled with the page number in the top-left corner.
    """
    thumbs: list[Image.Image] = []
    for p in png_paths:
        im = Image.open(p)
        im.thumbnail(thumb_size, Image.LANCZOS)
        thumbs.append(im)

    if not thumbs:
        msg = "No page images for contact sheet"
        raise ValueError(msg)

    rows_needed = (len(thumbs) + cols - 1) // cols
    gap = 4
    total_w = cols * thumb_size[0] + (cols - 1) * gap
    total_h = rows_needed * thumb_size[1] + (rows_needed - 1) * gap

    sheet = Image.new("RGB", (total_w, total_h), (245, 245, 245))
    from PIL import ImageDraw  # lazy import

    for idx, page_img in enumerate(thumbs):
        x = (idx % cols) * (thumb_size[0] + gap)
        y = (idx // cols) * (thumb_size[1] + gap)
        sheet.paste(page_img, (x, y))
        draw = ImageDraw.Draw(sheet)
        draw.text((x + 3, y + 3), str(idx + 1), fill=(200, 0, 0))

    sheet.save(output_path, "PNG")
    return output_path


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


def _now_str() -> str:
    """Return a compact timestamp via /bin/date."""
    try:
        return subprocess.run(
            ["date", "+%Y-%m-%d %H:%M:%S"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except Exception:
        return "(unknown date)"


def write_visual_qa_report(result: AuditResult, output_path: Path) -> Path:
    """Write visual_qa.md — human-readable per-page audit report."""
    sev = result.severity
    icon = {"PASS": "✅", "PASS_WITH_WARNINGS": "⚠️", "FAIL": "❌"}.get(sev, "❓")

    lines = [
        f"# Visual QA Report — `{Path(result.pdf_path).name}`",
        "",
        "## Summary",
        "",
        f"- **Status**: {icon} {sev}",
        f"- **Pages analysed**: {result.total_pages}",
        f"- **Render resolution**: {result.page_width_px}×{result.page_height_px} px ({DEFAULT_DPI} DPI)",
    ]
    if result.contact_sheet:
        lines.append(f"- **Contact sheet**: `{result.contact_sheet}`")
    lines.append(f"- **Artifacts**: `{result.artifacts_dir}/`")
    lines.append("")

    lines.append("## Severity Guide")
    lines.append("")
    lines.append("| Level | Meaning |")
    lines.append("|-------|---------|")
    lines.append("| **PASS** | No issues detected |")
    lines.append("| **PASS_WITH_WARNINGS** | Minor issues — inspect manually |")
    lines.append("| **FAIL** | Probable defects requiring correction |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Per-Page Findings")
    lines.append("")

    flagged = [
        f for f in result.findings
        if f.near_blank or f.orphan_heading or f.edge_clipping
        or f.low_density or f.table_suspect
    ]

    if not flagged:
        lines.append("*No significant issues detected.*")
        lines.append("")

    for f in flagged:
        issues: list[str] = []
        if f.near_blank:
            issues.append(f"**NEAR_BLANK** — {f.blank_reason}")
        if f.orphan_heading:
            issues.append(f"**ORPHAN_HEADING** — confidence={f.orphan_confidence}")
        if f.edge_clipping:
            issues.append(f"**EDGE_CLIPPING** — {f.edge_side} edge")
        if f.low_density:
            issues.append(f"**LOW_DENSITY** — ink fraction={f.density_frac}")
        if f.table_suspect:
            issues.append(f"**TABLE_SUSPECT** — confidence={f.table_confidence}")

        lines.append(f"### Page {f.page}")
        lines.append("")
        lines.append(f"- Center of mass (Y): {f.ink_center_of_mass_y:.3f}")
        for issue in issues:
            lines.append(f"- {issue}")
        if f.note:
            lines.append(f"- Note: {f.note}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        f"_Generated by `visual_pdf_auditor.py` on {_now_str()}_"
    )
    lines.append("")

    text = "\n".join(lines) + "\n"
    output_path.write_text(text, encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# Main audit pipeline
# ---------------------------------------------------------------------------


def audit_pdf(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = DEFAULT_DPI,
) -> AuditResult:
    """Run full visual audit on *pdf_path*, placing artifacts under *output_dir*."""
    pdf_path = pdf_path.resolve()
    output_dir = output_dir.resolve()
    artifacts_dir = output_dir / "rendered"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    result = AuditResult(
        pdf_path=str(pdf_path),
        artifacts_dir=str(artifacts_dir),
    )

    # ---- 1. Render ----
    try:
        pngs, page_w, page_h, n_pages = render_pdf_to_pngs(
            pdf_path, artifacts_dir, dpi,
        )
    except (FileNotFoundError, RuntimeError, subprocess.TimeoutExpired) as exc:
        result.render_success = False
        result.severity = "FAIL"
        result.summary = f"Render failed: {exc}"
        return result

    result.page_width_px = page_w
    result.page_height_px = page_h
    result.total_pages = n_pages

    # ---- 2. Per-page analysis ----
    for idx, png in enumerate(pngs):
        page_num = idx + 1
        with Image.open(png) as img:
            finding = PageFinding(page=page_num)

            # Near-blank
            blank, reason = check_near_blank(img)
            finding.near_blank = blank
            finding.blank_reason = reason

            # Edge clipping — individual pages with full-bleed background
            # are handled inside check_edge_clipping()
            side = check_edge_clipping(img)
            if side:
                finding.edge_clipping = True
                finding.edge_side = side

            # Orphan heading — cover pages with full-bleed background
            # are handled inside check_orphan_heading()
            orphan, conf = check_orphan_heading(img)
            finding.orphan_heading = orphan
            finding.orphan_confidence = conf

            # Low density
            low, dens = check_low_density(img)
            finding.low_density = low
            finding.density_frac = dens

            # Table suspect
            tbl, tblc = check_table_like(img)
            finding.table_suspect = tbl
            finding.table_confidence = tblc

            # Centre of mass
            finding.ink_center_of_mass_y = center_of_mass_y(img)

            result.findings.append(finding)

    # ---- 3. Contact sheet ----
    try:
        cs_path = output_dir / "contact_sheet.png"
        create_contact_sheet(pngs, cs_path)
        result.contact_sheet = str(cs_path)
    except Exception as exc:
        result.contact_sheet = f"ERROR: {exc}"

    # ---- 4. Severity ----
    n_pages = result.total_pages
    # Low density on inner pages (not cover, not last) counts as FAILURE.
    # Cover pages are naturally sparse; last page may be bibliography-only.
    failures = sum(
        1 for f in result.findings
        if f.near_blank or f.edge_clipping
        or (f.low_density and 1 < f.page < n_pages)
    )
    warnings = sum(
        1 for f in result.findings if f.orphan_heading or f.low_density
    )

    if failures > 0:
        result.severity = "FAIL"
    elif warnings > 0:
        result.severity = "PASS_WITH_WARNINGS"
    else:
        result.severity = "PASS"

    result.summary = (
        f"{result.total_pages} pages · "
        f"{failures} failures · {warnings} warnings"
    )

    # ---- 5. Report ----
    report_path = output_dir / "visual_qa.md"
    write_visual_qa_report(result, report_path)
    result.summary += f"\nReport: {report_path}"

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


# Code root, kept for callers that import it. Audit artefacts themselves (page
# renders, contact sheet, visual_qa.md) are build output for a specific report,
# so their default location lives in the content tree.
ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="visual_pdf_auditor",
        description=(
            "Heuristic page-image auditor for academic PDFs. "
            "Renders pages via pdftoppm, analyses with PIL, "
            "and produces a visual_qa.md report + contact sheet."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s report.pdf\n"
            "  %(prog)s report.pdf -o /tmp/audit/\n"
            "  %(prog)s report.pdf --dpi 200 --json\n"
            "\n"
            "Detects: near-blank pages, orphan headings, edge clipping,\n"
            "low content density, and table-like regions.\n"
            "\n"
            "Exit: 0 PASS / PASS_WITH_WARNINGS, 1 FAIL, 2 FATAL\n"
        ),
    )
    parser.add_argument(
        "pdf", type=Path, help="Path to the PDF file to audit",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Output directory (default: build/visual-audits/<pdf-stem>/)",
    )
    parser.add_argument(
        "--dpi", type=int, default=DEFAULT_DPI,
        help=f"Render resolution in DPI (default: {DEFAULT_DPI})",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Print machine-readable JSON report to stdout",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    pdf = args.pdf
    if not pdf.exists():
        print(f"ERROR: PDF not found: {pdf}", file=sys.stderr)
        return 2

    outdir = args.output or (CONTENT_ROOT / "build" / "visual-audits" / pdf.stem)

    try:
        result = audit_pdf(pdf, outdir, dpi=args.dpi)
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(asdict(result), indent=2, default=str))
    else:
        _print_summary(result)

    return 0 if result.severity in ("PASS", "PASS_WITH_WARNINGS") else 1


def _print_summary(result: AuditResult) -> None:
    """Pretty-print audit results to stderr/stdout."""
    sep = "=" * 58
    print(f"\n{sep}", file=sys.stderr)
    print(f"  Visual PDF Audit: {Path(result.pdf_path).name}", file=sys.stderr)
    print(f"{sep}", file=sys.stderr)
    print(f"  Severity:  {result.severity}", file=sys.stderr)
    print(f"  Pages:     {result.total_pages}", file=sys.stderr)
    failures = sum(1 for f in result.findings if f.near_blank or f.edge_clipping)
    warnings = sum(1 for f in result.findings if f.orphan_heading or f.low_density)
    print(f"  Failures:  {failures}", file=sys.stderr)
    print(f"  Warnings:  {warnings}", file=sys.stderr)
    print(f"{sep}", file=sys.stderr)
    if result.contact_sheet:
        print(f"  Contact:   {result.contact_sheet}", file=sys.stderr)
    print(f"  Report:    {Path(result.artifacts_dir).parent / 'visual_qa.md'}", file=sys.stderr)
    print(f"{sep}\n", file=sys.stderr)

    for f in result.findings:
        tags: list[str] = []
        if f.near_blank:
            tags.append("NEAR_BLANK")
        if f.orphan_heading:
            tags.append("ORPHAN_H")
        if f.edge_clipping:
            tags.append(f"CLIP-{f.edge_side}")
        if f.low_density:
            tags.append("LOW_DENSITY")
        if f.table_suspect:
            tags.append("TABLE")
        tag = " | ".join(tags) if tags else "OK"
        print(f"  [Page {f.page:2d}] {tag}", file=sys.stderr)

    print(file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
