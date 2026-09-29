"""Behavior tests for planned, read-only rubric assertions."""
from pathlib import Path

import pytest

from rubric_checks import run_checks


BODY = """# Óbjetivos
Investigación aplicada y evaluación sistemática [@one] [@two].
1. Analyze data
2. Present findings
![Chart](chart.png)
<https://example.org/one> [Site](https://example.org/two)

# Conclusiones
La investigación y evaluación aportan resultados.
"""


@pytest.mark.parametrize("check,expected", [
    ({"type": "heading_present", "section": "OBJETIVOS"}, True),
    ({"type": "heading_present", "section": "Absent"}, False),
    ({"type": "contains", "section": "objetivos", "text": "INVESTIGACIÓN"}, True),
    ({"type": "contains", "text": "never"}, False),
    ({"type": "matches", "section": "Objetivos", "pattern": r"evaluación\s+sistemática"}, True),
    ({"type": "matches", "pattern": r"never\d+"}, False),
    ({"type": "ordered_list", "section": "Objetivos", "min_items": 2}, True),
    ({"type": "ordered_list", "section": "Conclusiones"}, False),
    ({"type": "min_citations", "section": "Objetivos", "count": 2}, True),
    ({"type": "min_citations", "section": "Conclusiones", "count": 1}, False),
    ({"type": "figure_referenced", "section": "Objetivos"}, True),
    ({"type": "figure_referenced", "section": "Conclusiones"}, False),
    ({"type": "link_present", "section": "Objetivos", "pattern": "example.org/two"}, True),
    ({"type": "link_present", "section": "Objetivos", "pattern": "other"}, False),
    ({"type": "keywords_from_section", "section": "Conclusiones", "from_section": "Objetivos"}, True),
    ({"type": "keywords_from_section", "section": "Conclusiones", "from_section": "Absent"}, False),
    ({"type": "contains", "section": "Absent", "text": "data"}, False),
])
def test_each_check_pass_and_fail(tmp_path: Path, check: dict, expected: bool) -> None:
    result, = run_checks(tmp_path, [{"id": "objective", "checks": [check]}], BODY)
    assert result.ok is expected, result.detail
    assert result.criterion_id == "objective"
    assert result.check_index == 1
    assert result.type == check["type"]


def test_verbatim_requires_guide_and_section_and_normalizes_whitespace(tmp_path: Path) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text("Exact phrase from guide", encoding="utf-8")
    check = {"type": "verbatim_from_guide", "section": "Objetivos", "source": "guide.md", "text": "Exact phrase from guide"}
    criterion = [{"id": "exact", "checks": [check]}]
    assert run_checks(tmp_path, criterion, "# Objetivos\nExact\n phrase from guide")[0].ok
    assert not run_checks(tmp_path, criterion, BODY)[0].ok
    guide.write_text("Different guide", encoding="utf-8")
    assert not run_checks(tmp_path, criterion, "# Objetivos\nExact phrase from guide")[0].ok
    assert not run_checks(tmp_path, criterion, "odd body without headings")[0].ok
