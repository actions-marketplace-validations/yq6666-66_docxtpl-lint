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


## v1.1：两份评估的分歧（DeepSeek 第 10 轮）及实验裁决

| 编号 | 分歧 / 决定 | 实验（docxtpl 0.20.2） | 结论 |
|---|---|---|---|
| D58 | nested_loops_nested_tables：DeepSeek 认为 DTL206 是误诊 | 内层的 `{%tr for%}…{%tr endfor%}` 写在同一行时，docxtpl 报 "unknown tag 'endfor'"；把内层循环拆到单独的行后，能渲染出 [['p',''],['q','']] | DTL206 正确，DeepSeek 认错 |
| D59 | `{%tr%}` 所在行的其他单元格有文字，DeepSeek 认为"不需要报" | 渲染结果中整张表都消失了，"extra" 丢失 | 应该报：DTL209 扩展到同一行的其他单元格，DeepSeek 同意 |
| D60 | `{%tc if%}` / `{%tc endif%}` 跨行时，DeepSeek 认为 DTL207 是误报 | 输出变成 [['y'],['z']]，表格结构损坏，"extra" 丢失 | DTL207 正确，DeepSeek 认错 |
| D61 | 注释紧挨 `{%p%}` 时报 DTL209 | 渲染正常，没有内容丢失 | 是误报，计算时先去掉注释 |
| D62 | `{{ 'a }} b' }}` 报 DTL103 | docxtpl 正常输出 'a }} b' | 是误报，扫描器改为按 Jinja 的方式跳过字符串 |
| D63 | 行内有其他文字的 `{%tr%}` 新增 DTL209（如 nested_table_location、tr_prefix_mismatch） | 渲染后整张表消失，"outer"/"inner" 丢失 | 新报出的 DTL209 都正确；在官方 40 个模板上仍为 0 误报 |
| D64 | `{%p if%}x{%p endif%}` 写在同一段 | 报 "unknown tag 'endif'" | 新增 DTL210；这种情况不报 DTL209（因为不是静默丢失，而是直接报错） |
| D65 | 不间断空格（NBSP）紧挨标签 | 渲染正常；只丢了一个看不见的空格 | 不报，DeepSeek 同意 |
| D66 | schema 相关用例得到 DTL303 而不是 DTL305 | 测试脚本当时用 `--data` 跑这些用例，所以 DTL303 是对的 | 测试脚本加上 options（schema / report-unused-data / allow-cross-paragraph）后重跑 |
| D67 | GitHub 输出把 `%` 转义成 `%25` | 这是 workflow 命令规范的要求 | 不改，DeepSeek 同意 |
| D68 | infer 输出父级路径 | — | 按设计保留，DeepSeek 同意 |
| D69 | 缺少一个 `}` 时，后面的内容被吞掉，只报 DTL002 警告（自评发现） | broken.docx 里的 endfro 拼写错误因此被掩盖 | 在遇到下一个 `{{`/`{%` 时报 DTL001 错误，并从那里继续扫描；fix 会建议补上 `}` |
| D70 | 数据 JSON 带 BOM 时退出码为 2（自评发现） | 用 Windows 记事本格式保存的文件可以复现 | 改用 utf-8-sig 读取 |
| D71 | 子命令遇到坏文件时抛出 traceback（自评发现） | 用 fake.docx 复现 | 统一返回退出码 2，并给出一行提示 |
| D72 | 采纳 DeepSeek 的 UX 建议：`--explain`、单个模板时不输出 x-docxtpl-templates、改写 --data 帮助文字、在线试用页加载超时提示；不采纳：--quiet/--verbose，以及已有的彩色输出功能 | — | 详见 PLAN-v1.1.md |
| D73 | 发现的问题全部写成测试：86 个对抗用例加裁决后的预期结果（benchmark/adversarial_adjudicated.json）放进 pytest | 当前 86/86 通过 | 以后修改代码时，这批用例能防止回归 |


## v1.2：开源项目调研后的取舍（与 DeepSeek 讨论，见 docs/research/oss-survey.md）

