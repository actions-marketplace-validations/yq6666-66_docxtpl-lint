# PLAN v1.3 — Jinja correctness

Arc 1.3 → 2.0: see decisions D87.

## Probe (before planning)

| Template | Before 1.3 | Real docxtpl render |
|---|---|---|
| `{{ x\|money }}` | clean | TemplateAssertionError |
| `{% if x is money %}` | clean | TemplateRuntimeError |
| `{{ i.n }}` after `{% endfor %}` | clean, and `i` listed as top-level data | UndefinedError |
| `{% set last = i %}` inside a loop, `{{ last }}` after it | clean | renders empty |

## Scope

- DTL104 / DTL105 / DTL106 (docs/rules.md)
- `--filters`, `--tests`, `--jinja-env MODULE:ATTR`; the same as `[tool.docxtpl-lint]` keys

## Verification

- tests/test_v13.py: every rule has a render test that shows docxtpl failing or losing output.
- No false positives on namespace(), nested loops, macro args, `set` after the loop, or names that are also top-level data.
- Benchmark: 0 false positives. The DTL104 on custom_jinja_filters_tpl.docx is a true finding (D92).
