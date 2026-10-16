# docxtpl-lint

[English](README.md) | 中文

**一个用于 [docxtpl](https://github.com/elapouya/python-docx-template)（python-docx-template）Word 模板的静态检查工具。
它能将每个问题定位到确切的表格单元格，一次运行报告所有问题，并返回可供 CI 使用的退出码。**

**[▶ 在浏览器中试用](https://yq6666-66.github.io/docxtpl-lint/)**：拖入一个 `.docx` 即可查看报告。文件永远不会
离开你的电脑；该检查工具通过 Pyodide 在本地运行。

![docxtpl-lint 输出](https://raw.githubusercontent.com/yq6666-66/docxtpl-lint/main/docs/demo-zh.svg)

docxtpl 本身只会给你这样的信息，没有位置，而且只报第一个错误：

```text
jinja2.exceptions.TemplateSyntaxError: Encountered unknown tag 'endfor'. Jinja was looking for the following tags: 'elif' or 'else' or 'endif'.
```

> 与 python-docx-template 无隶属关系。已针对 docxtpl 0.20.2 测试，并每周对照 docxtpl 的最新发布版和 master 进行检查。

## 基准测试：docxtpl 自带的模板

python-docx-template 的 `tests/templates` 中的 40 个模板由 docxtpl 维护者编写，可正确渲染，
除了 `template_error_tpl.docx`，它是故意损坏的。CI 每周对它们全部进行检查
（[`scripts/benchmark.py`](scripts/benchmark.py)、[`benchmark/expected.json`](benchmark/expected.json)）：

| 版本 | 误报 | 发现的故意错误 |
|---|---|---|
| 0.1.0 | 7（`cellbg`/`colspan`/`vm`/`hm` 标签、Word 智能引号） | 是（DTL102） |
| 0.2.0 | **0** | 是（DTL102） |
| 1.0.0 | **0** | 是（DTL102） |

全部 40 个模板的检查耗时约 0.1 秒。自 1.0 起，基准测试还会运行 `verify`（推断示例数据，然后用真正的 docxtpl 渲染）：
40 个模板中有 37 个仅凭推断数据即可渲染，且 0 个 DTL401 误报。其余三个分别是故意损坏的模板，以及两个需要 Python 对象的模板（一个自定义 Jinja 过滤器、一个传入上下文的函数）。

## 对抗测试（1.1）

DeepSeek 根据文档设计了 86 个对抗性模板（[用例](docs/eval/adversarial_cases.json)），每个都生成为真实的 `.docx`，并用 docxtpl 实际渲染来裁决分歧。第一轮发现 5 个真实问题，已在 1.1 全部修复：字符串里的 `}}`、未闭合的 `{% raw %}`、注释被当成丢失文本、`{%tr %}` 行中其他单元格的文本、报错旁多余的 DTL209。现在 86 个用例在 CI 中全部符合[裁决后的预期](benchmark/adversarial_adjudicated.json)。报告：[DeepSeek 评估](docs/eval/deepseek-eval.md)、[自评](docs/eval/self-eval.md)。

<!-- releases -->

## 1.4 的新特性：修订记录和域代码

- **DTL003**：未接受的修订删除里还有 `{{ … }}`。docxtpl 也会渲染被删除的文字，渲染出的值会泄漏到每份生成文档的修订记录里。解决办法：先接受或拒绝全部修订。
- **域代码**（如 `HYPERLINK "{{ url }}"`）会被 docxtpl 渲染，现在也纳入检查和数据契约。

## 1.3 的新特性：Jinja 正确性

- **DTL104 / DTL105**：未知的过滤器和测试。例如 `{{ total|money }}` 会让 docxtpl 在渲染前就报错。如果你传了自己的 `jinja_env`，用 `--filters money`、`--tests vat`、配置项 `filters` / `tests`，或 `--jinja-env myapp.reports:jinja_env` 声明这些名字。
- **DTL106**：循环变量或循环里 `set` 的变量在循环外使用，结果是输出为空或报错。要把值带出循环，请用 `namespace()`。

## 1.2 的新特性：借鉴其他检查工具

从 19 个项目的调研中挑选（[docs/research/oss-survey.md](docs/research/oss-survey.md)，决策 D74–D86）：

| 功能 | 命令 / 写法 | 借鉴自 |
|---|---|---|
| 段落级抑制 | 在该段落里写 `{# docxtpl-lint: disable-line=DTL201 #}`，或在它前面单独一段写 `{#p docxtpl-lint: disable-next=DTL209 #}`（渲染时 docxtpl 会删掉这个 `{#p` 段落，不留空行） | ruff `noqa`、djLint |
| 报告无用的抑制注释 | DTL005 | ruff RUF100 |
| 存量模板目录的基线 | 先 `--write-baseline bl.json`，之后 `--baseline bl.json`（或在 pyproject 写 `baseline = "bl.json"`）：只有新增问题才会失败。条目按部件、单元格和段落文字定位，插入段落不会失效 | ESLint bulk suppressions |
| 按规则统计 | `--statistics` | ruff |
| 给只用 Word 的人看的标注副本 | `--annotate out/` 生成 `名称.annotated.docx`，每个有问题的段落一条 Word 批注；原模板不动 | lintxtpl |
| 数据的 Pydantic v2 模型 | `docxtpl-lint infer a.docx --pydantic models.py` | datamodel-code-generator |

## 1.0 的新特性：从检查到数据契约

有五件事是其他 docxtpl 工具都做不到的（推理过程见 [docs/PLAN-v1.0.md](docs/PLAN-v1.0.md)）：

| | 命令 | 你能得到什么 |
|---|---|---|
| 1 | `docxtpl-lint infer a.docx b.docx -o schema.json --sample sample.json` | 模板的**数据契约，以 JSON Schema 表示**（来自 `for` 循环的列表、嵌套字段、来自 `round`/算术/比较的数字、来自 `is defined`/`default` 的可选字段），跨模板合并，每个字段带 `x-docxtpl-templates`，外加可渲染的示例数据 |
| 2 | `docxtpl-lint verify a.docx` | **渲染等价性检查**：用真正的 docxtpl 和唯一哨兵值渲染，然后报告每一个静默消失的 `{{ value }}`（DTL401）或渲染失败（DTL402）。需要 `pip install "docxtpl-lint[render]"` |
| 3 | `docxtpl-lint diff old.docx new.docx --fail-on-breaking` | **模板版本之间的契约差异**：新增必填字段、列表 ↔ 对象变更、可选 → 必填属于破坏性变更；移除字段不属于；重命名会给出提示 |
| 4 | `docxtpl-lint a.docx --schema schema.json` | **模式一致性**：每个变量都必须在契约中声明（DTL304），循环必须遍历数组（DTL305） |
| 5 | `docxtpl-lint fix a.docx` | **以统一 diff 形式给出的修复建议**：`{% tr` → `{%tr`、前缀不匹配、`endfro` → `endfor`、`iff` → `if`、`custmer` → `customer`（配合 `--data`）。`.docx` 永远不会被改写；每种修复都会通过应用它并用 docxtpl 渲染来测试 |

`verify` 发现了 docxtpl 的一个没有任何规则覆盖的行为：紧邻 `{%p %}`、`{%tr %}` 或 `{%tc %}` 标签的文本会
在输出中被丢弃而不报错。这现在是静态规则 **DTL209**。在线试用页（Playground）也会显示修复建议以及推断出的模式/示例数据。

```console
$ docxtpl-lint verify invoice.docx
invoice.docx:body ¶1:7: error DTL401 `{{ total }}` was rendered by docxtpl but its value does not appear in the output document
    {{ total }}
      > ¶1             | Total {{ total }} {%p if x %}
        ¶2             | {%p endif %}
```

## 特性

- **表格单元格位置。** 每个问题都会指明部件（正文、`header1`、`footer2`、脚注）、段落，对于表格
  还会给出类似 `T1 R2 C2 > T2 R2 C1` 的路径（表格、行、列；支持嵌套表格）。有问题的标签文本始终会被打印出来。
- **一次运行找出所有块级问题。** 未闭合的 `if`/`for`、多余的 `endfor`/`else`，以及永不闭合的标签，都会用
  检查工具自己的标签栈找出，因此你无需反复修复-渲染。其他 Jinja 语法错误会像 Jinja 本身那样，每个文档部件报告一次。
- **了解 docxtpl 自己的标签。** `{%tr %}`、`{%tc %}`、`{%p %}`、`{%r %}`。每条 docxtpl 规则都有一个测试，用真正的 docxtpl
  渲染一个坏模板，并检查它确实会出错。
- **用示例数据检查模板。** `--data sample.json` 检查每个变量路径，包括嵌套字段和
  循环项，如 `items[*].price`。用 `is defined` 或 `| default(...)` 保护的路径不会被报告。
- **为 CI 而生。** 退出码、`--format json|github|sarif`、一个 GitHub Action 和一个 pre-commit 钩子。
- **只读。** 你的 `.docx` 永远不会被修改。检查工具用 lxml 读取 OOXML，不导入 docxtpl
  （只有 `verify` 会，通过可选的 `[render]` 附加项）。

## 安装

从 [PyPI](https://pypi.org/project/docxtpl-lint/) 安装：

```sh
pip install docxtpl-lint
pip install "docxtpl-lint[render]"   # + verify
```

## 用法

```sh
docxtpl-lint templates/*.docx
docxtpl-lint contract.docx --data sample.json            # + data checks (repeat --data for several contexts)
docxtpl-lint contract.docx --format json > report.json   # machine readable (schema_version: 1)
docxtpl-lint contract.docx --list-vars                   # which data does this template need?
docxtpl-lint contract.docx --lang zh                     # 中文提示
docxtpl-lint contract.docx --context 2                   # show 2 paragraphs around each issue
docxtpl-lint --list-rules
docxtpl-lint --explain DTL209                           # 规则说明及示例链接
docxtpl-lint infer contract.docx -o schema.json --sample sample.json
docxtpl-lint contract.docx --schema schema.json           # DTL304/305
docxtpl-lint verify contract.docx                        # needs docxtpl-lint[render]
docxtpl-lint diff v1/contract.docx v2/contract.docx --fail-on-breaking
docxtpl-lint fix contract.docx [--data sample.json]      # prints diffs, never writes
docxtpl-lint templates/*.docx --statistics               # count per rule
docxtpl-lint templates/*.docx --write-baseline bl.json   # accept today's findings ...
docxtpl-lint templates/*.docx --baseline bl.json         # ... and fail only on new ones
docxtpl-lint templates/*.docx --annotate review/         # copies with Word comments
docxtpl-lint infer contract.docx --pydantic models.py    # Pydantic v2 models
```

| 退出码 | 含义 |
|---|---|
| 0 | 无错误（除非 `--warnings-as-errors`，否则允许有警告） |
| 1 | 发现错误 |
| 2 | 参数错误、文件缺失、`.docx` / JSON 无法读取 |

其他选项：`--select DTL1,DTL206`、`--ignore DTL2`（前缀匹配）、`--allow-cross-paragraph`、
`--report-unused-data`、`--warnings-as-errors`、`--no-color`。

`--context N` 会打印周围段落及其表格位置，这样你无需打开 Word 就能找到位置。
在终端中默认为 1，在 CI 日志和管道中默认为 0。

### 配置

将默认值放在最近的 `pyproject.toml` 中。命令行选项优先，未知键会报错（退出码 2）：

```toml
[tool.docxtpl-lint]
ignore = ["DTL002"]
data = ["tests/sample_context.json"]  # relative to this pyproject.toml
warnings-as-errors = true
lang = "en"                           # or "zh"
# also: select, allow-cross-paragraph, report-unused-data, context, baseline, filters, tests, jinja-env
```

使用 `--config path/to/pyproject.toml` 指定文件，或用 `--no-config` 忽略它。

要为某个模板静默规则，可在其中任意位置放入 Jinja 注释（docxtpl 会将其渲染为空）：
`{# docxtpl-lint: disable=DTL301,DTL002 #}`。只针对一个段落时用 `disable-line=` / `disable-next=`（见
[docs/rules.md](docs/rules.md)）；没有匹配到任何问题的抑制注释会报 DTL005。

## 规则

每条规则都有示例和修复方法，见 [docs/rules.md](docs/rules.md)。JSON 和 SARIF 输出会链接到对应条目。

| id | 严重性 | 内容 | docxtpl 的行为 |
|---|---|---|---|
| DTL001 | error | 一个 `{{`、`{%` 或 `{#` 永不闭合 | 抛出异常 |
| DTL002 | warning | 一个标签跨越多个段落 | 合并段落，因此其格式会丢失 |
| DTL101 | error | 未闭合的 `if` / `for` / `with` / ... | 抛出异常，无位置信息 |
| DTL102 | error | `endX` / `else` / `elif` 没有对应的块 | 抛出异常，无位置信息 |
| DTL103 | error | 其他 Jinja2 语法错误，包括 `{% do %}` / `{% break %}`（docxtpl 中未启用） | 抛出异常 |
| DTL201 | error | `{%p/tr/tc/r … %}` 内的 `%` 或 `}` | 抛出异常（[#644](https://github.com/elapouya/python-docx-template/issues/644)） |
| DTL202 | error | `{% tr …`：`tr`/`tc`/`p`/`r` 前缀前有空格 | 抛出 "unknown tag" |
| DTL203 | error | `tr`/`tc` 标签在表格之外 | 抛出异常 |
| DTL204 | error | 前缀不匹配，例如 `{% for %}` … `{%tr endfor %}` | **静默地**丢失循环行（[#603](https://github.com/elapouya/python-docx-template/issues/603)） |
| DTL205 | error | `{%tr for %}` 和 `{%tr endfor %}` 在不同的表格中 | **静默地**丢失行 |
| DTL206 | error | `{%tr for %}` 和 `{%tr endfor %}` 在同一行中 | 抛出异常 |
| DTL207 | error | `{%tc for %}` 和 `{%tc endfor %}` 在不同的行中 | **静默地**破坏表格 |
| DTL208 | error | `{% cellbg %}` / `{% colspan %}` / `{% vm %}` / `{% hm %}` 在表格单元格之外 | 抛出 "unknown tag" |
| DTL209 | error | 与 `{%p %}` / `{%tr %}` / `{%tc %}` 标签在同一段 / 同一行 / 同一单元格的其他文本 | **静默地**丢弃该文本 |
| DTL210 | error | `{%p if %}` … `{%p endif %}` 写在同一段里 | 抛出异常 |
| DTL301 | error | （`--data`）变量在每个示例上下文中都缺失 | 渲染为空或抛出异常 |
| DTL302 | warning | （`--report-unused-data`）顶层数据键从未被使用 | 不适用 |
| DTL303 | error | （`--data`）对数字 / 布尔值 / null 进行 `for` | 在渲染时抛出异常 |
| DTL304 | error | （`--schema`）变量未在 JSON Schema 中声明 | 不适用（契约） |
| DTL305 | error | （`--schema`）对模式声明为数字 / 布尔值 / null 的值进行 `for` | 在渲染时抛出异常 |
| DTL401 | error | （`verify`）渲染出的 `{{ value }}` 在输出中缺失 | **静默地**丢失内容 |
| DTL402 | error | （`verify`）docxtpl 无法用推断的 / 给定的数据渲染 | 抛出异常 |

### 上游 issue → 规则

| python-docx-template issue | 由以下规则覆盖 |
|---|---|
| [#378](https://github.com/elapouya/python-docx-template/issues/378)："help to locate the error in the template" | 每条规则的位置；DTL101/102/103 |
| [#603](https://github.com/elapouya/python-docx-template/issues/603)："Why can't it loop in the table?" | DTL202、DTL204、DTL205、DTL206、DTL207 |
| [#644](https://github.com/elapouya/python-docx-template/issues/644)：`{%p %}` 遇到 `%` 或 `}` 时失败 | DTL201 |
| [#538](https://github.com/elapouya/python-docx-template/issues/538) / [#391](https://github.com/elapouya/python-docx-template/issues/391)：模板使用了哪些（嵌套）变量？ | `--list-vars`、`infer`（JSON Schema）、DTL301 |

## 在 CI 中使用

**GitHub Action**（注解会出现在运行记录和 PR 中）：

```yaml
- uses: actions/checkout@v7
- uses: yq6666-66/docxtpl-lint@v1.4.0
  with:
    files: |
      templates/**/*.docx
    args: --data tests/sample_context.json
```

**pre-commit**

```yaml
repos:
  - repo: https://github.com/yq6666-66/docxtpl-lint
    rev: v1.4.0
    hooks:
      - id: docxtpl-lint
        # args: [--data, tests/sample_context.json]
```

**纯 shell：** `docxtpl-lint --format github templates/*.docx`

**reviewdog**（SARIF 输入，可以在 PR 里写行内评审意见）：

```sh
docxtpl-lint --format sarif templates/*.docx | reviewdog -f=sarif -name=docxtpl-lint -reporter=github-pr-review
```

## 它不检查什么

- 运行时错误：未知过滤器、类型错误、失败的 `include`、宏签名不匹配、自定义
  `jinja_env` 扩展。检查工具假定使用 docxtpl 默认的 `jinja2.Environment()`。
- docxtpl 不渲染的部件：尾注、批注、图表、嵌入对象。文本框作为其段落的一部分被检查。
- `¶N` 会统计该部件的每个 `<w:p>`，包括表格单元格内的空段落。使用表格路径和打印出的
  片段来在 Word 中找到位置。
- DTL201 遵循 docxtpl ≤ 0.20.2 的正则。如果上游放宽了它（开放的 PR
  [#645](https://github.com/elapouya/python-docx-template/pull/645)），请使用 `--ignore DTL201`。

## 相关

splittist 的 [lintxtpl](https://github.com/splittist/lintxtpl) 是第一个用于 docxtpl 模板的检查工具，可以写出带
Word 批注的标注 `.docx`（docxtpl-lint 1.2 借鉴了这个思路，即 `--annotate`）。docxtpl-lint 专注于表格单元格位置、docxtpl 特有的规则以及针对示例数据的检查。

## 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。每条新的 docxtpl 规则都需要在 `tests/rule_cases.py` 中有一个用真正的 docxtpl 渲染的用例。

## 许可证

MIT