| 编号 | 决定 | 依据 / 实验（docxtpl 0.20.2） |
|---|---|---|
| D74 | 调研 19 个项目；curlylint（最后推送 2024-01）和 Carbone（2026-04-07）超过 6 个月未更新，按规则跳过 | 它们的点子在 djLint / docxtemplater 里都有，不属于"独有价值" |
| D75 | 采纳段落级抑制：`disable-line=`（本段）和 `disable-next=`（下一段），可写规则前缀 | DeepSeek 建议还加 `disable`/`enable` 区间；未采纳，因为现有的 `disable=` 已表示整文件，改语义会破坏兼容 |
| D76 | `disable-next` 推荐写成 `{#p … #}` | 实测：`{#p … #}` 所在段落渲染后被整段删除；单独一段的普通 `{# … #}` 会留下空行（测试 test_disable_next_with_p_comment_is_removed_by_docxtpl） |
| D77 | 新增 DTL005（warning）：段落抑制没有匹配到问题，或规则 id 不存在；DTL3xx/4xx 不报"未使用" | 这两类结果依赖 --data/--schema/verify，没传数据时必然"未使用"，报出来就是误报 |
| D78 | 采纳基线文件 `--baseline` / `--write-baseline`，格式 `{"version":1,"files":{file:{rule:{key:count}}}}` | 与 DeepSeek 一致：key 不用段落号，而是 部件 + 单元格路径 + 段落文字哈希，并按次数计；插入段落不失效，改了出问题的段落才失效（测试覆盖）。过期条目只提示，用 --write-baseline 清理 |
| D79 | 采纳 `--statistics`，仅 text 格式 | json/sarif 已能自行统计 |
| D80 | 修订 D54：采纳 `--annotate DIR`，写带 Word 批注的副本 | 用户这次要求吸收其他项目的好点子；对只用 Word 的模板维护者价值最高。只写副本，拒绝覆盖原文件；批注挂在段落上，不拆 run（DeepSeek 担心拆坏标签）。LibreOffice 能读出批注，python-docx 读出的正文与原文件一致 |
| D81 | 采纳 `infer --pydantic`，不引入依赖 | DeepSeek 建议只做顶层；我们的契约树只有对象/数组/数字/映射/Any，没有 $ref/oneOf，整棵树生成成本很低，所以全做。必填字段与 JSON Schema 的 required 一致；用生成的模型校验示例数据后交给 docxtpl 实际渲染通过 |
| D82 | 不做 fix 安全等级 | fix 从不写文件，标签没有意义；如以后做 `fix --write` 再议 |
| D83 | 不支持 docxtemplater / poi-tl / docx4j 语法 | 准确性来自对 docxtpl patch_xml 的建模，换引擎等于另写一个检查器 |
| D84 | 不改用 mammoth / docx2python 解析 | 它们会把 run/段落/单元格结构归一化掉，而这正是我们定位需要的 |
| D85 | reviewdog 只写文档示例（SARIF 输入） | 零代码 |
| D86 | 修复 `--lang zh` 下 DTL204 位置和 DTL209 单位名仍为英文；DeepSeek 代码审查 10 条中采纳 3 条 | 采纳：同一条抑制里重叠的规则（DTL2,DTL201）都记为已使用、`--pydantic -` 不再丢掉 `--sample`、`--statistics` 帮助注明仅 text。驳回："disable-next 差一"（段落号本来就是从 1 开始，测试证明正确）及其余无影响的条目 |


## v1.3：Jinja 正确性（整体路线与 DeepSeek 第 11、12 轮讨论）

| 编号 | 决定 | 依据 / 实验（docxtpl 0.20.2） |
|---|---|---|
| D87 | 1.3→2.0 路线：1.3 Jinja 正确性、1.4 Word 文档层面的隐患、1.5 契约类型、1.6 verify 增强、1.7 `fix --write`、1.8 CI 生态、1.9 稳定的 Python API、2.0 清理 | DeepSeek 认为 1.4 最弱，建议只做 content control（w:sdt），并建议不出 2.0。1.4 待实验后决定范围（见 PLAN-v1.4）；2.0 保留，但只做有实际理由的破坏性变更（见 PLAN-v2.0） |
| D88 | DTL104 未知过滤器（error） | DeepSeek 说"渲染为空"。实测：编译时抛出 TemplateAssertionError，所以 DeepSeek 错了。仍有价值：渲染前就能指出具体位置 |
| D89 | DTL105 未知测试（error） | 实测：执行到该表达式时抛出 TemplateRuntimeError |
| D90 | DTL106 循环变量 / `loop` / 循环内 `set` 的变量在循环外使用（error） | 实测：`{{ last }}` 静默输出为空，`{{ i.n }}` 抛出 UndefinedError。如果这个名字在模板里别处也被当作顶层数据使用，则不报（实测 `{{ item }}` 在循环前后都能渲染出顶层值）。这类名字不计入数据契约 |
| D91 | 自定义过滤器 / 测试的声明方式：`--filters`、`--tests`、配置项 `filters`/`tests`/`jinja-env`，以及 `--jinja-env MODULE:ATTR` | 与 DeepSeek 一致：没有这个出口，DTL104 就会成为误报来源。`--jinja-env` 会执行用户代码，帮助文字里已写明 |
| D92 | 官方模板 custom_jinja_filters_tpl.docx 的 DTL104 列入 must_report | 它的测试脚本是传入自定义 jinja_env 才能渲染的；不声明时 docxtpl 确实会报错，所以是真问题，不是误报 |
| D93 | DeepSeek 第 12 轮列出的 4 个误报场景：驳回 3 个，接受 1 个提醒 | 已写成测试：`if` 里的 `set`、循环之后的 `set`、名为 `loop` 的宏参数都不会误报（测试通过）。"同名的顶层数据会掩盖 DTL106"是有意的设计（D90） |


