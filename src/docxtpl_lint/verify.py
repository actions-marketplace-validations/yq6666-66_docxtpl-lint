"""Render-equivalence check (``docxtpl-lint verify``): render the template with real
docxtpl and sentinel data, then look for every unconditional ``{{ path }}`` in the output.

Needs docxtpl (``pip install docxtpl-lint[render]``).

What it can miss (documented false-negative surface): outputs inside ``if``/``else``,
``for … if``, loop ``else`` and ``x if y else z`` are skipped; filtered outputs
(``{{ x|upper }}``), numbers and objects are not sentinel-checked. Since 1.6 ``{{r …}}`` and
``{{p …}}`` get a RichText / Subdoc sentinel and are checked too.
A DTL401 is therefore always real, but its absence is no proof.
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


def verify_path(
    path: str | Path,
    data: Any = None,
    *,
    contexts: list[Any] | None = None,
    autoescape: bool = False,
    jinja_env: Any = None,
    out: str | Path | None = None,
) -> Report:
    """Render ``path`` with docxtpl. Without data: inferred sentinel data, DTL401 for lost
    output and DTL402 for a failing render. With ``data`` / ``contexts``: one render per
    context, DTL402 only. ``out`` saves the rendered file(s) for inspection."""
    try:
        from docxtpl import DocxTemplate
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise RuntimeError("`verify` needs docxtpl: pip install 'docxtpl-lint[render]'") from exc

    from docxtpl import RichText

    file = str(path)
    paras, tags = template_tags(path)
    an = analyse(tags)
    tree = build_tree(an)
    tokens: dict[str, str] = {}
    ctxs = list(contexts or []) + ([data] if data is not None else [])
    rep = Report(file)
    for p in paras:
        rep.paragraphs.setdefault(p.part, []).append(p)

    def render(ctx_fn: Any, n: int) -> str | None:
        """Render once; returns the output text, or None after adding DTL402."""
        try:
            doc = DocxTemplate(file)
            ctx = ctx_fn(doc)
            doc.render(ctx, jinja_env=jinja_env, autoescape=autoescape)
            buf = io.BytesIO()
            doc.save(buf)
        except Exception as exc:
            where = f" (--data #{n})" if len(ctxs) > 1 else ""
            msg = f"{type(exc).__name__}: {exc}{where}"
            rep.issues.append(Issue("DTL402", Location(file, "body", 0), "", {"error": msg}))
            return None
        if out is not None:
            od = Path(out)
            od.mkdir(parents=True, exist_ok=True)
            suffix = f".{n}" if len(ctxs) > 1 else ""
            (od / f"{Path(file).stem}.rendered{suffix}.docx").write_bytes(buf.getvalue())
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d) / "out.docx"
            tmp.write_bytes(buf.getvalue())
            return "\n".join(p.text for p in iter_paragraphs(tmp))

    if ctxs:
        for k, c in enumerate(ctxs, 1):
            render(lambda _doc, c=c: c, k)
        return rep  # no sentinels to look for with user data: only the render check applies

    unchecked: set[str] = set()

    def sentinel_ctx(doc: Any) -> Any:
        def leaf(p: str, n: int) -> Any:
            tokens[p] = token(n)
            obj = an.objects.get(p)
            if obj == "RichText":
                return RichText(tokens[p])
            if obj == "Subdoc":
                try:
                    sd = doc.new_subdoc()  # needs docxcompose (optional docxtpl dependency)
                except ImportError:
                    unchecked.add(p)
                    return RichText(tokens[p])
                sd.add_paragraph(tokens[p])
                return sd
            return tokens[p]

        return sample(tree, items=1, leaf=leaf)

    text = render(sentinel_ctx, 1)
    if text is None:
        return rep
    seen: set[str] = set()
    for p, tg, conditional in an.outputs:
        if conditional or tg.kind != "expr" or p not in tokens or p in seen or p in unchecked:
            continue
        seen.add(p)
        if tokens[p] not in text:
            rep.issues.append(Issue("DTL401", _loc(file, tg.para, tg.col), tg.raw, {"raw": tg.raw}))
    rep.variables = sorted(tokens)
    return rep
