# docxtpl-lint

[English](README.md) | 中文

**一个用于 [docxtpl](https://github.com/elapouya/python-docx-template)（python-docx-template）Word 模板的静态检查工具。
它能把每个问题定位到具体的表格单元格，在一次运行中报告所有问题，并返回可供 CI 使用的退出码。**

**[▶ 在浏览器中试用](https://yq6666-66.github.io/docxtpl-lint/)**：拖入一个 `.docx` 即可查看报告。文件永远不会
离开你的电脑；检查工具通过 Pyodide 在本地运行。

![docxtpl-lint 输出](https://raw.githubusercontent.com/yq6666-66/docxtpl-lint/main/docs/demo-zh.svg)

docxtpl 本身只会给你这样的信息，没有位置，而且只报第一个错误：

```text
jinja2.exceptions.TemplateSyntaxError: Encountered unknown tag 'endfor'. Jinja was looking for the following tags: 'elif' or 'else' or 'endif'.
```

> 与 python-docx-template 无隶属关系。已针对 docxtpl 0.20.2 测试，并每周对照 docxtpl 的最新发布版和 master 进行检查。

## 基准测试：docxtpl 自带的模板

python-docx-template 的 `tests/templates` 中有 40 个模板，由 docxtpl 维护者编写，均能正确渲染，
除了 `template_error_tpl.docx`，它是故意写坏的。CI 每周都会检查所有这些模板
（[`scripts/benchmark.py`](scripts/benchmark.py)、[`benchmark/expected.json`](benchmark/expected.json)）：

| 版本 | 误报 | 发现的故意错误 |
|---|---|---|
| 0.1.0 | 7（`cellbg`/`colspan`/`vm`/`hm` 标签、Word 智能引号） | 是（DTL102） |
| 0.2.0 | **0** | 是（DTL102） |

全部 40 个模板的检查耗时约 0.1 秒。

## 特性

- **表格单元格位置。** 每个问题都会指明所在部分（正文、`header1`、`footer2`、脚注）、段落，对于表格
  还会给出类似 `T1 R2 C2 > T2 R2 C1` 的路径（表格、行、列；支持嵌套表格）。有问题的标签文本始终会被打印出来。
- **一次运行报告所有块级问题。** 未闭合的 `if`/`for`、多余的 `endfor`/`else`，以及永不闭合的标签，都会通过
  检查工具自己的标签栈被发现，因此你无需反复修复-渲染。其他 Jinja 语法错误按文档部分各报告一次，
  与 Jinja 本身的行为一致。
- **了解 docxtpl 自己的标签。** `{%tr %}`、`{%tc %}`、`{%p %}`、`{%r %}`。每条 docxtpl 规则都有一个测试，会用真实的 docxtpl
  渲染一个坏模板，并检查它确实会出错。
- **用示例数据检查模板。** `--data sample.json` 会检查每个变量路径，包括嵌套字段和
  循环项，如 `items[*].price`。用 `is defined` 或 `| default(...)` 保护的路径不会被报告。
- **为 CI 而构建。** 退出码、`--format json|github|sarif`、一个 GitHub Action 和一个 pre-commit 钩子。
- **只读。** 你的 `.docx` 永远不会被修改。检查工具用 lxml 读取 OOXML，不导入 docxtpl。

## 安装

```sh
pip install docxtpl-lint
```

## 用法

```sh
docxtpl-lint templates/*.docx
docxtpl-lint contract.docx --data sample.json            # + 数据检查（可重复 --data 以提供多个上下文）
docxtpl-lint contract.docx --format json > report.json   # 机器可读（schema_version: 1）
docxtpl-lint contract.docx --list-vars                   # 这个模板需要哪些数据？
docxtpl-lint contract.docx --lang zh                     # 中文提示
docxtpl-lint contract.docx --context 2                   # 显示每个问题周围的 2 个段落
docxtpl-lint --list-rules
```

| 退出码 | 含义 |
|---|---|
| 0 | 无错误（除非 `--warnings-as-errors`，否则允许有警告） |
| 1 | 发现错误 |
| 2 | 参数错误、文件缺失、`.docx` / JSON 无法读取 |

其他选项：`--select DTL1,DTL206`、`--ignore DTL2`（前缀匹配）、`--allow-cross-paragraph`、
`--report-unused-data`、`--warnings-as-errors`、`--no-color`。

`--context N` 会打印周围段落及其表格位置，让你无需打开 Word 就能找到位置。
在终端中默认为 1，在 CI 日志和管道中默认为 0。

### 配置

将默认值放在最近的 `pyproject.toml` 中。命令行选项优先，未知键会报错（退出码 2）：

```toml
[tool.docxtpl-lint]
ignore = ["DTL002"]
data = ["tests/sample_context.json"]  # 相对于此 pyproject.toml
warnings-as-errors = true
lang = "en"                           # 或 "zh"
# 还有：select, allow-cross-paragraph, report-unused-data, context
```

使用 `--config path/to/pyproject.toml` 指定文件，或用 `--no-config` 忽略它。

要为某个模板静默规则，可在其中任意位置放一条 Jinja 注释（docxtpl 会将其渲染为空）：
`{# docxtpl-lint: disable=DTL301,DTL002 #}`

## 规则

每条规则都有示例和修复方法，见 [docs/rules.md](docs/rules.md)。JSON 和 SARIF 输出会链接到对应条目。

| id | 严重级别 | 内容 | docxtpl 的行为 |
|---|---|---|---|
| DTL001 | error | 一个 `{{`、`{%` 或 `{#` 从未闭合 | 抛出异常 |
| DTL002 | warning | 一个标签跨越多个段落 | 合并这些段落，因此其格式会丢失 |
| DTL101 | error | 未闭合的 `if` / `for` / `with` / ... | 抛出异常，无位置信息 |
| DTL102 | error | 没有对应块的 `endX` / `else` / `elif` | 抛出异常，无位置信息 |
| DTL103 | error | 其他 Jinja2 语法错误，包括 `{% do %}` / `{% break %}`（docxtpl 中未启用） | 抛出异常 |
| DTL201 | error | `{%p/tr/tc/r … %}` 内的 `%` 或 `}` | 抛出异常（[#644](https://github.com/elapouya/python-docx-template/issues/644)） |
| DTL202 | error | `{% tr …`：`tr`/`tc`/`p`/`r` 前缀前有空格 | 抛出 "unknown tag" |
| DTL203 | error | 表格外的 `tr`/`tc` 标签 | 抛出异常 |
| DTL204 | error | 前缀不匹配，例如 `{% for %}` … `{%tr endfor %}` | **静默地**丢失循环行（[#603](https://github.com/elapouya/python-docx-template/issues/603)） |
| DTL205 | error | `{%tr for %}` 和 `{%tr endfor %}` 在不同的表格中 | **静默地**丢失行 |
| DTL206 | error | `{%tr for %}` 和 `{%tr endfor %}` 在同一行中 | 抛出异常 |
| DTL207 | error | `{%tc for %}` 和 `{%tc endfor %}` 在不同的行中 | **静默地**破坏表格 |
| DTL208 | error | `{% cellbg %}` / `{% colspan %}` / `{% vm %}` / `{% hm %}` 在表格单元格之外 | 抛出 "unknown tag" |
| DTL301 | error | （`--data`）变量在所有示例上下文中都缺失 | 渲染为空或抛出异常 |
| DTL302 | warning | （`--report-unused-data`）顶层数据键从未被使用 | 不适用 |
| DTL303 | error | （`--data`）对数字 / 布尔值 / null 进行 `for` | 渲染时抛出异常 |

### 上游问题 → 规则

| python-docx-template 问题 | 由以下规则覆盖 |
|---|---|
| [#378](https://github.com/elapouya/python-docx-template/issues/378)："help to locate the error in the template" | 每条规则的位置；DTL101/102/103 |
| [#603](https://github.com/elapouya/python-docx-template/issues/603)："Why can't it loop in the table?" | DTL202、DTL204、DTL205、DTL206、DTL207 |
| [#644](https://github.com/elapouya/python-docx-template/issues/644)：`{%p %}` 遇到 `%` 或 `}` 时失败 | DTL201 |
| [#538](https://github.com/elapouya/python-docx-template/issues/538) / [#391](https://github.com/elapouya/python-docx-template/issues/391)：模板使用了哪些（嵌套）变量？ | `--list-vars`、DTL301 |

## 在 CI 中使用

**GitHub Action**（注释会出现在运行记录和 PR 中）：

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

**纯 shell：** `docxtpl-lint --format github templates/*.docx`

## 它不检查什么

- 运行时错误：未知过滤器、类型错误、失败的 `include`、宏签名不匹配、自定义
  `jinja_env` 扩展。检查工具假定使用 docxtpl 默认的 `jinja2.Environment()`。
- docxtpl 不渲染的部分：尾注、批注、图表、嵌入对象。文本框作为其段落的一部分被检查。
- `¶N` 统计该部分的每个 `<w:p>`，包括表格单元格内的空段落。请使用表格路径和打印的
  片段来在 Word 中找到位置。
- DTL201 遵循 docxtpl ≤ 0.20.2 的正则。如果上游放宽了它（开放的 PR
  [#645](https://github.com/elapouya/python-docx-template/pull/645)），请使用 `--ignore DTL201`。

## 相关项目

splittist 的 [lintxtpl](https://github.com/splittist/lintxtpl) 是第一个用于 docxtpl 模板的检查工具，可以写出带
Word 批注的标注 `.docx`。docxtpl-lint 专注于表格单元格位置、docxtpl 特有的规则以及针对
示例数据的检查。

## 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。每条新的 docxtpl 规则都需要在 `tests/rule_cases.py` 中有一个用真实 docxtpl 渲染的用例。

## 许可证

MIT
