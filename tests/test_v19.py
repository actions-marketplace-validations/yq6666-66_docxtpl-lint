"""v1.9: stable Python API, --fail-on, env autoescape handling."""

import io
import warnings

import jinja2
import pytest
from test_v16 import _doc

import docxtpl_lint
from docxtpl_lint import api
from docxtpl_lint.cli import main


def test_lint_accepts_path_bytes_and_stream(tmp_path):
    p = _doc(tmp_path, "{{ name }}", "{% if x %}")
    by_path = api.lint(p)
    raw = p.read_bytes()
    by_bytes = api.lint(raw)
    with open(p, "rb") as fh:
        by_stream = api.lint(fh)
        assert not fh.closed  # the caller owns the file object
    assert [i.rule for i in by_path.issues] == [i.rule for i in by_bytes.issues] == [i.rule for i in by_stream.issues]
    assert by_bytes.file == "<bytes>" and by_stream.file == str(p)
    assert all(i.location.file == "<bytes>" for i in by_bytes.issues)
    assert not by_path.ok and by_path.errors


def test_str_is_always_a_path():
    with pytest.raises(OSError):
        api.lint("{{ not a path }}")


def test_jinja_env_supplies_filters_tests_and_autoescape(tmp_path):
    p = _doc(tmp_path, "{{ amount|money }}", "{% if a is weekday %}x{% endif %}", "{{ a ~ b }}")
    env = jinja2.Environment(autoescape=True)
    env.filters["money"] = str
    env.tests["weekday"] = bool
    data = {"amount": 1, "a": "x & y", "b": "<i>"}
    plain = {i.rule for i in api.lint(p, data).issues}
    assert {"DTL104", "DTL105", "DTL308"} <= plain
    with_env = {i.rule for i in api.lint(p, data, jinja_env=env).issues}
    assert not {"DTL104", "DTL105", "DTL308"} & with_env


def test_effective_autoescape_matches_docxtpl():
    assert api.effective_autoescape(None, False) is False
    assert api.effective_autoescape(jinja2.Environment(autoescape=True)) is True
    assert api.effective_autoescape(jinja2.Environment(), True) is True
    # DeepSeek round 18: a callable must be evaluated; checked against a real docxtpl render
    sel = jinja2.Environment(autoescape=jinja2.select_autoescape(default_for_string=False))
    assert api.effective_autoescape(sel) is False


def test_callable_autoescape_off_still_reports_dtl308(tmp_path):
    from docxtpl import DocxTemplate

    p = _doc(tmp_path, "{{ a }}")
    env = jinja2.Environment(autoescape=jinja2.select_autoescape(default_for_string=False))
    t = DocxTemplate(str(p))
    t.render({"a": "x & y"}, jinja_env=env)
    assert t.docx.paragraphs[0].text == "x  y"  # really not escaped
    assert "DTL308" in [i.rule for i in api.lint(p, {"a": "x & y"}, jinja_env=env).issues]


def test_check_context_renders_without_mutating_env(tmp_path):
    p = _doc(tmp_path, "{{ name }}")
    env = jinja2.Environment()
    res = api.check_context(p, {"name": "A & B"}, jinja_env=env, autoescape=True)
    assert res.rendered and res.ok
    assert env.autoescape is False  # docxtpl itself would set it to True


def test_check_context_reports_render_failure(tmp_path):
    p = _doc(tmp_path, "{{ items|first }}")
    res = api.check_context(p.read_bytes(), {"items": 5})
    assert res.rendered and "DTL402" in [i.rule for i in res.issues]
    with pytest.raises(api.TemplateLintError) as ei:
        res.raise_for_errors()
    assert ei.value.result is res
    static = api.check_context(p, {"items": 5}, render=False)
    assert not static.rendered and "DTL402" not in [i.rule for i in static.issues]


def test_raise_for_errors_levels(tmp_path):
    p = _doc(tmp_path, "{{r name }}")
    res = api.lint(p, {"name": "x"})  # DTL307 (plain value for {{r}}) is a warning
    assert res.warnings and res.ok and res.raise_for_errors() is res
    with pytest.raises(api.TemplateLintError):
        res.raise_for_errors("warning")
    with pytest.raises(ValueError):
        res.raise_for_errors("never")


def test_select_ignore_and_to_dict(tmp_path):
    p = _doc(tmp_path, "{{ a }}", "{% if x %}")
    res = api.lint(p, {}, ignore=["DTL3"])
    assert all(not i.rule.startswith("DTL3") for i in res.issues)
    only = api.lint(p, {}, select=["DTL301"])
    assert {i.rule for i in only.issues} == {"DTL301"}
    d = only.to_dict()
    assert set(d) == {"file", "issues", "variables"} and d["variables"] == ["a"]


def test_infer_schema_is_json_schema(tmp_path):
    p = _doc(tmp_path, "{% for r in rows %}{{ r.n }}{% endfor %}")
    s = api.infer_schema([p])
    assert s["$schema"].startswith("https://json-schema.org/") and s["properties"]["rows"]["type"] == "array"


def test_top_level_exports():
    for name in ("lint", "check_context", "infer_schema", "Result", "TemplateLintError"):
        assert hasattr(docxtpl_lint, name)


def test_fail_on(tmp_path, capsys):
    p = _doc(tmp_path, "{{r name }}")
    d = tmp_path / "d.json"
    d.write_text('{"name": "x"}')
    args = [str(p), "--data", str(d)]
    assert main(args) == 0
    assert main([*args, "--fail-on", "warning"]) == 1
    assert main([*args, "--fail-on", "never"]) == 0
    bad = _doc(tmp_path, "{% if x %}", name="bad.docx")
    assert main([str(bad), "--fail-on", "never"]) == 0
    assert main([str(tmp_path / "missing.docx"), "--fail-on", "never"]) == 2
    capsys.readouterr()
    assert main([*args, "--warnings-as-errors"]) == 2
    assert "removed in 2.0" in capsys.readouterr().err


def test_fail_on_config(tmp_path, monkeypatch):
    p = _doc(tmp_path, "{{r name }}")
    (tmp_path / "d.json").write_text('{"name": "x"}')
    (tmp_path / "pyproject.toml").write_text('[tool.docxtpl-lint]\nfail-on = "warning"\ndata = ["d.json"]\n')
    monkeypatch.chdir(tmp_path)
    assert main([str(p)]) == 1
    (tmp_path / "pyproject.toml").write_text('[tool.docxtpl-lint]\nfail-on = "sometimes"\n')
    assert main([str(p)]) == 2


def test_cli_jinja_env_autoescape(tmp_path, monkeypatch):
    p = _doc(tmp_path, "{{ a ~ b }}")
    (tmp_path / "d.json").write_text('{"a": "x & y", "b": "<i>"}')
    (tmp_path / "myenv.py").write_text("import jinja2\nenv = jinja2.Environment(autoescape=True)\n")
    monkeypatch.chdir(tmp_path)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert main([str(p), "--data", "d.json", "--select", "DTL308"]) == 1
        assert main([str(p), "--data", "d.json", "--jinja-env", "myenv:env"]) == 0


def test_verify_does_not_mutate_env(tmp_path):
    from docxtpl_lint.verify import verify_path

    p = _doc(tmp_path, "{{ name }}")
    env = jinja2.Environment()
    verify_path(p, {"name": "x"}, jinja_env=env, autoescape=True)
    assert env.autoescape is False
    _ = io  # keep import for clarity of bytes tests
