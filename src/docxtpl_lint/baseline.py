"""Baseline file: accept the findings that exist today, fail only on new ones.

Modelled on ESLint bulk suppressions (``eslint-suppressions.json``): entries are counted per
file, rule and *paragraph fingerprint*. The fingerprint is the document part, the table-cell
path and a hash of the paragraph text, never a paragraph number, so inserting or deleting
paragraphs elsewhere in the template does not invalidate the baseline; editing the offending
paragraph does.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .core import Issue, Report

VERSION = 1


def _norm_file(file: str, base: Path) -> str:
    p = Path(file).resolve()
    try:
        return p.relative_to(base.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def fingerprint(rep: Report, issue: Issue) -> str:
    loc = issue.location
    if loc.part == "data":
        text = "data:" + issue.snippet + json.dumps(issue.params, sort_keys=True, default=str)
        return "data:" + hashlib.sha256(text.encode()).hexdigest()[:16]
    paras = rep.paragraphs.get(loc.part, [])
    text = paras[loc.paragraph - 1].text if 0 < loc.paragraph <= len(paras) else issue.snippet
    cells = "/".join(f"T{c.table}R{c.row}C{c.col}" for c in loc.cells)
    digest = hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()[:16]
    return f"{loc.part}|{cells}|{digest}"


def _counts(reports: list[Report], base: Path) -> dict[str, dict[str, Counter[str]]]:
    out: dict[str, dict[str, Counter[str]]] = {}
    for rep in reports:
        f = _norm_file(rep.file, base)
        for i in rep.issues:
            out.setdefault(f, {}).setdefault(i.rule, Counter())[fingerprint(rep, i)] += 1
    return out


def write(path: str | Path, reports: list[Report]) -> int:
    path = Path(path)
    counts = _counts(reports, path.parent)
    data: dict[str, Any] = {
        "version": VERSION,
        "tool": "docxtpl-lint",
        "files": {
            f: {r: dict(sorted(c.items())) for r, c in sorted(rules.items())} for f, rules in sorted(counts.items())
        },
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return sum(sum(c.values()) for rules in counts.values() for c in rules.values())


def load(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("version") != VERSION or not isinstance(data.get("files"), dict):
        raise ValueError(f"{path}: not a docxtpl-lint baseline (version {VERSION})")
    return data


def apply(path: str | Path, data: dict[str, Any], reports: list[Report]) -> tuple[int, int]:
    """Remove baselined issues from ``reports`` in place.

    Returns ``(suppressed, stale)``: how many findings the baseline hid and how many
    baseline entries no longer occur (re-run with ``--write-baseline`` to prune them).
    Only files linted in this run count towards ``stale``.
    """
    base = Path(path).parent
    budget = {
        (f, r, k): int(n) for f, rules in data["files"].items() for r, keys in rules.items() for k, n in keys.items()
    }
    seen_files = set()
    suppressed = 0
    for rep in reports:
        f = _norm_file(rep.file, base)
        seen_files.add(f)
        kept = []
        for i in rep.issues:
            key = (f, i.rule, fingerprint(rep, i))
            if budget.get(key, 0) > 0:
                budget[key] -= 1
                suppressed += 1
            else:
                kept.append(i)
        rep.issues = kept
    stale = sum(n for (f, _, _), n in budget.items() if f in seen_files and n > 0)
    return suppressed, stale


def fingerprints(reports: list[Report]) -> dict[int, str]:
    """Stable id per finding (same key as the baseline + occurrence), keyed by id(issue)."""
    out: dict[int, str] = {}
    seen: dict[str, int] = {}
    for rep in reports:
        for it in rep.issues:
            base = f"{Path(rep.file).as_posix()}|{it.rule}|{fingerprint(rep, it)}"
            k = seen.get(base, 0)
            seen[base] = k + 1
            out[id(it)] = hashlib.sha256(f"{base}|{k}".encode()).hexdigest()[:32]
    return out
