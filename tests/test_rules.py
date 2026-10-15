import json

import pytest
from docx import Document

from docxtpl_lint import lint_path
from docxtpl_lint.cli import main
from docxtpl_lint.reader import CellPos

CTX = {
    "customer": {"name": "A"},
    "items": [{"name": "p", "price": 1}],
    "company": "c",
    "order": {"id": 1, "lines": [{"name": "a", "qty": 1}], "comments": ["x"], "extra": [1]},
    "row_index": 2,
    "client": {"name": "n", "email": "e"},
    "paid": True,
    "amount": 3,
}


def rules(rep):
    return [i.rule for i in rep.issues]


def test_clean_template_has_no_issues(fx):
    rep = lint_path(fx / "clean.docx")
    assert rep.issues == []
    assert "items[].price" in rep.variables
    assert "total" not in rep.variables  # {% set %} local
    assert "item.name" not in rep.variables  # loop var resolved


def test_clean_template_really_renders_with_docxtpl(fx):
    docxtpl = pytest.importorskip("docxtpl")
    t = docxtpl.DocxTemplate(str(fx / "clean.docx"))
    t.render(CTX)


@pytest.mark.parametrize("name", ["issue603_table_loop", "issue644_percent", "issue378_unclosed"])
def test_broken_templates_really_fail_in_docxtpl(fx, name):
    docxtpl = pytest.importorskip("docxtpl")
    from jinja2 import TemplateSyntaxError

    with pytest.raises(TemplateSyntaxError):
        docxtpl.DocxTemplate(str(fx / f"{name}.docx")).render(CTX)


def test_split_runs_are_not_false_positives(fx):
    # clean.docx writes "{{ cust" "omer.name" " }}" as three runs
    assert "customer.name" in lint_path(fx / "clean.docx").variables


# --- #378: locate errors ----------------------------------------------------


def test_378_unclosed_if_located_to_cell(fx):
    rep = lint_path(fx / "issue378_unclosed.docx")
    (dtl101,) = [i for i in rep.issues if i.rule == "DTL101"]
    assert dtl101.location.cells == (CellPos(table=2, row=3, col=1),)
    assert dtl101.snippet == "{% if paid %}"


def test_378_reports_all_errors_not_just_first(fx):
    assert sorted(rules(lint_path(fx / "issue378_unclosed.docx"))) == ["DTL001", "DTL101", "DTL102"]


def test_378_cross_paragraph_split(fx):
    rep = lint_path(fx / "issue378_unclosed.docx")
    (i,) = [i for i in rep.issues if i.rule == "DTL001"]
    assert i.snippet.startswith("{{ client.")
    assert i.location.cells == ()


# --- #603: table loops ------------------------------------------------------


def test_603_rules(fx):
    rep = lint_path(fx / "issue603_table_loop.docx")
    assert rules(rep) == ["DTL206", "DTL204", "DTL202"]


def test_603_same_row_location(fx):
    rep = lint_path(fx / "issue603_table_loop.docx")
    i = next(i for i in rep.issues if i.rule == "DTL206")
    assert i.location.cells == (CellPos(1, 2, 2),)


# --- #644: % or } inside prefixed tags ---------------------------------------


def test_644_percent_and_brace(fx):
    rep = lint_path(fx / "issue644_percent.docx")
    assert rules(rep) == ["DTL201", "DTL201"]
    assert [i.location.paragraph for i in rep.issues] == [1, 4]


# --- misc rules -------------------------------------------------------------


def _doc(tmp_path, build):
    d = Document()
    build(d)
    path = tmp_path / "t.docx"
    d.save(path)
    return path


def test_tr_outside_table(tmp_path):
    p = _doc(tmp_path, lambda d: [d.add_paragraph("{%tr for x in xs %}"), d.add_paragraph("{%tr endfor %}")])
    assert "DTL203" in rules(lint_path(p))