## v1.4：修订记录和域代码里，docxtpl 实际看到的内容（DeepSeek 第 13 轮）

| 编号 | 决定 | 实验（docxtpl 0.20.2） |
|---|---|---|
| D94 | 1.4 的范围按实验结果收窄，部分采纳 DeepSeek "1.4 最弱"的意见 | 内容控件（w:sdt，块级和行内）、`w:ins`、标签中间的修订删除，docxtpl 都能正确处理，所以都不做规则 |
| D95 | 含有修订删除、域代码或 `moveFrom` 的段落，用 docxtpl 自己的 patch_xml 正则处理该段 XML 后再取文字 | 实测：标签内部的删除会被 striptags 去掉（`{{ <del>nmae</del>name }}` → 输出 name）；标签外部的删除文字和域代码会保留并被渲染。只有这类段落走新逻辑，普通段落不变（官方 40 个模板结果不变） |
| D96 | 新增 DTL003：修订删除里含有模板代码。DeepSeek 建议定为 error，采纳 | 实测：删除里的 `{{ old }}` 被渲染，值进入输出文档的 `<w:delText>`，用"显示标记"就能看到，属于数据泄漏；`moveFrom` 里的标签会渲染两次 |
| D97 | 域代码（HYPERLINK 等的 instrText、fldSimple 的 w:instr）纳入检查和数据契约 | 实测：`HYPERLINK "{{ url }}"` 会被渲染；域代码里写坏的标签会导致渲染失败，而 1.3 之前对此报"无问题" |
| D98 | DeepSeek 担心"照抄 docxtpl 内部正则会和上游脱节" | 每周跑的上游兼容性任务（docxtpl 最新版和 master）现在也跑 test_v13/test_v14，正则一旦脱节就会失败 |
| D99 | 不采纳：把 `moveTo` 也标出来 | moveTo 那一侧正常渲染一次，没有被隐藏的代码 |


## v1.5：数据契约更精确（DeepSeek 第 14 轮）

| 编号 | 决定 | 实验（docxtpl 0.20.2） |
|---|---|---|
| D100 | 不采纳 DeepSeek 路线里"`|upper` 等字符串过滤器 → string 类型" | 实测 `5|upper` 正常输出 "5"，字符串过滤器对数字也能用，推成 string 会误伤数字 |
| D101 | 列表过滤器（join/sum/sort/unique/map/select/reject/selectattr/rejectattr/batch/slice/groupby）的输入推为 array；配合 --data 新增 DTL306（error） | 实测：`"abc"|join` 静默输出 "a, b, c"，`5|join` 抛 TypeError，字典只遍历键（第 14 轮 DeepSeek 指出，采纳并写成测试）。`first`/`last` 用在字符串上是合理用法（`name|first`），不算列表过滤器 |
| D102 | 带属性的过滤器（`map(attribute=)`、`sum(attribute=)`、`sort(attribute=)`、`selectattr`、`groupby` 等）推出 `items[].attr`；`sum` 的属性推为 number | 实测：`sum(attribute='price')` 遇到字符串值会抛 TypeError。DeepSeek 认为 `selectattr('odd')` 的参数是测试名，这是错的：Jinja 的签名是 selectattr(attribute, test)，已写成测试（输出 "a"） |
| D103 | 遍历"不改变元素"的过滤器链时保留元素作用域，例如 `for i in items|selectattr('ok')|sort(attribute='n')` | 之前 `i.title` 会从数据契约里丢掉；`batch`/`slice` 改变了元素，所以不在此列（与 DeepSeek 的看法一致） |
| D104 | `{{r x}}` → RichText，`{{p x}}` → Subdoc：写入 schema（x-docxtpl-object）、Pydantic（字段注释）、diff（any → richtext 视为破坏性变更）；配合 --data 新增 DTL307（warning） | 实测：`A {{r x }} B` 中 x 为普通字符串或字典时，输出 "A  B"，值静默消失；`{{p x}}` 遇到字符串会删掉整个段落。DeepSeek 指出字典也不行，采纳 |


