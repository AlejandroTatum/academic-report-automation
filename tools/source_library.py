#!/usr/bin/env python3
"""Manage the local academic source library for UNL reports.

The manifest is intentionally simple and dependency-free. If PyYAML is
installed, it is used for reading; otherwise this script parses the small YAML
subset that it writes itself.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree
from urllib import request
from urllib.parse import unquote, urlparse

from report_config import CONTENT_ROOT, relative_label

# Code root; the source corpus and everything derived from it is content.
ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = CONTENT_ROOT / "academic-sources"
MANIFEST = SOURCE_ROOT / "manifest.yml"

SOURCE_TYPES = (
    "book",
    "article",
    "teacher_note",
    "rubric",
    "template",
    "previous_work",
)

TYPE_DIRS = {
    "book": "books",
    "article": "articles",
    "teacher_note": "teacher-notes",
    "rubric": "rubrics",
    "template": "templates",
    "previous_work": "previous-work",
}

SOURCE_FILE_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".epub"}

OFFICIAL_COURSES = (
    "diseno-software",
    "sistemas-operativos",
    "complejidad-computacional",
    "investigacion",
    "ecuaciones-diferenciales",
)

COURSE_RULES = {
    "diseno-software": (
        "diseño de software",
        "diseño de sofware",
        "diseñosoftware",
        "diseno de software",
        "diseno de sofware",
        "disenosoftware",
        "software design",
        "software engineering",
        "software-engineering",
        "requisitos",
        "requirements",
        "uml",
        "casos de uso",
        "use case",
        "historias de usuario",
        "arquitectura",
        "modelo de dominio",
        "domain model",
        "modelado",
        "scrum",
        "programación orientada a objetos",
        "programacion orientada a objetos",
        "orientada a objetos",
        "object oriented",
        "object-oriented",
        "poo",
        "oop",
        "clases",
        "objetos",
        "herencia",
        "polimorfismo",
    ),
    "sistemas-operativos": (
        "sistemas operativos",
        "sistemasoperativos",
        "operating system",
        "operating systems",
        "ing. hernán",
        "hernán leonardo torres",
        "hernan leonardo torres",
        "trabajo intra-clase",
        "ensayo nº",
        "ensayo no",
        "kernel",
        "linux",
        "process",
        "procesos",
        "thread",
        "hilo",
        "scheduling",
        "planificacion",
        "planificación",
        "memoria",
        "memory",
        "filesystem",
        "archivo",
        "deadlock",
        "virtualizacion",
        "virtualización",
    ),
    "complejidad-computacional": (
        "complejidad computacional",
        "complejidadcomputacional",
        "computational complexity",
        "introduction to computer science",
        "computer science theory",
        "theory of computation",
        "teoría de la computación",
        "teoria de la computacion",
        "models of computation",
        "automata",
        "autómata",
        "algorithms and complexity",
        "quantum computing",
        "computability",
        "np-complete",
        "np complete",
        "big o",
        "notación o",
        "notacion o",
        "recurrencias",
    ),
    "investigacion": (
        "investigación",
        "investigacion",
        "research",
        "metodología",
        "metodologia",
        "artículos científicos",
        "articulos cientificos",
        "matriz de extracción",
        "matriz de extraccion",
        "estado del arte",
        "enfoques en investigacion",
        "enfoques en investigación",
    ),
    "ecuaciones-diferenciales": (
        "ecuaciones diferenciales",
        "ecuacionesdiferenciales",
        "differential equations",
        "ordinary differential",
        "ode",
        "edo",
        "laplace",
        "fourier",
        "ecuación diferencial",
        "ecuacion diferencial",
        "derivadas",
        "valor inicial",
        "variables separables",
        "homogénea",
        "homogenea",
    ),
}

GENERIC_FILENAME_RE = re.compile(
    r"^(download|file|document|documento|untitled|sin-titulo|recurso|"
    r"articulo|artículo|paper|libro|manual|[0-9_.-]+)$",
    flags=re.IGNORECASE,
)

FIELD_ORDER = (
    "id",
    "title",
    "authors",
    "year",
    "course",
    "teacher",
    "type",
    "local_path",
    "url",
    "topics",
    "reliability_note",
    "useful_notes",
    "ieee_citation",
    "inspected",
    "added_at",
)

LIST_FIELDS = {"authors", "topics"}
BOOL_FIELDS = {"inspected"}


def slugify(value: str, fallback: str = "source") -> str:
    value = value.strip().lower()
    value = value.replace("_", "-")
    value = re.sub(r"[^\w\s.-]+", "", value, flags=re.UNICODE)
    value = re.sub(r"[\s.]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or fallback


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def quote_yaml(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        value = ""
    return json.dumps(str(value), ensure_ascii=False)


def parse_scalar(raw: str) -> object:
    raw = raw.strip()
    if raw == "[]":
        return []
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    if not raw:
        return ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def normalize_manifest(data: object) -> dict[str, object]:
    if not isinstance(data, dict):
        return {"version": 1, "sources": []}
    sources = data.get("sources", [])
    if sources is None:
        sources = []
    if not isinstance(sources, list):
        raise SystemExit("Invalid manifest: `sources` must be a list")
    normalized_sources: list[dict[str, object]] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        item = dict(source)
        for key in LIST_FIELDS:
            value = item.get(key, [])
            if isinstance(value, str):
                item[key] = split_csv(value)
            elif value is None:
                item[key] = []
        for key in BOOL_FIELDS:
            item[key] = bool(item.get(key, False))
        normalized_sources.append(item)
    return {"version": int(data.get("version", 1)), "sources": normalized_sources}


def parse_manifest_fallback(text: str) -> dict[str, object]:
    version = 1
    sources: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    pending_list_key: str | None = None

    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("version:"):
            version = int(str(parse_scalar(line.partition(":")[2])) or "1")
            continue
        if line.startswith("sources:"):
            continue
        if line.startswith("  - "):
            if current is not None:
                sources.append(current)
            current = {}
            pending_list_key = None
            content = line[4:]
            key, sep, raw = content.partition(":")
            if sep:
                value = [] if raw.strip() == "" else parse_scalar(raw)
                current[key.strip()] = value
                pending_list_key = key.strip() if value == [] else None
            continue
        if current is None:
            continue
        if line.startswith("      - "):
            if pending_list_key:
                current.setdefault(pending_list_key, [])
                values = current[pending_list_key]
                if isinstance(values, list):
                    values.append(parse_scalar(line[8:]))
            continue
        if line.startswith("    "):
            content = line[4:]
            key, sep, raw = content.partition(":")
            if not sep:
                continue
            key = key.strip()
            value = [] if raw.strip() == "" else parse_scalar(raw)
            current[key] = value
            pending_list_key = key if value == [] else None

    if current is not None:
        sources.append(current)
    return normalize_manifest({"version": version, "sources": sources})


def load_manifest() -> dict[str, object]:
    if not MANIFEST.exists():
        return {"version": 1, "sources": []}
    text = MANIFEST.read_text(encoding="utf-8").strip()
    if not text:
        return {"version": 1, "sources": []}
    if text.startswith("{"):
        return normalize_manifest(json.loads(text))
    try:
        import yaml  # type: ignore

        return normalize_manifest(yaml.safe_load(text))
    except ImportError:
        return parse_manifest_fallback(text)
    except Exception as exc:
        raise SystemExit(f"Invalid manifest YAML: {MANIFEST}\n{exc}") from exc


def write_manifest(data: dict[str, object]) -> None:
    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        raise SystemExit("Invalid manifest: `sources` must be a list")

    lines = ["version: 1"]
    if not sources:
        lines.append("sources: []")
    else:
        lines.append("sources:")
        for source in sources:
            if not isinstance(source, dict):
                continue
            keys = [key for key in FIELD_ORDER if key in source]
            keys.extend(sorted(key for key in source if key not in FIELD_ORDER))
            first = True
            for key in keys:
                value = source.get(key)
                prefix = "  - " if first else "    "
                first = False
                if key in LIST_FIELDS:
                    values = value if isinstance(value, list) else []
                    if values:
                        lines.append(f"{prefix}{key}:")
                        for item in values:
                            lines.append(f"      - {quote_yaml(item)}")
                    else:
                        lines.append(f"{prefix}{key}: []")
                    continue
                lines.append(f"{prefix}{key}: {quote_yaml(value)}")
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_structure() -> None:
    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    (SOURCE_ROOT / "inbox").mkdir(parents=True, exist_ok=True)
    for course in OFFICIAL_COURSES:
        for dirname in TYPE_DIRS.values():
            (SOURCE_ROOT / course / dirname).mkdir(parents=True, exist_ok=True)
    if not MANIFEST.exists():
        write_manifest({"version": 1, "sources": []})


def course_dir(course: str, source_type: str) -> Path:
    course_slug = slugify(course, fallback="inbox")
    if not course_slug or course_slug == "inbox":
        return SOURCE_ROOT / "inbox"
    return SOURCE_ROOT / course_slug / TYPE_DIRS[source_type]


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem}-{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def rel_to_root(path: Path) -> str:
    """Manifest-facing label: relative to the content root, absolute otherwise."""
    return relative_label(path.resolve(), CONTENT_ROOT)


def make_source_id(data: dict[str, object], existing_ids: set[str]) -> str:
    explicit = str(data.get("id") or "").strip()
    base = slugify(explicit, fallback="") if explicit else ""
    if not base:
        parts = [
            str(data.get("course") or ""),
            str(data.get("type") or ""),
            str(data.get("title") or ""),
            str(data.get("year") or ""),
        ]
        base = slugify("-".join(part for part in parts if part), fallback="source")
    base = base[:80].strip("-") or "source"
    candidate = base
    counter = 2
    while candidate in existing_ids:
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def append_source(data: dict[str, object]) -> dict[str, object]:
    manifest = load_manifest()
    sources = manifest["sources"]
    if not isinstance(sources, list):
        raise SystemExit("Invalid manifest: `sources` must be a list")
    existing_ids = {str(source.get("id")) for source in sources if isinstance(source, dict)}
    data["id"] = make_source_id(data, existing_ids)
    data["added_at"] = now_iso()
    sources.append(data)
    write_manifest(manifest)
    return data


def source_from_args(args: argparse.Namespace, *, local_path: str = "", url: str = "") -> dict[str, object]:
    return {
        "id": args.id or "",
        "title": args.title or "",
        "authors": split_csv(args.authors),
        "year": args.year or "",
        "course": args.course or "",
        "teacher": args.teacher or "",
        "type": args.type,
        "local_path": local_path,
        "url": url,
        "topics": split_csv(args.topics),
        "reliability_note": args.reliability_note or "",
        "useful_notes": args.useful_notes or "",
        "ieee_citation": args.ieee_citation or "",
        "inspected": bool(args.inspected),
    }


def copy_into_library(src: Path, course: str, source_type: str, title: str | None = None) -> Path:
    target_dir = course_dir(course, source_type)
    target_dir.mkdir(parents=True, exist_ok=True)
    extension = src.suffix or ".bin"
    base = slugify(title or src.stem, fallback=src.stem or "source")
    target = unique_path(target_dir / f"{base}{extension.lower()}")
    shutil.copy2(src, target)
    return target


def command_add_file(args: argparse.Namespace) -> int:
    ensure_structure()
    src = Path(args.path).expanduser()
    if not src.exists() or not src.is_file():
        raise SystemExit(f"File not found: {src}")
    title = args.title or src.stem
    if args.no_copy:
        local_path = str(src.resolve())
    else:
        target = copy_into_library(src.resolve(), args.course or "", args.type, title)
        local_path = rel_to_root(target)
    data = source_from_args(args, local_path=local_path)
    data["title"] = title
    saved = append_source(data)
    print(f"Fuente registrada: {saved['id']}")
    print(f"Ruta local: {saved['local_path']}")
    return 0


def filename_from_url(url: str, title: str | None, content_type: str | None = None) -> str:
    parsed = urlparse(url)
    name = unquote(Path(parsed.path).name)
    suffix = Path(name).suffix
    if not suffix and content_type:
        if "pdf" in content_type:
            suffix = ".pdf"
        elif "word" in content_type or "officedocument" in content_type:
            suffix = ".docx"
    base = slugify(title or Path(name).stem or parsed.netloc or "source")
    return f"{base}{suffix or '.bin'}"


def download_url(url: str, course: str, source_type: str, title: str | None) -> Path:
    target_dir = course_dir(course, source_type)
    target_dir.mkdir(parents=True, exist_ok=True)
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"}:
        req = request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with request.urlopen(req, timeout=45) as response:
            content_type = response.headers.get("content-type")
            target = unique_path(target_dir / filename_from_url(url, title, content_type))
            with target.open("wb") as handle:
                shutil.copyfileobj(response, handle)
    else:
        with request.urlopen(url, timeout=45) as response:
            content_type = response.headers.get("content-type") if response.headers else None
            target = unique_path(target_dir / filename_from_url(url, title, content_type))
            with target.open("wb") as handle:
                shutil.copyfileobj(response, handle)
    return target


def command_add_url(args: argparse.Namespace) -> int:
    ensure_structure()
    title = args.title or Path(unquote(urlparse(args.url).path)).stem or args.url
    local_path = ""
    if not args.metadata_only:
        target = download_url(args.url, args.course or "", args.type, title)
        local_path = rel_to_root(target)
    data = source_from_args(args, local_path=local_path, url=args.url)
    data["title"] = title
    saved = append_source(data)
    print(f"Fuente registrada: {saved['id']}")
    if saved["local_path"]:
        print(f"Descarga local: {saved['local_path']}")
    else:
        print("Registrada solo como metadata; no se descargó archivo.")
    return 0


def normalize_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def source_text(source: dict[str, object]) -> str:
    parts: list[str] = []
    for key, value in source.items():
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        else:
            parts.append(str(value))
    return normalize_search_text(" ".join(parts))


def filtered_sources(args: argparse.Namespace) -> list[dict[str, object]]:
    manifest = load_manifest()
    sources = manifest.get("sources", [])
    if not isinstance(sources, list):
        return []
    query = normalize_search_text(" ".join(getattr(args, "query", []) or []).strip())
    terms = [term for term in re.split(r"\s+", query) if term]
    result: list[dict[str, object]] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        if args.course and slugify(str(source.get("course", ""))) != slugify(args.course):
            continue
        if args.teacher and normalize_search_text(args.teacher) not in normalize_search_text(str(source.get("teacher", ""))):
            continue
        if args.type and source.get("type") != args.type:
            continue
        if getattr(args, "only_inspected", False) and not bool(source.get("inspected", False)):
            continue
        haystack = source_text(source)
        if terms and not all(term in haystack for term in terms):
            continue
        result.append(source)
    return result


def format_source_line(source: dict[str, object]) -> str:
    inspected = "inspeccionada" if source.get("inspected") else "pendiente"
    title = source.get("title") or "(sin título)"
    year = f" ({source.get('year')})" if source.get("year") else ""
    course = f" — {source.get('course')}" if source.get("course") else ""
    return f"- [{source.get('id')}] {title}{year} · {source.get('type')} · {inspected}{course}"


def command_search(args: argparse.Namespace) -> int:
    ensure_structure()
    matches = filtered_sources(args)
    if not matches:
        print("No encontré fuentes con esos filtros.")
        return 0
    for source in matches:
        print(format_source_line(source))
        topics = source.get("topics") or []
        if topics:
            print(f"  temas: {', '.join(str(topic) for topic in topics)}")
        local_path = source.get("local_path") or ""
        if local_path:
            print(f"  archivo: {local_path}")
        if source.get("url"):
            print(f"  url: {source.get('url')}")
    return 0


def markdown_source(source: dict[str, object]) -> str:
    title = source.get("title") or "(sin título)"
    lines = [f"### {title}"]
    lines.append(f"- ID: `{source.get('id')}`")
    lines.append(f"- Tipo: {source.get('type') or ''}")
    if source.get("authors"):
        lines.append(f"- Autores: {', '.join(str(item) for item in source.get('authors', []))}")
    if source.get("year"):
        lines.append(f"- Año: {source.get('year')}")
    if source.get("course"):
        lines.append(f"- Asignatura: {source.get('course')}")
    if source.get("teacher"):
        lines.append(f"- Docente: {source.get('teacher')}")
    if source.get("topics"):
        lines.append(f"- Temas: {', '.join(str(item) for item in source.get('topics', []))}")
    if source.get("local_path"):
        lines.append(f"- Archivo: `{source.get('local_path')}`")
    if source.get("url"):
        lines.append(f"- URL: {source.get('url')}")
    if source.get("reliability_note"):
        lines.append(f"- Confiabilidad: {source.get('reliability_note')}")
    if source.get("useful_notes"):
        lines.append(f"- Idea útil: {source.get('useful_notes')}")
    if source.get("ieee_citation"):
        lines.append(f"- IEEE: {source.get('ieee_citation')}")
    return "\n".join(lines)


def build_pack(args: argparse.Namespace, matches: list[dict[str, object]]) -> str:
    query = " ".join(args.query).strip() or "sin consulta específica"
    inspected = [source for source in matches if source.get("inspected")]
    pending = [source for source in matches if not source.get("inspected")]
    lines = [
        f"# Pack de fuentes — {query}",
        "",
        f"Generado: {now_iso()}",
        "",
        "## Regla de uso",
        "",
        "- Usar fuentes locales primero.",
        "- Citar solo fuentes con `inspected: true`.",
        "- Las fuentes pendientes sirven para lectura/revisión, no para bibliografía final.",
        "",
        "## Fuentes inspeccionadas",
        "",
    ]
    if inspected:
        for source in inspected:
            lines.append(markdown_source(source))
            lines.append("")
    else:
        lines.append("_No hay fuentes inspeccionadas para esta consulta._")
        lines.append("")
    lines.extend(["## Pendientes de inspección", ""])
    if pending:
        for source in pending:
            lines.append(markdown_source(source))
            lines.append("")
    else:
        lines.append("_No hay fuentes pendientes._")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def command_pack(args: argparse.Namespace) -> int:
    ensure_structure()
    matches = filtered_sources(args)
    content = build_pack(args, matches)
    if args.out:
        out = Path(args.out)
        if not out.is_absolute():
            out = CONTENT_ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        print(f"Pack generado: {out}")
    else:
        print(content, end="")
    return 0


def command_courses(args: argparse.Namespace) -> int:
    ensure_structure()
    manifest = load_manifest()
    sources = manifest.get("sources", [])
    if not isinstance(sources, list):
        sources = []

    totals: dict[str, dict[str, int]] = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        course = slugify(str(source.get("course") or "sin-materia"), fallback="sin-materia")
        source_type = str(source.get("type") or "unknown")
        totals.setdefault(course, {"total": 0})
        totals[course]["total"] += 1
        totals[course][source_type] = totals[course].get(source_type, 0) + 1

    course_dirs = [
        path.name
        for path in SOURCE_ROOT.iterdir()
        if path.is_dir() and path.name != "inbox"
    ] if SOURCE_ROOT.exists() else []
    for course in course_dirs:
        totals.setdefault(course, {"total": 0})

    if not totals:
        print("Todavía no hay materias registradas.")
        return 0

    for course in sorted(totals):
        counts = totals[course]
        type_counts = ", ".join(
            f"{source_type}={count}"
            for source_type, count in sorted(counts.items())
            if source_type != "total"
        )
        suffix = f" ({type_counts})" if type_counts else ""
        print(f"- {course}: {counts.get('total', 0)} fuente(s){suffix}")
    return 0


def manifest_local_paths() -> set[str]:
    manifest = load_manifest()
    sources = manifest.get("sources", [])
    if not isinstance(sources, list):
        return set()
    paths: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            continue
        local_path = str(source.get("local_path") or "")
        if local_path:
            paths.add(local_path)
            paths.add(str((CONTENT_ROOT / local_path).resolve()))
    return paths


def command_inbox(args: argparse.Namespace) -> int:
    ensure_structure()
    inbox = SOURCE_ROOT / "inbox"
    registered = manifest_local_paths()
    files = [
        path
        for path in sorted(inbox.rglob("*"))
        if path.is_file() and path.suffix.lower() in SOURCE_FILE_EXTENSIONS
    ]
    if not files:
        print("El inbox está vacío.")
        return 0

    for path in files:
        rel = rel_to_root(path)
        status = "registrado" if rel in registered or str(path.resolve()) in registered else "pendiente"
        print(f"- {rel} · {status}")
        if status == "pendiente":
            print("  registrar: python3 tools/source_library.py add-file "
                  f"{rel} --course <materia> --type book --title \"<título>\"")
    return 0


def run_optional(cmd: list[str], timeout: int = 12) -> str:
    if shutil.which(cmd[0]) is None:
        return ""
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def docx_text(path: Path, limit: int = 4000) -> tuple[str, str]:
    title = ""
    body = ""
    try:
        with zipfile.ZipFile(path) as archive:
            if "docProps/core.xml" in archive.namelist():
                root = ElementTree.fromstring(archive.read("docProps/core.xml"))
                for elem in root.iter():
                    if elem.tag.endswith("title") and elem.text:
                        title = clean_text(elem.text)
                        break
            if "word/document.xml" in archive.namelist():
                root = ElementTree.fromstring(archive.read("word/document.xml"))
                texts = [elem.text for elem in root.iter() if elem.tag.endswith("}t") and elem.text]
                body = clean_text(" ".join(texts))[:limit]
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError):
        pass
    return title, body


def pptx_text(path: Path, limit: int = 4000) -> tuple[str, str]:
    title = ""
    body_parts: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            if "docProps/core.xml" in archive.namelist():
                root = ElementTree.fromstring(archive.read("docProps/core.xml"))
                for elem in root.iter():
                    if elem.tag.endswith("title") and elem.text:
                        title = clean_text(elem.text)
                        break
            for name in sorted(archive.namelist()):
                if not name.startswith("ppt/slides/slide") or not name.endswith(".xml"):
                    continue
                root = ElementTree.fromstring(archive.read(name))
                texts = [elem.text for elem in root.iter() if elem.tag.endswith("}t") and elem.text]
                body_parts.extend(texts)
                if len(" ".join(body_parts)) >= limit:
                    break
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError):
        pass
    return title, clean_text(" ".join(body_parts))[:limit]


def pdf_info(path: Path) -> dict[str, str]:
    output = run_optional(["pdfinfo", str(path)])
    info: dict[str, str] = {}
    for line in output.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            info[key.strip().lower()] = value.strip()
    return info


def pdf_first_page_text(path: Path, limit: int = 4000) -> str:
    return clean_text(run_optional(["pdftotext", "-f", "1", "-l", "1", str(path), "-"]))[:limit]


def inspect_source_file(path: Path) -> dict[str, object]:
    suffix = path.suffix.lower()
    title = ""
    text = ""
    pages = 0
    if suffix == ".pdf":
        info = pdf_info(path)
        title = clean_text(info.get("title", ""))
        pages_raw = info.get("pages", "")
        if pages_raw.isdigit():
            pages = int(pages_raw)
        text = pdf_first_page_text(path)
    elif suffix == ".docx":
        title, text = docx_text(path)
    elif suffix == ".pptx":
        title, text = pptx_text(path)
    if not title:
        title = clean_text(path.stem.replace("_", " ").replace("-", " "))
    return {"title": title, "text": text, "pages": pages}


def infer_course(text: str) -> tuple[str, int]:
    normalized = text.lower()
    best_course = ""
    best_score = 0
    for course, keywords in COURSE_RULES.items():
        score = sum(1 for keyword in keywords if keyword in normalized)
        if score > best_score:
            best_course = course
            best_score = score
    return best_course, best_score


def infer_source_type(path: Path, text: str, pages: int = 0) -> str:
    normalized = text.lower()
    if any(word in normalized for word in ("rúbrica", "rubrica", "criterios de evaluación", "criterios de evaluacion")):
        return "rubric"
    if any(word in normalized for word in ("plantilla", "template", "formato", "modelo de ensayo", "modelo de trabajo")):
        return "template"
    if any(word in normalized for word in ("book", "libro", "manual", "textbook")):
        return "book"
    if pages >= 80:
        return "book"
    if any(word in normalized for word in ("diapositiva", "slide", "clase", "apunte", "guía", "guia")):
        return "teacher_note"
    if any(word in normalized for word in ("ieee", "doi", "abstract", "resumen", "journal", "conference", "artículo", "articulo")):
        return "article"
    if path.suffix.lower() in {".ppt", ".pptx"}:
        return "teacher_note"
    if 1 <= pages <= 50:
        return "article"
    return "book" if path.suffix.lower() in {".epub"} else "article"


def is_generic_filename(path: Path) -> bool:
    stem = slugify(path.stem, fallback="")
    return len(stem) < 5 or bool(GENERIC_FILENAME_RE.match(stem))


def proposed_inbox_move(path: Path, args: argparse.Namespace) -> dict[str, object]:
    metadata = inspect_source_file(path)
    title = str(metadata.get("title") or path.stem)
    text_for_rules = f"{path.name} {title} {metadata.get('text', '')}"
    course, score = (slugify(args.course), 99) if args.course else infer_course(text_for_rules)
    source_type = args.type or infer_source_type(path, text_for_rules, int(metadata.get("pages") or 0))
    if course:
        target_dir = course_dir(course, source_type)
        if course == "sistemas-operativos" and source_type == "template":
            lowered_title = title.lower()
            if "modelo" in lowered_title or "ensayo" in lowered_title or "trabajo ic" in lowered_title:
                target_dir = target_dir / "modelos-ensayo"
        filename = f"{slugify(title, fallback=path.stem)}{path.suffix.lower()}" if is_generic_filename(path) else path.name
        target = unique_path(target_dir / filename)
    else:
        target = None
    return {
        "path": path,
        "title": title,
        "course": course,
        "course_score": score,
        "type": source_type,
        "target": target,
    }


def command_triage_inbox(args: argparse.Namespace) -> int:
    ensure_structure()
    inbox = SOURCE_ROOT / "inbox"
    files = [
        path
        for path in sorted(inbox.rglob("*"))
        if path.is_file() and path.suffix.lower() in SOURCE_FILE_EXTENSIONS
    ]
    if not files:
        print("El inbox está vacío.")
        return 0

    proposals = [proposed_inbox_move(path, args) for path in files]
    for proposal in proposals:
        path = proposal["path"]
        target = proposal["target"]
        print(f"- {rel_to_root(path)}")
        print(f"  título detectado: {proposal['title']}")
        if proposal["course"]:
            print(f"  materia: {proposal['course']} (score={proposal['course_score']})")
            print(f"  tipo: {proposal['type']}")
            print(f"  destino: {rel_to_root(target)}")
        else:
            print("  materia: REVISAR MANUALMENTE")
            print("  acción: se queda en inbox")

    if not args.apply:
        print("\nVista previa solamente. Para mover/registrar: agregá --apply")
        return 0

    moved = 0
    for proposal in proposals:
        source = proposal["path"]
        target = proposal["target"]
        if target is None:
            continue
        assert isinstance(source, Path)
        assert isinstance(target, Path)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        moved += 1
        if not args.no_register:
            append_source({
                "id": "",
                "title": proposal["title"],
                "authors": [],
                "year": "",
                "course": proposal["course"],
                "teacher": "",
                "type": proposal["type"],
                "local_path": rel_to_root(target),
                "url": "",
                "topics": [],
                "reliability_note": "Clasificado automáticamente desde inbox; revisar antes de citar.",
                "useful_notes": "",
                "ieee_citation": "",
                "inspected": False,
            })
    print(f"\nMovidos: {moved}. Pendientes manuales: {len(proposals) - moved}.")
    return 0


def add_common_metadata_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--id", help="ID estable opcional para la fuente")
    parser.add_argument("--title", help="Título de la fuente")
    parser.add_argument("--authors", default="", help="Autores separados por coma")
    parser.add_argument("--year", default="", help="Año de publicación")
    parser.add_argument("--course", default="", help="Asignatura, ej. sistemas-operativos")
    parser.add_argument("--teacher", default="", help="Docente relacionado")
    parser.add_argument("--type", choices=SOURCE_TYPES, required=True, help="Tipo de fuente")
    parser.add_argument("--topics", default="", help="Temas/palabras clave separados por coma")
    parser.add_argument("--reliability-note", default="", help="Nota breve de confiabilidad")
    parser.add_argument("--useful-notes", default="", help="Idea útil o páginas/capítulos relevantes")
    parser.add_argument("--ieee-citation", default="", help="Entrada bibliográfica IEEE")
    parser.add_argument("--inspected", action="store_true", help="Marcar como fuente ya inspeccionada")


def add_filter_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("query", nargs="*", help="Texto a buscar en título, temas, notas, cita, docente, etc.")
    parser.add_argument("--course", default="", help="Filtrar por asignatura")
    parser.add_argument("--teacher", default="", help="Filtrar por docente")
    parser.add_argument("--type", choices=SOURCE_TYPES, help="Filtrar por tipo")
    parser.add_argument("--only-inspected", action="store_true", help="Mostrar solo fuentes inspeccionadas")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Biblioteca local de fuentes docentes para reportes UNL")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_file = subparsers.add_parser("add-file", help="Copiar y registrar un PDF/DOCX local")
    add_file.add_argument("path", help="Ruta del archivo local")
    add_file.add_argument("--no-copy", action="store_true", help="Registrar la ruta original sin copiar al kit")
    add_common_metadata_args(add_file)
    add_file.set_defaults(func=command_add_file)

    add_url = subparsers.add_parser("add-url", help="Descargar y registrar una fuente desde URL")
    add_url.add_argument("url", help="URL legal/provista por el docente")
    add_url.add_argument("--metadata-only", action="store_true", help="Registrar URL sin descargar archivo")
    add_common_metadata_args(add_url)
    add_url.set_defaults(func=command_add_url)

    search = subparsers.add_parser("search", help="Buscar fuentes registradas")
    add_filter_args(search)
    search.set_defaults(func=command_search)

    courses = subparsers.add_parser("courses", help="Listar materias registradas y conteos por tipo")
    courses.set_defaults(func=command_courses)

    inbox = subparsers.add_parser("inbox", help="Ver archivos descargados pendientes de registrar")
    inbox.set_defaults(func=command_inbox)

    triage_inbox = subparsers.add_parser("triage-inbox", help="Proponer o aplicar clasificación automática del inbox")
    triage_inbox.add_argument("--apply", action="store_true", help="Mover archivos a carpetas de materia/tipo")
    triage_inbox.add_argument("--no-register", action="store_true", help="Mover sin agregar entradas al manifest")
    triage_inbox.add_argument("--course", default="", help="Forzar una materia para todo el inbox")
    triage_inbox.add_argument("--type", choices=SOURCE_TYPES, help="Forzar un tipo para todo el inbox")
    triage_inbox.set_defaults(func=command_triage_inbox)

    pack = subparsers.add_parser("pack", help="Generar ficha Markdown de fuentes relevantes")
    add_filter_args(pack)
    pack.add_argument("--out", help="Ruta de salida Markdown; si se omite, imprime en stdout")
    pack.set_defaults(func=command_pack)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
