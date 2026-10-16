"""Read a .docx package and yield paragraphs with table-cell-aware locations.

Deliberately independent of docxtpl internals: we parse WordprocessingML with lxml.
"""

from __future__ import annotations

import re
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_W = f"{{{W}}}"

_PART_PATTERNS = [
    (re.compile(r"^word/document\.xml$"), "body"),
    (re.compile(r"^word/header\d*\.xml$"), "header"),
    (re.compile(r"^word/footer\d*\.xml$"), "footer"),
    (re.compile(r"^word/footnotes\.xml$"), "footnotes"),
]
# Only the parts docxtpl 0.20 actually renders (body, headers, footers, footnotes).
# Endnotes and comments are NOT rendered by docxtpl, so Jinja-looking text there is
# not template code and linting it would only produce false positives.


@dataclass(frozen=True)
class CellPos:
    table: int  # 1-based, per part, document order (nested tables counted too)
    row: int  # 1-based
    col: int  # 1-based


@dataclass(frozen=True)
class Paragraph:
    part: str  # e.g. "body", "header1"
    index: int  # 1-based paragraph index within the part (all paragraphs, flat)
    cells: tuple[CellPos, ...]  # outermost -> innermost table cell; empty if not in a table
    cell_para: int  # 1-based paragraph index inside innermost cell (0 if not in table)
    text: str
    deleted_code: str = ""  # template code inside a tracked deletion (w:del / w:moveFrom), see DTL003


def _part_label(name: str) -> str | None:
    for pat, kind in _PART_PATTERNS:
        if pat.match(name):
            num = re.findall(r"\d+", name.rsplit("/", 1)[-1])
            return kind + (num[0] if num and kind in ("header", "footer") else "")
    return None


def _sort_key(name: str) -> tuple[int, int]:
    order = {"body": 0, "header": 1, "footer": 2, "footnotes": 3, "endnotes": 4, "comments": 5}
    label = _part_label(name) or ""
    kind = re.sub(r"\d+$", "", label)
    num = re.findall(r"\d+$", label)
    return (order.get(kind, 9), int(num[0]) if num else 0)


def _para_text(p: etree._Element) -> str:
    """Concatenate run text belonging to this paragraph (not to nested text-box paragraphs)."""
    out: list[str] = []
    for el in p.iter(f"{_W}t", f"{_W}tab", f"{_W}br"):
        anc = el.getparent()
        while anc is not None and anc.tag != f"{_W}p":
            anc = anc.getparent()
        if anc is not p:
            continue
        if el.tag == f"{_W}t":
            out.append(el.text or "")
        else:
            out.append(" ")
    return "".join(out)


_SPECIAL = (f"{_W}delText", f"{_W}instrText", f"{_W}fldSimple")
_TEXT_RE = re.compile(
    r"<w:(?:t|delText|instrText)(?:\s[^>]*)?>([^<]*)</w:(?:t|delText|instrText)>|<w:fldSimple\s[^>]*?w:instr=\"([^\"]*)\""
)
_FIRST_RE = re.compile(r"(?<={)(<[^>]*>)+(?=[\{%\#])|(?<=[%\}\#])(<[^>]*>)+(?=\})", re.DOTALL)
_TAG_RE = re.compile(r"{%(?:(?!%}).)*|{#(?:(?!#}).)*|{{(?:(?!}}).)*", re.DOTALL)
_STRIP_RE = re.compile(r"</w:t>.*?(<w:t>|<w:t [^>]*>)", re.DOTALL)
_CODE_RE = re.compile(r"{[{%#]")


def _own(p: etree._Element, tags: tuple[str, ...]) -> list[etree._Element]:
    out = []
    for el in p.iter(*tags):
        anc = el.getparent()
        while anc is not None and anc.tag != f"{_W}p":
            anc = anc.getparent()
        if anc is p:
            out.append(el)
    return out


def _docxtpl_text(p: etree._Element) -> str:
    """Paragraph text as docxtpl's Jinja sees it when the paragraph has tracked deletions or
    field codes: docxtpl's own ``patch_xml`` regexes are applied to the paragraph XML, so XML
    between ``</w:t>`` and ``<w:t>`` inside a tag (e.g. a deletion in the middle of ``{{ … }}``)
    disappears, while deleted text and field codes *outside* tags stay and are rendered."""
    import html

    q = etree.fromstring(etree.tostring(p))
    for nested in list(q.iter(f"{_W}p"))[1:]:  # text boxes are their own paragraphs
        nested.getparent().remove(nested)
    xml = etree.tostring(q, encoding="unicode")
    xml = _FIRST_RE.sub("", xml)
    xml = _TAG_RE.sub(lambda m: _STRIP_RE.sub("", m.group(0)), xml)
    return html.unescape("".join(a or b for a, b in _TEXT_RE.findall(xml)))


def _deleted_code(p: etree._Element) -> str:
    deleted = [el.text or "" for el in _own(p, (f"{_W}delText",))]
    for mv in _own(p, (f"{_W}moveFrom",)):
        deleted += [t.text or "" for t in mv.iter(f"{_W}t")]
    text = "".join(deleted)
    return text if _CODE_RE.search(text) else ""


def iter_paragraphs(path: str | Path) -> Iterator[Paragraph]:
    with zipfile.ZipFile(path) as zf:
        names = sorted((n for n in zf.namelist() if _part_label(n)), key=_sort_key)
        for name in names:
            label = _part_label(name)
            assert label is not None
            root = etree.fromstring(zf.read(name))
            yield from _walk_part(root, label)


def _walk_part(root: etree._Element, label: str) -> Iterator[Paragraph]:
    counters = {"p": 0, "tbl": 0}
    # stack entries: [table_no, row_no, col_no, para_in_cell]
    stack: list[list[int]] = []

    def visit(el: etree._Element) -> Iterator[Paragraph]:
        tag = el.tag
        if tag == f"{_W}tbl":
            counters["tbl"] += 1
            stack.append([counters["tbl"], 0, 0, 0])
            for child in el:
                yield from visit(child)
            stack.pop()
            return
        if tag == f"{_W}tr" and stack:
            stack[-1][1] += 1
            stack[-1][2] = 0
        elif tag == f"{_W}tc" and stack:
            stack[-1][2] += 1
            stack[-1][3] = 0
        elif tag == f"{_W}p":
            counters["p"] += 1
            if stack:
                stack[-1][3] += 1
            special = bool(_own(el, _SPECIAL)) or bool(_own(el, (f"{_W}moveFrom",)))
            yield Paragraph(
                part=label,
                index=counters["p"],
                cells=tuple(CellPos(t, r, c) for t, r, c, _ in stack),
                cell_para=stack[-1][3] if stack else 0,
                text=_docxtpl_text(el) if special else _para_text(el),
                deleted_code=_deleted_code(el) if special else "",
            )
        for child in el:
            if isinstance(child.tag, str):
                yield from visit(child)

    yield from visit(root)
