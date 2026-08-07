"""The example this repository ships must be the pattern the validator enforces.

`examples/` is what a reader copies. For years the only justification for the
output-location exemption was `_example_latex_essay`, a folder that lives in the
private content tree and is not versioned here — so anyone starting from what
this repository actually shipped inherited an exemption, and their first
ordinary report failed a rule the example never had to satisfy.

These tests close that gap by pinning the shipped example against the real
loader and the real validators: no underscore prefix, no exemption, no rule bent
in its favour.

The example ships sources only. A compiled PDF and `build/main.tex` are build
products (and `*.pdf` is gitignored), so every assertion here covers what is
knowable without LuaLaTeX: the config loads, the route resolves, the route's
metadata is complete, the final output location is accepted, and the body and
bibliography agree with each other. Compiling would additionally prove the PDF
layout and the rendered IEEE bibliography; that needs Docker and is deliberately
not a precondition for this file.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from report_config import (  # noqa: E402
    LOCAL_OUTPUTS_ERROR,
    ROOT,
    ROUTE_KEY,
    load_report_config,
    targets_local_outputs,
)
from validate_ieee_refs import bib_keys, cited_keys  # noqa: E402
from validate_report import common_validation, metadata_validation  # noqa: E402

EXAMPLE = ROOT / "examples" / "ejemplo_informe_academico"


def load_example():
    return load_report_config(EXAMPLE)


# ---------------------------------------------------------------------------
# The example exists, as sources
# ---------------------------------------------------------------------------


def test_the_shipped_example_is_a_report_folder_not_a_loose_markdown_file():
    assert (EXAMPLE / "report.yml").exists()
    assert (EXAMPLE / "body.md").exists()
    assert (EXAMPLE / "sources.bib").exists()


def test_the_shipped_example_loads_through_the_real_loader():
    """No SystemExit: the loader is where the layout and route rules fail fast."""
    config = load_example()

    assert config.backend == "latex"
    assert config.output_format == "pdf"


# ---------------------------------------------------------------------------
# It claims no exemption
# ---------------------------------------------------------------------------


def test_the_shipped_example_claims_no_underscore_exemption():
    assert not EXAMPLE.name.startswith("_")


def test_the_shipped_examples_output_location_is_accepted_on_its_own_merits():
    config = load_example()

    assert not targets_local_outputs(config)
    assert (config.folder / "outputs").resolve() not in config.pdf_path.resolve().parents


def test_the_shipped_example_decides_global_publication_explicitly():
    """`publish_global:` written down, not inferred from a folder-name prefix."""
    config = load_example()

    assert "publish_global" in config.raw


# ---------------------------------------------------------------------------
# It satisfies the routing contract
# ---------------------------------------------------------------------------


def test_the_shipped_example_declares_its_route_instead_of_relying_on_the_default():
    config = load_example()

    assert ROUTE_KEY in config.raw
    assert config.route_is_known


def test_the_shipped_example_carries_every_metadata_key_its_route_requires():
    config = load_example()
    meta = config.metadata

    missing = [key for key in config.required_metadata if not str(meta.get(key) or "").strip()]

    assert missing == []
    assert metadata_validation(config).errors == []


# ---------------------------------------------------------------------------
# Nothing is wrong with it except that it has not been built
# ---------------------------------------------------------------------------


def test_the_shipped_examples_only_outstanding_error_is_the_pdf_it_never_compiled():
    config = load_example()

    errors = common_validation(config).errors

    assert len(errors) == 1, errors
    assert str(config.pdf_path) in errors[0]


def test_the_shipped_example_never_trips_the_output_location_rule():
    config = load_example()

    errors = common_validation(config).errors

    assert not any(LOCAL_OUTPUTS_ERROR in error for error in errors)


def test_every_citation_in_the_shipped_example_has_a_bibtex_entry():
    config = load_example()
    body = config.body_path.read_text(encoding="utf-8")
    bib = config.bib_path.read_text(encoding="utf-8")

    keys, cited = bib_keys(bib), cited_keys(body)

    assert cited, "the example should demonstrate citing a source"
    assert cited - keys == set()
    assert keys - cited == set(), "unused BibTeX entries would warn on every build"
