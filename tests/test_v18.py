"""v1.8: CI formats (markdown, GitLab Code Quality), stable fingerprints, --output / --report."""

import json

from docx import Document

from docxtpl_lint.cli import main


def _doc(tmp_path, *paras, name="t.docx"):
    d = Document()
    for p in paras:
        d.add_paragraph(p)
    path = tmp_path / name
    d.save(path)
    return path


def test_markdown(tmp_path, capsys):
    p = _doc(tmp_path, "{% if a %}", "{{ x }")
    assert main([str(p), "--format", "markdown", "--no-config"]) == 1
    out = capsys.readouterr().out
    assert out.startswith("### docxtpl-lint") and "| [DTL101](" in out and "DTL001" in out
    assert main([str(p), "--format", "markdown", "--lang", "zh", "--no-config"]) == 1
    assert "| 规则 | 级别 | 位置 | 说明 |" in capsys.readouterr().out
    clean = _doc(tmp_path, "{{ a }}", name="c.docx")
    assert main([str(clean), "--format", "markdown", "--no-config"]) == 0
    assert "template(s) clean" in capsys.readouterr().out


def test_gitlab_fingerprints_stable_across_paragraph_shift(tmp_path, capsys):
    p = _doc(tmp_path, "{% if a %}", "{% if a %}")
    main([str(p), "--format", "gitlab", "--no-config"])
    first = json.loads(capsys.readouterr().out)
    assert [x["check_name"] for x in first] == ["DTL101", "DTL101"]
    assert first[0]["fingerprint"] != first[1]["fingerprint"]  # same text twice: occurrence index differs
    assert first[0]["severity"] == "major" and first[0]["location"]["lines"]["begin"] == 1
    _doc(tmp_path, "new intro", "{% if a %}", "{% if a %}")
    main([str(p), "--format", "gitlab", "--no-config"])
    second = json.loads(capsys.readouterr().out)
    assert {x["fingerprint"] for x in first} == {x["fingerprint"] for x in second}


def test_sarif_partial_fingerprints(tmp_path, capsys):
    p = _doc(tmp_path, "{% if a %}")
    main([str(p), "--format", "sarif", "--no-config"])
    res = json.loads(capsys.readouterr().out)["runs"][0]["results"]
    assert len(res[0]["partialFingerprints"]["docxtplLint/v1"]) == 32


def test_output_and_extra_reports(tmp_path, capsys):
    p = _doc(tmp_path, "{% if a %}")
    rc = main([str(p), "--no-config", "--format", "github", "-o", str(tmp_path / "gh.txt"),
               "--report", f"sarif:{tmp_path / 'r.sarif'}", "--report", f"markdown:{tmp_path / 's.md'}"])  # fmt: skip
    assert rc == 1
    assert capsys.readouterr().out == ""
    assert (tmp_path / "gh.txt").read_text().startswith("::error")
    assert json.loads((tmp_path / "r.sarif").read_text())["version"] == "2.1.0"
    assert "DTL101" in (tmp_path / "s.md").read_text()
    assert main([str(p), "--no-config", "--report", "text:x"]) == 2
    assert main([str(p), "--no-config", "--report", "nope"]) == 2
