"""Tests for ``tools/link_check.py`` (verify-concise-drafts T6).

The fetcher is always injected: no test may touch the network.
"""
from __future__ import annotations

import socket
import urllib.error

import pytest

import link_check


class FakeFetcher:
    """Returns a scripted status (or raises) per ``(method, url)``; records calls."""

    def __init__(self, script: dict) -> None:
        self.script = script
        self.calls: list[tuple[str, str]] = []

    def __call__(self, url: str, method: str) -> int:
        self.calls.append((method, url))
        outcome = self.script.get((method, url), self.script.get(url, 200))
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def test_extract_urls_finds_http_and_https_in_order_without_trailing_punctuation() -> None:
    text = "Ver https://a.example/x, y (http://b.example/y). Otra [l](https://c.example/z) y <https://d.example>."
    assert link_check.extract_urls(text) == [
        "https://a.example/x",
        "http://b.example/y",
        "https://c.example/z",
        "https://d.example",
    ]


def test_extract_urls_dedupes_repeats() -> None:
    assert link_check.extract_urls("https://a.example y https://a.example") == ["https://a.example"]


def test_200_passes_with_a_single_head_request() -> None:
    fetcher = FakeFetcher({})
    [result] = link_check.check_links(["https://ok.example"], fetcher)
    assert result.status == "ok"
    assert fetcher.calls == [("HEAD", "https://ok.example")]


@pytest.mark.parametrize("code", [404, 410, 403, 500])
def test_http_error_status_fails(code: int) -> None:
    fetcher = FakeFetcher({"https://bad.example": code})
    [result] = link_check.check_links(["https://bad.example"], fetcher)
    assert result.status == "broken"
    assert str(code) in result.detail


def test_head_rejected_falls_back_to_get() -> None:
    fetcher = FakeFetcher({("HEAD", "https://h.example"): 405, ("GET", "https://h.example"): 200})
    [result] = link_check.check_links(["https://h.example"], fetcher)
    assert result.status == "ok"
    assert fetcher.calls == [("HEAD", "https://h.example"), ("GET", "https://h.example")]


def test_head_failing_with_a_network_error_falls_back_to_get() -> None:
    fetcher = FakeFetcher({("HEAD", "https://h.example"): TimeoutError("slow"), ("GET", "https://h.example"): 200})
    [result] = link_check.check_links(["https://h.example"], fetcher)
    assert result.status == "ok"


@pytest.mark.parametrize(
    "error",
    [TimeoutError("timed out"), socket.gaierror("dns"), urllib.error.URLError("no route"), OSError("down")],
)
def test_timeout_or_dns_is_unreachable_not_broken(error: BaseException) -> None:
    fetcher = FakeFetcher({"https://off.example": error})
    [result] = link_check.check_links(["https://off.example"], fetcher)
    assert result.status == "unreachable"


def test_results_are_cached_per_url_across_calls() -> None:
    fetcher = FakeFetcher({})
    cache: dict = {}
    link_check.check_links(["https://a.example", "https://a.example"], fetcher, cache)
    link_check.check_links(["https://a.example", "https://b.example"], fetcher, cache)
    assert fetcher.calls == [("HEAD", "https://a.example"), ("HEAD", "https://b.example")]


def test_default_fetcher_uses_user_agent_and_short_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict = {}

    class Response:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout=None):
        seen["method"] = request.get_method()
        seen["agent"] = request.get_header("User-agent")
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setattr(link_check.urllib.request, "urlopen", fake_urlopen)

    assert link_check.default_fetcher("https://x.example", "HEAD") == 204
    assert seen["method"] == "HEAD" and seen["agent"]
    assert 0 < seen["timeout"] <= 8


def test_default_fetcher_returns_http_error_code(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 404, "nf", {}, None)

    monkeypatch.setattr(link_check.urllib.request, "urlopen", fake_urlopen)
    assert link_check.default_fetcher("https://x.example", "GET") == 404
