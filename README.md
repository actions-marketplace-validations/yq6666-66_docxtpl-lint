# docxtpl-lint

**Static linter for [docxtpl](https://github.com/elapouya/python-docx-template) Word templates. It points each error to the exact table cell, so you don't have to scroll through a 40-page contract hunting for a stray `{% endif %}`.**

[中文说明](#中文说明) · [Rules](#rules) · [CI](#use-in-ci)

```text
$ docxtpl-lint invoice.docx
invoice.docx:body ¶7 [表2 行3 列1 ¶1]:1: error DTL101 `{% if %}` 未闭合，缺少 `{% endif %}`（直到文档末尾 / until end of part）/ unclosed block
    {% if paid %}
invoice.docx:body ¶9:10: error DTL001 标签 `{{` 在本段内没有闭合 `}}` / tag `{{` not closed within the paragraph
    {{ client.
invoice.docx:body ¶11:1: error DTL102 `{% endfor %}` 没有对应的开始标签 / has no matching opening tag
    {% endfor %}

✖ 3 error(s), 0 warning(s) in 1 file(s)
```

docxtpl itself only gives you this (no location, and only the first error):

```text
jinja2.exceptions.TemplateSyntaxError: Encountered unknown tag 'endfor'. Jinja was looking for ...
```

## Why

- **Exact locations**: part (body/header/footer/footnotes), paragraph number, and for tables a full path such as `表1 行2 列2 > 表2 行2 列1` (nested tables are supported).
- **Reports every error at once**: it uses its own tag stack instead of stopping at the first Jinja exception.
- **Understands docxtpl itself**: `{%tr %}`, `{%tc %}`, `{%p %}` and `{%r %}` tags, and the traps behind real issues [#603](https://github.com/elapouya/python-docx-template/issues/603), [#644](https://github.com/elapouya/python-docx-template/issues/644) and [#378](https://github.com/elapouya/python-docx-template/issues/378).
- **Data contract**: with `--data sample.json` it checks that every variable (including nested ones and fields of loop items such as `items[*].price`) exists in your data.
- **CI-friendly**: exit codes are 0 for clean, 1 for issues and 2 for usage/IO errors. Supports `--format json`, `--select` and `--ignore`. Ships a pre-commit hook and a GitHub Action.
- **No autofix**: it only reads your `.docx` and never modifies it. It does not depend on docxtpl internals; it reads the OOXML directly with lxml.
- **Few false positives on run splits**: tags that Word splits across runs inside one paragraph are fine for docxtpl, so they are not reported.

## Install

```sh
pip install docxtpl-lint
```

## Usage

```sh
docxtpl-lint templates/*.docx
docxtpl-lint contract.docx --data sample.json        # + variable checks
docxtpl-lint contract.docx --format json > report.json
docxtpl-lint contract.docx --list-vars                # what data does this template need?
docxtpl-lint --list-rules
```

## Rules

| id | severity | what |
|---|---|---|
| DTL001 | error | `{{`/`{%`/`{#` opened but not closed in the same paragraph |
| DTL101 | error | unclosed `if` / `for` / `with` / `macro` / ... block |
| DTL102 | error | `endX` / `else` / `elif` without a matching block |
| DTL103 | error | any other Jinja2 syntax error, located to the tag |
| DTL201 | error | `%` or `}` inside `{%p/tr/tc/r … %}`: docxtpl's regex silently truncates it (#644) |
| DTL202 | error | `{% tr for … %}`: a space before the prefix turns it into the unknown tag `tr` |
| DTL203 | error | `tr`/`tc` tag placed outside a table |
| DTL204 | error | prefix mismatch, e.g. `{% for %}` … `{%tr endfor %}` (#603) |
| DTL205 | error | `{%tr for %}` and `{%tr endfor %}` in different tables |
| DTL206 | error | `{%tr for %}` and `{%tr endfor %}` in the same row: the row gets eaten |
| DTL301 | error | (`--data`) variable missing from the sample data |
| DTL302 | warning | (`--data`) top-level data key never used |

## Use in CI

**GitHub Action**

```yaml
- uses: actions/checkout@v4
- uses: OWNER/docxtpl-lint@v0.1.0
  with:
    files: "templates/**/*.docx"
    args: "--data tests/sample_context.json"
```

**pre-commit**

```yaml
repos:
  - repo: https://github.com/OWNER/docxtpl-lint
    rev: v0.1.0
    hooks:
      - id: docxtpl-lint
```

## Limitations

- Each paragraph is checked independently. A tag deliberately split across paragraphs is reported as DTL001, because docxtpl merges such tags and silently drops the paragraph structure.
- `--data` checks one sample context. An empty list cannot prove that a field is missing, so it is skipped.
- Text boxes are scanned as part of their host part; comments are not scanned.

---

## 中文说明

`docxtpl-lint` 是一个针对 docxtpl（python-docx-template）Word 模板的**静态检查器**。

- **定位到单元格**：告诉你错误在哪一部分（正文、页眉、页脚、脚注）、第几段、哪张表的第几行第几列，嵌套表格也能定位。
- **一次报出全部错误**，不会像 docxtpl 那样只抛第一个错误、而且不给位置。
- **懂 docxtpl 专用语法**：能识别 `{%tr %}`、`{%tc %}`、`{%p %}`、`{%r %}` 的常见坑，比如 tr 开闭标签写在同一行、开闭跨了两张表、前缀不一致、前缀前多了空格、表达式里含 `%` 或 `}`。
- **数据契约**：`--data 样例.json` 会检查模板里用到的每个变量（含嵌套字段和循环项字段）在数据里是否存在。
- **适合 CI**：退出码 0 表示通过，1 表示发现问题，2 表示参数或文件错误。支持 JSON 输出，提供 pre-commit 钩子和 GitHub Action。
- **不做自动修复**，也不会修改你的文档。

```sh
pip install docxtpl-lint
docxtpl-lint 模板/*.docx --data 样例数据.json
```

## License

MIT
