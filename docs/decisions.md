# 决策记录（与 DeepSeek 的讨论）

流程是：DeepSeek（deepseek-reasoner）先评审计划，我用 **docxtpl 0.20.2 实际渲染**逐条核对，再把结论交给 DeepSeek（deepseek-chat）反驳，最后由我拍板。
双方原文见 [deepseek-review.md](deepseek-review.md)。
凡是“docxtpl 实际怎么表现”的结论，都写成了 `tests/test_docxtpl_behaviour.py` 里的测试，结论以测试结果为准。

| # | 议题 | DeepSeek 的意见 | 实测 / 我的判断 | 结论 |
|---|---|---|---|---|
| D1 | 标签跨段落时，默认报 error 还是 warning | 默认降成 warning | 跨段落的 `{{ client.` / `email }}` 能正常渲染，只是两段被合并 | **采纳**：拆成两条。DTL001（直到文末都没闭合）报 error；DTL002（跨段但最终闭合）报 warning；`--allow-cross-paragraph` 用来关掉 DTL002 |
| D2 | DTL206（tr 的开始和结束写在同一行） | 怀疑会误报，要求真机验证 | 同一行会抛 TemplateSyntaxError；分在不同行可以正常渲染 | **保留**，验证用例放在 rule_cases 里 |
| D3 | DTL205（tr 循环跨两张表） | 改提示文案 | 不报错，但循环里的行被静默丢掉 | **保留**，提示文案改成“静默丢行” |
| D4 | `{%tc %}` 的对称规则 | 建议补上 | 同一行正常；跨行不报错但表格结构错乱 | **新增 DTL207**（tc 循环的开始和结束必须在同一张表的同一行） |
| D5 | DTL204（开始和结束的前缀不一致） | 无 | 实测**不报错**，但循环数据被吞（原以为会报错） | 保留，标为“静默”类 |
| D6 | 是否启用 Jinja 的 do 和 loopcontrols 扩展 | docxtpl 默认没有启用 | `{% do %}`、`{% break %}` 在 docxtpl 里报 unknown tag | **采纳**：改用默认的 `Environment()`，这类写法由 DTL103 报出 |
| D7 | `{% raw %}` 块里的内容 | 应跳过 | 能正常渲染 | **采纳**，raw 块即使跨段落也会跳过 |
| D8 | `{% set x %}…{% endset %}` | 说会误报 DTL103 | Jinja 解析正常，DeepSeek 事后也承认说错了 | **不改**，补了回归测试 |
| D9 | `&lt;` 转义规则 | 可能是高频坑 | patch_xml 会反转义，`<` 能正常渲染 | **拒绝** |
| D10 | 前缀写错规则（`{{p x}}` 这类） | 建议新增 | docxtpl 的正则本身就认 `{{p`、`{{tr`、`{{tc` | **拒绝**。DeepSeek 追问 `{% p x %}` 这种中间带空格的写法 → 把 DTL202 扩展到 p 和 r，补了用例，实测报 unknown tag |
| D11 | DTL202 与 204/205/206 重复报 | 只报 DTL202 | 同意 | **采纳**：前缀前带空格的标签不再参与开闭配对检查 |
| D12 | 宏、import、`is defined`、`default` 引起的 DTL301 误报 | 应修 | 确认是 bug | **采纳**：宏名、宏参数、import 名、CallBlock 参数都算局部变量；守卫过的路径不报 |
| D13 | DTL103 在“模板意外结束”时的定位 | 越界时不要硬指到最后一个标签 | 同意 | **采纳**：这种情况只报到“部分”这一级，不给段号 |
| D14 | DTL303（for 循环的对象不可迭代） | 字符串只给 warning | Jinja 会把字符串逐字符迭代，不会报错 | **采纳并收紧**：只报数字、布尔、null，字符串不报 |
| D15 | DTL302（数据字段未被模板使用） | 共享数据文件时全是噪音 | 同意 | **采纳**：默认关闭，用 `--report-unused-data` 开启 |
| D16 | 多份数据（多 context） | 建议 v0.1 就支持 | 实现成本低 | **采纳**：`--data` 可以写多次，只有所有数据文件里都缺的路径才报 |
| D17 | 提示文案中英混排 | 不专业 | 同意 | **采纳**：`--lang en|zh`（默认 en），规则表放在 messages.py |
| D18 | `--format github` 与 SARIF | 先说删 SARIF，后来改口同意都保留 | 两种都已实现并有测试 | 都保留 |
| D19 | 浏览器 Playground | 认为是最大的增长杠杆 | 要把规则移植到 JS 或 wasm，成本远超 v0.1 的范围 | **推迟**到路线图 |
| D20 | 包名、上游兼容层 | 后来同意保留现名并加声明 | — | 保留 `docxtpl-lint`，加 “Not affiliated” 声明；不做 `docxtpl.lint` 兼容层 |
| D21 | 扫描尾注和批注 | 建议扫描 endnotes 和 comments | docxtpl 0.20.2 源码只渲染正文、页眉、页脚和**脚注** | **拒绝**：扫描它们只会带来误报，已有测试保证批注不会被扫描 |
| D22 | 修订插入 `w:ins` 会不会重复计数 | 担心重复 | 插入的文字在文档里只出现一次，删除的文字在 `w:delText` 里，本来就不读 | 不改，补测试（DeepSeek 起草，我审核） |
| D23 | `¶N` 和用户在 Word 里数的段落对不上 | 建议额外打印上一段内容 | 已有表格路径和原文片段，再加会增加噪音 | 只在 README 里说明，不改输出 |
| D24 | GitHub Action 路径含空格 | 会出问题 | 同意 | **采纳**：files 改成按行输入，并在 CI 里用带空格的路径实测 |
| D25 | 跟进 docxtpl 新版本 | nightly 跑上游 master | 同意，改成每周一次 | CI 里加 docxtpl-upstream job，测最新发布版和 master |
| D26 | README 演示 GIF | 必须在 v0.1 就有 | 用 rich 导出静态 SVG，可重复生成，不需要录屏工具 | **采纳**：docs/demo.svg 和 demo-zh.svg |
| D27 | 推广方式 | 不要去 issue 里刷链接，先给上游提改进 PR，发中文社区 | 同意，但这些都属于对外发言 | 写进 PLAN，**发布动作必须由老板确认** |

## 第 3 轮：DeepSeek 审查代码时报的 bug
| DeepSeek 报告的 bug | 核实结果 | 结论 |
|---|---|---|
| `{% set x %}…{% endset %}` 会被误报为 DTL101/102 | `_keyword` 里已经把 `endset` 映射成 `endset_block`，DeepSeek 看漏了；`set_block_ok` 测试能通过 | 驳回 |
| `{{ items[0].name }}` 不会被记录 | 属实：之前只记录了 `items`，没记录 `.name` | **修复**：整数下标按 `items[].name` 处理，补了测试 |
| DTL202 遇到没闭合的标签时，片段会截成 `{` | 代码里已有 `end >= 0` 判断，会退回整段匹配 | 驳回 |
| 表格单元格里的文本框段落会让单元格内段号加 1 | 属实，但文本框本来就在这个单元格里，这样数是合理的 | 不改 |
