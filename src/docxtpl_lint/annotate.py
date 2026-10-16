"""Write a *copy* of a template with one Word comment per finding (idea from lintxtpl).

The original file is never touched. Only the body (word/document.xml) can carry Word
comments; findings in headers, footers or footnotes are listed in a comment on the first
body paragraph. The copy is for reviewing in Word, not for rendering.
"""

from __future__ import annotations

import datetime as _dt
import zipfile
from pathlib import Path

from lxml import etree

from .core import Report

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_W = f"{{{W}}}"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
COMMENTS_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
COMMENTS_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"


def _w(tag: str) -> str:
    return _W + tag


def annotate(rep: Report, out: str | Path, lang: str = "en", author: str = "docxtpl-lint") -> int:
    """Write ``out``; returns the number of comments added."""
    src = Path(rep.file)
    with zipfile.ZipFile(src) as zf:
        files = {n: zf.read(n) for n in zf.namelist()}
        infos = {i.filename: i for i in zf.infolist()}
    doc = etree.fromstring(files["word/document.xml"])
    paras = list(doc.iter(_w("p")))
    if not paras:
        return 0

    comments_name = "word/comments.xml"
    rels_name = "word/_rels/document.xml.rels"
    rels = etree.fromstring(files[rels_name]) if rels_name in files else etree.Element(f"{{{PKG_REL}}}Relationships")
    rel = next((r for r in rels if r.get("Type") == COMMENTS_TYPE), None)
    if rel is not None:
        comments_name = "word/" + rel.get("Target").lstrip("/").removeprefix("word/")
    if comments_name in files:
        comments = etree.fromstring(files[comments_name])
    else:
        comments = etree.Element(_w("comments"), nsmap={"w": W})
    ids = [int(c.get(_w("id"))) for c in comments.iter(_w("comment")) if (c.get(_w("id")) or "").isdigit()]
    for el in doc.iter(_w("commentRangeStart"), _w("commentReference")):
        if (el.get(_w("id")) or "").isdigit():
            ids.append(int(el.get(_w("id"))))
    next_id = max(ids, default=-1) + 1

    by_para: dict[int, list[str]] = {}
    elsewhere: list[str] = []
    for i in rep.issues:
        loc = i.location
        text = f"{i.rule} {i.severity}: {i.message_for(lang)}"
        if loc.part == "body" and 0 < loc.paragraph <= len(paras):
            by_para.setdefault(loc.paragraph, []).append(text)
        else:
            elsewhere.append(f"[{loc.human(lang)}] {text}")
    if elsewhere:
        by_para.setdefault(1, []).extend(elsewhere)

    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    added = 0
    for n, texts in sorted(by_para.items()):
        p = paras[n - 1]
        cid = str(next_id)
        next_id += 1
        c = etree.SubElement(comments, _w("comment"), {_w("id"): cid, _w("author"): author, _w("date"): now,
                                                        _w("initials"): "DTL"})  # fmt: skip
        for t in texts:
            cp = etree.SubElement(c, _w("p"))
            tr = etree.SubElement(cp, _w("r"))
            te = etree.SubElement(tr, _w("t"))
            te.text = t
            te.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        start = etree.Element(_w("commentRangeStart"), {_w("id"): cid})
        ppr = p.find(_w("pPr"))
        p.insert(p.index(ppr) + 1 if ppr is not None else 0, start)
        p.append(etree.Element(_w("commentRangeEnd"), {_w("id"): cid}))
        ref_run = etree.SubElement(p, _w("r"))
        etree.SubElement(ref_run, _w("commentReference"), {_w("id"): cid})
        added += 1

    files["word/document.xml"] = etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)
    files[comments_name] = etree.tostring(comments, xml_declaration=True, encoding="UTF-8", standalone=True)
    if rel is None:
        used = {r.get("Id") for r in rels}
        rid = next(f"rId{k}" for k in range(1, 10_000) if f"rId{k}" not in used)
        etree.SubElement(rels, f"{{{PKG_REL}}}Relationship", {"Id": rid, "Type": COMMENTS_TYPE,
                                                              "Target": "comments.xml"})  # fmt: skip
        files[rels_name] = etree.tostring(rels, xml_declaration=True, encoding="UTF-8", standalone=True)
    ct = etree.fromstring(files["[Content_Types].xml"])
    part = "/" + comments_name
    if not any(o.get("PartName") == part for o in ct if o.tag == f"{{{CT_NS}}}Override"):
        etree.SubElement(ct, f"{{{CT_NS}}}Override", {"PartName": part, "ContentType": COMMENTS_CT})
        files["[Content_Types].xml"] = etree.tostring(ct, xml_declaration=True, encoding="UTF-8", standalone=True)

    out = Path(out)
    if out.resolve() == src.resolve():
        raise ValueError("refusing to overwrite the template itself")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
        order = ["[Content_Types].xml"] + [n for n in files if n != "[Content_Types].xml"]
        for n in order:
            zo.writestr(infos.get(n, n), files[n])
    return added
