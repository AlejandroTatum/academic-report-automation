"""Guard against silently redefined top-level functions.

Python accepts two `def` statements with the same name in one module: the
second simply replaces the first, with no warning. The earlier body becomes
unreachable, which is how a guard clause can disappear from a function that
still looks correct when read from the top.

This test parses every tool module and fails on any repeated top-level
function name, so the next accidental redefinition is caught by the suite
instead of by a wrong result in a rendered PDF.
"""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent

MODULES = sorted(
    path for path in TOOLS.glob("*.py") if not path.name.startswith("test_")
)


@pytest.mark.parametrize("module", MODULES, ids=lambda p: p.name)
def test_module_has_no_duplicate_top_level_functions(module: Path) -> None:
    tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
    names = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
    assert not duplicates, (
        f"{module.name} defines these functions more than once, so only the "
        f"last definition survives: {', '.join(duplicates)}"
    )
