"""Rule catalogue and bilingual message templates.

Every rule has a stable id, a default severity, a one-line summary and a message
template in English (default) and Chinese (``--lang zh``). Messages are rendered
with :py:meth:`str.format` from the parameters stored on each issue.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    id: str
    severity: str
    summary: str
    en: str
    zh: str


_RULES = [
    Rule(
        "DTL001",
        "error",
        "tag never closed",
        "`{open}` is never closed with `{close}`",
        "标签 `{open}` 一直没有用 `{close}` 闭合",
    ),
    Rule(
        "DTL002",
        "warning",
        "tag spans several paragraphs",
        "`{open}` is only closed in paragraph ¶{end_para}; docxtpl merges these paragraphs and their "
        "formatting is lost (use --allow-cross-paragraph if intended)",
        "`{open}` 直到第 ¶{end_para} 段才闭合；docxtpl 会把这几段合并成一段，段落格式丢失"
        "（如属有意为之，可加 --allow-cross-paragraph）",
    ),
    Rule(
        "DTL101",
        "error",
        "unclosed block",
        "`{{% {kw} %}}` is never closed: missing `{{% end{kw} %}}`",
        "`{{% {kw} %}}` 没有闭合，缺少 `{{% end{kw} %}}`",
    ),
    Rule(
        "DTL102",
        "error",
        "stray end/else/elif",
        "`{raw}` has no matching opening block",
        "`{raw}` 找不到对应的开始标签",
    ),
    Rule(
        "DTL103",
        "error",
        "Jinja2 syntax error",
        "Jinja2 syntax error: {msg}",
        "Jinja2 语法错误：{msg}",
    ),
    Rule(
        "DTL201",
        "error",
        "`%` or `}` inside a {%p/tr/tc/r %} tag (docxtpl #644)",
        "`{prefix}` tag expression contains `%` or `}}`; docxtpl cannot parse it (python-docx-template "
        "#644). Compute the value with `{{% set %}}` first",
        "`{prefix}` 标签的表达式里含有 `%` 或 `}}`，docxtpl 解析不了（python-docx-template #644）。"
        "请先用 `{{% set %}}` 算好再引用",
    ),
    Rule(
        "DTL202",
        "error",
        "space before tr/tc prefix",
        "write `{{%{prefix} …` without a space; `{{% {prefix} …` is an unknown Jinja tag",
        "应写成 `{{%{prefix} …`，中间不能有空格；`{{% {prefix} …` 会被当成未知的 Jinja 标签",
    ),
    Rule(
        "DTL203",
        "error",
        "tr/tc tag outside a table",
        "`{raw}` uses the `{prefix}` prefix but is not inside a table cell",
        "`{raw}` 使用了 `{prefix}` 前缀，但不在表格单元格里",
    ),
    Rule(
        "DTL204",
        "error",
        "prefix mismatch between opening and closing tag (docxtpl #603)",
        "`{close_raw}` closes `{open_raw}` ({open_loc}) but the prefixes differ ({open_prefix} vs {close_prefix}); "
        "docxtpl removes the row/paragraph only for one of them",
        "`{close_raw}` 关闭的是 `{open_raw}`（{open_loc}），但两者前缀不一致（{open_prefix} vs {close_prefix}）；"
        "docxtpl 只会删掉其中一处的行/段落",
    ),
    Rule(
        "DTL205",
        "error",
        "{%tr %} block spans two tables",
        "`{open_raw}` is in table {t1} but `{close_raw}` is in table {t2}; docxtpl renders this without error "
        "but the rows are silently lost",
        "`{open_raw}` 在表 {t1}，`{close_raw}` 却在表 {t2}；docxtpl 不会报错，但行会被静默丢掉",
    ),
    Rule(
        "DTL206",
        "error",
        "{%tr %} open and close in the same row",
        "`{open_raw}` and `{close_raw}` are in the same row (table {table}, row {row}); docxtpl replaces the "
        "whole row with the first tag and the template fails. Put them in separate rows",
        "`{open_raw}` 和 `{close_raw}` 在同一行（表 {table} 行 {row}）；docxtpl 会用第一个标签替换整行，"
        "渲染失败。请把它们放在不同的行",
    ),
    Rule(
        "DTL207",
        "error",
        "{%tc %} block must stay inside one row",
        "`{open_raw}` and `{close_raw}` are in different rows/tables; docxtpl produces a corrupt table",
        "`{open_raw}` 和 `{close_raw}` 不在同一行或同一张表；docxtpl 生成的表格结构会错乱",
    ),
    Rule(
        "DTL208",
        "error",
        "cellbg/colspan/vm/hm tag outside a table cell",
        "`{raw}` only works inside a table cell; docxtpl leaves it to Jinja, which fails with 'unknown tag'",
        "`{raw}` 只能写在表格单元格里；放在别处时 docxtpl 不会处理它，Jinja 会报 unknown tag",
    ),
    Rule(
        "DTL301",
        "error",
        "variable missing from --data",
        "`{path}` is not present in the data file",
        "数据文件里没有 `{path}`",
    ),
    Rule(
        "DTL302",
        "warning",
        "data key never used (--report-unused-data)",
        "data key `{key}` is never used by the template",
        "数据字段 `{key}` 在模板里从未使用",
    ),
    Rule(
        "DTL303",
        "error",
        "loop over a non-iterable value from --data",
        "`{{% for … in {path} %}}` but `{path}` is a {type} in the data file",
        "`{{% for … in {path} %}}` 中的 `{path}` 在数据文件里是 {type}，不能循环",
    ),
]

RULES: dict[str, Rule] = {r.id: r for r in _RULES}

DOCS_URL = "https://github.com/yq6666-66/docxtpl-lint/blob/main/docs/rules.md"


def help_url(rule_id: str) -> str:
    return f"{DOCS_URL}#{rule_id.lower()}"


def render(rule_id: str, params: dict[str, object], lang: str = "en") -> str:
    rule = RULES[rule_id]
    template = rule.zh if lang == "zh" else rule.en
    return template.format(**params)