def test_tr_across_tables(tmp_path):
    def b(d):
        d.add_table(rows=1, cols=1).cell(0, 0).text = "{%tr for x in xs %}"
        d.add_table(rows=1, cols=1).cell(0, 0).text = "{%tr endfor %}"

    assert rules(lint_path(_doc(tmp_path, b))) == ["DTL205"]


def test_else_outside_block(tmp_path):
    p = _doc(tmp_path, lambda d: d.add_paragraph("{% else %}"))
    assert rules(lint_path(p)) == ["DTL102"]


def test_other_syntax_error(tmp_path):
    p = _doc(tmp_path, lambda d: d.add_paragraph("{{ a | }}"))
    assert rules(lint_path(p)) == ["DTL103"]


def test_nested_table_location(tmp_path):
    def b(d):
        outer = d.add_table(rows=2, cols=2)
        inner = outer.cell(1, 1).add_table(rows=2, cols=1)
        inner.cell(1, 0).text = "{% if x %}"

    (i,) = lint_path(_doc(tmp_path, b)).issues
    assert i.location.cells == (CellPos(1, 2, 2), CellPos(2, 2, 1))
    assert "表1 行2 列2 > 表2 行2 列1" in i.location.human()


def test_header_footer_scanned(tmp_path):
    def b(d):
        d.sections[0].header.paragraphs[0].text = "{% if x %}"

    (i,) = lint_path(_doc(tmp_path, b)).issues
    assert i.location.part == "header1"


def test_with_and_for_tuple_scope(tmp_path):
    def b(d):
        d.add_paragraph("{% with y = a.b %}{{ y.c }}{% endwith %}")
        d.add_paragraph("{% for k, v in m.items() %}{{ k }}{{ v }}{{ loop.index }}{% endfor %}")
        d.add_paragraph("{% for i in range(3) %}{{ i }}{% endfor %}")

    rep = lint_path(_doc(tmp_path, b))
    assert rep.issues == []
    assert rep.variables == ["a.b", "m"]


# --- data contract ------------------------------------------------------------


def test_data_contract(fx):
    data = json.loads((fx / "clean.data.json").read_text())
    rep = lint_path(fx / "clean.docx", data)
    errs = [(i.rule, i.message.split("`")[1]) for i in rep.issues]
    assert ("DTL301", "items[*].price") in errs
    assert ("DTL302", "unused_key") in errs
    assert len(errs) == 2


def test_empty_list_cannot_prove_absence(fx):
    rep = lint_path(fx / "clean.docx", {"customer": {"name": 1}, "items": [], "company": 1})
    assert rep.issues == []


# --- CLI ----------------------------------------------------------------------


def test_cli_exit_codes(fx, capsys):
    assert main([str(fx / "clean.docx")]) == 0
    assert main([str(fx / "issue644_percent.docx")]) == 1
    assert main([]) == 2
    assert main([str(fx / "nope.docx")]) == 2
    assert main([str(fx / "clean.docx"), "--data", str(fx / "missing.json")]) == 2


def test_cli_warnings_policy(fx):
    data = fx / "w.json"
    data.write_text(json.dumps({"customer": {"name": 1}, "items": [], "company": 1, "extra": 1}))
    assert main([str(fx / "clean.docx"), "--data", str(data)]) == 0
    assert main([str(fx / "clean.docx"), "--data", str(data), "--warnings-as-errors"]) == 1


def test_cli_select_ignore(fx):
    assert main([str(fx / "issue603_table_loop.docx"), "--ignore", "DTL2"]) == 0
    assert main([str(fx / "issue603_table_loop.docx"), "--select", "DTL1"]) == 0


def test_cli_json(fx, capsys):
    main([str(fx / "issue378_unclosed.docx"), "--format", "json"])
    out = json.loads(capsys.readouterr().out)
    issue = next(i for i in out["files"][0]["issues"] if i["rule"] == "DTL101")
    assert issue["location"]["cells"] == [{"table": 2, "row": 3, "col": 1}]


def test_cli_corrupt_file(tmp_path):
    bad = tmp_path / "bad.docx"
    bad.write_text("not a zip")
    assert main([str(bad)]) == 2
