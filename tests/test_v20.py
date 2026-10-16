"""2.0: verify shares lint's config/outputs, removals and deprecations."""

import json

import pytest
from docxtpl import DocxTemplate
from test_v16 import _doc

import docxtpl_lint
from docxtpl_lint import api
from docxtpl_lint.cli import main

ENV = "import jinja2\nenv = jinja2.Environment()\nenv.filters['money'] = lambda v: f'{v} EUR'\n"


@pytest.fixture
def proj(tmp_path, monkeypatch):
    p = _doc(tmp_path, "Total {{ amount|money }}")
    (tmp_path / "env20.py").write_text(ENV)
    (tmp_path / "pyproject.toml").write_text('[tool.docxtpl-lint]\njinja-env = "env20:env"\n')
    monkeypatch.chdir(tmp_path)
    return p


def test_without_the_env_docxtpl_really_fails(proj):
    with pytest.raises(Exception, match="money"):
        DocxTemplate(str(proj)).render({"amount": 1})


def test_verify_uses_config_jinja_env(proj, capsys):
    assert main([str(proj)]) == 0  # lint already honours the config
    assert main(["verify", str(proj)]) == 0  # 1.x: DTL402 "No filter named 'money'"
    assert main(["verify", str(proj), "--no-config"]) == 1
    assert "DTL402" in capsys.readouterr().out


def test_verify_ignores_config_data(tmp_path, monkeypatch):
    """Config data would switch verify to user-data mode and silently drop DTL401."""
    p = _doc(tmp_path, "{%p if x %}lost {{ y }}{%p endif %}")
    (tmp_path / "d.json").write_text('{"x": 1, "y": "v"}')
    (tmp_path / "pyproject.toml").write_text('[tool.docxtpl-lint]\ndata = ["d.json"]\n')
    monkeypatch.chdir(tmp_path)
    plain = main(["verify", str(p), "--no-config"])
    assert main(["verify", str(p)]) == plain


def test_verify_formats_select_baseline_fail_on(tmp_path, monkeypatch, capsys):
    p = _doc(tmp_path, "Total {{ amount|money }}")
    monkeypatch.chdir(tmp_path)
    assert main(["verify", str(p), "--format", "sarif", "-o", "v.sarif"]) == 1
    sarif = json.loads((tmp_path / "v.sarif").read_text())
    assert sarif["runs"][0]["results"][0]["ruleId"] == "DTL402"
    assert main(["verify", str(p), "--ignore", "DTL402"]) == 0
    assert main(["verify", str(p), "--fail-on", "never"]) == 0
    assert main(["verify", str(p), "--write-baseline", "bl.json"]) == 0
    assert main(["verify", str(p), "--baseline", "bl.json"]) == 0
    assert main(["verify", str(p), "--format", "github"]) == 1
    assert "::error" in capsys.readouterr().out


def test_verify_rejects_lint_only_flags(tmp_path):
    p = _doc(tmp_path, "{{ a }}")
    assert main(["verify", str(p), "--schema", "s.json"]) == 2


def test_warnings_as_errors_removed(tmp_path, monkeypatch, capsys):
    p = _doc(tmp_path, "{{ a }}")
    assert main([str(p), "--warnings-as-errors"]) == 2
    assert "--fail-on warning" in capsys.readouterr().err
    (tmp_path / "pyproject.toml").write_text("[tool.docxtpl-lint]\nwarnings-as-errors = true\n")
    monkeypatch.chdir(tmp_path)
    assert main([str(p)]) == 2
    assert 'fail-on = "warning"' in capsys.readouterr().err


def test_json_fingerprint_matches_sarif_and_api(tmp_path, capsys):
    p = _doc(tmp_path, "{% if x %}")
    main([str(p), "--format", "json"])
    issue = json.loads(capsys.readouterr().out)["files"][0]["issues"][0]
    main([str(p), "--format", "sarif"])
    res = json.loads(capsys.readouterr().out)["runs"][0]["results"][0]
    assert issue["fingerprint"] == res["partialFingerprints"]["docxtplLint/v1"]
    assert api.lint(p).to_dict()["issues"][0]["fingerprint"] == issue["fingerprint"]


def test_lint_path_deprecated_but_works(tmp_path):
    p = _doc(tmp_path, "{% if x %}")
    with pytest.warns(DeprecationWarning, match="docxtpl_lint.lint"):
        fn = docxtpl_lint.lint_path
    assert fn(p).issues
    with pytest.raises(AttributeError):
        _ = docxtpl_lint.nope


def test_diff_fail_on(tmp_path, capsys):
    old = _doc(tmp_path, "{{ a }}", name="old.docx")
    new = _doc(tmp_path, "{{ a }} {{ b }}", name="new.docx")
    assert main(["diff", str(old), str(new)]) == 0
    assert main(["diff", str(old), str(new), "--fail-on", "breaking"]) == 1
    assert main(["diff", str(old), str(old), "--fail-on", "change"]) == 0
    assert main(["diff", str(new), str(old), "--fail-on", "change"]) == 1
    capsys.readouterr()
    assert main(["diff", str(old), str(new), "--fail-on-breaking"]) == 1
    assert "deprecated" in capsys.readouterr().err


def test_diff_conflicting_flags(tmp_path):
    old = _doc(tmp_path, "{{ a }}", name="old.docx")
    assert main(["diff", str(old), str(old), "--fail-on", "change", "--fail-on-breaking"]) == 2


def test_verify_help_hides_lint_only_flags(capsys):
    with pytest.raises(SystemExit):
        main(["verify", "-h"])
    out = capsys.readouterr().out
    assert "--out" in out and "--schema" not in out and "--fail-on" in out
