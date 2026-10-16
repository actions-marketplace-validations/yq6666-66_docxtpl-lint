"""Ground truth: every rule case is rendered with the real docxtpl, so a rule can
never claim a problem that docxtpl does not actually have."""

import pytest
from rule_cases import CASES, CTX, build

docxtpl = pytest.importorskip("docxtpl")
from docx import Document  # noqa: E402
from jinja2 import TemplateSyntaxError  # noqa: E402


def _cells(path):
    return [c.text for t in Document(str(path)).tables for r in t.rows for c in r.cells]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_docxtpl_really_behaves_as_documented(case, tmp_path):
    src, out = tmp_path / "in.docx", tmp_path / "out.docx"
    build(case, src)
    tpl = docxtpl.DocxTemplate(str(src))
    if case.docxtpl == "raises":
        with pytest.raises(TemplateSyntaxError):
            tpl.render(CTX)
        return
    tpl.render(CTX)
    tpl.save(str(out))
    if case.lost:
        doc = Document(str(out))
        text = [p.text for p in doc.paragraphs] + _cells(out)
        assert not any(case.lost in t for t in text)
        return
    if case.docxtpl == "silent":
        # renders without error, but the loop output ("1", "2") is lost or mangled
        cells = _cells(out)
        assert cells.count("1") + cells.count("2") < 2 or "" in cells
