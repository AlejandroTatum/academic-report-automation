#!/usr/bin/env python3
"""Mechanical link resolution for the verify phase (verify-concise-drafts T6).

``content_check`` runs ``links_resolve`` over every http(s) URL in ``body.md``.
Each URL gets a HEAD request with GET as fallback and a short timeout; results
are cached per URL. An HTTP error status (404, 410, other 4xx/5xx) is
``broken`` and fails the check; DNS failures and timeouts are ``unreachable``,
a warning only, so working offline never blocks a report.

The network is reached only through an injectable ``fetcher(url, method) ->
status``; it returns the HTTP status and raises ``OSError`` (including
``TimeoutError`` and ``urllib.error.URLError``) when the host cannot be reached.
Tests always inject a fake fetcher.
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable

TIMEOUT_SECONDS = 8
USER_AGENT = "Mozilla/5.0 (compatible; academic-report-automation link-check)"

Fetcher = Callable[[str, str], int]

_URL_RE = re.compile(r"https?://[^\s<>\]\)\"'`]+")
_TRAILING = ".,;:!?*_"


@dataclass(frozen=True)
class LinkResult:
    url: str
    status: str  # ok | broken | unreachable
    detail: str


def extract_urls(text: str) -> list[str]:
    """Distinct http(s) URLs in order of first appearance, without trailing punctuation."""
    urls: list[str] = []
    for match in _URL_RE.finditer(text):
        url = match.group(0).rstrip(_TRAILING)
        if url not in urls:
            urls.append(url)
    return urls


def default_fetcher(url: str, method: str) -> int:
    """The production fetcher: urllib, short timeout, explicit User-Agent."""
    request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return exc.code


def _check_one(url: str, fetcher: Fetcher) -> LinkResult:
    status: int | None = None
    error: Exception | None = None
    for method in ("HEAD", "GET"):
        try:
            status = fetcher(url, method)
            error = None
        except (OSError, ValueError) as exc:  # ValueError: URL urllib cannot parse
            status, error = None, exc
        if status is not None and status < 400:
            return LinkResult(url, "ok", f"HTTP {status}")
    if status is not None:
        return LinkResult(url, "broken", f"HTTP {status}")
    return LinkResult(url, "unreachable", f"{type(error).__name__}: {error}")


def check_links(
    urls: list[str], fetcher: Fetcher | None = None, cache: dict[str, LinkResult] | None = None
) -> list[LinkResult]:
    """Check each URL once; ``cache`` persists results across calls within a run."""
    fetch = fetcher if fetcher is not None else default_fetcher
    results = cache if cache is not None else {}
    for url in urls:
        if url not in results:
            results[url] = _check_one(url, fetch)
    return [results[url] for url in dict.fromkeys(urls)]
