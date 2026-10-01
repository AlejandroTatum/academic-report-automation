#!/usr/bin/env python3
"""Check report bibliography identifiers against Crossref and Open Library."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import yaml

from report_config import load_report_config
from source_count import _ENTRY_HEADER

USER_AGENT = "academic-report-automation/1.0 (mailto omitted)"


def entries(text: str):
    """Split entries using the shared BibTeX header; extract simple braced/quoted fields."""
    headers = list(_ENTRY_HEADER.finditer(text))
    for index, header in enumerate(headers):
        if header.group(1).lower() in {"string", "comment", "preamble"}:
            continue
        body = text[header.end():headers[index + 1].start() if index + 1 < len(headers) else len(text)]
        fields = {}
        for match in re.finditer(r"\b(title|author|year|doi|isbn)\s*=\s*", body, re.I):
            value = body[match.end():].lstrip()
            if value.startswith("{"):
                depth = 0
                for pos, char in enumerate(value):
                    depth += (char == "{") - (char == "}")
                    if depth == 0:
                        value = value[1:pos]
                        break
            elif value.startswith('"'):
                value = value[1:].split('"', 1)[0]
            else:
                value = value.split(",", 1)[0].strip().rstrip("}")
            fields[match.group(1).lower()] = value.strip()
        yield header.group(2), fields


def normalized(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()


def tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", normalized(value)))


class RegistryDataError(ValueError):
    """Registry answered 200 but the payload or a required field is unusable."""


def _covers(reference: set[str], candidate: set[str]) -> bool:
    return bool(reference) and len(reference & candidate) / len(reference) >= 0.8


def _title_matches(expected: str, found: str) -> bool:
    """Match full titles, or a registry that stores only the main title.

    Open Library often drops the subtitle, so a found title that covers the
    expected main title (text before ':') and adds no foreign words also matches.
    """
    expected_tokens, found_tokens = tokens(expected), tokens(found)
    if _covers(expected_tokens, found_tokens):
        return True
    main_tokens = tokens(expected.split(":", 1)[0])
    return _covers(main_tokens, found_tokens) and _covers(found_tokens, expected_tokens)


def year_of(value: object) -> int | None:
    match = re.search(r"\b(?:19|20)\d{2}\b", str(value or ""))
    return int(match.group()) if match else None


def _family_tokens(value: str) -> list[str]:
    return [word for word in re.findall(r'[a-z0-9]+', normalized(value))
            if word not in {'de', 'del', 'van', 'von', 'da', 'der'}]


def compare(fields: dict, remote: dict, kind: str) -> dict:
    mismatches = {}
    warnings = {}
    if not isinstance(remote, dict):
        raise RegistryDataError('registry response is not an object')
    message = remote.get("message", {}) if kind == "doi" else remote
    if not isinstance(message, dict):
        raise RegistryDataError('registry record is not an object')
    titles = message.get('title')
    if kind == 'doi':
        if not isinstance(titles, list) or not titles or not isinstance(titles[0], str) or not titles[0].strip():
            raise RegistryDataError('registry title missing or malformed')
        found_title = titles[0]
    else:
        if not isinstance(titles, str) or not titles.strip():
            raise RegistryDataError('registry title missing or malformed')
        found_title = titles
    expected_title = fields.get("title", "")
    if not _title_matches(expected_title, found_title):
        mismatches["title"] = {"expected": expected_title, "found": found_title}
    if kind == "doi":
        date = message.get("issued") or message.get("published-print") or {}
        if not isinstance(date, dict):
            raise RegistryDataError('registry issued date is not an object')
        parts = date.get("date-parts") or [[]]
        if not isinstance(parts, list) or not parts or not isinstance(parts[0], list):
            raise RegistryDataError('registry date-parts is not a list of lists')
        found_year = year_of(parts[0][0] if parts[0] else None)
    else:
        found_year = year_of(message.get("publish_date"))
    expected_year = year_of(fields.get("year"))
    if expected_year != found_year:
        target = warnings if expected_year is not None and found_year is not None and abs(expected_year - found_year) == 1 else mismatches
        target["year"] = {"expected": expected_year, "found": found_year}
    authors = message.get("author")
    if kind == "doi" and authors and fields.get("author"):
        if not isinstance(authors, list) or not isinstance(authors[0], dict):
            raise RegistryDataError('registry author list is not a list of objects')
        author = fields["author"].split(" and ", 1)[0]
        expected = author.split(",", 1)[0].strip() if "," in author else author.split()[-1]
        found = authors[0].get("family", "")
        if not isinstance(found, str):
            raise RegistryDataError('registry author family name is not a string')
        if expected and found and _family_tokens(expected) != _family_tokens(found):
            mismatches["author"] = {"expected": expected, "found": found}
    result = {"status": "MISMATCH" if mismatches else "VERIFIED_WITH_WARNINGS" if warnings else "VERIFIED"}
    if mismatches:
        result["mismatches"] = mismatches
    if warnings:
        result["warnings"] = warnings
    return result


def default_fetch(request: Request, timeout: int):
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def verify_sources(folder: Path, fetch=None, sleep=None) -> int:
    folder = Path(folder)
    if not (folder / "report.yml").is_file():
        raise ValueError("report.yml does not exist")
    config = load_report_config(folder)
    bib = config.bib_path
    if bib is None:
        raise ValueError("report bibliography does not exist")
    data = bib.read_bytes()
    results = []
    for key, fields in entries(data.decode("utf-8")):
        result = {"key": key}
        doi = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:)', '', fields.get('doi', '').strip(), flags=re.I)
        isbn = re.sub(r"[^0-9Xx]", "", fields.get("isbn", ""))
        if doi:
            url, kind = "https://api.crossref.org/works/" + quote(doi, safe="/"), "doi"
        elif isbn:
            url, kind = f"https://openlibrary.org/isbn/{isbn}.json", "isbn"
        else:
            result["status"] = "NO_IDENTIFIER"
            results.append(result)
            continue
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            try:
                remote = (fetch or default_fetch)(request, 15)
            except HTTPError as error:
                if error.code not in (429, 503):
                    raise
                (sleep or time.sleep)(2)
                remote = (fetch or default_fetch)(request, 15)
            result.update(compare(fields, remote, kind))
        except RegistryDataError as error:
            result['status'] = 'MISMATCH'
            result['detail'] = f'Registry data unusable: {error}'
        except HTTPError as error:
            result['status'] = 'NOT_FOUND' if error.code == 404 else 'NETWORK_ERROR'
            result['detail'] = f'HTTP {error.code}: {error.reason}'
        except json.JSONDecodeError as error:
            result['status'] = 'MISMATCH'
            result['detail'] = f'Registry returned malformed JSON: {error}'
        except (URLError, TimeoutError, OSError) as error:
            result['status'] = 'NETWORK_ERROR'
            result['detail'] = f'Registry unreachable: {error}'
        results.append(result)
    if not results:
        results.append({'key': '', 'status': 'NO_IDENTIFIER', 'detail': 'Empty bibliography: no entries to verify'})
    output = {"schema": "academic.sources-verification/v1", "bib_sha256": hashlib.sha256(data).hexdigest(),
              "checked_at": datetime.now(timezone.utc).isoformat(), "results": results}
    destination = folder / "research" / "sources-verification.yml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(yaml.safe_dump(output, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return 0 if all(row["status"] in {"VERIFIED", "VERIFIED_WITH_WARNINGS"} for row in results) else 1


def main(argv=None, fetch=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args(argv)
    try:
        return verify_sources(args.folder, fetch=fetch)
    except (OSError, ValueError, UnicodeError) as error:
        parser.print_usage()
        print(f"verify_sources: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
