from pathlib import Path

from build_latex_report import convert_inline, markdown_to_latex


def test_autolink_and_named_link_are_clickable():
    rendered = convert_inline('<https://github.com/a_b/repo%20x#top~end> [repo](https://github.com/a_b/repo%20x#top~end)')
    assert r'\url{https://github.com/a_b/repo%20x#top~end}' in rendered
    assert r'\href{https://github.com/a_b/repo%20x#top~end}{repo}' in rendered


def test_inline_ssh_remote_uses_breakable_nolinkurl():
    rendered = markdown_to_latex('`git@github.com:AlejandroTatum/academic-report-automation.git`')
    assert r'\nolinkurl{git@github.com:AlejandroTatum/academic-report-automation.git}' in rendered
    assert r'\texttt{' not in rendered


def test_url_like_inline_code_preserves_url_special_characters():
    rendered = convert_inline('`https://github.com/a_b/repo%20x#top~end`')
    assert r'\nolinkurl{https://github.com/a_b/repo%20x#top~end}' in rendered


def test_report_templates_enable_arbitrary_url_breaks():
    templates = Path(__file__).resolve().parent.parent / 'templates'
    for name in ('ape-report.tex', 'unl-report.tex', 'plain-report.tex'):
        source = (templates / name).read_text(encoding='utf-8')
        assert r'\usepackage{xurl}' in source, name
        assert source.index(r'\usepackage[hidelinks]{hyperref}') < source.index(r'\usepackage{xurl}'), name


def test_nested_list_preserves_enumerate_and_continuation():
    rendered = markdown_to_latex('1. a\n2. b\n   - x\n   - y\n   continuation paragraph\n3. c')
    assert rendered.count(r'\begin{enumerate}') == 1
    assert rendered.count(r'\end{enumerate}') == 1
    assert rendered.index(r'\begin{itemize}') < rendered.index(r'\item x') < rendered.index(r'\end{itemize}') < rendered.index(r'\item c')
    assert rendered.index('continuation paragraph') < rendered.index(r'\item c')
