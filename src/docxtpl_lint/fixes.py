"""Fix suggestions as unified diffs of paragraph text (``docxtpl-lint fix``), and since 1.7
``fix --write OUT``: the same edits applied to a *copy* of the template.

The template itself is never rewritten. Edits are applied inside the existing ``<w:t>``
runs (characters are removed from / inserted into the runs they touch), so run formatting
is kept. Each suggestion is a small, deterministic text change; every kind is checked in
the test-suite by applying it and rendering with docxtpl.

Safety: ``safe`` fixes restore what the author evidently meant (a missing ``}``, a space
before ``tr``, a prefix that must match its pair, a misspelt Jinja keyword). Fixes that
guess at intent (renaming a data path after ``--data``, removing a stray tag, dropping a
``tr``/``tc`` prefix whose pair must change too) are ``unsafe`` and need ``--unsafe``.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .core import Issue, Location, Report

JINJA_KEYWORDS = [
    "if", "elif", "else", "endif", "for", "endfor", "set", "endset", "with", "endwith",
    "macro", "endmacro", "call", "endcall", "filter", "endfilter", "block", "endblock",
    "raw", "endraw", "include", "import", "from", "extends", "autoescape", "endautoescape",
    "cellbg", "colspan", "vm", "hm",
]  # fmt: skip

_STMT = re.compile(r"^\{%(-?)\s*(?:(tr|tc|p|r)\s+)?(.*?)\s*(-?)%\}$", re.S)


@dataclass
class Fix:
    issue: Issue
    old: str  # paragraph text before
    new: str  # paragraph text after
    note: str
    location: Location | None = None  # paragraph changed, if not the issue's own
    safe: bool = True

    def diff(self, lang: str = "en") -> str:
        loc = self.location or self.issue.location
        where = loc.human(lang)
        name = loc.file.lstrip("/")
        lines = difflib.unified_diff(
            [self.old], [self.new], f"a/{name} ({where})", f"b/{name} ({where})", lineterm="", n=0
        )
        return f"# {self.issue.rule}: {self.note}\n" + "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        loc = (self.location or self.issue.location).to_dict()
        return {
            **loc,
            "rule": self.issue.rule,
            "old": self.old,
            "new": self.new,
            "note": self.note,
            "safe": self.safe,
        }


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def closest(word: str, choices: list[str], max_dist: int = 2) -> str | None:
    """Closest choice within ``max_dist`` edits (ties: none, to avoid confident nonsense)."""
    scored = sorted((edit_distance(word, c), c) for c in choices if c != word)
    if not scored or scored[0][0] > max_dist:
        return None
    if len(scored) > 1 and scored[1][0] == scored[0][0]:
        return None
    return scored[0][1]


def _stmt(raw: str, prefix: str) -> str | None:
    m = _STMT.match(raw)
    if not m:
        return None
    lws, _, body, rws = m.groups()
    return "{%" + lws + (prefix + " " if prefix else " ") + body + " " + rws + "%}"


def _data_paths(data: Any, path: str = "") -> list[str]:
    out: list[str] = []
    if isinstance(data, dict):
        for k, v in data.items():
            p = f"{path}.{k}" if path else str(k)
            out.append(p)
            out += _data_paths(v, p)
    elif isinstance(data, list):
        for v in data[:1]:
            out += _data_paths(v, path + "[]")
    return out


_OPENER_RE = re.compile(r"\{%-?\s*(?:(?:tr|tc|p|r)\s+)?([A-Za-z_]\w*)")


def _misspelt_opener(rep: Report, iss: Issue, end_kw: str) -> Fix | None:
    """`{% iff x %}…{% endif %}`: the stray end tag is caused by a typo in the opening tag."""
    want = end_kw[3:]
    loc = iss.location
    paras = rep.paragraphs.get(loc.part, [])[: loc.paragraph]
    for para in reversed(paras):
        for m in reversed(list(_OPENER_RE.finditer(para.text))):
            word = m.group(1)
            if word not in JINJA_KEYWORDS and edit_distance(word, want) <= 2:
                new = para.text[: m.start(1)] + want + para.text[m.end(1) :]
                where = replace(loc, paragraph=para.index, cells=para.cells, cell_paragraph=para.cell_para, column=0)
                return Fix(iss, para.text, new, f"`{word}` is not a Jinja tag; did you mean `{want}`?", where)
    return None


def suggest(rep: Report, contexts: list[Any] | None = None) -> list[Fix]:
    fixes: list[Fix] = []
    known = sorted({p for d in contexts or [] for p in _data_paths(d)})
    for iss in rep.issues:
        loc = iss.location
        paras = rep.paragraphs.get(loc.part, [])
        if not (0 < loc.paragraph <= len(paras)) or not iss.snippet:
            continue
        text = paras[loc.paragraph - 1].text
        raw = iss.snippet
        if raw not in text:
            continue
        new_raw: str | None = None
        note = ""
        safe = True
        if iss.rule == "DTL001" and raw.startswith("{{") and len(raw) < 60:
            body = raw.rstrip()
            if body.endswith("}") and not body.endswith("}}"):
                new_raw = raw.replace(body, body + "}", 1)
                note = "close the tag with `}}`"
        elif iss.rule == "DTL202":
            new_raw = re.sub(r"\{%(-?)\s+(tr|tc|p|r)\s+", r"{%\1\2 ", raw, count=1)
            note = "no space between `{%` and the prefix"
        elif iss.rule == "DTL204":
            op, cp = iss.params["open_prefix"], iss.params["close_prefix"]
            if cp in ("tr", "tc") and op not in ("tr", "tc"):
                # the closing tag is the table-aware one: fix the opening tag instead
                ops = rep.paragraphs.get(iss.params["_open_part"], [])
                oi = iss.params["_open_paragraph"]
                otext = ops[oi - 1].text if 0 < oi <= len(ops) else ""
                oraw = iss.params["open_raw"]
                onew = _stmt(oraw, cp)
                if oraw in otext and onew:
                    o_loc = replace(loc, part=iss.params["_open_part"], paragraph=oi, cells=ops[oi - 1].cells,
                                    cell_paragraph=ops[oi - 1].cell_para, column=0)  # fmt: skip
                    fixes.append(Fix(iss, otext, otext.replace(oraw, onew, 1), f"use `{{%{cp}` like {raw}", o_loc))
                continue
            new_raw = _stmt(raw, "" if op == "-" else op)
            note = f"use the same prefix as {iss.params['open_raw']}"
        elif iss.rule == "DTL203":
            new_raw = _stmt(raw, "")
            note = "tr/tc prefixes only work inside a table; use a plain tag (remember its pair)"
            safe = False
        elif iss.rule == "DTL102":
            m = _STMT.match(raw)
            kw = m.group(3).split()[0] if m and m.group(3).split() else ""
            best = closest(kw, JINJA_KEYWORDS) if kw and kw not in JINJA_KEYWORDS else None
            opener = _misspelt_opener(rep, iss, kw) if kw.startswith("end") and not best else None
            if best:
                new_raw = re.sub(rf"\b{re.escape(kw)}\b", best, raw, count=1)
                note = f"did you mean `{best}`?"
            elif opener:
                fixes.append(opener)
                continue
            else:
                new_raw = ""
                note = "remove the stray tag (or add the missing opening tag)"
                safe = False
        elif iss.rule == "DTL103":
            m = re.search(r"unknown tag '(\w+)'", iss.params.get("msg", ""))
            if m:
                best = closest(m.group(1), JINJA_KEYWORDS)
                if best:
                    new_raw = re.sub(rf"\b{re.escape(m.group(1))}\b", best, raw, count=1)
                    note = f"did you mean `{best}`?"
        elif iss.rule == "DTL301" and known:
            path = iss.params["path"].replace("[*]", "[]")
            best = closest(path, known)
            if best and best.count(".") == path.count("."):
                old_segs, new_segs = path.split("."), best.split(".")
                diffs = [(a, b) for a, b in zip(old_segs, new_segs, strict=True) if a != b]
                if len(diffs) == 1 and "[]" not in diffs[0][0]:
                    a, b = diffs[0]
                    cand = re.sub(rf"\b{re.escape(a)}\b", b, raw, count=1)
                    if cand != raw:
                        new_raw, note = cand, f"did you mean `{best.replace('[]', '[*]')}`?"
                        safe = False
        if new_raw is None or new_raw == raw:
            continue
        new = text.replace(raw, new_raw, 1)
        if not new_raw:
            new = re.sub(r"\s{2,}", " ", new).strip() if new.strip() else ""
        fixes.append(Fix(iss, text, new, note, safe=safe))
    return fixes


# ---------------------------------------------------------------- fix --write (1.7)


def _part_names(names: list[str]) -> dict[str, str]:
    from .reader import _part_label

    return {lbl: n for n in names if (lbl := _part_label(n))}


def _apply_in_runs(p: Any, old: str, new: str) -> bool:
    """Turn the paragraph text ``old`` into ``new`` by editing its ``<w:t>`` elements in place.
    Returns False (and changes nothing) if the paragraph is not plain text the edit can map onto."""
    from .reader import _W, _para_text

    if _para_text(p) != old:
        return False
    segs: list[tuple[Any, int, int]] = []  # (element or None for tab/br, start, end)
    pos = 0
    for el in p.iter(f"{_W}t", f"{_W}tab", f"{_W}br", f"{_W}delText", f"{_W}instrText"):
        anc = el.getparent()
        while anc is not None and anc.tag != f"{_W}p":
            anc = anc.getparent()
        if anc is not p:
            continue
        if el.tag in (f"{_W}delText", f"{_W}instrText"):
            return False  # tracked changes / field codes: leave to the author
        n = len(el.text or "") if el.tag == f"{_W}t" else 1
        segs.append((el if el.tag == f"{_W}t" else None, pos, pos + n))
        pos += n
    ops = difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_opcodes()
    texts = {id(e): list(e.text or "") for e, _, _ in segs if e is not None}
    for tag, i1, i2, j1, j2 in reversed(ops):
        if tag == "equal":
            continue
        ins = new[j1:j2]
        touched = [(e, a, b) for e, a, b in segs if a < i2 and b > i1] if i2 > i1 else []
        if any(e is None for e, _, _ in touched):
            return False
        if i2 > i1:
            first = True
            for e, a, b in touched:
                lo, hi = max(i1, a) - a, min(i2, b) - a
                chars = texts[id(e)]
                chars[lo:hi] = list(ins) if first else []
                first = False
        else:  # pure insertion at i1: into the run that ends at or contains i1
            host = next(((e, a) for e, a, b in segs if e is not None and a <= i1 <= b), None)
            if host is None:
                return False
            e, a = host
            texts[id(e)][i1 - a : i1 - a] = list(ins)
    for e, _, _ in segs:
        if e is not None:
            t = "".join(texts[id(e)])
            if t != (e.text or ""):
                e.text = t
                e.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return _para_text(p) == new


def write_fixed(src: str, out: str, contexts: list[Any] | None = None, unsafe: bool = False) -> list[Fix]:
    """Apply fixes to a copy of ``src`` written to ``out``; repeats until nothing applies
    (one fix per paragraph per pass). Returns the fixes applied."""
    import shutil
    import zipfile

    from lxml import etree

    from .core import lint_path
    from .reader import _W

    if Path(out).resolve() == Path(src).resolve():
        raise ValueError("refusing to overwrite the template itself; give another output path")
    shutil.copyfile(src, out)
    applied: list[Fix] = []
    for _ in range(10):
        rep = lint_path(out, contexts=contexts)
        todo = [f for f in suggest(rep, contexts) if f.safe or unsafe]
        with zipfile.ZipFile(out) as zf:
            files = {i.filename: zf.read(i.filename) for i in zf.infolist()}
            infos = zf.infolist()
        parts = _part_names(list(files))
        roots: dict[str, Any] = {}
        done_paras: set[tuple[str, int]] = set()
        progress: list[Fix] = []
        for fx in todo:
            loc = fx.location or fx.issue.location
            key = (loc.part, loc.paragraph)
            name = parts.get(loc.part)
            if name is None or key in done_paras:
                continue
            root = roots.setdefault(name, etree.fromstring(files[name]))
            paras = list(root.iter(f"{_W}p"))
            if not 0 < loc.paragraph <= len(paras):
                continue
            if _apply_in_runs(paras[loc.paragraph - 1], fx.old, fx.new):
                done_paras.add(key)
                progress.append(fx)
        if not progress:
            break
        for name, root in roots.items():
            files[name] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
        tmp = Path(out).with_suffix(".tmp.docx")
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
            for i in infos:
                zo.writestr(i, files[i.filename])
        before = len(rep.issues)
        after = len(lint_path(tmp, contexts=contexts).issues)
        if after >= before:  # a fix that does not reduce the findings is not kept
            tmp.unlink()
            break
        tmp.replace(out)
        applied += progress
    return applied
