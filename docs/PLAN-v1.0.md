# docxtpl-lint v1.0 计划（定稿）

目标：做出至少 5 个竞品都没有的真正创新功能。每个功能都要能对照真实的 docxtpl 0.20.2 验证，并配齐测试、文档和 README。计划经过 DeepSeek 三轮讨论（第 7–9 轮，原文见 `docs/deepseek-review.md`），各项决定记录在 `docs/decisions.md` 的 D41–D55。

竞品情况：lintxtpl 能报 Jinja 语法错误，并生成带标注的 docx；通用的 Jinja 检查工具（djlint、j2lint）不理解 docx 把文字拆成多个 run 的情况，也不认识 docxtpl 的 p/tr/tc/r 前缀。它们都不会生成数据契约，也不会做渲染验证。

## 创新点（全部完成）

| # | 功能 | 命令 / 参数 | 如何对照真实 docxtpl 验证 |
|---|---|---|---|
| 1 | 从模板推断数据契约，输出 JSON Schema 和示例数据，可合并多个模板 | `infer a.docx b.docx -o schema.json --sample sample.json` | docxtpl 官方的 40 个模板中，37 个能用推断出的示例数据直接渲染成功。其余 3 个：1 个是故意写错的模板，2 个需要 Python 对象（自定义过滤器、上下文里传入的函数）。另外，所有标为 "ok" 的规则用例都能用示例数据渲染成功 |
| 2 | 渲染等价验证：用真实 docxtpl 和哨兵数据渲染，找出输出里静默丢失的内容 | `verify a.docx` → DTL401 / DTL402 | 40 个官方模板上 DTL401 误报为 0；两个会丢内容的模板都能检出 |
| 3 | 比较两个模板版本的数据契约，判断是否破坏兼容 | `diff old.docx new.docx --fail-on-breaking` | 有测试覆盖新增、删除、类型变化、可选→必填，以及重命名提示 |
| 4 | 用 Schema 当契约检查模板 | `--schema schema.json` → DTL304 / DTL305 | 自洽性测试：从模板推断出 schema，再用它检查同一模板，结果为干净 |
| 5 | 把修复建议输出成 unified diff（不改写 docx） | `fix a.docx [--data]` | 每种修复都在测试里应用到 docx 后用 docxtpl 渲染，必须渲染成功且重新检查后没有问题。DTL204 还检查了输出行确实是 ["1","2"] |
| 6 | 从验证结果反推出新的静态规则 DTL209：`{%p/tr/tc %}` 旁边的文字会被静默丢弃 | 默认检查 | 规则用例用真实 docxtpl 渲染，确认这些文字确实从输出中消失 |
| 7 | 在线试用页也能直接看修复建议、推断的 Schema 和示例数据 | Playground 的 "Show" 选项 | 冒烟测试要求 Pyodide 里的输出（包括推断出的 Schema）和 CPython 逐字一致 |

## 不做的事项

- **LSP / 编辑器插件**：要做好需要几周，而且各家 linter 都有，不算创新。推迟。
- **生成带标注的 docx 报告**：lintxtpl 已经有这个功能；另外改写 docx 的 run 有损坏文件的风险。
- **`fix --write` 自动改写 docx**：Word 会把文字拆成多个 run，自动改写不安全，所以只输出 diff。
- **verify 强制走遍每个条件分支**：v1 先不做。条件分支里的输出直接跳过，这类漏报在 rules.md 的 DTL401 一节写明。

## 已知限制（已写进文档）

- verify 不检查这些输出：条件分支内的、带过滤器的、`{{r}}` / `{{p}}` 对象、数字和对象。所以报出的 DTL401 一定是真问题，但没报不代表没有问题。
- infer 推断出的叶子字段不标类型（因为模板打印出来的值可以是任意类型）。只有能确定时才标 number / array / object。
