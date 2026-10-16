"""Run DeepSeek-designed adversarial cases (docs/eval/adversarial_cases.json).

Each case is built as a real .docx (python-docx), run through docxtpl-lint, and
also rendered with the real docxtpl ("ground truth": ok / raises <Error>).
Usage: python scripts/adversarial.py docs/eval/adversarial_cases.json [--md out.md]
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from docxtpl_lint.core import lint_path  # noqa: E402
from docxtpl_lint.contract import flatten, infer_tree  # noqa: E402
from docxtpl_lint.fixes import suggest  # noqa: E402
from docxtpl_lint.verify import verify_path  # noqa: E402


def build(case: dict, path: Path) -> None:
    d = Document()
    for b in case.get("blocks", []):
        if "p" in b:
            d.add_paragraph(b["p"])
        elif "table" in b:
            rows = b["table"]
            t = d.add_table(rows=len(rows), cols=max(len(r) for r in rows))
            for i, r in enumerate(rows):
                for j, txt in enumerate(r):
                    t.cell(i, j).text = txt
    if case.get("header"):
        d.sections[0].header.paragraphs[0].text = case["header"]
    d.save(path)


def ground_truth(path: Path, data) -> str:
    try:
        import docxtpl

        t = docxtpl.DocxTemplate(str(path))
        t.render(data or {})
        t.save(io.BytesIO())
        return "ok"
    except Exception as exc:
        return f"raises {type(exc).__name__}: {str(exc)[:60]}"


def actual(case: dict, path: Path) -> list[str]:
    cmd, data = case["command"], case.get("data")
    opt = case.get("options", {})
    if cmd == "lint":
        rep = lint_path(
            path,
            None if "schema" in opt else data,
            schema=opt.get("schema"),
            report_unused_data=opt.get("report_unused_data", False),
            allow_cross_paragraph=opt.get("allow_cross_paragraph", False),
        )
        return sorted({i.rule for i in rep.issues})
    if cmd == "verify":
        return sorted({i.rule for i in verify_path(path).issues})
    if cmd == "infer":
        return sorted(flatten(infer_tree([path])))
    if cmd == "fix":
        return ["fix"] if suggest(lint_path(path, data), [data] if data else []) else []
    raise ValueError(cmd)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--adjudicated", type=Path, help="override expected results (after checking with docxtpl)")
    a = ap.parse_args()
    cases = json.loads(a.cases.read_text(encoding="utf-8"))
    if a.adjudicated:
        adj = json.loads(a.adjudicated.read_text(encoding="utf-8"))["cases"]
        for c in cases:
            if c["name"] in adj:
                c.update(adj[c["name"]])
    rows = []
    with tempfile.TemporaryDirectory() as d:
        for c in cases:
            p = Path(d) / f"{c['name']}.docx"
            build(c, p)
            try:
                got = actual(c, p)
            except Exception as exc:
                got = [f"CRASH {type(exc).__name__}: {exc}"]
            exp = sorted(c["expected_rules"])
            truth = ground_truth(p, c.get("data"))
            row = {"name": c["name"], "command": c["command"], "expected": exp, "actual": got, "match": got == exp}
            rows.append({**row, "docxtpl": truth, "why": c.get("why", "")})
    if a.json:
        a.json.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    for r in rows:
        mark = "OK  " if r["match"] else "DIFF"
        print(
            f"{mark} {r['name']:<40} {r['command']:<6} exp={r['expected']} got={r['actual']} | docxtpl: {r['docxtpl']}"
        )
    print(f"\n{sum(r['match'] for r in rows)}/{len(rows)} match the expectation")
    return 0 if all(r["match"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
