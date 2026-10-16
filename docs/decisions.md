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


## v0.2 讨论（DeepSeek 第 5、6 轮）

| 编号 | 决定 | 依据 |
|---|---|---|
| D28 | 基准测试是 P0 | 跑 docxtpl 官方的 40 个模板，v0.1 有 7 个误报，修复后为 0 |
| D29 | 保留 DTL208 | DeepSeek 原本建议删掉，但真实 docxtpl 遇到这种情况会直接报错，它后来撤回了建议 |
| D30 | 做 Playground | DeepSeek 担心维护成本；我在 Node 和浏览器里实测可用、Pyodide 版本已固定、CI 有冒烟测试，它撤回了顾虑 |
| D31 | Actions 升到 v7 | DeepSeek 说"v7 不存在"，这是错的；我用 GitHub API 核实过 |
| D32 | 配置文件里允许写 `data` | 路径按 pyproject.toml 所在位置解析；DeepSeek 后来同意 |
| D33 | `--context` 在终端里默认 1，其他情况默认 0 | DeepSeek 原本提议默认 2，后来接受了按是否在终端区分 |
| D34 | 版本号用 0.2.0，不用 0.1.1 | 新增了功能和规则，按 SemVer 应该升次版本号 |
| D35 | PyPI 发布工作流只能手动触发 | 不经用户确认绝不发布 |
| D36 | 不做 --fix-safe、mkdocs、VS Code 插件、vhs GIF | 理由见 PLAN-v0.2.md |
| D37 | 基准测试的允许误报名单如果有条目已经不再出现，基准测试判为失败 | DeepSeek 第 6 轮建议，已实现并加了测试 |
| D38 | Playground 冒烟测试要求输出和 CPython CLI 逐字一致 | DeepSeek 第 6 轮建议，已实现 |
| D39 | rules.md 写明这些行为是在 docxtpl 0.20.2 上验证的 | DeepSeek 第 6 轮建议，已实现 |
| D40 | 不采纳：没有 pyproject 时把 `--data` 当作相对配置文件解析；`--context` 默认值改为 None | 前者在没有配置文件时不存在这个问题；后者已经实现 |


## v1.0 讨论（DeepSeek 第 7–9 轮）

| 编号 | 决定 | 依据 / DeepSeek 的影响 |
|---|---|---|
| D41 | 做 infer（JSON Schema + 示例数据），优先级最高 | DeepSeek 第 7 轮排第一；它提出的"推断 → 渲染往返"现在就是基准测试的一部分（37/40） |
| D42 | `|length` 不代表输入是数字；只有 round/int/float/abs、算术运算和与数字比较才判为数字 | 我提出，DeepSeek 同意。实现后发现 `v % 2` 这种取模也必须算作数字，否则 dtl201_good 用例渲染失败 |
| D43 | 做 verify（哨兵渲染） | DeepSeek：竞品都不渲染，这是独有优势。它要求写明 verify 会漏报哪些情况，已写入 rules.md 的 DTL401 |
| D44 | verify 跳过条件分支和 `x if y else z` | 只要报出来就一定是真问题；v1 不做强制走分支 |
| D45 | verify 只检查 `{{ }}` 输出 | 第一次跑基准测试时，`{% cellbg a.bg %}` 被误报为 DTL401，因为它被当成了输出 |
| D46 | 新增 DTL209 | verify 在测试中发现 `Total {{ total }} {%p if x %}` 里的 total 会被静默丢掉，于是做成静态规则，并用真实 docxtpl 确认 |
| D47 | 同一行已报 DTL206 时不再报 DTL209 | 避免对同一个问题重复报告 |
| D48 | fix 只输出 diff，不提供 `--write` | 我和 DeepSeek 意见一致：Word 会把文字拆成多个 run，自动改写不安全 |
| D49 | 拼写纠正要求编辑距离不超过 2，且最接近的候选不能并列 | DeepSeek 第 8 轮提出，以免给出"自信的胡说" |
| D50 | 不同意 DeepSeek 第 8 轮提出的"fix 必须强制依赖 docxtpl" | 修复建议的正确性已经在测试里用真实 docxtpl 验证过了，运行时不需要再渲染；而且 fix 也要能在在线试用页（Pyodide，没有 docxtpl）里用 |
| D51 | DTL102 的修复：如果多余的 end 标签其实是开始标签拼错造成的（如 `{% iff %}…{% endif %}`），就改开始标签，不删 end 标签 | 测试中发现，原先的"删掉多余标签"在这种情况下会给出错误建议 |
| D52 | DTL204 的修复：哪一端带 tr/tc 前缀，就把另一端改成同样的前缀 | 实测发现，把 `{%tr endfor %}` 改成普通的 `{% endfor %}` 虽然能渲染，但会产生空行；改成在开始标签上加 `{%tr` 才能输出正确的 ["1","2"] |
| D53 | diff：模板删掉字段不算破坏兼容，新增必填字段算；重命名只给提示，仍按破坏兼容处理 | DeepSeek 建议把重命名当警告；我认为对数据提供方来说改名依然是破坏性变更，所以只加了提示 |
| D54 | 不做 LSP 和带标注的 docx 报告 | DeepSeek 第 7 轮：LSP 成本高、不算新；带标注的 docx 是 lintxtpl 已有的功能 |
| D55 | 第 9 轮代码审查的 4 条全部驳回 | (1) 同一路径的 DTL401 误报：每个路径只有一个哨兵，已补测试证明不会误报；(2) 守卫语义与 DTL301 保持一致，是设计如此；(3) `\bname\b` 不会匹配到 `names` 里的 name；(4) 新增嵌套字段时，父字段已经报为破坏性变更，子字段不再重复报 |
| D56 | 版本号定为 1.0.0 | 新增了子命令和规则；原有的 `docxtpl-lint file.docx` 用法完全兼容 |
| D57 | Pages 改为在推送到 main 时部署 | v0.2.0 用 release 事件触发时，因为是在 tag 上运行，被 github-pages 环境的保护规则拒绝，后来手动在 main 上触发才部署成功 |
