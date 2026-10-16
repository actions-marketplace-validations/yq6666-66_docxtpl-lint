"""Command line interface.

Exit codes (lint and verify): 0 = no findings at the ``--fail-on`` level (default: error), 1 = findings
at that level, 2 = usage / IO error (also with ``--fail-on never``).
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

from . import __version__
from .api import file_dict
from .baseline import fingerprints as _fingerprints
from .config import ConfigError, find_config, load_config
from .core import Report, lint_path, load_data
from .messages import RULES, help_url

JSON_SCHEMA_VERSION = 1

_COLOR = {"error": "\033[31m", "warning": "\033[33m", "dim": "\033[2m", "bold": "\033[1m", "reset": "\033[0m"}


def _c(name: str, text: str, enable: bool) -> str:
    return f"{_COLOR[name]}{text}{_COLOR['reset']}" if enable else text


def render_text(
    reports: list[Report], color: bool = False, show_vars: bool = False, lang: str = "en", context: int = 0
) -> str:
    lines: list[str] = []
    total = {"error": 0, "warning": 0}
    for rep in reports:
        for it in rep.issues:
            total[it.severity] += 1
            loc = it.location
            lines.append(
                f"{_c('bold', rep.file, color)}:{loc.human(lang)}:{loc.column}: "
                f"{_c(it.severity, it.severity, color)} {_c('bold', it.rule, color)} {it.message_for(lang)}"
            )
            if it.snippet:
                lines.append("    " + _c("dim", it.snippet, color))
            for para in rep.context(loc, context):
                mark = ">" if para.index == loc.paragraph else " "
                cell = " > ".join(f"T{c.table}R{c.row}C{c.col}" for c in para.cells)
                text = para.text if len(para.text) <= 100 else para.text[:97] + "..."
                lines.append(_c("dim", f"      {mark} ¶{para.index:<4}{cell:<10}| {text}", color))
        if show_vars and rep.variables:
            lines.append(f"{rep.file}: " + ("变量:" if lang == "zh" else "variables:"))
            lines.extend(f"  - {v.replace('[]', '[*]')}" for v in rep.variables)
    n = len(reports)
    if total["error"] or total["warning"]:
        if lang == "zh":
            lines.append(f"\n✖ {n} 个文件中有 {total['error']} 个错误、{total['warning']} 个警告")
        else:
            lines.append(f"\n✖ {total['error']} error(s), {total['warning']} warning(s) in {n} file(s)")
    else:
        lines.append(f"✔ {n} 个文件全部通过" if lang == "zh" else f"✔ {n} file(s) clean")
    return "\n".join(lines)


def render_statistics(reports: list[Report]) -> str:
    """ruff-style ``--statistics``: count, rule, severity, summary; most frequent first."""
    from collections import Counter

    counts = Counter(i.rule for r in reports for i in r.issues)
    if not counts:
        return f"✔ {len(reports)} file(s) clean"
    width = len(str(max(counts.values())))
    return "\n".join(
        f"{n:>{width}}  {rule}  {RULES[rule].severity:<7}  {RULES[rule].summary}"
        for rule, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    )


def render_json(reports: list[Report], lang: str = "en") -> str:
    fps = _fingerprints(reports)
    return json.dumps(
        {
            "schema_version": JSON_SCHEMA_VERSION,
            "tool": "docxtpl-lint",
            "version": __version__,
            "files": [file_dict(r, lang, fps) for r in reports],
        },
        ensure_ascii=False,
        indent=2,
    )


def _gh_escape(s: str) -> str:
    return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _gh_prop(s: str) -> str:
    return _gh_escape(s).replace(":", "%3A").replace(",", "%2C")


def render_github(reports: list[Report], lang: str = "en") -> str:
    """GitHub Actions workflow commands: annotations in the PR / run summary.
    A .docx has no lines, so the location is put in the title and message."""
    out = []
    for rep in reports:
        for it in rep.issues:
            title = f"{it.rule} {it.location.human(lang)}"
            out.append(
                f"::{it.severity} file={_gh_prop(rep.file)},title={_gh_prop(title)}::"
                f"{_gh_escape(it.location.human(lang) + ': ' + it.message_for(lang))}"
            )
    return "\n".join(out)


def render_markdown(reports: list[Report], lang: str = "en") -> str:
    """Markdown for a CI job summary / PR comment: one table per file with findings."""
    n_err = sum(i.severity == "error" for r in reports for i in r.issues)
    n_warn = sum(i.severity == "warning" for r in reports for i in r.issues)
    zh = lang == "zh"
    if not n_err and not n_warn:
        return f"### docxtpl-lint\n\n✔ {len(reports)} " + ("个模板没有问题" if zh else "template(s) clean")
    head = (
        f"### docxtpl-lint\n\n{n_err} 个错误、{n_warn} 个警告，共 {len(reports)} 个模板\n"
        if zh
        else f"### docxtpl-lint\n\n{n_err} error(s), {n_warn} warning(s) in {len(reports)} template(s)\n"
    )
    cols = "| 规则 | 级别 | 位置 | 说明 |" if zh else "| Rule | Severity | Where | Message |"

    def cell(t: str) -> str:
        return t.replace("|", "\\|").replace("\n", " ")

    parts = [head]
    for rep in reports:
        if not rep.issues:
            continue
        parts.append(f"\n**{cell(rep.file)}**\n\n{cols}\n|---|---|---|---|")
        for it in rep.issues:
            parts.append(
                f"| [{it.rule}]({help_url(it.rule)}) | {it.severity} | {cell(it.location.human(lang))} | "
                f"{cell(it.message_for(lang))} |"
            )
    return "\n".join(parts)


def render_gitlab(reports: list[Report], lang: str = "en") -> str:
    """GitLab Code Quality report (Code Climate subset). Paragraph number as the line."""
    fps = _fingerprints(reports)
    sev = {"error": "major", "warning": "minor"}
    items = [
        {
            "description": f"[{it.location.human(lang)}] {it.message_for(lang)}",
            "check_name": it.rule,
            "fingerprint": fps[id(it)],
            "severity": sev.get(it.severity, "info"),
            "location": {"path": rep.file, "lines": {"begin": max(it.location.paragraph, 1)}},
        }
        for rep in reports
        for it in rep.issues
    ]
    return json.dumps(items, ensure_ascii=False, indent=2)


def render_sarif(reports: list[Report], lang: str = "en") -> str:
    """SARIF 2.1.0. A .docx has no lines, so the paragraph number is used as the
    line and the table-cell path is put in the message."""
    results = []
    fps = _fingerprints(reports)
    for rep in reports:
        for it in rep.issues:
            loc = it.location
            results.append(
                {
                    "ruleId": it.rule,
                    "partialFingerprints": {"docxtplLint/v1": fps[id(it)]},
                    "level": it.severity,
                    "message": {"text": f"[{loc.human(lang)}] {it.message_for(lang)}"},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": rep.file},
                                "region": {"startLine": max(loc.paragraph, 1)},
                            }
                        }
                    ],
                }
            )
    driver = {
        "name": "docxtpl-lint",
        "version": __version__,
        "informationUri": "https://github.com/yq6666-66/docxtpl-lint",
        "rules": [
            {"id": r.id, "shortDescription": {"text": r.summary}, "helpUri": help_url(r.id)} for r in RULES.values()
        ],
    }
    return json.dumps(
        {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [{"tool": {"driver": driver}, "results": results}],
        },
        ensure_ascii=False,
        indent=2,
    )


FORMATS = {
    "text": None,
    "json": render_json,
    "github": render_github,
    "sarif": render_sarif,
    "gitlab": render_gitlab,
    "markdown": render_markdown,
}


VERIFY_ONLY_LINT_FLAGS = ("schema", "report_unused_data", "allow_cross_paragraph", "list_vars", "filters", "tests")


def build_parser(verify: bool = False) -> argparse.ArgumentParser:
    """The lint parser. ``verify`` (2.0) shares it, so both read the same config and support the
    same output formats, baseline, --select/--ignore and --fail-on; it adds --out."""
    ap = argparse.ArgumentParser(
        prog="docxtpl-lint verify" if verify else "docxtpl-lint",
        description="Render each template with real docxtpl (sentinel data, or --data) and report output that is "
        "silently lost (DTL401) or a failing render (DTL402). Needs docxtpl. Reads [tool.docxtpl-lint] like lint, "
        "except `data` (it would switch off the DTL401 check)."
        if verify
        else "Static linter for docxtpl (python-docx-template) Word templates.",
        epilog="subcommands: infer (data contract -> JSON Schema + sample), verify (render with docxtpl and find "
        "silently lost output), diff (contract changes between two template versions), fix (suggested "
        "fixes as diffs). Run `docxtpl-lint <subcommand> -h`.",
    )
    ap.add_argument("files", nargs="*", help=".docx templates")
    ap.add_argument(
        "--data",
        action="append",
        help="JSON file with a sample context; enables DTL301/DTL303. Repeatable: a path is reported "
        "only if it is absent from all given --data files",
    )
    ap.add_argument(
        "--schema",
        help="JSON Schema used as the data contract (e.g. from `docxtpl-lint infer`); enables DTL304/DTL305",
    )
    ap.add_argument("--report-unused-data", action="store_true", help="also report unused top-level data keys (DTL302)")
    ap.add_argument("--format", choices=list(FORMATS), default="text")
    ap.add_argument("--output", "-o", metavar="FILE", help="write the report to FILE instead of stdout (UTF-8)")
    ap.add_argument(
        "--report",
        action="append",
        metavar="FORMAT:FILE",
        help="also write a report in another format, e.g. --report sarif:out.sarif --report markdown:summary.md",
    )
    ap.add_argument("--lang", choices=["en", "zh"], default="en", help="message language (default: en)")
    ap.add_argument("--select", help="comma separated rule ids/prefixes to enable, e.g. DTL1,DTL206")
    ap.add_argument("--ignore", help="comma separated rule ids/prefixes to disable")
    ap.add_argument("--allow-cross-paragraph", action="store_true", help="accept tags spanning paragraphs (no DTL002)")
    ap.add_argument(
        "--fail-on",
        choices=["error", "warning", "never"],
        default=None,
        help="lowest severity that makes the exit code 1 (default: error); never = always 0 unless "
        "the input cannot be read (exit 2)",
    )
    ap.add_argument("--list-vars", action="store_true", help="print the data paths each template uses")
    ap.add_argument("--list-rules", action="store_true", help="print all rules and exit")
    ap.add_argument("--explain", metavar="RULE", help="explain one rule (e.g. DTL209) and exit")
    ap.add_argument(
        "--context",
        type=int,
        metavar="N",
        help="show N paragraphs around each issue (text format; default: 1 in a terminal, 0 otherwise)",
    )
    ap.add_argument("--config", help="pyproject.toml to read [tool.docxtpl-lint] from (default: nearest one)")
    ap.add_argument("--no-config", action="store_true", help="ignore [tool.docxtpl-lint] settings")
    ap.add_argument(
        "--autoescape", action="store_true", help="your code renders with autoescape=True (silences DTL308)"
    )
    ap.add_argument("--filters", help="comma separated custom Jinja filter names your jinja_env provides (DTL104)")
    ap.add_argument("--tests", help="comma separated custom Jinja test names your jinja_env provides (DTL105)")
    ap.add_argument(
        "--jinja-env",
        metavar="MODULE:ATTR",
        help="import your jinja2.Environment (or a function returning one) and take its filters/tests; runs your code",
    )
    ap.add_argument(
        "--statistics",
        action="store_true",
        help="text format: print one line per rule with its count instead of each finding",
    )
    ap.add_argument(
        "--baseline", metavar="FILE", help="hide findings recorded in this baseline file; only new ones fail"
    )
    ap.add_argument(
        "--write-baseline", metavar="FILE", help="record all current findings in FILE (creates or prunes it) and exit 0"
    )
    ap.add_argument(
        "--annotate",
        metavar="DIR",
        help="write <name>.annotated.docx copies with a Word comment per finding into DIR (originals untouched)",
    )
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--version", action="version", version=__version__)
    if verify:
        ap.add_argument("--out", metavar="DIR", help="save the rendered documents to DIR")
        for act in ap._actions:  # lint-only flags: accepted by the shared parser, rejected, not advertised
            if act.dest in VERIFY_ONLY_LINT_FLAGS:
                act.help = argparse.SUPPRESS
    return ap


def _csv(v: object) -> set[str]:
    if not v:
        return set()
    items = v if isinstance(v, list) else str(v).split(",")
    return {x.strip() for x in items if x.strip()}


def _load_env(spec: str) -> Any:
    """Import ``MODULE:ATTR``: a jinja2.Environment or a function returning one (runs user code)."""
    import importlib

    mod_name, _, attr = spec.partition(":")
    if not attr:
        raise ValueError("expected MODULE:ATTR, e.g. myapp.reports:jinja_env")
    sys.path.insert(0, str(Path.cwd()))
    try:
        obj = getattr(importlib.import_module(mod_name), attr)
    finally:
        sys.path.pop(0)
    env = obj() if callable(obj) and not hasattr(obj, "filters") else obj
    if not hasattr(env, "filters") or not hasattr(env, "tests"):
        raise TypeError(f"{spec} is not a jinja2.Environment")
    return env


def _custom_jinja(args: argparse.Namespace) -> tuple[set[str], set[str], bool, Any]:
    """Filter/test names from --filters/--tests and an optional --jinja-env MODULE:ATTR, plus the
    autoescape docxtpl will really use (the env's own setting counts, see api.effective_autoescape)."""
    from .api import effective_autoescape

    filters, tests = _csv(args.filters), _csv(args.tests)
    env = None
    if args.jinja_env:
        env = _load_env(args.jinja_env)
        filters |= set(env.filters)
        tests |= set(env.tests)
    return filters, tests, effective_autoescape(env, args.autoescape), env


SUBCOMMANDS = ("infer", "verify", "diff", "fix")


def _reconf() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")


def _write(text: str, out: str | None) -> None:
    if out:
        Path(out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def main_infer(argv: list[str]) -> int:
    from .contract import infer_tree, sample, to_schema

    ap = argparse.ArgumentParser(
        prog="docxtpl-lint infer",
        description="Infer the data contract (JSON Schema) of one or more templates; several templates are merged "
        "and each property lists the templates that use it (x-docxtpl-templates).",
    )
    ap.add_argument("files", nargs="+")
    ap.add_argument("-o", "--output", help="write the JSON Schema here (default: stdout)")
    ap.add_argument("--sample", help="also write sample data that satisfies the schema")
    ap.add_argument("--items", type=int, default=2, help="list items in the sample (default 2)")
    ap.add_argument(
        "--pydantic", metavar="FILE", help="also write Pydantic v2 models for the contract to FILE ('-' = stdout)"
    )
    a = ap.parse_args(argv)
    tree = infer_tree(a.files)
    if a.pydantic:
        from .contract import to_pydantic

        code = to_pydantic(tree)
        if a.pydantic == "-":
            print(code, end="")
            if not a.output:
                if a.sample:
                    _write(json.dumps(sample(tree, a.items), indent=2, ensure_ascii=False), a.sample)
                return 0
        else:
            Path(a.pydantic).write_text(code, encoding="utf-8")
    _write(json.dumps(to_schema(tree), indent=2, ensure_ascii=False), a.output)
    if a.sample:
        _write(json.dumps(sample(tree, a.items), indent=2, ensure_ascii=False), a.sample)
    return 0


def main_diff(argv: list[str]) -> int:
    from .contract import diff, infer_tree

    ap = argparse.ArgumentParser(
        prog="docxtpl-lint diff",
        description="Compare the data contracts of two template versions (breaking = data producers must change).",
    )
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument(
        "--fail-on",
        choices=["breaking", "change", "never"],
        default="never",
        help="exit 1 on a breaking change / on any change (default: never)",
    )
    ap.add_argument("--fail-on-breaking", action="store_true", help="deprecated alias of --fail-on breaking")
    a = ap.parse_args(argv)
    if a.fail_on_breaking and a.fail_on not in ("never", "breaking"):
        print("docxtpl-lint diff: --fail-on-breaking conflicts with --fail-on " + a.fail_on, file=sys.stderr)
        return 2
    if a.fail_on_breaking:
        print("docxtpl-lint diff: --fail-on-breaking is deprecated (removed in 3.0); use --fail-on breaking",
              file=sys.stderr)  # fmt: skip
        a.fail_on = "breaking"
    changes = diff(infer_tree([a.old]), infer_tree([a.new]))
    if a.format == "json":
        print(json.dumps([c.to_dict() for c in changes], indent=2, ensure_ascii=False))
    elif not changes:
        print("data contract unchanged")
    else:
        for c in changes:
            mark = "BREAKING" if c.breaking else "ok      "
            sign = {"added": "+", "removed": "-", "type": "~", "optional": "~"}[c.kind]
            detail = f"  ({c.detail})" if c.detail else ""
            print(f"{mark} {sign} {c.path.replace('[]', '[*]')}{detail}")
        nb = sum(c.breaking for c in changes)
        print(f"\n{len(changes)} change(s), {nb} breaking")
    if a.fail_on == "change":
        return 1 if changes else 0
    return 1 if a.fail_on == "breaking" and any(c.breaking for c in changes) else 0


def main_fix(argv: list[str]) -> int:
    from .fixes import suggest

    ap = argparse.ArgumentParser(
        prog="docxtpl-lint fix",
        description="Print fix suggestions as unified diffs of the paragraph text, or apply them to a copy with "
        "--write. The template itself is never modified.",
    )
    ap.add_argument("files", nargs="+")
    ap.add_argument(
        "--write",
        metavar="OUT",
        help="write a fixed copy: a .docx path for one template, or a directory (<name>.fixed.docx) for several",
    )
    ap.add_argument("--unsafe", action="store_true", help="also apply fixes that guess at intent (see docs)")
    ap.add_argument("--data", action="append", help="sample data, enables `did you mean` for DTL301")
    ap.add_argument("--format", choices=["diff", "json"], default="diff")
    ap.add_argument("--lang", choices=["en", "zh"], default="en")
    a = ap.parse_args(argv)
    contexts = [load_data(d) for d in a.data or []]
    if a.write:
        from .fixes import write_fixed

        total = 0
        for f in a.files:
            dst = Path(a.write)
            if len(a.files) > 1 or dst.is_dir() or not dst.suffix:
                dst.mkdir(parents=True, exist_ok=True)
                dst = dst / (Path(f).stem + ".fixed.docx")
            done = write_fixed(f, str(dst), contexts, a.unsafe)
            total += len(done)
            for fx in done:
                where = (fx.location or fx.issue.location).human(a.lang)
                print(f"{f}: {where}: {fx.issue.rule} {fx.note}")
            left = lint_path(str(dst), contexts=contexts).issues
            print(f"wrote {dst}: {len(done)} fix(es) applied, {len(left)} finding(s) left", file=sys.stderr)
        return 0
    allfx = []
    for f in a.files:
        allfx += suggest(lint_path(f, contexts=contexts), contexts)
    if a.format == "json":
        print(json.dumps([x.to_dict() for x in allfx], indent=2, ensure_ascii=False))
    elif allfx:
        print(
            "\n\n".join(
                x.diff(a.lang) + ("" if x.safe else "\n# (unsafe: applied by --write only with --unsafe)")
                for x in allfx
            )
        )
    else:
        print("no fix suggestions")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    verify = bool(argv) and argv[0] == "verify"
    if verify:
        _reconf()
        argv = argv[1:]
    elif argv and argv[0] in SUBCOMMANDS:
        _reconf()
        sub = {"infer": main_infer, "diff": main_diff, "fix": main_fix}[argv[0]]
        try:
            return sub(argv[1:])
        except (OSError, zipfile.BadZipFile, KeyError, ValueError) as exc:
            # documented exit code 2 = unreadable input, never a traceback
            print(f"docxtpl-lint {argv[0]}: cannot read input (is it a .docx / JSON file?): {exc}", file=sys.stderr)
            return 2
    if "--warnings-as-errors" in argv:
        print("docxtpl-lint: --warnings-as-errors was removed in 2.0; use --fail-on warning "
              "(docs/MIGRATION-2.0.md)", file=sys.stderr)  # fmt: skip
        return 2
    ap = build_parser(verify)
    pre, _ = ap.parse_known_args(argv)
    if not pre.no_config:
        cfg_path = Path(pre.config) if pre.config else find_config()
        if cfg_path is not None:
            try:
                cfg = load_config(cfg_path)
            except ConfigError as exc:
                print(f"docxtpl-lint: {exc}", file=sys.stderr)
                return 2
            cfg_data = cfg.pop("data", None)
            if verify:
                cfg_data = None  # D134: config data would turn off verify's DTL401 sentinel check
                for k in VERIFY_ONLY_LINT_FLAGS:
                    cfg.pop(k, None)
            ap.set_defaults(**cfg)
            args = ap.parse_args(argv)
            if args.data is None and cfg_data:
                args.data = cfg_data
        else:
            args = ap.parse_args(argv)
    else:
        args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        # e.g. Windows cp1252 consoles cannot print ✔ / ¶ / Chinese messages
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    if args.explain:
        r = RULES.get(args.explain.upper())
        if r is None:
            print(f"docxtpl-lint: unknown rule {args.explain}", file=sys.stderr)
            return 2
        msg = r.zh if args.lang == "zh" else r.en
        print(f"{r.id} ({r.severity}): {r.summary}\n\n  message: {msg}\n\n  details, examples and docxtpl behaviour: "
              f"{help_url(r.id)}")  # fmt: skip
        return 0
    if args.list_rules:
        for r in RULES.values():
            print(f"{r.id}  {r.severity:<7}  {r.summary}")
        return 0
    if verify:
        bad_flags = [k for k in VERIFY_ONLY_LINT_FLAGS if getattr(args, k)]
        if bad_flags:
            names = ", ".join("--" + k.replace("_", "-") for k in bad_flags)
            print(f"docxtpl-lint verify: {names} only apply to lint", file=sys.stderr)
            return 2
    if not args.files:
        ap.print_usage(sys.stderr)
        print("docxtpl-lint: error: no files given", file=sys.stderr)
        return 2

    contexts = []
    for d in args.data or []:
        try:
            contexts.append(load_data(d))
        except (OSError, ValueError) as exc:
            print(f"docxtpl-lint: cannot read --data: {exc}", file=sys.stderr)
            return 2

    schema = None
    if args.schema:
        from .contract import load_schema

        try:
            schema = load_schema(args.schema)
        except (OSError, ValueError) as exc:
            print(f"docxtpl-lint: cannot read --schema: {exc}", file=sys.stderr)
            return 2

    try:
        filters, tests, autoescape, env = _custom_jinja(args)
    except Exception as exc:  # user code: report, never a traceback
        print(f"docxtpl-lint: cannot load --jinja-env {args.jinja_env}: {exc}", file=sys.stderr)
        return 2
    sel = [s.strip() for s in args.select.split(",")] if args.select else None
    ign = [s.strip() for s in args.ignore.split(",")] if args.ignore else []

    reports: list[Report] = []
    for f in args.files:
        if not Path(f).is_file():
            print(f"docxtpl-lint: file not found: {f}", file=sys.stderr)
            return 2
        if verify:
            from .verify import verify_path

            try:
                rep = verify_path(f, contexts=contexts, autoescape=args.autoescape, jinja_env=env, out=args.out)
            except RuntimeError as exc:  # docxtpl not installed
                print(f"docxtpl-lint: {exc}", file=sys.stderr)
                return 2
            except Exception as exc:
                print(f"docxtpl-lint: cannot read {f} (is it a .docx?): {exc}", file=sys.stderr)
                return 2
        else:
            try:
                rep = lint_path(
                    f,
                    contexts=contexts,
                    allow_cross_paragraph=args.allow_cross_paragraph,
                    report_unused_data=args.report_unused_data,
                    schema=schema,
                    filters=filters,
                    tests=tests,
                    autoescape=autoescape,
                )
            except Exception as exc:
                print(f"docxtpl-lint: cannot read {f} (is it a .docx?): {exc}", file=sys.stderr)
                return 2
        rep.issues = [
            i
            for i in rep.issues
            if (sel is None or any(i.rule.startswith(s) for s in sel)) and not any(i.rule.startswith(s) for s in ign)
        ]
        reports.append(rep)

    if args.write_baseline:
        from . import baseline

        n = baseline.write(args.write_baseline, reports)
        print(f"docxtpl-lint: wrote {n} finding(s) to baseline {args.write_baseline}", file=sys.stderr)
        return 0
    if args.baseline:
        from . import baseline

        try:
            bl = baseline.load(args.baseline)
        except (OSError, ValueError) as exc:
            print(f"docxtpl-lint: cannot read --baseline: {exc}", file=sys.stderr)
            return 2
        hidden, stale = baseline.apply(args.baseline, bl, reports)
        if hidden or stale:
            msg = f"docxtpl-lint: baseline hid {hidden} finding(s)"
            if stale:
                msg += f"; {stale} stale baseline entr{'y' if stale == 1 else 'ies'} (prune with --write-baseline)"
            print(msg, file=sys.stderr)
    if args.annotate:
        from .annotate import annotate

        out_dir = Path(args.annotate)
        out_dir.mkdir(parents=True, exist_ok=True)
        for rep in reports:
            if rep.issues:
                dst = out_dir / (Path(rep.file).stem + ".annotated.docx")
                n = annotate(rep, dst, args.lang)
                print(f"docxtpl-lint: {dst} ({n} comment(s))", file=sys.stderr)

    for spec in args.report or []:
        fmt, _, path = spec.partition(":")
        if fmt not in FORMATS or fmt == "text" or not path:
            print(f"docxtpl-lint: --report expects FORMAT:FILE with FORMAT in {', '.join(FORMATS)}", file=sys.stderr)
            return 2
        Path(path).write_text(FORMATS[fmt](reports, args.lang) + "\n", encoding="utf-8")
    if args.statistics and args.format == "text":
        main_out = render_statistics(reports)
    elif args.format == "text":
        tty = sys.stdout.isatty() and not args.output
        color = not args.no_color and tty
        context = args.context if args.context is not None else (1 if tty else 0)
        main_out = render_text(reports, color, args.list_vars, args.lang, context)
    else:
        main_out = FORMATS[args.format](reports, args.lang)
    if args.output:
        Path(args.output).write_text(main_out + "\n", encoding="utf-8")
    elif main_out:
        print(main_out)

    fail_on = args.fail_on or "error"
    bad = {"error": {"error"}, "warning": {"error", "warning"}, "never": set()}[fail_on]
    return 1 if any(i.severity in bad for r in reports for i in r.issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
