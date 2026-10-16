"""Fix suggestions as unified diffs of paragraph text (``docxtpl-lint fix``).

The .docx is never rewritten: Word splits text into runs, so an automatic edit
could break formatting. Each suggestion is a small, deterministic text change;
every kind is checked in the test-suite by applying it and rendering with docxtpl.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, replace
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
        return {**loc, "rule": self.issue.rule, "old": self.old, "new": self.new, "note": self.note}


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
        if iss.rule == "DTL202":
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
        if new_raw is None or new_raw == raw:
            continue
        new = text.replace(raw, new_raw, 1)
        if not new_raw:
            new = re.sub(r"\s{2,}", " ", new).strip() if new.strip() else ""
        fixes.append(Fix(iss, text, new, note))
    return fixes
