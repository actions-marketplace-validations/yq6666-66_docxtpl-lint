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
        "DTL003",
        "error",
        "template code inside a tracked deletion",
        "this paragraph has an unaccepted tracked deletion that contains template code; docxtpl still renders "
        "deleted text, so the code runs and its output stays in the document's revision history. Accept or reject "
        "all tracked changes before using the file as a template",
        "该段落里有未接受的修订删除，其中含有模板代码；docxtpl 仍会渲染被删除的文字，这段代码会执行，"
        "渲染结果还会留在生成文档的修订记录里。请先接受或拒绝全部修订，再把文件当模板使用",
    ),
    Rule(
        "DTL005",
        "warning",
        "unused or unknown suppression comment",
        "suppression `{directive}` matched no finding here: {rules}",
        "抑制注释 `{directive}` 在此处没有匹配到任何问题：{rules}",
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
        "DTL104",
        "error",
        "unknown Jinja filter",
        "filter `{name}` does not exist in docxtpl's default Jinja environment; rendering raises "
        "TemplateAssertionError (declare custom filters with --filters or --jinja-env)",
        "docxtpl 默认的 Jinja 环境里没有过滤器 `{name}`，渲染时会抛出 TemplateAssertionError"
        "（自定义过滤器请用 --filters 或 --jinja-env 声明）",
    ),
    Rule(
        "DTL105",
        "error",
        "unknown Jinja test",
        "test `is {name}` does not exist in docxtpl's default Jinja environment; rendering raises "
        "TemplateRuntimeError when it is evaluated (declare custom tests with --tests or --jinja-env)",
        "docxtpl 默认的 Jinja 环境里没有测试 `is {name}`，执行到这里时会抛出 TemplateRuntimeError"
        "（自定义测试请用 --tests 或 --jinja-env 声明）",
    ),
    Rule(
        "DTL106",
        "error",
        "loop variable used outside its loop",
        "`{name}` only exists inside a `for` loop (loop variable, `loop`, or a `set` inside the loop) but is used "
        "after it; Jinja does not leak loop scope, so it renders empty or raises UndefinedError",
        "`{name}` 只在 `for` 循环内部存在（循环变量、`loop` 或循环里 `set` 的变量），却在循环外使用；"
        "Jinja 的循环作用域不会外泄，结果是输出为空或抛出 UndefinedError",
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
        "DTL209",
        "error",
        "other content next to a {%p/tr/tc %} tag is silently dropped",
        "`{raw}` makes docxtpl replace the whole {unit} with the tag, so `{rest}` next to it disappears "
        "from the output without any error. Move that content to its own paragraph",
        "`{raw}` 会让 docxtpl 把整个{unit}替换成这个标签，旁边的 `{rest}` 会在输出中静默消失、不报任何错。"
        "请把这些内容放到单独的段落",
    ),
    Rule(
        "DTL210",
        "error",
        "{%p %} open and close in the same paragraph",
        "`{open_raw}` and `{close_raw}` are in the same paragraph; docxtpl replaces the paragraph with the first tag "
        "and the template fails. Put them in separate paragraphs",
        "`{open_raw}` 和 `{close_raw}` 在同一段里；docxtpl 会用第一个标签替换整段，渲染失败。请把它们放在不同的段落",
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
    Rule(
        "DTL304",
        "error",
        "variable not declared in --schema",
        "`{path}` is not declared in the JSON Schema (data contract)",
        "`{path}` 没有在 JSON Schema（数据契约）里声明",
    ),
    Rule(
        "DTL305",
        "error",
        "loop over a value the --schema declares as non-iterable",
        "`{{% for … in {path} %}}` but the schema declares `{path}` as {type}",
        "`{{% for … in {path} %}}` 中的 `{path}` 在 schema 里声明为 {type}，不能循环",
    ),
    Rule(
        "DTL306",
        "error",
        "list filter applied to a non-list value from --data",
        "`{path}` is a {type} in --data but `|{filter}` needs a list; a number raises TypeError, a string is "
        "silently split into characters and a mapping is iterated by its keys",
        "`{path}` 在 --data 里是 {type}，但 `|{filter}` 需要列表；数字会抛出 TypeError，字符串会被静默拆成单个字符，"
        "字典则只会遍历它的键",
    ),
    Rule(
        "DTL307",
        "warning",
        "plain value for a {{r}} / {{p}} tag",
        "`{raw}` expects a docxtpl {object} object, but `{path}` is a plain value in --data; docxtpl renders a plain "
        "value in this tag as nothing. Build it with {object}(...) in Python (or use `{{{{ {path} }}}}`)",
        "`{raw}` 需要 docxtpl 的 {object} 对象，但 `{path}` 在 --data 里是普通值；"
        "docxtpl 在这种标签里会把普通值渲染为空。"
        "请在 Python 里用 {object}(...) 构造（或改用 `{{{{ {path} }}}}`）",
    ),
    Rule(
        "DTL308",
        "error",
        "data value with & or < printed without escaping",
        '`{path}` contains `{char}` in --data ("{value}") and is printed without `|e`; docxtpl renders with '
        "autoescape off by default, so the text is silently cut (`Smith & Co` -> `Smith  Co`, `<b>` drops the rest of "
        "the paragraph). Render with autoescape=True (then pass --autoescape) or write `{{{{ {path}|e }}}}`",
        '`{path}` 在 --data 里含有 `{char}`（"{value}"），输出时没有加 `|e`；docxtpl 默认不转义，文字会被静默截掉'
        "（`Smith & Co` → `Smith  Co`，`<b>` 会吞掉段落剩余部分）。请用 autoescape=True 渲染（并加 --autoescape），"
        "或写成 `{{{{ {path}|e }}}}`",
    ),
    Rule(
        "DTL401",
        "error",
        "verify: output silently lost when rendered by docxtpl",
        "`{raw}` was rendered by docxtpl but its value does not appear in the output document",
        "docxtpl 渲染了 `{raw}`，但它的值没有出现在输出文档里（内容被静默丢掉）",
    ),
    Rule(
        "DTL402",
        "error",
        "verify: docxtpl fails to render the template",
        "docxtpl failed to render the template with the inferred sample data: {error}",
        "用推断出的示例数据渲染时 docxtpl 报错：{error}",
    ),
]

RULES: dict[str, Rule] = {r.id: r for r in _RULES}

DOCS_URL = "https://github.com/yq6666-66/docxtpl-lint/blob/main/docs/rules.md"


def help_url(rule_id: str) -> str:
    return f"{DOCS_URL}#{rule_id.lower()}"


def render(rule_id: str, params: dict[str, object], lang: str = "en") -> str:
    rule = RULES[rule_id]
    template = rule.zh if lang == "zh" else rule.en
    if lang == "zh":
        # location-like params carry a localised twin, e.g. open_loc / open_loc_zh
        params = {k: params.get(k + "_zh", v) for k, v in params.items()}
    return template.format(**params)