## v1.6：转义问题和更强的 verify（DeepSeek 第 15 轮）

| 编号 | 决定 | 实验（docxtpl 0.20.2） |
|---|---|---|
| D105 | 新增 DTL308（error，配合 --data）：数据里含 `&` 或 `<` 的字符串没加 `|e` 就输出 | 实测默认 autoescape=False 时：`Smith & Co` → `Smith  Co`，`a < b` → `a  b`，`<b>bold</b>` 之后的段落内容全部丢失；`>` 和引号没问题。加 `|e` 或用 autoescape=True 渲染都能正常输出 |
| D106 | `--autoescape` / 配置项 `autoescape` 表示调用方用 autoescape=True 渲染，此时不报 DTL308 | — |
| D107 | 不采纳 DeepSeek "DTL308 应该改成静态检查（不需要 --data）" | 统计：官方 40 个模板里，23 个文件共有 79 处未转义的输出，静态检查会全部报出来，无法使用。改为只在数据里真的出现 `&`/`<` 时报 |
| D108 | 采纳 DeepSeek 指出的漏报：`~` 拼接、`+` 和 `x if c else y` 两个分支里的输出 | 已写成测试（拼接后输出 "Co: x  y "，`<i>` 吞掉了后面的内容） |
| D109 | verify：`{{r}}` / `{{p}}` 改用 RichText / Subdoc 作为哨兵值，纳入 DTL401 检查；没装 docxcompose 时 Subdoc 退回 RichText，且不检查该路径 | 之前这两类标签完全不检查；现在 `{{r x }} {%p if y %}` 中被吞掉的 x 能被 verify 发现 |
| D110 | verify 增加：可重复的 `--data`（每份数据渲染一次，DTL402 注明是第几份）、`--autoescape`、`--jinja-env`（用调用方真实的过滤器渲染）、`--out DIR`（保存渲染结果） | 与调用方的渲染方式一致，才能得出真实结论 |


## v1.7：`fix --write`（DeepSeek 第 16 轮）

| 编号 | 决定 | 依据 / 实验 |
|---|---|---|
| D111 | 修订 D82：做 `fix --write OUT`，只写副本，从不覆盖模板 | 直接在原有的 `<w:t>` 里删改字符，未改动的 run 格式保持不变（测试：加粗的 "Total: " 不受影响）；跨 run 的标签也能修。修完的副本 docxtpl 能正确渲染，LibreOffice 能打开 |
| D112 | 保留两级安全等级（safe / unsafe），不采纳 DeepSeek 第 11 轮"取消分级"的建议 | 把 DTL301 改成最接近的数据路径、删除多余标签、去掉需要成对修改的 tr/tc 前缀，都是在猜作者意图；默认只做 safe 修复，unsafe 需要加 `--unsafe` |
| D113 | 最多 10 轮：每轮每段只做一处修复；只有问题数下降的那一轮才保留 | 同一段里有多个问题时，下一轮按新文本重新给出建议，避免基于旧文本的修改相互冲突 |
| D114 | 含修订删除或域代码的段落不自动修复 | 这类段落的文字和 run 结构对应不上，交给作者手动处理（有测试） |
| D115 | 第 16 轮代码审查：只采纳"删除无用的 iselement 检查" | 驳回的条目："插入时选错 run"（插在 run 边界时写进前一个 run，与在 Word 里打字的行为一致）、"old == new 时空转"（suggest 不会产生这种修复）、"同标签部件冲突"（每个部件文件名唯一）等 |


## v1.8：CI 生态（DeepSeek 第 17 轮）

