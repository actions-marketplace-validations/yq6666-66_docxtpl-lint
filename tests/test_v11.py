"""v1.1: fixes from the DeepSeek adversarial run and the self-evaluation."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from docx import Document

from docxtpl_lint.core import lint_path
from docxtpl_lint.cli import main
from docxtpl_lint.contract import infer_tree, to_schema
from docxtpl_lint.fixes import suggest

ROOT = Path(__file__).resolve().parents[1]


def _doc(tmp_path, *paras, name="t.docx"):
    d = Document()
    for p in paras:
        d.add_paragraph(p)
    path = tmp_path / name
    d.save(path)
    return path


def test_data_with_bom_and_crlf(tmp_path):
    p = _doc(tmp_path, "{{ a }}")
    (tmp_path / "d.json").write_bytes(b'\xef\xbb\xbf{\r\n "a": 1\r\n}\r\n')
    assert main([str(p), "--data", str(tmp_path / "d.json"), "--no-config"]) == 0


@pytest.mark.parametrize("sub", [["infer"], ["verify"], ["fix"], ["diff", "{f}"]])
def test_subcommands_exit_2_on_non_docx(tmp_path, capsys, sub):
    fake = tmp_path / "fake.docx"
    fake.write_text("not a zip")
    args = [sub[0], str(fake)] + [a.format(f=fake) for a in sub[1:]]
    assert main(args) == 2
    assert "cannot read" in capsys.readouterr().err


def test_explain(capsys):
    assert main(["--explain", "dtl209"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("DTL209 (error)") and "rules.md#dtl209" in out
    assert main(["--explain", "DTL999"]) == 2


def test_templates_annotation_only_when_merging(tmp_path):
    a = _doc(tmp_path, "{{ x }}", name="a.docx")
    b = _doc(tmp_path, "{{ y }}", name="b.docx")
    assert "x-docxtpl-templates" not in json.dumps(to_schema(infer_tree([a])))
    assert to_schema(infer_tree([a, b]))["properties"]["x"]["x-docxtpl-templates"] == ["a.docx"]


def test_missing_brace_fix(tmp_path):
    p = _doc(tmp_path, "Total {{ total }", "{% if x %}ok{% endif %}")
    rep = lint_path(p)
    assert [i.rule for i in rep.issues] == ["DTL001"]  # the next paragraph is not swallowed
    fx = suggest(rep)
    assert fx and fx[0].new == "Total {{ total }}"


def test_adversarial_suite_matches_adjudicated_expectations():
    pytest.importorskip("docxtpl")
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/adversarial.py"),
            str(ROOT / "docs/eval/adversarial_cases.json"),
            "--adjudicated",
            str(ROOT / "benchmark/adversarial_adjudicated.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert "86/86" in r.stdout
