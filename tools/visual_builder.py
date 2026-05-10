#!/usr/bin/env python3
"""Render and validate academic visuals for academic report automation.

Renderers:
- Mermaid CLI for diagrams.
- Vega-Lite / vl-convert for academic charts.
- ECharts SVG SSR through Node.
- HTML screenshot through Playwright + local Chrome for custom cards.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
NODE_BIN = ROOT / "node_modules" / ".bin"
BACKUPS = ROOT / "backups" / "visual-renders"
LOCAL_CHROME_ROOT = ROOT / ".cache" / "puppeteer" / "chrome"
DEFAULT_WIDTH = 1400
DEFAULT_HEIGHT = 900


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(str(c) for c in cmd))
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    proc = subprocess.run(cmd, cwd=cwd or ROOT, env=merged_env, text=True, capture_output=True)
    if proc.returncode != 0:
        if proc.stdout:
            print(proc.stdout)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        raise SystemExit(f"FAILED: {' '.join(str(c) for c in cmd)}")
    if proc.stdout.strip():
        print(proc.stdout.strip())
    return proc


def resolve_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def newest_local_chrome() -> Path | None:
    candidates = sorted(LOCAL_CHROME_ROOT.glob("linux-*/chrome-linux64/chrome"), key=lambda p: p.stat().st_mtime, reverse=True)
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate
    home_candidates = sorted(Path.home().glob(".cache/puppeteer/chrome/linux-*/chrome-linux64/chrome"), key=lambda p: p.stat().st_mtime, reverse=True)
    for candidate in home_candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate
    return None


def require_chrome() -> Path:
    chrome = newest_local_chrome()
    if not chrome:
        raise SystemExit(
            "Chrome/Chromium no encontrado. Instalá localmente con: "
            "npx @puppeteer/browsers install chrome@stable --path .cache/puppeteer"
        )
    return chrome


def mmdc_bin() -> Path:
    local = NODE_BIN / "mmdc"
    if local.exists():
        return local
    global_bin = shutil.which("mmdc")
    if global_bin:
        return Path(global_bin)
    raise SystemExit("Mermaid CLI no encontrado. Instalá @mermaid-js/mermaid-cli localmente.")


def puppeteer_config() -> Path:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    chrome = require_chrome()
    config = BACKUPS / "puppeteer-config.json"
    config.write_text(json.dumps({"executablePath": str(chrome), "args": ["--no-sandbox"]}, indent=2), encoding="utf-8")
    return config


def command_mermaid(args: argparse.Namespace) -> int:
    src = resolve_path(args.input)
    out = resolve_path(args.out)
    ensure_parent(out)
    if not src.exists():
        raise SystemExit(f"No existe spec Mermaid: {src}")
    cmd = [
        str(mmdc_bin()),
        "-i", str(src),
        "-o", str(out),
        "-w", str(args.width),
        "-H", str(args.height),
        "-b", args.background,
        "-p", str(puppeteer_config()),
    ]
    if args.css_file:
        cmd.extend(["-C", str(resolve_path(args.css_file))])
    if args.theme:
        cmd.extend(["-t", args.theme])
    run(cmd)
    print(f"VISUAL={out}")
    return 0


def command_vegalite(args: argparse.Namespace) -> int:
    src = resolve_path(args.input)
    out = resolve_path(args.out)
    ensure_parent(out)
    if not src.exists():
        raise SystemExit(f"No existe spec Vega-Lite: {src}")
    spec = json.loads(src.read_text(encoding="utf-8"))
    fmt = args.format or out.suffix.lower().lstrip(".") or "svg"
    import vl_convert as vlc  # type: ignore

    if fmt == "svg":
        rendered = vlc.vegalite_to_svg(spec)
        out.write_text(rendered, encoding="utf-8")
    elif fmt == "png":
        rendered = vlc.vegalite_to_png(spec, scale=args.scale)
        out.write_bytes(rendered)
    elif fmt == "pdf":
        rendered = vlc.vegalite_to_pdf(spec)
        out.write_bytes(rendered)
    else:
        raise SystemExit("Formato Vega-Lite soportado: svg, png, pdf")
    print(f"VISUAL={out}")
    return 0


def command_echarts(args: argparse.Namespace) -> int:
    src = resolve_path(args.input)
    out = resolve_path(args.out)
    ensure_parent(out)
    if not src.exists():
        raise SystemExit(f"No existe spec ECharts: {src}")
    node_script = dedent(
        """
        const fs = require('fs');
        const echarts = require('echarts');
        const [specPath, outPath, widthRaw, heightRaw] = process.argv.slice(2);
        const option = JSON.parse(fs.readFileSync(specPath, 'utf8'));
        const width = Number(widthRaw || 1400);
        const height = Number(heightRaw || 900);
        const chart = echarts.init(null, null, { renderer: 'svg', ssr: true, width, height });
        chart.setOption(option);
        fs.writeFileSync(outPath, chart.renderToSVGString(), 'utf8');
        chart.dispose();
        """
    )
    BACKUPS.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".cjs", dir=BACKUPS, delete=False, encoding="utf-8") as tmp:
        tmp.write(node_script)
        tmp_path = Path(tmp.name)
    try:
        run(["node", str(tmp_path), str(src), str(out), str(args.width), str(args.height)])
    finally:
        tmp_path.unlink(missing_ok=True)
    print(f"VISUAL={out}")
    return 0


def command_html_shot(args: argparse.Namespace) -> int:
    src = resolve_path(args.input)
    out = resolve_path(args.out)
    ensure_parent(out)
    if not src.exists():
        raise SystemExit(f"No existe HTML: {src}")
    chrome = require_chrome()
    node_script = dedent(
        """
        const { chromium } = require('playwright');
        const path = require('path');
        const [htmlPath, outPath, widthRaw, heightRaw, selector, chromePath] = process.argv.slice(2);
        (async () => {
          const browser = await chromium.launch({ executablePath: chromePath, headless: true, args: ['--no-sandbox'] });
          const page = await browser.newPage({ viewport: { width: Number(widthRaw || 1400), height: Number(heightRaw || 900) }, deviceScaleFactor: 2 });
          await page.goto('file://' + path.resolve(htmlPath), { waitUntil: 'networkidle' });
          if (selector && selector !== 'page') {
            await page.locator(selector).screenshot({ path: outPath, omitBackground: false });
          } else {
            await page.screenshot({ path: outPath, fullPage: true, omitBackground: false });
          }
          await browser.close();
        })().catch(err => { console.error(err); process.exit(1); });
        """
    )
    BACKUPS.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".cjs", dir=BACKUPS, delete=False, encoding="utf-8") as tmp:
        tmp.write(node_script)
        tmp_path = Path(tmp.name)
    try:
        run(["node", str(tmp_path), str(src), str(out), str(args.width), str(args.height), args.selector, str(chrome)])
    finally:
        tmp_path.unlink(missing_ok=True)
    print(f"VISUAL={out}")
    return 0


def validate_image(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"no existe: {path}"]
    if path.stat().st_size < 800:
        errors.append(f"archivo demasiado pequeño: {path}")
    suffix = path.suffix.lower()
    if suffix == ".svg":
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "<svg" not in text:
            errors.append(f"SVG inválido: {path}")
        if not re.search(r"(width|viewBox)=", text):
            errors.append(f"SVG sin width/viewBox: {path}")
    elif suffix == ".png":
        from PIL import Image

        with Image.open(path) as im:
            w, h = im.size
            if max(w, h) < 800 or min(w, h) < 350:
                errors.append(f"PNG demasiado pequeño ({w}x{h}): {path}")
    elif suffix == ".pdf":
        if path.stat().st_size < 2000:
            errors.append(f"PDF visual demasiado pequeño: {path}")
    else:
        errors.append(f"formato no validable: {path}")
    return errors


def metadata_errors(folder: Path) -> list[str]:
    meta = folder / "figures.yml"
    if not meta.exists():
        return [f"falta metadata: {meta}"]
    text = meta.read_text(encoding="utf-8")
    errors = []
    for required in ("file:", "caption:", "source:", "renderer:"):
        if required not in text:
            errors.append(f"figures.yml no contiene {required}")
    return errors


def command_validate(args: argparse.Namespace) -> int:
    target = resolve_path(args.target)
    if not target.exists():
        raise SystemExit(f"No existe target: {target}")
    files = [target] if target.is_file() else sorted(
        p for p in target.rglob("*") if p.suffix.lower() in {".svg", ".png", ".pdf"}
    )
    errors: list[str] = []
    if not files:
        errors.append("no hay visuales SVG/PNG/PDF para validar")
    for file in files:
        errors.extend(validate_image(file))
    if target.is_dir() and not args.no_metadata:
        errors.extend(metadata_errors(target))
    if errors:
        raise SystemExit("VALIDATION FAILED:\n- " + "\n- ".join(errors))
    print(f"VALIDATION_OK {target}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Academic visual renderer for academic report automation")
    sub = parser.add_subparsers(dest="command", required=True)

    mermaid = sub.add_parser("mermaid", help="Render Mermaid spec to SVG/PNG/PDF")
    mermaid.add_argument("input")
    mermaid.add_argument("--out", required=True)
    mermaid.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    mermaid.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    mermaid.add_argument("--background", default="white")
    mermaid.add_argument("--theme", default="neutral")
    mermaid.add_argument("--css-file", help="CSS file to style Mermaid output")
    mermaid.set_defaults(func=command_mermaid)

    vegalite = sub.add_parser("vegalite", help="Render Vega-Lite JSON spec")
    vegalite.add_argument("input")
    vegalite.add_argument("--out", required=True)
    vegalite.add_argument("--format", choices=["svg", "png", "pdf"])
    vegalite.add_argument("--scale", type=float, default=2.0)
    vegalite.set_defaults(func=command_vegalite)

    echarts = sub.add_parser("echarts", help="Render ECharts JSON option to SVG")
    echarts.add_argument("input")
    echarts.add_argument("--out", required=True)
    echarts.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    echarts.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    echarts.set_defaults(func=command_echarts)

    html = sub.add_parser("html-shot", help="Screenshot local HTML through Playwright + local Chrome")
    html.add_argument("input")
    html.add_argument("--out", required=True)
    html.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    html.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    html.add_argument("--selector", default="page")
    html.set_defaults(func=command_html_shot)

    validate = sub.add_parser("validate", help="Validate generated visual file/folder")
    validate.add_argument("target")
    validate.add_argument("--no-metadata", action="store_true")
    validate.set_defaults(func=command_validate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
