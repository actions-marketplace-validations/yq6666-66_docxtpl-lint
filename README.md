# docxtpl-lint

[中文文档 / Chinese](README.zh.md)

**A static linter for [docxtpl](https://github.com/elapouya/python-docx-template) (python-docx-template) Word templates.
It points each problem to the exact table cell, reports all problems in one run, and returns exit codes your CI can use.**

**[▶ Try it in your browser](https://yq6666-66.github.io/docxtpl-lint/)**: drop a `.docx` and see the report. The file never
leaves your computer; the linter runs locally via Pyodide.

![docxtpl-lint output](https://raw.githubusercontent.com/yq6666-66/docxtpl-lint/main/docs/demo.svg)

docxtpl itself only gives you this, with no location and only the first error:

```text
jinja2.exceptions.TemplateSyntaxError: Encountered unknown tag 'endfor'. Jinja was looking for the following tags: 'elif' or 'else' or 'endif'.
```

> Not affiliated with python-docx-template. Tested against docxtpl 0.20.2 and checked weekly against docxtpl's latest release and master.

## Benchmark: docxtpl's own templates

The 40 templates in python-docx-template's `tests/templates` are written by the docxtpl maintainers and render correctly,
except `template_error_tpl.docx`, which is broken on purpose. CI lints all of them every week
([`scripts/benchmark.py`](scripts/benchmark.py), [`benchmark/expected.json`](benchmark/expected.json)):

| version | false positives | deliberate error found |
|---|---|---|
| 0.1.0 | 7 (`cellbg`/`colspan`/`vm`/`hm` tags, Word smart quotes) | yes (DTL102) |
| 0.2.0 | **0** | yes (DTL102) |
| 1.0.0 | **0** | yes (DTL102) |

All 40 templates are linted in about 0.1 s. Since 1.0 the benchmark also runs `verify` (infer sample data, then render
with the real docxtpl): 37 of 40 templates render with inferred data alone, with 0 false DTL401. The other three are the
deliberately broken template and two that need Python objects (a custom Jinja filter, a function passed in the context).

## Tested adversarially (1.1)

DeepSeek designed 86 adversarial templates from the docs ([cases](docs/eval/adversarial_cases.json)). Each was built as
a real `.docx` and also rendered with docxtpl to decide disputes. The first run found 5 real problems, all fixed in 1.1:
`}}` inside a string literal, unclosed `{% raw %}`, comments counted as lost text, text in other cells of a `{%tr %}` row,
and noisy DTL209 next to errors. Now all 86 cases match the
[adjudicated expectations](benchmark/adversarial_adjudicated.json) in CI. Reports: [DeepSeek's evaluation](docs/eval/deepseek-eval.md),
[self-evaluation](docs/eval/self-eval.md).

<!-- releases -->

## New in 1.9: stable Python API

```python
from docxtpl_lint import check_context, lint

lint("invoice.docx").raise_for_errors()           # static, in tests or CI
res = check_context(tpl_bytes, ctx, jinja_env=env)  # right before rendering in your app
if not res.ok:
    log.error(res.to_dict())
```

Semver-stable (docs/api.md). `--fail-on error|warning|never` replaces the deprecated `--warnings-as-errors` (removed in 2.0).

## New in 1.8: CI ecosystem

- The GitHub Action writes a Markdown table to the job summary. New inputs: `baseline`, `sarif: docxtpl-lint.sarif` (for `github/codeql-action/upload-sarif`), and `annotate: true` (failing templates with Word comments, uploaded as an artifact).
- `--format gitlab` for GitLab Code Quality; `--format markdown`; `--report FORMAT:FILE` to write several reports in one run. Findings carry stable fingerprints, so CI tools can track them across commits.

## New in 1.7: fix --write

`docxtpl-lint fix contract.docx --write contract.fixed.docx` applies the safe fixes (missing `}`, `{% tr` → `{%tr`, prefix pairs, misspelt `endfro`) to a **copy**, editing inside the existing Word runs so formatting is kept. Guesses (e.g. renaming `custmer` after `--data`) need `--unsafe`. The original template is never touched.

## New in 1.6: escaping and a stronger verify

- **DTL308** (with `--data`): docxtpl renders with `autoescape=False` by default, so `Smith & Co` becomes `Smith  Co` and `<b>` cuts the paragraph, with no error. Use `render(ctx, autoescape=True)` (and `--autoescape`) or `{{ name|e }}`.
- `verify` now renders the way your code does (`--jinja-env`, `--autoescape`, several `--data` files), checks `{{r}}` / `{{p}}` too, and can keep the output with `--out DIR`.

## New in 1.5: a more precise data contract

- List and attribute filters feed the contract: `items|sum(attribute='price')` makes `items[].price` a number, and loops over `items|selectattr('ok')` keep the item fields.
- **DTL306** (with `--data`): `tags|join(", ")` on a string silently prints `u, r, g, e, n, t`; on a number it raises.
- **DTL307** (with `--data`): `{{r note }}` with a plain string renders nothing. The schema and Pydantic models mark such fields as `RichText` / `Subdoc`.

## New in 1.4: tracked changes and field codes

- **DTL003**: an unaccepted tracked deletion that still contains `{{ … }}`. docxtpl renders deleted text too, so the value leaks into the revision history of every generated document. Fix: accept or reject all changes first.
- **Field codes** (`HYPERLINK "{{ url }}"`) are rendered by docxtpl and are now linted and included in the data contract.

## New in 1.3: Jinja correctness

- **DTL104 / DTL105**: unknown filters and tests (`{{ total|money }}` makes docxtpl raise before rendering). If you pass your own `jinja_env`, declare the names with `--filters money`, `--tests vat`, the `filters` / `tests` config keys, or `--jinja-env myapp.reports:jinja_env`.
- **DTL106**: a loop variable or a `set` inside a loop used after the loop. It renders empty or raises; use `namespace()` instead.

## New in 1.2: ideas from other linters

Picked from a survey of 19 projects ([docs/research/oss-survey.md](docs/research/oss-survey.md), decisions D74–D86):

| Feature | Command / syntax | Borrowed from |
|---|---|---|
| Paragraph-level suppression | `{# docxtpl-lint: disable-line=DTL201 #}` in the paragraph, or `{#p docxtpl-lint: disable-next=DTL209 #}` on its own line before it (docxtpl removes that `{#p` paragraph when rendering) | ruff `noqa`, djLint |
| Unused suppressions are reported | DTL005 | ruff RUF100 |
| Baseline for legacy template folders | `--write-baseline bl.json`, then `--baseline bl.json` (or `baseline = "bl.json"` in pyproject): only new findings fail. Entries are keyed by part, table cell and paragraph text, so they survive inserted paragraphs | ESLint bulk suppressions |
| Per-rule counts | `--statistics` | ruff |
| Annotated copy for Word users | `--annotate out/` writes `name.annotated.docx` with one Word comment per paragraph with findings; the template itself is not touched | lintxtpl |
| Pydantic v2 models for the data | `docxtpl-lint infer a.docx --pydantic models.py` | datamodel-code-generator |

## What's new in 1.0: from linting to data contracts

Five things no other docxtpl tool does (see [docs/PLAN-v1.0.md](docs/PLAN-v1.0.md) for the reasoning):

| | command | what you get |
|---|---|---|
| 1 | `docxtpl-lint infer a.docx b.docx -o schema.json --sample sample.json` | the template's **data contract as JSON Schema** (lists from `for` loops, nested fields, numbers from `round`/arithmetic/comparisons, optional fields from `is defined`/`default`), merged across templates with `x-docxtpl-templates` per field, plus sample data that renders |
| 2 | `docxtpl-lint verify a.docx` | **render-equivalence check**: renders with the real docxtpl and unique sentinel values, then reports every `{{ value }}` that silently vanished (DTL401) or a render that fails (DTL402). Needs `pip install "docxtpl-lint[render]"` |
| 3 | `docxtpl-lint diff old.docx new.docx --fail-on-breaking` | **contract diff between template versions**: new required fields, list ↔ object changes, optional → required are breaking; removed fields are not; renames are hinted |
| 4 | `docxtpl-lint a.docx --schema schema.json` | **schema conformance**: every variable must be declared in the contract (DTL304), loops must be over arrays (DTL305) |
| 5 | `docxtpl-lint fix a.docx` | **fix suggestions as unified diffs**: `{% tr` → `{%tr`, mismatched prefixes, `endfro` → `endfor`, `iff` → `if`, `custmer` → `customer` (with `--data`). The `.docx` is never rewritten; every fix kind is tested by applying it and rendering with docxtpl |

`verify` found a docxtpl behaviour that no rule covered: text next to a `{%p %}`, `{%tr %}` or `{%tc %}` tag is dropped from
the output without an error. That is now the static rule **DTL209**. The playground shows the fix suggestions and the
inferred schema/sample data too.

```console
$ docxtpl-lint verify invoice.docx
invoice.docx:body ¶1:7: error DTL401 `{{ total }}` was rendered by docxtpl but its value does not appear in the output document
    {{ total }}
      > ¶1             | Total {{ total }} {%p if x %}
        ¶2             | {%p endif %}
```

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
- **Read-only.** Your `.docx` is never modified. The linter reads the OOXML with lxml and does not import docxtpl
  (only `verify` does, through the optional `[render]` extra).

## Install

Install from [PyPI](https://pypi.org/project/docxtpl-lint/):

```sh
pip install docxtpl-lint
pip install "docxtpl-lint[render]"   # + verify
```

## Usage

```sh
docxtpl-lint templates/*.docx
docxtpl-lint contract.docx --data sample.json            # + data checks (repeat --data for several contexts)
docxtpl-lint contract.docx --format json > report.json   # machine readable (schema_version: 1)
docxtpl-lint contract.docx --list-vars                   # which data does this template need?
docxtpl-lint contract.docx --lang zh                     # 中文提示
docxtpl-lint contract.docx --context 2                   # show 2 paragraphs around each issue
docxtpl-lint --list-rules
docxtpl-lint --explain DTL209                           # what a rule means, with a link to examples
docxtpl-lint infer contract.docx -o schema.json --sample sample.json
docxtpl-lint contract.docx --schema schema.json           # DTL304/305
docxtpl-lint verify contract.docx                        # needs docxtpl-lint[render]
docxtpl-lint diff v1/contract.docx v2/contract.docx --fail-on-breaking
docxtpl-lint fix contract.docx [--data sample.json]      # prints diffs
docxtpl-lint fix contract.docx --write fixed.docx         # apply safe fixes to a copy
docxtpl-lint templates/*.docx --statistics               # count per rule
docxtpl-lint templates/*.docx --write-baseline bl.json   # accept today's findings ...
docxtpl-lint templates/*.docx --baseline bl.json         # ... and fail only on new ones
docxtpl-lint templates/*.docx --annotate review/         # copies with Word comments
docxtpl-lint infer contract.docx --pydantic models.py    # Pydantic v2 models
```

| exit code | meaning |
|---|---|
| 0 | no findings at the `--fail-on` level (default: errors only) |
| 1 | errors found |
| 2 | bad arguments, missing file, unreadable `.docx` / JSON |

Other options: `--select DTL1,DTL206`, `--ignore DTL2` (prefix match), `--allow-cross-paragraph`,
`--report-unused-data`, `--fail-on error|warning|never`, `--no-color`.

`--context N` prints the surrounding paragraphs with their table position, so you can find the spot without opening Word.
It defaults to 1 in a terminal and 0 in CI logs and pipes.

### Configuration

Put defaults in the nearest `pyproject.toml`. Command-line options take precedence, and unknown keys are an error (exit 2):

```toml
[tool.docxtpl-lint]
ignore = ["DTL002"]
data = ["tests/sample_context.json"]  # relative to this pyproject.toml
fail-on = "warning"
lang = "en"                           # or "zh"
# also: select, allow-cross-paragraph, report-unused-data, context, baseline, filters, tests, jinja-env, autoescape
```

Use `--config path/to/pyproject.toml` to pick a file, or `--no-config` to ignore it.

To silence rules for one template, put a Jinja comment anywhere in it (docxtpl renders it as nothing):
`{# docxtpl-lint: disable=DTL301,DTL002 #}`. For one paragraph use `disable-line=` / `disable-next=` (see
[docs/rules.md](docs/rules.md)); a suppression that matches nothing is reported as DTL005.

## Rules

Each rule has examples and a fix in [docs/rules.md](docs/rules.md). JSON and SARIF output link to the matching entry.

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
| DTL208 | error | `{% cellbg %}` / `{% colspan %}` / `{% vm %}` / `{% hm %}` outside a table cell | raises "unknown tag" |
| DTL209 | error | other text next to a `{%p %}` / `{%tr %}` / `{%tc %}` tag (same paragraph / row / cell) | **silently** drops that text |
| DTL210 | error | `{%p if %}` … `{%p endif %}` in one paragraph | raises |
| DTL301 | error | (`--data`) variable missing from every sample context | renders empty or raises |
| DTL302 | warning | (`--report-unused-data`) top-level data key never used | n/a |
| DTL303 | error | (`--data`) `for` over a number / boolean / null | raises at render time |
| DTL304 | error | (`--schema`) variable not declared in the JSON Schema | n/a (contract) |
| DTL305 | error | (`--schema`) `for` over a value the schema declares as number / boolean / null | raises at render time |
| DTL401 | error | (`verify`) a rendered `{{ value }}` is missing from the output | **silently** loses content |
| DTL402 | error | (`verify`) docxtpl fails to render with the inferred / given data | raises |

### Upstream issues → rules

| python-docx-template issue | covered by |
|---|---|
| [#378](https://github.com/elapouya/python-docx-template/issues/378): "help to locate the error in the template" | every rule's location; DTL101/102/103 |
| [#603](https://github.com/elapouya/python-docx-template/issues/603): "Why can't it loop in the table?" | DTL202, DTL204, DTL205, DTL206, DTL207 |
| [#644](https://github.com/elapouya/python-docx-template/issues/644): `{%p %}` fails with `%` or `}` | DTL201 |
| [#538](https://github.com/elapouya/python-docx-template/issues/538) / [#391](https://github.com/elapouya/python-docx-template/issues/391): which (nested) variables does a template use? | `--list-vars`, `infer` (JSON Schema), DTL301 |

## Use in CI

**GitHub Action** (annotations appear on the run and in the PR):

```yaml
- uses: actions/checkout@v7
- uses: yq6666-66/docxtpl-lint@v1.9.0
  with:
    files: |
      templates/**/*.docx
    args: --data tests/sample_context.json
    # baseline: docxtpl-lint-baseline.json
    # sarif: docxtpl-lint.sarif
    # annotate: true
```

**pre-commit**

```yaml
repos:
  - repo: https://github.com/yq6666-66/docxtpl-lint
    rev: v1.9.0
    hooks:
      - id: docxtpl-lint
        # args: [--data, tests/sample_context.json]
```

**GitLab CI** (Code Quality report):

```yaml
docxtpl-lint:
  image: python:3.12
  script:
    - pip install docxtpl-lint
    - docxtpl-lint --format gitlab -o gl-code-quality.json templates/*.docx
  artifacts:
    when: always
    reports:
      codequality: gl-code-quality.json
```

**Plain shell:** `docxtpl-lint --format github templates/*.docx`

**reviewdog** (reads SARIF, can post PR review comments):

```sh
docxtpl-lint --format sarif templates/*.docx | reviewdog -f=sarif -name=docxtpl-lint -reporter=github-pr-review
```

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
annotated `.docx` with Word comments (docxtpl-lint 1.2 adopted that idea as `--annotate`). docxtpl-lint focuses on table-cell locations, docxtpl-specific rules and checks
against sample data.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Every new docxtpl rule needs a case in `tests/rule_cases.py` that renders with the real docxtpl.

## License

MIT
