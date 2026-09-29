from build_latex_report import markdown_to_latex, resolve_figure, validate_figure_paths


def test_report_relative_figures_take_precedence_and_render_resolved_path(tmp_path):
    report = tmp_path / 'report'
    build = report / 'build'
    build.mkdir(parents=True)
    (report / 'figures').mkdir()
    (build / 'figures').mkdir()
    (report / 'figures/x.png').write_bytes(b'report')
    (build / 'figures/x.png').write_bytes(b'build')
    assert resolve_figure('figures/x.png', build) == report / 'figures/x.png'
    assert validate_figure_paths('![cap](figures/x.png)', build) == []
    assert r'../figures/x.png' in markdown_to_latex('![cap](figures/x.png)', build_dir=build)


def test_ambiguous_figure_warns_with_both_paths(tmp_path, capsys):
    build = tmp_path / 'report/build'
    build.mkdir(parents=True)
    (build.parent / 'x.png').write_bytes(b'report')
    (build / 'x.png').write_bytes(b'build')
    assert resolve_figure('x.png', build) == build.parent / 'x.png'
    warning = capsys.readouterr().err
    assert str(build.parent / 'x.png') in warning
    assert str(build / 'x.png') in warning


def test_legacy_build_relative_path_remains_valid(tmp_path):
    build = tmp_path / 'report/build'
    build.mkdir(parents=True)
    (tmp_path / 'report/figures').mkdir()
    (tmp_path / 'report/figures/x.png').write_bytes(b'x')
    assert validate_figure_paths('![cap](../figures/x.png)', build) == []
