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
    (re.compile(r"^word/endnotes\.xml$"), "endnotes"),
]


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


def _part_label(name: str) -> str | None:
    for pat, kind in _PART_PATTERNS:
        if pat.match(name):
            num = re.findall(r"\d+", name.rsplit("/", 1)[-1])
            return kind + (num[0] if num and kind in ("header", "footer") else "")
    return None


def _sort_key(name: str) -> tuple[int, int]:
    order = {"body": 0, "header": 1, "footer": 2, "footnotes": 3, "endnotes": 4}
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
            yield Paragraph(
                part=label,
                index=counters["p"],
                cells=tuple(CellPos(t, r, c) for t, r, c, _ in stack),
                cell_para=stack[-1][3] if stack else 0,
                text=_para_text(el),
            )
        for child in el:
            if isinstance(child.tag, str):
                yield from visit(child)

    yield from visit(root)
