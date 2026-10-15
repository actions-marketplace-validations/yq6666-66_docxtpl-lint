"""Command line interface. Exit codes: 0 clean, 1 issues found, 2 usage / IO error."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import Report, lint_path, load_data

RULES = {
    "DTL001": "tag not closed within its paragraph / 标签在段内未闭合",
    "DTL101": "unclosed block (if/for/with/...) / 块未闭合",
    "DTL102": "stray end/else/elif tag / 多余的结束或 else 标签",
    "DTL103": "other Jinja2 syntax error / 其他 Jinja2 语法错误",
    "DTL201": "% or } inside {%p/tr/tc/r %} expression (docxtpl #644)",
    "DTL202": "space before tr/tc prefix, e.g. `{% tr for %}`",
    "DTL203": "tr/tc tag outside a table cell / tr/tc 标签不在表格中",
    "DTL204": "prefix mismatch between opening and closing tag / 开闭标签前缀不一致",
    "DTL205": "{%tr %} block spans two tables / tr 块跨表",
    "DTL206": "{%tr %} open and close in the same row / tr 开闭在同一行",
    "DTL301": "variable missing from --data JSON / 数据中缺少变量",
    "DTL302": "top-level data key unused (warning) / 数据字段未使用",
}

_COLOR = {"error": "\033[31m", "warning": "\033[33m", "dim": "\033[2m", "bold": "\033[1m", "reset": "\033[0m"}


def _c(name: str, text: str, enable: bool) -> str:
    return f"{_COLOR[name]}{text}{_COLOR['reset']}" if enable else text


def render_text(reports: list[Report], color: bool, show_vars: bool) -> str:
    lines: list[str] = []
    total = {"error": 0, "warning": 0}
    for rep in reports:
        for it in rep.issues:
            total[it.severity] += 1
            loc = it.location
            lines.append(
                f"{_c('bold', rep.file, color)}:{loc.human()}:{loc.column}: "
                f"{_c(it.severity, it.severity, color)} {_c('bold', it.rule, color)} {it.message}"
            )
            if it.snippet:
                lines.append("    " + _c("dim", it.snippet, color))
        if show_vars and rep.variables:
            lines.append(f"{rep.file}: variables / 变量:")
            lines.extend(f"  - {v.replace('[]', '[*]')}" for v in rep.variables)
    n = len(reports)
    if total["error"] or total["warning"]:
        lines.append(f"\n✖ {total['error']} error(s), {total['warning']} warning(s) in {n} file(s)")
    else:
        lines.append(f"✔ {n} file(s) clean")
    return "\n".join(lines)


def render_json(reports: list[Report]) -> str:
    return json.dumps(
        {
            "version": __version__,
            "files": [
                {"file": r.file, "issues": [i.to_dict() for i in r.issues], "variables": r.variables} for r in reports
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="docxtpl-lint", description="Static linter for docxtpl Word templates.")
    ap.add_argument("files", nargs="*", help=".docx templates")
    ap.add_argument("--data", help="JSON file with sample context; enables DTL301/DTL302")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--select", help="comma separated rule ids/prefixes to enable, e.g. DTL1,DTL206")
    ap.add_argument("--ignore", help="comma separated rule ids/prefixes to disable")
    ap.add_argument("--warnings-as-errors", action="store_true", help="exit 1 on warnings too")
    ap.add_argument("--list-vars", action="store_true", help="print variables used by each template")
    ap.add_argument("--list-rules", action="store_true")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args(argv)

    if args.list_rules:
        for k, v in RULES.items():
            print(f"{k}  {v}")
        return 0
    if not args.files:
        ap.print_usage(sys.stderr)
        print("docxtpl-lint: error: no files given", file=sys.stderr)
        return 2

    data = None
    if args.data:
        try:
            data = load_data(args.data)
        except (OSError, ValueError) as exc:
            print(f"docxtpl-lint: cannot read --data: {exc}", file=sys.stderr)
            return 2

    sel = [s.strip() for s in args.select.split(",")] if args.select else None
    ign = [s.strip() for s in args.ignore.split(",")] if args.ignore else []

    reports: list[Report] = []
    for f in args.files:
        if not Path(f).is_file():
            print(f"docxtpl-lint: file not found: {f}", file=sys.stderr)
            return 2
        try:
            rep = lint_path(f, data)
        except Exception as exc:
            print(f"docxtpl-lint: cannot read {f}: {exc}", file=sys.stderr)
            return 2
        rep.issues = [
            i
            for i in rep.issues
            if (sel is None or any(i.rule.startswith(s) for s in sel)) and not any(i.rule.startswith(s) for s in ign)
        ]
        reports.append(rep)

    if args.format == "json":
        print(render_json(reports))
    else:
        color = not args.no_color and sys.stdout.isatty()
        print(render_text(reports, color, args.list_vars))

    bad = {"error", "warning"} if args.warnings_as_errors else {"error"}
    return 1 if any(i.severity in bad for r in reports for i in r.issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
