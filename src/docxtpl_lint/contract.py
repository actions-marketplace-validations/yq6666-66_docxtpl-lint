"""Data contract of a template: JSON Schema inference, sample data, schema checks, contract diff.

A *path* is the dotted data path used by :func:`docxtpl_lint.core.analyse`
(``items[].name`` = the ``name`` of every item of the list ``items``).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .core import Analysis, Issue, Tag, _loc, analyse, template_tags

SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"


@dataclass
class Node:
    """One data path. ``kind``: any | number | array | object | mapping."""

    children: dict[str, Node] = field(default_factory=dict)
    array: bool = False
    item: Node | None = None
    numeric: bool = False
    mapping: bool = False
    optional: bool = False
    templates: set[str] = field(default_factory=set)
    tags: list[Tag] = field(default_factory=list, repr=False)

    @property
    def kind(self) -> str:
        if self.array:
            return "array"
        if self.children:
            return "object"
        if self.mapping:
            return "mapping"
        if self.numeric:
            return "number"
        return "any"


def _split(path: str) -> list[str]:
    """``a.b[].c`` -> ``["a", "b", "[]", "c"]``."""
    out: list[str] = []
    for part in path.split("."):
        if part.endswith("[]"):
            out += [part[:-2], "[]"]
        else:
            out.append(part)
    return out


def _walk(root: Node, path: str, create: bool = True) -> Node | None:
    cur = root
    for seg in _split(path):
        if seg == "[]":
            cur.array = True
            if cur.item is None:
                if not create:
                    return None
                cur.item = Node()
            cur = cur.item
        else:
            if seg not in cur.children:
                if not create:
                    return None
                cur.children[seg] = Node()
            cur = cur.children[seg]
    return cur


def build_tree(an: Analysis, template: str = "") -> Node:
    root = Node()
    for path, tg in an.uses:
        n = _walk(root, path)
        assert n is not None
        n.tags.append(tg)
        if template:
            n.templates.add(template)
    for path, _ in an.iterables:
        n = _walk(root, path)
        assert n is not None
        n.array = True
        if n.item is None:
            n.item = Node()
    for path in an.numeric:
        n = _walk(root, path)
        assert n is not None
        n.numeric = True
    for path in an.mappings:
        n = _walk(root, path)
        assert n is not None
        n.mapping = True
    for path in an.guarded:
        n = _walk(root, path)
        assert n is not None
        n.optional = True
    _propagate_templates(root, template)
    return root


def _propagate_templates(n: Node, template: str) -> None:
    if template:
        n.templates.add(template)
    for c in n.children.values():
        _propagate_templates(c, template)
    if n.item is not None:
        _propagate_templates(n.item, template)


def merge(a: Node, b: Node) -> Node:
    """Union of two contracts (a path is optional only if optional/absent in both)."""
    out = Node(
        array=a.array or b.array,
        numeric=a.numeric or b.numeric,
        mapping=a.mapping or b.mapping,
        optional=a.optional and b.optional,
        templates=a.templates | b.templates,
    )
    for k in dict.fromkeys([*a.children, *b.children]):
        if k in a.children and k in b.children:
            out.children[k] = merge(a.children[k], b.children[k])
        else:
            out.children[k] = a.children.get(k) or b.children[k]
    if a.item or b.item:
        out.item = merge(a.item or Node(), b.item or Node())
    return out


def infer_tree(paths: list[str | Path]) -> Node:
    root: Node | None = None
    for p in paths:
        _, tags = template_tags(p)
        t = build_tree(analyse(tags), Path(p).name)
        root = t if root is None else merge(root, t)
    return root or Node()


# ---------------------------------------------------------------- JSON Schema


def to_schema(root: Node, title: str = "docxtpl template data") -> dict[str, Any]:
    if len(root.templates) <= 1:
        _clear_templates(root)  # x-docxtpl-templates only helps when several templates are merged
    s = _schema(root, top=True)
    return {"$schema": SCHEMA_DIALECT, "title": title, **s}


def _clear_templates(n: Node) -> None:
    n.templates = set()
    for c in n.children.values():
        _clear_templates(c)
    if n.item is not None:
        _clear_templates(n.item)


def _schema(n: Node, top: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if n.array:
        out["type"] = "array"
        out["items"] = _schema(n.item or Node())
    elif n.children or top:
        out["type"] = "object"
        out["properties"] = {k: _schema(c) for k, c in n.children.items()}
        req = [k for k, c in n.children.items() if not c.optional]
        if req:
            out["required"] = req
    elif n.mapping:
        out["type"] = "object"
    elif n.numeric:
        out["type"] = "number"
    if n.templates and not top:
        out["x-docxtpl-templates"] = sorted(n.templates)
    return out


def sample(root: Node, items: int = 2, leaf: Any = None) -> Any:
    """Sample context that satisfies the contract. ``leaf(path)`` produces leaf values."""
    counter = [0]

    def gen(n: Node, path: str) -> Any:
        if n.array:
            return [gen(n.item or Node(), path + "[]") for _ in range(items)]
        if n.children:
            return {k: gen(c, f"{path}.{k}" if path else k) for k, c in n.children.items()}
        if n.mapping:
            return {"key": "value"}
        if n.numeric:
            return 1
        counter[0] += 1
        return leaf(path, counter[0]) if leaf else f"[{path}]"

    out = gen(root, "")
    return out if isinstance(out, dict) else {}


# ---------------------------------------------------------------- schema conformance (DTL304/305)


def _schema_at(schema: dict[str, Any], path: str) -> dict[str, Any] | None:
    cur: dict[str, Any] = schema
    for seg in _split(path):
        if seg == "[]":
            if cur.get("type") not in (None, "array"):
                return cur  # type mismatch is reported by the caller
            cur = cur.get("items", {})
        else:
            props = cur.get("properties")
            if props is None or seg not in props:
                return None
            cur = props[seg]
    return cur


def check_schema(file: str, an: Analysis, schema: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    seen: set[str] = set()
    for path, tg in an.uses:
        if path in seen or any(path == g or path.startswith(g + ".") for g in an.guarded):
            continue
        seen.add(path)
        if _schema_at(schema, path) is None:
            issues.append(Issue("DTL304", _loc(file, tg.para, tg.col), tg.raw, {"path": path.replace("[]", "[*]")}))
    for path, tg in an.iterables:
        node = _schema_at(schema, path)
        typ = node.get("type") if node else None
        if typ not in (None, "array", "string", "object"):
            issues.append(
                Issue("DTL305", _loc(file, tg.para, tg.col), tg.raw, {"path": path.replace("[]", "[*]"), "type": typ})
            )
    return issues


def load_schema(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


# ---------------------------------------------------------------- contract diff


def flatten(n: Node, path: str = "", out: dict[str, Node] | None = None) -> dict[str, Node]:
    out = {} if out is None else out
    for k, c in n.children.items():
        p = f"{path}.{k}" if path else k
        out[p] = c
        flatten(c, p, out)
    if n.item is not None:
        flatten(n.item, path + "[]" if path else "[]", out)
    return out


@dataclass
class Change:
    kind: str  # added | removed | type | optional
    path: str
    breaking: bool
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"change": self.kind, "path": self.path, "breaking": self.breaking, "detail": self.detail}


def diff(old: Node, new: Node) -> list[Change]:
    """How the data contract changed from ``old`` to ``new`` (seen from the data producer).

    New required path: breaking (producers must supply it). Removed path: not breaking.
    Kind change between known kinds (array/object/number): breaking. Required -> optional
    is not breaking, optional -> required is.
    """
    fo, fn = flatten(old), flatten(new)
    out: list[Change] = []
    removed = [p for p in fo if p not in fn]
    for p, n in fn.items():
        if p not in fo:
            parent_present = ("." not in p and "[]" not in p) or p.rsplit(".", 1)[0] in fo
            req = not n.optional and parent_present
            hint = ""
            parent = p.rsplit(".", 1)[0] if "." in p else ""
            for r in removed:
                rparent = r.rsplit(".", 1)[0] if "." in r else ""
                if rparent == parent and fo[r].kind == n.kind:
                    hint = f"renamed from {r}?"
                    break
            out.append(Change("added", p, req, hint))
        else:
            o = fo[p]
            if o.kind != n.kind and "any" not in (o.kind, n.kind):
                out.append(Change("type", p, True, f"{o.kind} -> {n.kind}"))
            elif o.kind == "any" and n.kind in ("array", "object", "number", "mapping"):
                out.append(Change("type", p, True, f"any -> {n.kind}"))
            if o.optional and not n.optional:
                out.append(Change("optional", p, True, "optional -> required"))
    for p in removed:
        out.append(Change("removed", p, False))
    return out


# ---------------------------------------------------------------- Pydantic v2 model code (infer --pydantic)

_PY_KEYWORDS = frozenset(__import__("keyword").kwlist) | {"model_config", "model_fields"}


def _class_name(path: list[str]) -> str:
    words = [w for seg in path for w in re.split(r"[^0-9A-Za-z]+", seg) if w]
    name = "".join(w[:1].upper() + w[1:] for w in words) or "Item"
    return name if name[0].isalpha() else "M" + name


def to_pydantic(root: Node, name: str = "TemplateData") -> str:
    """Pydantic v2 models for the inferred contract (inspired by datamodel-code-generator,
    but without the dependency and with names taken from the template paths).

    Unknown leaves are ``Any`` (the template prints them, any type renders); variables only
    used under a guard (``{% if x %}``, ``x is defined``) are optional. ``extra="allow"`` because
    a template contract is a lower bound: extra keys in the data are fine for docxtpl.
    """
    classes: list[str] = []
    taken: set[str] = set()

    def unique(base: str) -> str:
        n, k = base, 2
        while n in taken:
            n, k = f"{base}{k}", k + 1
        taken.add(n)
        return n

    def type_of(n: Node, path: list[str]) -> str:
        if n.array:
            return f"list[{type_of(n.item or Node(), [*path, 'item'])}]"
        if n.children:
            return model(n, path)
        if n.mapping:
            return "dict[str, Any]"
        if n.numeric:
            return "float"
        return "Any"

    def model(n: Node, path: list[str], cls: str | None = None) -> str:
        cls = unique(cls or _class_name(path))
        lines = [f"class {cls}(BaseModel):", '    model_config = ConfigDict(extra="allow", populate_by_name=True)', ""]
        fields = []
        for key, child in n.children.items():
            t = type_of(child, [*path, key])
            ident = key if key.isidentifier() and key not in _PY_KEYWORDS and not key.startswith("_") else None
            if ident is None:
                ident = re.sub(r"\W", "_", key).strip("_") or "field"
                ident = ("f_" + ident) if (not ident[0].isalpha() or ident in _PY_KEYWORDS) else ident
                default = "None" if child.optional else "..."
                t = f"{t} | None" if child.optional and t != "Any" else t
                fields.append(f"    {ident}: {t} = Field({default}, alias={key!r})")
            elif child.optional:
                fields.append(f"    {ident}: {t if t == 'Any' else t + ' | None'} = None")
            else:
                fields.append(f"    {ident}: {t}")
        lines += fields or ["    pass"]
        classes.append("\n".join(lines))
        return cls

    model(root, [], name)
    head = (
        '"""Generated by docxtpl-lint infer --pydantic. Do not edit by hand; re-run infer instead.\n\n'
        "Render with: DocxTemplate(path).render(TemplateData(**data).model_dump(by_alias=True))\n"
        '"""\n\nfrom __future__ import annotations\n\nfrom typing import Any\n\n'
        "from pydantic import BaseModel, ConfigDict, Field\n"
    )
    body = "\n\n\n".join(classes)
    return head + "\n\n" + body + "\n"
