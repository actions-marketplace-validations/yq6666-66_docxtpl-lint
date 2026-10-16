"""Command line interface.

Exit codes: 0 = no errors, 1 = errors found (or warnings with
``--warnings-as-errors``), 2 = usage / IO error.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

from . import __version__
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


def render_json(reports: list[Report], lang: str = "en") -> str:
    return json.dumps(
        {
            "schema_version": JSON_SCHEMA_VERSION,
            "tool": "docxtpl-lint",
            "version": __version__,
            "files": [
                {"file": r.file, "issues": [i.to_dict(lang) for i in r.issues], "variables": r.variables}
                for r in reports
            ],
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


def render_sarif(reports: list[Report], lang: str = "en") -> str:
    """SARIF 2.1.0. A .docx has no lines, so the paragraph number is used as the
    line and the table-cell path is put in the message."""
    results = []
    for rep in reports:
        for it in rep.issues:
            loc = it.location
            results.append(
                {
                    "ruleId": it.rule,
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


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="docxtpl-lint",
        description="Static linter for docxtpl (python-docx-template) Word templates.",
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
    ap.add_argument("--format", choices=["text", "json", "github", "sarif"], default="text")
    ap.add_argument("--lang", choices=["en", "zh"], default="en", help="message language (default: en)")
    ap.add_argument("--select", help="comma separated rule ids/prefixes to enable, e.g. DTL1,DTL206")
    ap.add_argument("--ignore", help="comma separated rule ids/prefixes to disable")
    ap.add_argument("--allow-cross-paragraph", action="store_true", help="accept tags spanning paragraphs (no DTL002)")
    ap.add_argument("--warnings-as-errors", action="store_true", help="exit 1 on warnings too")
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
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--version", action="version", version=__version__)
    return ap


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
    a = ap.parse_args(argv)
    tree = infer_tree(a.files)
    _write(json.dumps(to_schema(tree), indent=2, ensure_ascii=False), a.output)
    if a.sample:
        _write(json.dumps(sample(tree, a.items), indent=2, ensure_ascii=False), a.sample)
    return 0


def main_verify(argv: list[str]) -> int:
    from .verify import verify_path

    ap = argparse.ArgumentParser(
        prog="docxtpl-lint verify",
        description="Render each template with real docxtpl and sentinel data and report output that is silently "
        "lost (DTL401) or a failing render (DTL402). Needs docxtpl.",
    )
    ap.add_argument("files", nargs="+")
    ap.add_argument("--data", help="render with this JSON instead of inferred sentinel data (only DTL402)")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--lang", choices=["en", "zh"], default="en")
    a = ap.parse_args(argv)
    data = load_data(a.data) if a.data else None
    try:
        reports = [verify_path(f, data) for f in a.files]
    except RuntimeError as exc:
        print(f"docxtpl-lint: {exc}", file=sys.stderr)
        return 2
    print(render_json(reports, a.lang) if a.format == "json" else render_text(reports, False, False, a.lang, 1))
    return 1 if any(r.issues for r in reports) else 0


def main_diff(argv: list[str]) -> int:
    from .contract import diff, infer_tree

    ap = argparse.ArgumentParser(
        prog="docxtpl-lint diff",
        description="Compare the data contracts of two template versions (breaking = data producers must change).",
    )
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--fail-on-breaking", action="store_true", help="exit 1 if there is a breaking change")
    a = ap.parse_args(argv)
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
    return 1 if a.fail_on_breaking and any(c.breaking for c in changes) else 0


def main_fix(argv: list[str]) -> int:
    from .fixes import suggest

    ap = argparse.ArgumentParser(
        prog="docxtpl-lint fix",
        description="Print fix suggestions as unified diffs of the paragraph text. The .docx is never modified.",
    )
    ap.add_argument("files", nargs="+")
    ap.add_argument("--data", action="append", help="sample data, enables `did you mean` for DTL301")
    ap.add_argument("--format", choices=["diff", "json"], default="diff")
    ap.add_argument("--lang", choices=["en", "zh"], default="en")
    a = ap.parse_args(argv)
    contexts = [load_data(d) for d in a.data or []]
    allfx = []
    for f in a.files:
        allfx += suggest(lint_path(f, contexts=contexts), contexts)
    if a.format == "json":
        print(json.dumps([x.to_dict() for x in allfx], indent=2, ensure_ascii=False))
    elif allfx:
        print("\n\n".join(x.diff(a.lang) for x in allfx))
    else:
        print("no fix suggestions")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in SUBCOMMANDS:
        _reconf()
        sub = {"infer": main_infer, "verify": main_verify, "diff": main_diff, "fix": main_fix}[argv[0]]
        try:
            return sub(argv[1:])
        except (OSError, zipfile.BadZipFile, KeyError, ValueError) as exc:
            # documented exit code 2 = unreadable input, never a traceback
            print(f"docxtpl-lint {argv[0]}: cannot read input (is it a .docx / JSON file?): {exc}", file=sys.stderr)
            return 2
    ap = build_parser()
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

    sel = [s.strip() for s in args.select.split(",")] if args.select else None
    ign = [s.strip() for s in args.ignore.split(",")] if args.ignore else []

    reports: list[Report] = []
    for f in args.files:
        if not Path(f).is_file():
            print(f"docxtpl-lint: file not found: {f}", file=sys.stderr)
            return 2
        try:
            rep = lint_path(
                f,
                contexts=contexts,
                allow_cross_paragraph=args.allow_cross_paragraph,
                report_unused_data=args.report_unused_data,
                schema=schema,
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

    if args.format == "json":
        print(render_json(reports, args.lang))
    elif args.format == "github":
        out = render_github(reports, args.lang)
        if out:
            print(out)
    elif args.format == "sarif":
        print(render_sarif(reports, args.lang))
    else:
        color = not args.no_color and sys.stdout.isatty()
        context = args.context if args.context is not None else (1 if sys.stdout.isatty() else 0)
        print(render_text(reports, color, args.list_vars, args.lang, context))

    bad = {"error", "warning"} if args.warnings_as_errors else {"error"}
    return 1 if any(i.severity in bad for r in reports for i in r.issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
