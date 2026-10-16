"""Render-equivalence check (``docxtpl-lint verify``): render the template with real
docxtpl and sentinel data, then look for every unconditional ``{{ path }}`` in the output.

Needs docxtpl (``pip install docxtpl-lint[render]``).

What it can miss (documented false-negative surface): outputs inside ``if``/``else``,
``for … if``, loop ``else`` and ``x if y else z`` are skipped; filtered outputs
(``{{ x|upper }}``), ``{{r …}}``/``{{p …}}`` objects, numbers and objects are not
sentinel-checked. A DTL401 is therefore always real, but its absence is no proof.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Any

from .contract import build_tree, sample
from .core import Issue, Location, Report, _loc, analyse, template_tags
from .reader import iter_paragraphs


def token(n: int) -> str:
    return f"DTLV{n}Q"


def verify_path(path: str | Path, data: Any = None) -> Report:
    try:
        from docxtpl import DocxTemplate
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise RuntimeError("`verify` needs docxtpl: pip install 'docxtpl-lint[render]'") from exc

    file = str(path)
    paras, tags = template_tags(path)
    an = analyse(tags)
    tree = build_tree(an)
    tokens: dict[str, str] = {}

    def leaf(p: str, n: int) -> str:
        tokens[p] = token(n)
        return tokens[p]

    ctx = sample(tree, items=1, leaf=leaf) if data is None else data
    rep = Report(file)
    for p in paras:
        rep.paragraphs.setdefault(p.part, []).append(p)
    try:
        doc = DocxTemplate(file)
        doc.render(ctx)
        buf = io.BytesIO()
        doc.save(buf)
    except Exception as exc:
        rep.issues.append(Issue("DTL402", Location(file, "body", 0), "", {"error": f"{type(exc).__name__}: {exc}"}))
        return rep
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "out.docx"
        out.write_bytes(buf.getvalue())
        text = "\n".join(p.text for p in iter_paragraphs(out))
    if data is not None:
        return rep  # no sentinels to look for with user data: only the render check applies
    seen: set[str] = set()
    for p, tg, conditional in an.outputs:
        if conditional or tg.kind != "expr" or tg.prefix in ("r", "p") or p not in tokens or p in seen:
            continue
        seen.add(p)
        if tokens[p] not in text:
            rep.issues.append(Issue("DTL401", _loc(file, tg.para, tg.col), tg.raw, {"raw": tg.raw}))
    rep.variables = sorted(tokens)
    return rep
