"""Benchmark: lint python-docx-template's own test templates.

Those templates are written by the docxtpl maintainers and render correctly
(except template_error_tpl.docx, which is broken on purpose), so any finding
on them is a false positive.

    git clone --depth 1 https://github.com/elapouya/python-docx-template /tmp/docxtpl
    python scripts/benchmark.py /tmp/docxtpl/tests/templates [--json out.json]

Exit code 0 when the result matches benchmark/expected.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from docxtpl_lint.core import lint_path  # noqa: E402


def run(templates: Path, expected: dict) -> dict:
    files = sorted(templates.glob("*.docx"))
    must = expected.get("must_report", {})
    known = expected.get("known_false_positives", {})
    result = {
        "files": len(files),
        "false_positives": [],
        "missed": [],
        "found": [],
        "stale_allowlist": [],
        "seconds": 0.0,
    }
    t0 = time.perf_counter()
    for f in files:
        rules = sorted({i.rule for i in lint_path(f).issues})
        want = set(must.get(f.name, []))
        allowed = want | set(known.get(f.name, []))
        result["false_positives"] += [f"{f.name}:{r}" for r in rules if r not in allowed]
        result["missed"] += [f"{f.name}:{r}" for r in sorted(want - set(rules))]
        result["found"] += [f"{f.name}:{r}" for r in rules if r in want]
        # an allow-listed false positive that no longer happens must be removed from expected.json
        result["stale_allowlist"] += [f"{f.name}:{r}" for r in known.get(f.name, []) if r not in rules]
    result["seconds"] = round(time.perf_counter() - t0, 2)
    try:
        import docxtpl  # noqa: F401
    except ImportError:
        result["verify"] = None
        return result
    from docxtpl_lint.verify import verify_path

    # verify = infer sample data + render with the real docxtpl + look for lost output
    vmust = expected.get("verify_must_report", {})
    unsupported = expected.get("verify_unsupported", {})
    v = {"rendered": 0, "unsupported": [], "false_positives": [], "missed": []}
    for f in files:
        rules = sorted({i.rule for i in verify_path(f).issues})
        if not rules:
            v["rendered"] += 1
        want = set(vmust.get(f.name, []))
        if f.name in unsupported and rules == ["DTL402"]:
            v["unsupported"].append(f"{f.name}: {unsupported[f.name]}")
            continue
        v["false_positives"] += [f"{f.name}:{r}" for r in rules if r not in want]
        v["missed"] += [f"{f.name}:{r}" for r in sorted(want - set(rules))]
    result["verify"] = v
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("templates", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    expected = json.loads((ROOT / "benchmark" / "expected.json").read_text(encoding="utf-8"))
    res = run(args.templates, expected)
    if args.json:
        args.json.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(
        f"{res['files']} templates in {res['seconds']}s | found: {len(res['found'])} | "
        f"false positives: {len(res['false_positives'])} | missed: {len(res['missed'])}"
    )
    for x in res["false_positives"]:
        print("  false positive:", x)
    for x in res["missed"]:
        print("  missed:", x)
    for x in res["stale_allowlist"]:
        print("  stale known_false_positives entry (remove it):", x)
    v = res.get("verify")
    if v is not None:
        print(
            f"verify (infer + render with docxtpl): {v['rendered']}/{res['files']} rendered with inferred data | "
            f"false positives: {len(v['false_positives'])} | missed: {len(v['missed'])}"
        )
        for x in v["unsupported"]:
            print("  needs Python objects:", x)
        for x in v["false_positives"]:
            print("  verify false positive:", x)
        for x in v["missed"]:
            print("  verify missed:", x)
    ok = res["files"] and not (res["false_positives"] or res["missed"] or res["stale_allowlist"])
    ok = ok and not (v and (v["false_positives"] or v["missed"]))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
