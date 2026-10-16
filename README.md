# docxtpl-lint

[中文文档 / Chinese](README.zh.md)

**A static linter for [docxtpl](https://github.com/elapouya/python-docx-template) (python-docx-template) Word templates.
It points each problem to the exact table cell, reports all problems in one run, and returns exit codes your CI can use.**

![docxtpl-lint output](https://raw.githubusercontent.com/yq6666-66/docxtpl-lint/main/docs/demo.svg)

docxtpl itself only gives you this, with no location and only the first error:

```text
jinja2.exceptions.TemplateSyntaxError: Encountered unknown tag 'endfor'. Jinja was looking for the following tags: 'elif' or 'else' or 'endif'.
```

> Not affiliated with python-docx-template. Tested against docxtpl 0.20.2.

## Features

- **Table-cell locations.** Each issue names the part (body, `header1`, `footer2`, footnotes), the paragraph, and for tables
  a path like `T1 R2 C2 > T2 R2 C1` (table, row, column; nested tables supported). The offending tag text is always printed.
- **All block problems in one run.** Unclosed `if`/`for`, stray `endfor`/`else`, and tags that never close are found with
  the linter's own tag stack, so you don't fix-render-repeat. Other Jinja syntax errors are reported once per document part,
  as Jinja itself does.
- **Knows docxtpl's own tags.** `{%tr %}`, `{%tc %}`, `{%p %}`, `{%r %}`. Each docxtpl rule has a test that renders a bad
  template with the real docxtpl and checks that it really breaks.
- **Checks templates against sample data.** `--data sample.json` checks every variable path, including nested fields and
  loop items such as `items[*].price`. Paths guarded with `is defined` or `| default(...)` are not reported.
- **Built for CI.** Exit codes, `--format json|github|sarif`, a GitHub Action and a pre-commit hook.
- **Read-only.** Your `.docx` is never modified. The linter reads the OOXML with lxml and does not import docxtpl.

## Install

```sh
pip install docxtpl-lint
```

## Usage

```sh
docxtpl-lint templates/*.docx
docxtpl-lint contract.docx --data sample.json            # + data checks (repeat --data for several contexts)
docxtpl-lint contract.docx --format json > report.json   # machine readable (schema_version: 1)
docxtpl-lint contract.docx --list-vars                   # which data does this template need?
docxtpl-lint contract.docx --lang zh                     # 中文提示
docxtpl-lint --list-rules
```

| exit code | meaning |
|---|---|
| 0 | no errors (warnings allowed unless `--warnings-as-errors`) |
| 1 | errors found |
| 2 | bad arguments, missing file, unreadable `.docx` / JSON |

Other options: `--select DTL1,DTL206`, `--ignore DTL2` (prefix match), `--allow-cross-paragraph`,
`--report-unused-data`, `--warnings-as-errors`, `--no-color`.

To silence rules for one template, put a Jinja comment anywhere in it (docxtpl renders it as nothing):
`{# docxtpl-lint: disable=DTL301,DTL002 #}`

## Rules

| id | severity | what | docxtpl does |
|---|---|---|---|
| DTL001 | error | a `{{`, `{%` or `{#` is never closed | raises |
| DTL002 | warning | a tag spans several paragraphs | merges the paragraphs, so their formatting is lost |
| DTL101 | error | unclosed `if` / `for` / `with` / ... | raises, with no location |
| DTL102 | error | `endX` / `else` / `elif` without a block | raises, with no location |
| DTL103 | error | other Jinja2 syntax error, incl. `{% do %}` / `{% break %}` (not enabled in docxtpl) | raises |
| DTL201 | error | `%` or `}` inside `{%p/tr/tc/r … %}` | raises ([#644](https://github.com/elapouya/python-docx-template/issues/644)) |
| DTL202 | error | `{% tr …`: a space before the `tr`/`tc`/`p`/`r` prefix | raises "unknown tag" |
| DTL203 | error | `tr`/`tc` tag outside a table | raises |
| DTL204 | error | prefix mismatch, e.g. `{% for %}` … `{%tr endfor %}` | **silently** loses loop rows ([#603](https://github.com/elapouya/python-docx-template/issues/603)) |
| DTL205 | error | `{%tr for %}` and `{%tr endfor %}` in different tables | **silently** loses rows |
| DTL206 | error | `{%tr for %}` and `{%tr endfor %}` in the same row | raises |
| DTL207 | error | `{%tc for %}` and `{%tc endfor %}` in different rows | **silently** corrupts the table |
| DTL301 | error | (`--data`) variable missing from every sample context | renders empty or raises |
| DTL302 | warning | (`--report-unused-data`) top-level data key never used | n/a |
| DTL303 | error | (`--data`) `for` over a number / boolean / null | raises at render time |

### Upstream issues → rules

| python-docx-template issue | covered by |
|---|---|
| [#378](https://github.com/elapouya/python-docx-template/issues/378): "help to locate the error in the template" | every rule's location; DTL101/102/103 |
| [#603](https://github.com/elapouya/python-docx-template/issues/603): "Why can't it loop in the table?" | DTL202, DTL204, DTL205, DTL206, DTL207 |
| [#644](https://github.com/elapouya/python-docx-template/issues/644): `{%p %}` fails with `%` or `}` | DTL201 |
| [#538](https://github.com/elapouya/python-docx-template/issues/538) / [#391](https://github.com/elapouya/python-docx-template/issues/391): which (nested) variables does a template use? | `--list-vars`, DTL301 |

## Use in CI

**GitHub Action** (annotations appear on the run and in the PR):

```yaml
- uses: actions/checkout@v4
- uses: yq6666-66/docxtpl-lint@v0.1.0
  with:
    files: |
      templates/**/*.docx
    args: --data tests/sample_context.json
```

**pre-commit**

```yaml
repos:
  - repo: https://github.com/yq6666-66/docxtpl-lint
    rev: v0.1.0
    hooks:
      - id: docxtpl-lint
        # args: [--data, tests/sample_context.json]
```

**Plain shell:** `docxtpl-lint --format github templates/*.docx`

## What it does not check

- Runtime errors: unknown filters, wrong types, failing `include`, macro signature mismatches, custom
  `jinja_env` extensions. The linter assumes docxtpl's default `jinja2.Environment()`.
- Parts docxtpl does not render: endnotes, comments, charts, embedded objects. Text boxes are checked as part of their paragraph.
- `¶N` counts every `<w:p>` of the part, including empty paragraphs inside table cells. Use the table path and the printed
  snippet to find the spot in Word.
- DTL201 follows the regex of docxtpl ≤ 0.20.2. If upstream relaxes it (open PR
  [#645](https://github.com/elapouya/python-docx-template/pull/645)), use `--ignore DTL201`.

## Related

[lintxtpl](https://github.com/splittist/lintxtpl) by splittist was the first linter for docxtpl templates and can write an
annotated `.docx` with Word comments. docxtpl-lint focuses on table-cell locations, docxtpl-specific rules and checks
against sample data.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Every new docxtpl rule needs a case in `tests/rule_cases.py` that renders with the real docxtpl.

## License

MIT
