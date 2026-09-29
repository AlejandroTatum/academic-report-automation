"""Offline contract tests for bibliography verification."""
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError, URLError

import yaml

from verify_sources import verify_sources, main


def report(tmp_path, entry):
    folder = tmp_path / "report"
    folder.mkdir()
    (folder / "report.yml").write_text("title: Test report\n", encoding="utf-8")
    (folder / "sources.bib").write_text(entry, encoding="utf-8")
    return folder


def doi_response(year=2020, title="A Study of Trees", author="García"):
    return {"message": {"title": [title], "issued": {"date-parts": [[year]]}, "author": [{"family": author}]}}


def test_verified_doi_and_bib_hash(tmp_path):
    folder = report(tmp_path, '@article{tree, title={A Study of Trees}, author={García, Ana}, year={2020}, doi={10.1234/tree}}')
    seen = []

    def fetch(request, timeout):
        seen.append((request.full_url, request.get_header("User-agent"), timeout))
        return doi_response()

    assert verify_sources(folder, fetch=fetch) == 0
    output = yaml.safe_load((folder / "research/sources-verification.yml").read_text())
    assert output["schema"] == "academic.sources-verification/v1"
    assert output["bib_sha256"] == hashlib.sha256((folder / "sources.bib").read_bytes()).hexdigest()
    assert output["checked_at"]
    assert output["results"][0]["status"] == "VERIFIED"
    assert seen == [("https://api.crossref.org/works/10.1234/tree", "academic-report-automation/1.0 (mailto omitted)", 15)]


def test_verified_isbn(tmp_path):
    folder = report(tmp_path, '@book{b, title={A Study of Trees}, year={2020}, isbn={978-1-234-56789-7}}')
    seen = []

    def fetch(request, timeout):
        seen.append(request.full_url)
        return {"title": "A Study of Trees", "publish_date": "2020"}

    assert verify_sources(folder, fetch=fetch) == 0
    assert seen == ["https://openlibrary.org/isbn/9781234567897.json"]


def test_year_warning(tmp_path):
    folder = report(tmp_path, '@article{x, title={A Study of Trees}, year={2021}, doi={10.1/x}}')
    assert verify_sources(folder, fetch=lambda request, timeout: doi_response()) == 0
    assert yaml.safe_load((folder / "research/sources-verification.yml").read_text())["results"][0]["status"] == "VERIFIED_WITH_WARNINGS"


def test_main_title_without_subtitle_matches(tmp_path):
    # Open Library often stores only the main title (seen for Humble 2010, Adzic 2011).
    folder = report(tmp_path, '@book{b, title={Specification by Example: How Successful Teams Deliver the Right Software}, year={2011}, isbn={978-1-61729-008-4}}')
    fetch = lambda request, timeout: {"title": "Specification by example", "publish_date": "2011"}
    assert verify_sources(folder, fetch=fetch) == 0


def test_shared_prefix_word_is_not_a_title_match(tmp_path):
    folder = report(tmp_path, '@book{b, title={Specification by Example: How Teams Work}, year={2011}, isbn={978-1-61729-008-4}}')
    fetch = lambda request, timeout: {"title": "Specification of Real-Time Systems", "publish_date": "2011"}
    assert verify_sources(folder, fetch=fetch) == 1


def test_title_mismatch(tmp_path):
    folder = report(tmp_path, '@article{x, title={Completely Different Work}, year={2020}, doi={10.1/x}}')
    assert verify_sources(folder, fetch=lambda request, timeout: doi_response()) == 1
    result = yaml.safe_load((folder / "research/sources-verification.yml").read_text())["results"][0]
    assert result["status"] == "MISMATCH"
    assert result["mismatches"]["title"] == {"expected": "Completely Different Work", "found": "A Study of Trees"}


def test_not_found(tmp_path):
    folder = report(tmp_path, '@article{x, title={A Study of Trees}, doi={10.1/x}}')

    def missing(request, timeout):
        raise HTTPError(request.full_url, 404, "missing", {}, None)

    assert verify_sources(folder, fetch=missing) == 1
    assert yaml.safe_load((folder / "research/sources-verification.yml").read_text())["results"][0]["status"] == "NOT_FOUND"


def test_network_error(tmp_path):
    folder = report(tmp_path, '@article{x, title={A Study of Trees}, doi={10.1/x}}')

    def unavailable(request, timeout):
        raise URLError("offline")

    assert verify_sources(folder, fetch=unavailable) == 1
    assert yaml.safe_load((folder / "research/sources-verification.yml").read_text())["results"][0]["status"] == "NETWORK_ERROR"


def test_no_identifier_and_usage_exit(tmp_path):
    folder = report(tmp_path, '@book{x, title={A Study of Trees}, year={2020}}')

    def forbidden(request, timeout):
        raise AssertionError("network access")

    assert verify_sources(folder, fetch=forbidden) == 1
    assert yaml.safe_load((folder / "research/sources-verification.yml").read_text())["results"][0]["status"] == "NO_IDENTIFIER"
    assert main([str(tmp_path / "missing")], fetch=forbidden) == 2
