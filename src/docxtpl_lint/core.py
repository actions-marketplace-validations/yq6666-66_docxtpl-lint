"""Tag extraction and lint rules."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .reader import CellPos, Paragraph, iter_paragraphs

# ---------------------------------------------------------------- data model


@dataclass(frozen=True)
class Location:
    file: str
    part: str
    paragraph: int
    cells: tuple[CellPos, ...] = ()
    cell_paragraph: int = 0
    column: int = 0  # 1-based char offset inside paragraph text

    def human(self) -> str:
        if self.part == "data":
            return "data"
        s = f"{self.part} ¶{self.paragraph}"
        if self.cells:
            path = " > ".join(f"表{c.table} 行{c.row} 列{c.col}" for c in self.cells)
            s += f" [{path} ¶{self.cell_paragraph}]"
        return s

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["cells"] = [asdict(c) for c in self.cells]
        return d


@dataclass(frozen=True)
class Issue:
    rule: str
    severity: str  # "error" | "warning"
    message: str
    location: Location
    snippet: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
            "location": self.location.to_dict(),
            "snippet": self.snippet,
        }


@dataclass
class Tag:
    kind: str  # "stmt" | "expr" | "comment"
    prefix: str  # "", "p", "tr", "tc", "r"
    body: str  # inner text without delimiters/prefix
    raw: str
    para: Paragraph
    col: int


@dataclass
class Report:
    file: str
    issues: list[Issue] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- tag scanning

_OPEN = {"{{": ("}}", "expr"), "{%": ("%}", "stmt"), "{#": ("#}", "comment")}
_PREFIX_RE = re.compile(r"^(tr|tc|p|r) ")
BLOCKS = {"if", "for", "with", "macro", "call", "filter", "block", "raw", "set_block"}
JINJA_GLOBALS = {"range", "lipsum", "dict", "cycler", "joiner", "namespace", "loop"}
MIDDLE = {"elif": {"if"}, "else": {"if", "for"}}


def _loc(file: str, p: Paragraph, col: int = 0) -> Location:
    return Location(file, p.part, p.index, p.cells, p.cell_para, col)


def scan_tags(file: str, paras: list[Paragraph], issues: list[Issue]) -> list[Tag]:
    """Extract Jinja tags paragraph by paragraph (DTL001: unterminated tag in paragraph)."""
    tags: list[Tag] = []
    opener = re.compile(r"\{[{%#]")
    for p in paras:
        t = p.text
        i = 0
        while True:
            m = opener.search(t, i)
            if not m:
                break
            start = m.start()
            close, kind = _OPEN[m.group()]
            end = t.find("%}", m.end()) if kind == "stmt" and close == "%}" else t.find(close, m.end())
            if end < 0:
                issues.append(
                    Issue(
                        "DTL001",
                        "error",
                        f"标签 `{m.group()}` 在本段内没有闭合 `{close}` / "
                        f"tag `{m.group()}` not closed within the paragraph",
                        _loc(file, p, start + 1),
                        t[start : start + 60],
                    )
                )
                break
            inner = t[m.end() : end]
            prefix = ""
            pm = _PREFIX_RE.match(inner)
            if not pm and kind != "comment":
                pm = re.match(r"^-?\s+(tr|tc) ", inner)  # `{% tr for %}`: reported by DTL202
            if pm and (kind != "comment" or pm.group(1) != "r"):
                prefix = pm.group(1)
                inner = inner[pm.end() :]
            tags.append(Tag(kind, prefix, inner.strip(" -+"), t[start : end + 2], p, start + 1))
            i = end + 2
    return tags


# ---------------------------------------------------------------- DTL1xx block balance


def check_blocks(file: str, tags: list[Tag]) -> list[Issue]:
    issues: list[Issue] = []
    stack: list[tuple[str, Tag]] = []
    for tg in tags:
        if tg.kind != "stmt":
            continue
        words = tg.body.split()
        if not words:
            continue
        kw = words[0]
        if kw == "set" and "=" not in tg.body:
            kw = "set_block"
        if kw in BLOCKS:
            stack.append((kw, tg))
        elif kw in MIDDLE:
            if not stack or stack[-1][0] not in MIDDLE[kw]:
                issues.append(
                    Issue(
                        "DTL102",
                        "error",
                        f"`{{% {kw} %}}` 不在任何 {'/'.join(sorted(MIDDLE[kw]))} 块内 / "
                        f"`{kw}` outside of a matching block",
                        _loc(file, tg.para, tg.col),
                        tg.raw,
                    )
                )
        elif kw.startswith("end"):
            want = kw[3:]
            if want == "set":
                want = "set_block"
            if stack and stack[-1][0] == want:
                stack.pop()
                continue
            if any(k == want for k, _ in stack):
                # close inner unclosed blocks, report them
                while stack and stack[-1][0] != want:
                    k, open_tag = stack.pop()
                    issues.append(_unclosed(file, k, open_tag, f"在 `{tg.raw}` 之前 / before `{tg.raw}`"))
                stack.pop()
            else:
                issues.append(
                    Issue(
                        "DTL102",
                        "error",
                        f"`{tg.raw}` 没有对应的开始标签 / has no matching opening tag",
                        _loc(file, tg.para, tg.col),
                        tg.raw,
                    )
                )
    for k, open_tag in stack:
        issues.append(_unclosed(file, k, open_tag, "直到文档末尾 / until end of part"))
    return issues


def _unclosed(file: str, kw: str, tg: Tag, where: str) -> Issue:
    name = "set" if kw == "set_block" else kw
    return Issue(
        "DTL101",
        "error",
        f"`{{% {name} %}}` 未闭合，缺少 `{{% end{name} %}}`（{where}）/ unclosed block",
        _loc(file, tg.para, tg.col),
        tg.raw,
    )


# ---------------------------------------------------------------- DTL2xx docxtpl placement

_SPACED_PREFIX = re.compile(r"\{[%{]-?\s+(tr|tc)\s")
_PREFIXED_RAW = re.compile(r"(\{%|\{\{)(tr|tc|p|r) ")


def check_docxtpl_tags(file: str, tags: list[Tag], paras: list[Paragraph]) -> list[Issue]:
    issues: list[Issue] = []
    # DTL201: prefixed tag body containing % or } is silently mangled by patch_xml ([^}%]*)
    for p in paras:
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
                        "error",
                        f"`{m.group(1)}{m.group(2)} …` 表达式里含有 `%` 或 `}}`，docxtpl 的 patch_xml "
                        "会截断它（见 docxtpl #644）；请先用 {% set %} 算好再引用 / expression "
                        "contains `%` or `}` which docxtpl cannot handle in prefixed tags",
                        _loc(file, p, m.start() + 1),
                        p.text[m.start() : end + 2],
                    )
                )
        # DTL202: "{% tr for ...%}" — space before prefix means docxtpl treats it as plain jinja
        for m in _SPACED_PREFIX.finditer(p.text):
            issues.append(
                Issue(
                    "DTL202",
                    "error",
                    f"`{m.group(0).strip()}` 中 `{m.group(1)}` 前不能有空格，应写成 "
                    f"`{{%{m.group(1)} …`，否则 Jinja 会报 unknown tag / no space allowed before "
                    f"the `{m.group(1)}` prefix",
                    _loc(file, p, m.start() + 1),
                    p.text[m.start() : p.text.find("%}", m.start()) + 2] or m.group(0),
                )
            )

    # DTL203: tr/tc tags must live inside a table
    for tg in tags:
        if tg.prefix in ("tr", "tc") and not tg.para.cells:
            issues.append(
                Issue(
                    "DTL203",
                    "error",
                    f"`{tg.raw}` 使用了 {tg.prefix} 前缀，但不在表格单元格中 / "
                    f"`{tg.prefix}` tag must be placed inside a table cell",
                    _loc(file, tg.para, tg.col),
                    tg.raw,
                )
            )

    # DTL204/205/206: pairing of prefixed block tags
    stack: list[tuple[str, Tag]] = []
    for tg in tags:
        if tg.kind != "stmt" or not tg.body.split():
            continue
        kw = tg.body.split()[0]
        if kw in BLOCKS:
            stack.append((kw, tg))
        elif kw.startswith("end"):
            want = kw[3:]
            idx = next((i for i in range(len(stack) - 1, -1, -1) if stack[i][0] == want), None)
            if idx is None:
                continue  # reported by DTL102
            _, op = stack[idx]
            del stack[idx:]
            if op.prefix != tg.prefix:
                issues.append(
                    Issue(
                        "DTL204",
                        "error",
                        f"开始标签 `{op.raw}`（{op.para.part} ¶{op.para.index}）与结束标签 "
                        f"`{tg.raw}` 的前缀不一致（{op.prefix or '无'} vs {tg.prefix or '无'}），"
                        "docxtpl 只会删除其中一处的行/段落 / prefix mismatch between opening "
                        "and closing tag",
                        _loc(file, tg.para, tg.col),
                        tg.raw,
                    )
                )
            elif op.prefix == "tr" and op.para.cells and tg.para.cells:
                oc, cc = op.para.cells[-1], tg.para.cells[-1]
                if (op.para.part, oc.table) != (tg.para.part, cc.table):
                    issues.append(
                        Issue(
                            "DTL205",
                            "error",
                            f"`{op.raw}` 在 表{oc.table}，而 `{tg.raw}` 在 表{cc.table}；"
                            "{%tr %} 循环的开始和结束必须在同一张表 / tr block must open and "
                            "close in the same table",
                            _loc(file, tg.para, tg.col),
                            tg.raw,
                        )
                    )
                elif oc.row == cc.row:
                    issues.append(
                        Issue(
                            "DTL206",
                            "error",
                            f"`{op.raw}` 和 `{tg.raw}` 在同一行（表{oc.table} 行{oc.row}）；"
                            "docxtpl 会用第一个 tr 标签替换整行，第二个会丢失。请把它们放在不同行 / "
                            "tr open and close tags in the same row",
                            _loc(file, tg.para, tg.col),
                            tg.raw,
                        )
                    )
    return issues


# ---------------------------------------------------------------- DTL3xx data contract


def build_jinja_source(tags: list[Tag]) -> tuple[str, list[Tag]]:
    """One tag per line so jinja node.lineno maps back to a Tag."""
    lines: list[str] = []
    kept: list[Tag] = []
    for tg in tags:
        if tg.kind == "comment":
            continue
        if tg.kind == "stmt":
            lines.append("{% " + tg.body + " %}")
        else:
            lines.append("{{ " + tg.body + " }}")
        kept.append(tg)
    return "\n".join(lines), kept


def check_syntax(file: str, tags: list[Tag]) -> list[Issue]:
    from jinja2 import Environment, TemplateSyntaxError

    src, kept = build_jinja_source(tags)
    try:
        Environment(extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"]).parse(src)
    except TemplateSyntaxError as exc:
        ln = (exc.lineno or 1) - 1
        tg = kept[min(max(ln, 0), len(kept) - 1)] if kept else None
        if tg is None:
            return []
        return [
            Issue(
                "DTL103",
                "error",
                f"Jinja2 语法错误 / syntax error: {exc.message}",
                _loc(file, tg.para, tg.col),
                tg.raw,
            )
        ]
    return []


def collect_paths(tags: list[Tag]) -> list[tuple[str, Tag]]:
    """Return (dotted path, tag) for every free variable access; loop vars resolved to `x[]`."""
    from jinja2 import Environment, nodes

    src, kept = build_jinja_source(tags)
    try:
        ast = Environment(extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"]).parse(src)
    except Exception:
        return []
    out: list[tuple[str, Tag]] = []

    def path_of(n: nodes.Node, scope: dict[str, str | None]) -> str | None:
        if isinstance(n, nodes.Name):
            if n.name in scope:
                return scope[n.name]
            return n.name
        if isinstance(n, nodes.Getattr):
            base = path_of(n.node, scope)
            return f"{base}.{n.attr}" if base else None
        if isinstance(n, nodes.Getitem) and isinstance(n.arg, nodes.Const) and isinstance(n.arg.value, str):
            base = path_of(n.node, scope)
            return f"{base}.{n.arg.value}" if base else None
        return None

    def tag_for(n: nodes.Node) -> Tag:
        return kept[min(max(n.lineno - 1, 0), len(kept) - 1)]

    def names(t: nodes.Node) -> list[str]:
        if isinstance(t, nodes.Name):
            return [t.name]
        return [x.name for x in t.find_all(nodes.Name)]

    def visit(n: nodes.Node, scope: dict[str, str | None]) -> None:
        if isinstance(n, nodes.For):
            visit(n.iter, scope)
            it = path_of(n.iter, scope)
            inner = dict(scope)
            inner["loop"] = None
            if isinstance(n.target, nodes.Name):
                inner[n.target.name] = f"{it}[]" if it else None
            else:
                for nm in names(n.target):
                    inner[nm] = None
            for c in n.body + n.else_:
                visit(c, inner)
            if n.test is not None:
                visit(n.test, inner)
            return
        if isinstance(n, nodes.Assign | nodes.AssignBlock):
            if isinstance(n, nodes.Assign):
                visit(n.node, scope)
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
        if isinstance(n, nodes.Macro | nodes.CallBlock):
            return
        if isinstance(n, nodes.Name) and n.ctx == "load" and n.name in scope and scope[n.name] is None:
            return  # local variable (set / with / loop target tuple / loop)
        if isinstance(n, nodes.Call) and isinstance(n.node, nodes.Getattr):
            # method call such as `m.items()` / `name.upper()`: only the receiver is data
            visit(n.node.node, scope)
            for c in [*n.args, *n.kwargs]:
                visit(c, scope)
            return
        if isinstance(n, nodes.Name) and n.name in JINJA_GLOBALS and n.name not in scope:
            return
        if isinstance(n, nodes.Getattr | nodes.Getitem | nodes.Name) and getattr(n, "ctx", "load") == "load":
            p = path_of(n, scope)
            if p is not None:
                out.append((p, tag_for(n)))
                if isinstance(n, nodes.Getitem):
                    visit(n.arg, scope)
                return
        for c in n.iter_child_nodes():
            visit(c, scope)

    visit(ast, {})
    return out


def _lookup(data: Any, path: str) -> bool:
    cur: list[Any] = [data]
    for part in path.split("."):
        is_list = part.endswith("[]")
        key = part[:-2] if is_list else part
        nxt: list[Any] = []
        for c in cur:
            if isinstance(c, dict) and key in c:
                nxt.append(c[key])
        if not nxt:
            return False
        if is_list:
            items = [x for v in nxt if isinstance(v, list) for x in v]
            if not items:
                return True  # empty list: cannot prove absence
            nxt = items
        cur = nxt
    return True


def _data_paths(data: Any, prefix: str = "") -> set[str]:
    out: set[str] = set()
    if isinstance(data, dict):
        for k, v in data.items():
            p = f"{prefix}.{k}" if prefix else k
            out.add(p)
            out |= _data_paths(v, p)
    elif isinstance(data, list):
        for x in data:
            out |= _data_paths(x, prefix + "[]")
    return out


def check_data(file: str, tags: list[Tag], data: Any) -> list[Issue]:
    issues: list[Issue] = []
    used = collect_paths(tags)
    seen: set[str] = set()
    used_set: set[str] = set()
    for path, tg in used:
        segs = path.split(".")
        for i in range(1, len(segs) + 1):
            used_set.add(".".join(segs[:i]))
        if path in seen:
            continue
        seen.add(path)
        if not _lookup(data, path):
            issues.append(
                Issue(
                    "DTL301",
                    "error",
                    f"变量 `{path.replace('[]', '[*]')}` 在数据文件中不存在 / variable not found in data",
                    _loc(file, tg.para, tg.col),
                    tg.raw,
                )
            )
    roots = {p.split(".")[0] for p in used_set}
    if isinstance(data, dict):
        for key in data:
            if key not in roots:
                issues.append(
                    Issue(
                        "DTL302",
                        "warning",
                        f"数据字段 `{key}` 在模板中从未使用 / data key never used by template",
                        Location(file, "data", 0),
                    )
                )
    return issues


# ---------------------------------------------------------------- entry


def lint_path(path: str | Path, data: Any = None) -> Report:
    file = str(path)
    paras = list(iter_paragraphs(path))
    issues: list[Issue] = []
    tags: list[Tag] = []
    for part in dict.fromkeys(p.part for p in paras):
        part_paras = [p for p in paras if p.part == part]
        part_tags = scan_tags(file, part_paras, issues)
        tags.extend(part_tags)
        block = check_blocks(file, part_tags)
        issues.extend(block)
        issues.extend(check_docxtpl_tags(file, part_tags, part_paras))
        if not block:
            issues.extend(check_syntax(file, part_tags))
    order = {p: i for i, p in enumerate(dict.fromkeys(p.part for p in paras))}
    issues.sort(key=lambda i: (order.get(i.location.part, 99), i.location.paragraph, i.location.column))
    rep = Report(file, issues)
    rep.variables = sorted({p for p, _ in collect_paths(tags)})
    if data is not None:
        rep.issues.extend(check_data(file, tags, data))
    return rep


def load_data(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))
