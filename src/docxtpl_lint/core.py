"""Tag extraction and lint rules.

Pipeline per document part (body, each header/footer, footnotes):

1. :func:`scan_tags` turns paragraph text into a list of :class:`Tag` objects
   (DTL001/DTL002) and skips ``{% raw %}`` sections.
2. :func:`check_blocks` checks if/for/... balance with its own stack, so every
   problem is reported, not just the first one (DTL101/DTL102).
3. :func:`check_docxtpl_tags` checks docxtpl's ``{%p/tr/tc/r %}`` tags (DTL2xx).
4. :func:`check_syntax` runs the real Jinja2 parser when the blocks balance (DTL103).
5. :func:`analyse` walks the Jinja2 AST to find data paths, used for
   ``--list-vars`` and the ``--data`` checks (DTL3xx).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .messages import RULES, help_url, render
from .reader import CellPos, Paragraph, iter_paragraphs

# ---------------------------------------------------------------- data model


@dataclass(frozen=True)
class Location:
    """Where an issue is. ``paragraph`` counts every paragraph of the part (1-based);
    ``cells`` is the table path, outermost first; ``column`` is a 1-based character
    offset inside the paragraph text."""

    file: str
    part: str
    paragraph: int
    cells: tuple[CellPos, ...] = ()
    cell_paragraph: int = 0
    column: int = 0

    def human(self, lang: str = "en") -> str:
        if self.part == "data":
            return "data"
        s = f"{self.part} ¶{self.paragraph}"
        if self.cells:
            if lang == "zh":
                path = " > ".join(f"表{c.table} 行{c.row} 列{c.col}" for c in self.cells)
            else:
                path = " > ".join(f"T{c.table} R{c.row} C{c.col}" for c in self.cells)
            s += f" [{path} ¶{self.cell_paragraph}]"
        return s

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["cells"] = [asdict(c) for c in self.cells]
        return d


@dataclass(frozen=True)
class Issue:
    rule: str
    location: Location
    snippet: str = ""
    params: dict[str, Any] = field(default_factory=dict, compare=False)

    @property
    def severity(self) -> str:
        return RULES[self.rule].severity

    def message_for(self, lang: str = "en") -> str:
        return render(self.rule, self.params, lang)

    @property
    def message(self) -> str:
        return self.message_for("en")

    def to_dict(self, lang: str = "en") -> dict[str, Any]:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message_for(lang),
            "location": self.location.to_dict(),
            "snippet": self.snippet,
            "help_url": help_url(self.rule),
        }


@dataclass
class Tag:
    kind: str  # "stmt" | "expr" | "comment"
    prefix: str  # "", "p", "tr", "tc", "r"
    body: str  # inner text without delimiters/prefix
    raw: str
    para: Paragraph
    col: int
    spaced: bool = False  # `{% tr ... %}` (invalid, reported by DTL202)


@dataclass
class Report:
    file: str
    issues: list[Issue] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)
    disabled: set[str] = field(default_factory=set)
    # paragraph texts per part, for --context (not serialised)
    paragraphs: dict[str, list[Paragraph]] = field(default_factory=dict, repr=False)

    def context(self, loc: Location, n: int) -> list[Paragraph]:
        """``n`` paragraphs before and after ``loc`` (same part)."""
        paras = self.paragraphs.get(loc.part, [])
        if n <= 0 or loc.paragraph <= 0:
            return []
        lo, hi = max(1, loc.paragraph - n), min(len(paras), loc.paragraph + n)
        return paras[lo - 1 : hi]


def _loc(file: str, p: Paragraph, col: int = 0) -> Location:
    return Location(file, p.part, p.index, p.cells, p.cell_para, col)


def _where(tg: Tag) -> str:
    return _loc("", tg.para, tg.col).human()


# ---------------------------------------------------------------- tag scanning

_OPEN = {"{{": ("}}", "expr"), "{%": ("%}", "stmt"), "{#": ("#}", "comment")}
_PREFIX_RE = re.compile(r"^(tr|tc|p|r) ")
_SPACED_RE = re.compile(r"^-?\s+(tr|tc|p|r) ")
_ENDRAW_RE = re.compile(r"\{%-?\s*endraw\s*-?%\}")
_DISABLE_RE = re.compile(r"^\s*docxtpl-lint:\s*disable\s*=\s*([A-Z0-9_,\s]+?)\s*$")

# docxtpl cell tags rewritten by patch_xml before Jinja sees the template
CELL_TAGS = {"cellbg", "colspan", "vm", "hm"}
# patch_xml replaces Word's smart quotes inside tags with plain ones
_SMART_QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})
BLOCKS = {"if", "for", "with", "macro", "call", "filter", "block", "set_block", "autoescape"}
MIDDLE = {"elif": {"if"}, "else": {"if", "for"}}
JINJA_GLOBALS = {"range", "lipsum", "dict", "cycler", "joiner", "namespace", "loop", "caller", "varargs", "kwargs"}


def _strip_ws_control(s: str) -> str:
    s = s.strip()
    if s[:1] in "-+":
        s = s[1:]
    if s[-1:] in "-+":
        s = s[:-1]
    return s.strip()


def scan_tags(file: str, paras: list[Paragraph], issues: list[Issue]) -> list[Tag]:
    """Extract Jinja tags from the paragraphs of one part.

    A tag that is not closed in its paragraph is continued into the next
    paragraphs (docxtpl's ``patch_xml`` merges such paragraphs). If it closes
    later, DTL002 (warning) is reported; if it never closes, DTL001 (error).
    """
    tags: list[Tag] = []
    opener = re.compile(r"\{[{%#]")
    carry: tuple[str, Paragraph, int] | None = None  # pending text, start paragraph, start column
    in_raw = False
    for p in paras:
        prev, carry = carry, None
        offset = len(prev[0]) if prev else 0
        t = (prev[0] if prev else "") + p.text
        i = 0
        if in_raw:
            m_end = _ENDRAW_RE.search(t)
            if not m_end:
                continue
            in_raw, i = False, m_end.end()
        while True:
            m = opener.search(t, i)
            if not m:
                break
            start = m.start()
            close, kind = _OPEN[m.group()]
            end = t.find(close, m.end())
            if prev is not None and start == 0:
                tag_para, tag_col = prev[1], prev[2]
            else:
                tag_para, tag_col = p, start + 1 - offset
            if end < 0:
                carry = (t[start:], tag_para, tag_col)
                break
            if tag_para is not p:
                issues.append(
                    Issue(
                        "DTL002",
                        _loc(file, tag_para, tag_col),
                        t[start : end + 2][:80],
                        {"open": m.group(), "end_para": p.index},
                    )
                )
            inner = t[m.end() : end]
            prefix, spaced = "", False
            pm = _PREFIX_RE.match(inner)
            if not pm and kind == "stmt":
                pm = _SPACED_RE.match(inner)
                spaced = pm is not None
            if pm and (kind != "comment" or pm.group(1) != "r"):
                prefix = pm.group(1)
                inner = inner[pm.end() :]
            body = _strip_ws_control(inner)
            if kind != "comment":
                body = body.translate(_SMART_QUOTES)
            i = end + 2
            if kind == "stmt" and not prefix and body == "raw":
                m_end = _ENDRAW_RE.search(t, i)
                if m_end:
                    i = m_end.end()
                    continue
                in_raw = True
                break
            tags.append(Tag(kind, prefix, body, t[start:i], tag_para, tag_col, spaced))
    if carry is not None:
        text, cp, ccol = carry
        issues.append(Issue("DTL001", _loc(file, cp, ccol), text[:60], {"open": text[:2], "close": _OPEN[text[:2]][0]}))
    return tags


def disabled_rules(tags: list[Tag]) -> set[str]:
    """File-level suppression: ``{# docxtpl-lint: disable=DTL301,DTL302 #}`` anywhere."""
    out: set[str] = set()
    for tg in tags:
        if tg.kind == "comment":
            m = _DISABLE_RE.match(tg.body)
            if m:
                out |= {x.strip() for x in m.group(1).split(",") if x.strip()}
    return out


# ---------------------------------------------------------------- DTL1xx block balance


def _keyword(tg: Tag) -> str:
    words = tg.body.split()
    if not words:
        return ""
    kw = words[0]
    if kw == "set" and "=" not in tg.body:
        return "set_block"
    if kw == "endset":
        return "endset_block"
    return kw


def check_blocks(file: str, tags: list[Tag]) -> list[Issue]:
    issues: list[Issue] = []
    stack: list[tuple[str, Tag]] = []
    for tg in tags:
        if tg.kind != "stmt":
            continue
        kw = _keyword(tg)
        if kw in BLOCKS:
            stack.append((kw, tg))
        elif kw in MIDDLE:
            if not stack or stack[-1][0] not in MIDDLE[kw]:
                issues.append(Issue("DTL102", _loc(file, tg.para, tg.col), tg.raw, {"raw": tg.raw}))
        elif kw.startswith("end"):
            want = "set_block" if kw == "endset_block" else kw[3:]
            if stack and stack[-1][0] == want:
                stack.pop()
            elif any(k == want for k, _ in stack):
                while stack and stack[-1][0] != want:
                    issues.append(_unclosed(file, *stack.pop()))
                stack.pop()
            else:
                issues.append(Issue("DTL102", _loc(file, tg.para, tg.col), tg.raw, {"raw": tg.raw}))
    for k, open_tag in stack:
        issues.append(_unclosed(file, k, open_tag))
    return issues


def _unclosed(file: str, kw: str, tg: Tag) -> Issue:
    name = "set" if kw == "set_block" else kw
    return Issue("DTL101", _loc(file, tg.para, tg.col), tg.raw, {"kw": name})


# ---------------------------------------------------------------- DTL2xx docxtpl tags

_PREFIXED_RAW = re.compile(r"(\{%|\{\{)(tr|tc|p|r) ")
_SPACED_PREFIX = re.compile(r"\{%-?\s+(tr|tc|p|r)\s")


def check_docxtpl_tags(file: str, tags: list[Tag], paras: list[Paragraph]) -> list[Issue]:
    issues: list[Issue] = []
    for p in paras:
        # DTL201: docxtpl's patch_xml matches prefixed tags with `[^}%]*` (#644)
        for m in _PREFIXED_RAW.finditer(p.text):
            close = "%}" if m.group(1) == "{%" else "}}"
            end = p.text.find(close, m.end())
            if end < 0:
                continue
            body = p.text[m.end() : end]
            if "%" in body or "}" in body:
                issues.append(
                    Issue(
                        "DTL201",
                        _loc(file, p, m.start() + 1),
                        p.text[m.start() : end + 2],
                        {"prefix": m.group(1) + m.group(2)},
                    )
                )
        # DTL202: "{% tr for ... %}"
        for m in _SPACED_PREFIX.finditer(p.text):
            end = p.text.find("%}", m.start())
            issues.append(
                Issue(
                    "DTL202",
                    _loc(file, p, m.start() + 1),
                    p.text[m.start() : end + 2] if end >= 0 else m.group(0),
                    {"prefix": m.group(1)},
                )
            )

    for tg in tags:
        # DTL209: patch_xml replaces the whole paragraph/row/cell with the bare tag
        if tg.prefix in ("p", "tr", "tc") and (tg.kind == "stmt" or tg.prefix == "p") and tg.raw in tg.para.text:
            rest = tg.para.text.replace(tg.raw, "", 1).strip()
            if rest:
                unit = {"p": "paragraph", "tr": "table row", "tc": "table cell"}[tg.prefix]
                issues.append(
                    Issue(
                        "DTL209", _loc(file, tg.para, tg.col), tg.raw, {"raw": tg.raw, "rest": rest[:40], "unit": unit}
                    )
                )
        if tg.kind == "stmt" and _keyword(tg) in CELL_TAGS and not tg.para.cells:
            issues.append(Issue("DTL208", _loc(file, tg.para, tg.col), tg.raw, {"raw": tg.raw}))
        if tg.prefix in ("tr", "tc") and not tg.para.cells:
            issues.append(Issue("DTL203", _loc(file, tg.para, tg.col), tg.raw, {"raw": tg.raw, "prefix": tg.prefix}))

    stack: list[tuple[str, Tag]] = []
    for tg in tags:
        if tg.kind != "stmt":
            continue
        kw = _keyword(tg)
        if kw in BLOCKS:
            stack.append((kw, tg))
            continue
        if not kw.startswith("end"):
            continue
        want = "set_block" if kw == "endset_block" else kw[3:]
        idx = next((i for i in range(len(stack) - 1, -1, -1) if stack[i][0] == want), None)
        if idx is None:
            continue  # DTL102
        op = stack[idx][1]
        del stack[idx:]
        if op.spaced or tg.spaced:
            continue  # DTL202 already explains it
        issues.extend(_pair_issues(file, op, tg))
    # a row already reported by DTL206 (render fails) needs no extra DTL209
    rows206 = {(i.location.part, i.params["table"], i.params["row"]) for i in issues if i.rule == "DTL206"}
    return [
        i
        for i in issues
        if not (
            i.rule == "DTL209"
            and i.location.cells
            and (i.location.part, i.location.cells[-1].table, i.location.cells[-1].row) in rows206
        )
    ]


def _pair_issues(file: str, op: Tag, cl: Tag) -> list[Issue]:
    loc = _loc(file, cl.para, cl.col)
    base = {"open_raw": op.raw, "close_raw": cl.raw}
    if op.prefix != cl.prefix:
        return [
            Issue(
                "DTL204",
                loc,
                cl.raw,
                {
                    **base,
                    "open_loc": _where(op),
                    "_open_paragraph": op.para.index,
                    "_open_part": op.para.part,
                    "open_prefix": op.prefix or "-",
                    "close_prefix": cl.prefix or "-",
                },
            )
        ]
    if op.prefix not in ("tr", "tc") or not op.para.cells or not cl.para.cells:
        return []
    oc, cc = op.para.cells[-1], cl.para.cells[-1]
    same_table = (op.para.part, len(op.para.cells), oc.table) == (cl.para.part, len(cl.para.cells), cc.table)
    if op.prefix == "tr":
        if not same_table:
            return [Issue("DTL205", loc, cl.raw, {**base, "t1": oc.table, "t2": cc.table})]
        if oc.row == cc.row:
            return [Issue("DTL206", loc, cl.raw, {**base, "table": oc.table, "row": oc.row})]
    elif not same_table or oc.row != cc.row:
        return [Issue("DTL207", loc, cl.raw, base)]
    return []


# ---------------------------------------------------------------- DTL103 syntax


def build_jinja_source(tags: list[Tag]) -> tuple[str, list[Tag]]:
    """One tag per line so jinja's ``lineno`` maps back to a :class:`Tag`."""
    lines: list[str] = []
    kept: list[Tag] = []
    for tg in tags:
        if tg.kind == "comment":
            continue
        if tg.kind == "stmt" and _keyword(tg) in CELL_TAGS:
            expr = tg.body.split(None, 1)[1] if len(tg.body.split(None, 1)) > 1 else ""
            if not expr:
                continue
            lines.append("{{ " + expr + " }}")  # analyse cellbg/colspan expressions
        else:
            lines.append(("{% " + tg.body + " %}") if tg.kind == "stmt" else ("{{ " + tg.body + " }}"))
        kept.append(tg)
    return "\n".join(lines), kept


def _env() -> Any:
    from jinja2 import Environment

    # Same as docxtpl's default: no `do` / `loopcontrols` extensions.
    return Environment()


def check_syntax(file: str, tags: list[Tag]) -> list[Issue]:
    from jinja2 import TemplateSyntaxError

    src, kept = build_jinja_source(tags)
    if not kept:
        return []
    try:
        _env().parse(src)
    except TemplateSyntaxError as exc:
        ln = (exc.lineno or 0) - 1
        if 0 <= ln < len(kept):
            tg = kept[ln]
            return [Issue("DTL103", _loc(file, tg.para, tg.col), tg.raw, {"msg": exc.message})]
        # error at end of input: no reliable tag position, report at part level
        return [Issue("DTL103", Location(file, kept[0].para.part, 0), "", {"msg": exc.message})]
    return []


# ---------------------------------------------------------------- AST analysis


@dataclass
class Analysis:
    uses: list[tuple[str, Tag]] = field(default_factory=list)  # data paths, loop items as `x[]`
    guarded: set[str] = field(default_factory=set)  # `is defined` / `| default` paths
    iterables: list[tuple[str, Tag]] = field(default_factory=list)  # `for … in <path>`
    numeric: set[str] = field(default_factory=set)  # input of round/int/float/abs or compared with a number
    mappings: set[str] = field(default_factory=set)  # receiver of .items()/.keys()/.values()
    # plain `{{ path }}` outputs: (path, tag, conditional) — conditional if inside if/else/for-else/x if y else z
    outputs: list[tuple[str, Tag, bool]] = field(default_factory=list)


NUMERIC_FILTERS = {"round", "int", "float", "abs", "filesizeformat"}
MAPPING_METHODS = {"items", "keys", "values"}


def _is_guard(n: Any) -> bool:
    from jinja2 import nodes

    if isinstance(n, nodes.Test):
        return n.name in ("defined", "undefined", "none")
    return isinstance(n, nodes.Filter) and n.name in ("default", "d") and n.node is not None


def analyse(tags: list[Tag]) -> Analysis:
    """Find every free data path used by the template.

    Locals (``set``, ``with``, loop targets, macros, imports) are excluded and
    loop variables are resolved to their iterable: ``{% for i in items %}{{ i.x }}``
    yields ``items`` and ``items[].x``.
    """
    from jinja2 import nodes

    res = Analysis()
    src, kept = build_jinja_source(tags)
    if not kept:
        return res
    try:
        ast = _env().parse(src)
    except Exception:
        # Broken template: analyse each {{ expression }} on its own (no scoping),
        # so --list-vars still works on templates with errors.
        if len(kept) > 1:
            for tg in kept:
                if tg.kind == "expr":
                    sub = analyse([tg])
                    res.uses += sub.uses
                    res.guarded |= sub.guarded
        return res

    def path_of(n: nodes.Node, scope: dict[str, str | None]) -> str | None:
        if isinstance(n, nodes.Name):
            return scope.get(n.name, n.name)
        if isinstance(n, nodes.Getattr):
            base = path_of(n.node, scope)
            return f"{base}.{n.attr}" if base else None
        if isinstance(n, nodes.Getitem) and isinstance(n.arg, nodes.Const):
            base = path_of(n.node, scope)
            if not base:
                return None
            if isinstance(n.arg.value, str):
                return f"{base}.{n.arg.value}"
            if isinstance(n.arg.value, int) and not isinstance(n.arg.value, bool):
                return f"{base}[]"  # items[0].x -> items[].x
            return None
        return None

    def tag_for(n: nodes.Node) -> Tag:
        return kept[min(max(n.lineno - 1, 0), len(kept) - 1)]

    def names(t: nodes.Node) -> list[str]:
        return [t.name] if isinstance(t, nodes.Name) else [x.name for x in t.find_all(nodes.Name)]

    depth = [0]  # >0 while inside a conditional branch

    def visit(n: nodes.Node, scope: dict[str, str | None]) -> None:
        if isinstance(n, nodes.Filter) and n.name in NUMERIC_FILTERS and n.node is not None:
            fp = path_of(n.node, scope)
            if fp:
                res.numeric.add(fp)
        if isinstance(n, nodes.Compare):
            sides = [n.expr, *(o.expr for o in n.ops)]
            if any(
                isinstance(x, nodes.Const) and isinstance(x.value, int | float) and not isinstance(x.value, bool)
                for x in sides
            ):
                for x in sides:
                    cp = path_of(x, scope)
                    if cp:
                        res.numeric.add(cp)
        if isinstance(n, nodes.Mul | nodes.Div | nodes.FloorDiv | nodes.Mod | nodes.Sub | nodes.Pow | nodes.Neg):
            for x in n.iter_child_nodes():
                ap = path_of(x, scope)
                if ap:
                    res.numeric.add(ap)
        if isinstance(n, nodes.Output):
            for c in n.nodes:
                if isinstance(c, nodes.Name | nodes.Getattr | nodes.Getitem):
                    op_ = path_of(c, scope)
                    if op_:
                        res.outputs.append((op_, tag_for(c), depth[0] > 0))
        if isinstance(n, nodes.If):
            visit(n.test, scope)
            depth[0] += 1
            for c in [*n.body, *n.elif_, *n.else_]:
                visit(c, scope)
            depth[0] -= 1
            return
        if isinstance(n, nodes.CondExpr):
            depth[0] += 1
            for c in n.iter_child_nodes():
                visit(c, scope)
            depth[0] -= 1
            return
        if _is_guard(n):
            gp = path_of(n.node, scope)  # type: ignore[attr-defined]
            if gp:
                res.guarded.add(gp)
        if isinstance(n, nodes.For):
            visit(n.iter, scope)
            it = path_of(n.iter, scope)
            if it and isinstance(n.iter, nodes.Name | nodes.Getattr | nodes.Getitem):
                res.iterables.append((it, tag_for(n)))
            inner = dict(scope)
            inner["loop"] = None
            if isinstance(n.target, nodes.Name):
                inner[n.target.name] = f"{it}[]" if it else None
            else:
                for nm in names(n.target):
                    inner[nm] = None
            if n.test is not None:
                visit(n.test, inner)
                depth[0] += 1  # `for x in xs if cond`: items may be filtered out
            for c in n.body:
                visit(c, inner)
            if n.test is not None:
                depth[0] -= 1
            depth[0] += 1
            for c in n.else_:
                visit(c, scope)
            depth[0] -= 1
            return
        if isinstance(n, nodes.Assign | nodes.AssignBlock):
            if isinstance(n, nodes.Assign):
                visit(n.node, scope)
            else:
                for c in n.body:
                    visit(c, scope)
            for nm in names(n.target):
                scope[nm] = None
            return
        if isinstance(n, nodes.With):
            inner = dict(scope)
            for t, v in zip(n.targets, n.values, strict=False):
                visit(v, scope)
                for nm in names(t):
                    inner[nm] = None
            for c in n.body:
                visit(c, inner)
            return
        if isinstance(n, nodes.Macro):
            scope[n.name] = None
            inner = dict(scope)
            for a in n.args:
                inner[a.name] = None
            for c in n.body:
                visit(c, inner)
            return
        if isinstance(n, nodes.CallBlock):
            visit(n.call, scope)
            inner = dict(scope)
            for a in n.args:
                inner[a.name] = None
            for c in n.body:
                visit(c, inner)
            return
        if isinstance(n, nodes.Import):
            scope[n.target] = None
            return
        if isinstance(n, nodes.FromImport):
            for nm in n.names:
                scope[nm[1] if isinstance(nm, tuple) else nm] = None
            return
        if isinstance(n, nodes.Name) and n.ctx == "load" and n.name in scope and scope[n.name] is None:
            return
        if isinstance(n, nodes.Call) and isinstance(n.node, nodes.Getattr):
            # method call such as `m.items()`: only the receiver is data
            if n.node.attr in MAPPING_METHODS:
                mp = path_of(n.node.node, scope)
                if mp:
                    res.mappings.add(mp)
            visit(n.node.node, scope)
            for c in [*n.args, *n.kwargs]:
                visit(c, scope)
            return
        if isinstance(n, nodes.Name) and n.name in JINJA_GLOBALS and n.name not in scope:
            return
        if isinstance(n, nodes.Getattr | nodes.Getitem | nodes.Name) and getattr(n, "ctx", "load") == "load":
            p = path_of(n, scope)
            if p is not None:
                res.uses.append((p, tag_for(n)))
                if isinstance(n, nodes.Getitem):
                    visit(n.arg, scope)
                return
        for c in n.iter_child_nodes():
            visit(c, scope)

    visit(ast, {})
    return res


# ---------------------------------------------------------------- DTL3xx data contract


def _resolve(data: Any, path: str) -> list[Any] | None:
    """Values at ``path`` (``[]`` = every list item). ``None`` if provably absent;
    an empty list if absence cannot be proven (e.g. an empty list on the way)."""
    cur: list[Any] = [data]
    for part in path.split("."):
        is_list = part.endswith("[]")
        key = part[:-2] if is_list else part
        nxt = [c[key] for c in cur if isinstance(c, dict) and key in c]
        if not nxt:
            return None if cur else []
        if is_list:
            nxt = [x for v in nxt if isinstance(v, list) for x in v] + [v for v in nxt if isinstance(v, dict)]
            if not nxt:
                return []
        cur = nxt
    return cur


def _type_name(v: Any) -> str:
    return {str: "string", int: "number", float: "number", bool: "boolean", type(None): "null"}.get(
        type(v), type(v).__name__
    )


def check_data(file: str, an: Analysis, contexts: list[Any], report_unused: bool = False) -> list[Issue]:
    """DTL301/303 (and DTL302 if ``report_unused``) against one or more sample contexts.

    With several contexts (e.g. one shared JSON per customer type) a path is only
    reported as missing if it is missing from *all* of them.
    """
    issues: list[Issue] = []
    seen: set[str] = set()
    roots: set[str] = set()
    for path, tg in an.uses:
        roots.add(path.split(".")[0].removesuffix("[]"))
        if path in seen or any(path == g or path.startswith(g + ".") for g in an.guarded):
            continue
        seen.add(path)
        if all(_resolve(d, path) is None for d in contexts):
            issues.append(Issue("DTL301", _loc(file, tg.para, tg.col), tg.raw, {"path": path.replace("[]", "[*]")}))
    for path, tg in an.iterables:
        if path in an.guarded:
            continue
        vals = [v for d in contexts for v in (_resolve(d, path) or [])]
        # strings are iterable (per character) in Jinja, so only flag numbers/booleans/null
        bad = [v for v in vals if v is None or isinstance(v, bool | int | float)]
        if bad:
            issues.append(
                Issue(
                    "DTL303",
                    _loc(file, tg.para, tg.col),
                    tg.raw,
                    {"path": path.replace("[]", "[*]"), "type": _type_name(bad[0])},
                )
            )
    if report_unused:
        keys = dict.fromkeys(k for d in contexts if isinstance(d, dict) for k in d)
        for key in keys:
            if key not in roots:
                issues.append(Issue("DTL302", Location(file, "data", 0), "", {"key": key}))
    return issues


# ---------------------------------------------------------------- entry


def lint_path(
    path: str | Path,
    data: Any = None,
    *,
    contexts: list[Any] | None = None,
    allow_cross_paragraph: bool = False,
    report_unused_data: bool = False,
    schema: dict[str, Any] | None = None,
) -> Report:
    """Lint one ``.docx`` template.

    ``data`` is an optional sample context (parsed JSON); ``contexts`` allows
    several. Either enables the DTL3xx data checks.
    """
    file = str(path)
    paras = list(iter_paragraphs(path))
    issues: list[Issue] = []
    tags: list[Tag] = []
    parts = list(dict.fromkeys(p.part for p in paras))
    for part in parts:
        part_paras = [p for p in paras if p.part == part]
        part_tags = scan_tags(file, part_paras, issues)
        tags.extend(part_tags)
        block = check_blocks(file, part_tags)
        issues.extend(block)
        issues.extend(check_docxtpl_tags(file, part_tags, part_paras))
        if not block:
            issues.extend(check_syntax(file, part_tags))
    order = {p: i for i, p in enumerate(parts)}
    issues.sort(key=lambda i: (order.get(i.location.part, 99), i.location.paragraph, i.location.column))
    an = analyse(tags)
    ctxs = list(contexts or []) + ([data] if data is not None else [])
    if ctxs:
        issues.extend(check_data(file, an, ctxs, report_unused_data))
    if schema is not None:
        from .contract import check_schema

        issues.extend(check_schema(file, an, schema))
    disabled = disabled_rules(tags)
    if allow_cross_paragraph:
        disabled.add("DTL002")
    rep = Report(file, [i for i in issues if i.rule not in disabled], disabled=disabled)
    for p in paras:
        rep.paragraphs.setdefault(p.part, []).append(p)
    rep.variables = sorted({p for p, _ in an.uses})
    return rep


def template_tags(path: str | Path) -> tuple[list[Paragraph], list[Tag]]:
    """Paragraphs and Jinja tags of a template (issues discarded)."""
    paras = list(iter_paragraphs(path))
    tags: list[Tag] = []
    for part in dict.fromkeys(p.part for p in paras):
        tags.extend(scan_tags(str(path), [p for p in paras if p.part == part], []))
    return paras, tags


def load_data(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))
