"""Stable Python API (since 1.9).

Everything in this module follows semantic versioning: function signatures,
:class:`Result` attributes and the shape of :meth:`Result.to_dict` only change
in a major release, after at least one minor release of DeprecationWarning.
Message wording, ``repr`` and log output are not covered. See docs/api.md.

The functions are reentrant and keep no global state; a passed ``jinja_env``
is never modified and passed file objects are read but not closed.
"""

from __future__ import annotations

import io
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any

from .core import Issue, Report
from .core import lint_path as _lint_path

Template = str | Path | bytes | bytearray | IO[bytes]

__all__ = ["Result", "Template", "TemplateLintError", "check_context", "effective_autoescape", "infer_schema", "lint"]


class TemplateLintError(Exception):
    """Raised by :meth:`Result.raise_for_errors`; ``.result`` holds the :class:`Result`."""

    def __init__(self, result: Result, fail_on: str = "error") -> None:
        self.result = result
        bad = result.errors if fail_on == "error" else result.errors + result.warnings
        lines = [f"{result.file}: {len(bad)} problem(s)"]
        lines += [f"  {i.rule} {i.location.part}¶{i.location.paragraph}: {i.message}" for i in bad[:20]]
        super().__init__("\n".join(lines))


@dataclass
class Result:
    """Findings for one template."""

    file: str
    issues: list[Issue] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)  # data paths the template references
    rendered: bool = False  # True when check_context actually rendered with docxtpl

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def ok(self) -> bool:
        """No error-severity findings (the CLI's default exit 0)."""
        return not self.errors

    def raise_for_errors(self, fail_on: str = "error") -> Result:
        """Raise :class:`TemplateLintError` on errors (``fail_on="warning"``: also on warnings)."""
        if fail_on not in ("error", "warning"):
            raise ValueError("fail_on must be 'error' or 'warning'")
        if self.errors or (fail_on == "warning" and self.warnings):
            raise TemplateLintError(self, fail_on)
        return self

    def to_dict(self, lang: str = "en") -> dict[str, Any]:
        """Same shape as one entry of ``files`` in ``--format json``."""
        return {"file": self.file, "issues": [i.to_dict(lang) for i in self.issues], "variables": self.variables}


def effective_autoescape(jinja_env: Any = None, autoescape: bool = False) -> bool:
    """What docxtpl actually does: ``render(autoescape=True)`` forces escaping, otherwise the
    environment's own ``autoescape`` applies. docxtpl compiles XML with ``env.from_string``, so a
    callable (e.g. ``select_autoescape``) is asked with template name ``None``."""
    if autoescape:
        return True
    ae = getattr(jinja_env, "autoescape", False) if jinja_env is not None else False
    return bool(ae(None)) if callable(ae) else bool(ae)


def _source(template: Template) -> tuple[Any, str]:
    if isinstance(template, (str, Path)):
        return str(template), str(template)
    if isinstance(template, (bytes, bytearray)):
        return io.BytesIO(bytes(template)), "<bytes>"
    if hasattr(template, "read"):
        data = template.read()
        return io.BytesIO(data), str(getattr(template, "name", "<stream>"))
    raise TypeError("template must be a path, bytes or a binary file object")


def _report(rep: Report, name: str) -> Result:
    if rep.file != name:
        rep.issues = [_rename(i, name) for i in rep.issues]
    return Result(name, list(rep.issues), list(rep.variables))


def _rename(i: Issue, name: str) -> Issue:
    from dataclasses import replace

    return replace(i, location=replace(i.location, file=name))


def lint(
    template: Template,
    data: Any = None,
    *,
    contexts: Iterable[Any] | None = None,
    schema: dict[str, Any] | None = None,
    jinja_env: Any = None,
    filters: Iterable[str] = (),
    tests: Iterable[str] = (),
    autoescape: bool = False,
    select: Iterable[str] | None = None,
    ignore: Iterable[str] = (),
) -> Result:
    """Statically lint a template; never runs docxtpl.

    ``template`` is a path (a ``str`` is always a path), ``bytes`` or a binary file object.
    ``data`` / ``contexts`` enable the DTL3xx data checks, ``schema`` (a JSON Schema dict)
    DTL304/305. Custom filter/test names are the union of ``filters``/``tests`` and those of
    ``jinja_env``; autoescape is :func:`effective_autoescape`. ``select``/``ignore`` take rule
    ids or prefixes, like the CLI.
    """
    src, name = _source(template)
    f, t = set(filters), set(tests)
    if jinja_env is not None:
        f |= set(jinja_env.filters)
        t |= set(jinja_env.tests)
    rep = _lint_path(
        src,
        data,
        contexts=list(contexts or []),
        schema=schema,
        filters=f,
        tests=t,
        autoescape=effective_autoescape(jinja_env, autoescape),
    )
    sel = list(select) if select is not None else None
    ign = list(ignore)
    rep.issues = [
        i
        for i in rep.issues
        if (sel is None or any(i.rule.startswith(s) for s in sel)) and not any(i.rule.startswith(s) for s in ign)
    ]
    return _report(rep, name)


def check_context(
    template: Template,
    context: Any,
    *,
    jinja_env: Any = None,
    filters: Iterable[str] = (),
    tests: Iterable[str] = (),
    autoescape: bool = False,
    render: bool = True,
) -> Result:
    """Runtime guard before rendering ``context`` into ``template`` in your app.

    Lints with the context as data (DTL3xx) and, with ``render=True`` (default), also renders
    it once with docxtpl in memory (DTL402 if the render raises; ``Result.rendered`` tells
    whether it ran). Rendering executes the template exactly as your app is about to.
    """
    src, name = _source(template)
    if not isinstance(src, str):
        raw = src.getvalue()
        src = io.BytesIO(raw)
    res = lint(src, context, jinja_env=jinja_env, filters=filters, tests=tests, autoescape=autoescape)
    res = Result(name, [_rename(i, name) for i in res.issues], res.variables)
    if not render:
        return res
    from .verify import render_check

    issue = render_check(src if isinstance(src, str) else io.BytesIO(raw), context, jinja_env, autoescape)
    res.rendered = True
    if issue is not None:
        res.issues.append(_rename(issue, name))
    return res


def infer_schema(templates: Iterable[str | Path], title: str = "docxtpl template data") -> dict[str, Any]:
    """JSON Schema (draft 2020-12) of the data the templates need, as ``docxtpl-lint infer``.
    Takes paths only (template names end up in ``x-docxtpl-templates``)."""
    from .contract import infer_tree, to_schema

    return to_schema(infer_tree(list(templates)), title)
