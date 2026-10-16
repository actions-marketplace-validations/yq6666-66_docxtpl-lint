"""Command line interface.

Exit codes: 0 = no errors, 1 = errors found (or warnings with
``--warnings-as-errors``), 2 = usage / IO error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import Report, lint_path, load_data
from .messages import RULES

JSON_SCHEMA_VERSION = 1

_COLOR = {"error": "\033[31m", "warning": "\033[33m", "dim": "\033[2m", "bold": "\033[1m", "reset": "\033[0m"}


def _c(name: str, text: str, enable: bool) -> str:
    return f"{_COLOR[name]}{text}{_COLOR['reset']}" if enable else text


def render_text(reports: list[Report], color: bool = False, show_vars: bool = False, lang: str = "en") -> str:
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
        "rules": [{"id": r.id, "shortDescription": {"text": r.summary}} for r in RULES.values()],
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
    )
    ap.add_argument("files", nargs="*", help=".docx templates")
    ap.add_argument(
        "--data",
        action="append",
        help="JSON file with a sample context; enables DTL301/DTL303. Repeatable: a path is only "
        "reported missing if it is missing from every file",
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
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--version", action="version", version=__version__)
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        # e.g. Windows cp1252 consoles cannot print ✔ / ¶ / Chinese messages
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

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
        print(render_text(reports, color, args.list_vars, args.lang))

    bad = {"error", "warning"} if args.warnings_as_errors else {"error"}
    return 1 if any(i.severity in bad for r in reports for i in r.issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