| 编号 | 决定 | 依据 |
|---|---|---|
| D116 | 新增 `--format markdown`，用于 job summary 或 PR 评论 | 不看日志的人也能直接看到一张问题表 |
| D117 | 新增 `--format gitlab`（GitLab Code Quality） | GitLab 用户此前没有可用的格式。fingerprint 复用基线的定位键（部件 + 单元格 + 段落文字哈希）再加出现序号，插入段落后不变（有测试） |
| D118 | SARIF 增加 `partialFingerprints` | 与 GitLab 用同一个 id，GitHub 代码扫描能跨提交去重 |
| D119 | 新增 `--output FILE` 和可重复的 `--report FORMAT:FILE` | 运行一次就能同时生成 GitHub 注解、SARIF 和 Markdown，Action 正是这样调用的 |
| D120 | Action 新增输入 `summary`（默认开启）、`baseline`、`sarif`、`annotate`（上传带批注的副本为 artifact）；CI 用失败的示例模板实际跑一遍 Action | 采纳 DeepSeek 的建议：布尔输入接受 true/1/yes/on。驳回：`format` 输入（Action 只服务 GitHub）、给 args 加引号解析（在输入说明里注明不支持引号）；它怀疑 `--annotate` 参数名写错，核对后没有问题 |
| D121 | 不做 JUnit 格式 | 与 DeepSeek 第 11 轮一致：SARIF 已覆盖 GitHub，Code Quality 已覆盖 GitLab |


## v1.9 — Stable Python API (DeepSeek rounds 18–19)

| # | Decision | Why / evidence |
|---|---|---|
| D122 | New `docxtpl_lint.api`: `lint()`, `check_context()`, `infer_schema()`, `Result`, `TemplateLintError`, `effective_autoescape()`; also exported at top level. Semver policy in docs/api.md | Apps need an in-process guard; until now only `lint_path` with internal kwargs was public |
| D123 | `template` may be a path, bytes or a binary file object; a `str` is always a path; file objects are not closed | DeepSeek #9 (str ambiguity) accepted |
| D124 | `check_context` stays and renders by default (`render=False` opt-out, `Result.rendered`) | DeepSeek wanted it folded into `lint`/off by default ("10–100× slower"). Measured: render ≈13 ms/template vs lint ≈1.4 ms over 40 official templates; the guard runs right before the app renders anyway. Kept as a distinct contract: lint never renders |
| D125 | Never mutate the user's `jinja_env` | Verified by real render: docxtpl `render(jinja_env=env, autoescape=True)` sets `env.autoescape = True` on the caller's env. api and `verify` render through `env.overlay(autoescape=True)` |
| D126 | Autoescape from the env: `effective_autoescape` = flag or env.autoescape; a callable is evaluated with name `None` | DeepSeek #5/#6. Bug fixed: CLI `--jinja-env` with an autoescaping env still reported DTL308. Callable case checked by render: `select_autoescape(default_for_string=False)` does NOT escape, so `bool(callable)` would have hidden real DTL308 |
| D127 | `filters`/`tests` stay, unioned with the env's | DeepSeek #4 wanted env-only; rejected: CLI parity and users without importable envs. Precedence documented (union) |
| D128 | `--fail-on error|warning|never` (config `fail-on`); `--warnings-as-errors` deprecated (stderr notice), removed in 2.0. `never` still exits 2 on unreadable input | DeepSeek #12 accepted for `never`; distinct exit codes per level rejected (would break existing exit-1 contract) |
| D129 | Top-level `lint_path` NOT deprecated in 1.9 | DeepSeek #11: it is the only previously public API |
| D130 | `config=True` magic and `infer_schema` rename rejected/omitted | No config param in api (explicit args only, #3); `infer_schema` really returns JSON Schema (`$schema` 2020-12), so the name is accurate (#8 rejected) |
| D131 | `check_context` takes `filters`/`tests`; `Template` alias exported and includes bytearray | DeepSeek review of api.py #8/#10/#15 |

**D132.** Ship the 1.9 line as **1.9.1** and leave the unreleased `v1.9.0` tag in place. The pushed v1.9.0 tag failed CI only on `ruff format --check` of README code blocks (local ruff did not format Markdown). Moving a pushed tag rewrites remote history, so a new patch version was cut instead; 1.9.0 was never on PyPI or a GitHub Release. Local `check.sh` now runs `ruff format --check .` on the whole repo like CI.
