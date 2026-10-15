# docxtpl-lint 项目计划

## 命名
- 包名、命令名、仓库名都用 **`docxtpl-lint`**，import 名是 `docxtpl_lint`。
- 2026-10-16 查了一下：PyPI 上 `docxtpl-lint` 没被占用（404）；`docxlint` 已被占用（200），不能用。
- GitHub 上搜 `docxtpl-lint`，没有同名仓库。
- 选这个名字的理由：包含 “docxtpl” 这个搜索关键词，能直接借上游 2.7k 星仓库的搜索流量。

## 范围（v0.1）
1. **块配对检查（DTL101/102/103）+ 单元格级定位**：位置格式为“文档部分 ¶段号 [表 行 列 > 嵌套表… ¶单元格内段号]”，一次报出全部问题。
2. **docxtpl 专用标签放置检查（DTL201–206）**，对应上游 issue #644 和 #603。
3. **数据契约检查（DTL301/302）**：通过 `--data` 传入样例 JSON，支持嵌套字段和循环变量。
4. 另外附带 DTL001：标签在本段内没有闭合。
5. 命令行：`--format json`、`--select`、`--ignore`、`--warnings-as-errors`、`--list-vars`。退出码 0 表示无问题，1 表示有问题，2 表示参数或 IO 错误。
6. 提供 GitHub Action（`action.yml`）、pre-commit 钩子（`.pre-commit-hooks.yaml`）和 CI 工作流（Python 3.10–3.13）。
7. 不做：自动修复、渲染、跨 run 拆分报警（docxtpl 会自动合并这类拆分，报出来就是误报）。

## 和 lintxtpl 的差异
| | lintxtpl | docxtpl-lint |
|---|---|---|
| 规则数 | 2 | 12 |
| 错误定位 | 段号（不区分是否在表格里） | 表/行/列，支持嵌套表 |
| 一次能报多少个错误 | 语法错误只报第一个 | 全部 |
| docxtpl 专用标签（tr/tc/p/r） | 无 | 6 条规则 |
| 数据校验 | 只输出变量清单 | 用 `--data` 实际核对 |
| 是否依赖 docxtpl 内部实现 | 锁死 0.20.2 的 patch_xml | 不依赖，直接用 lxml 读文档 |
| JSON 输出、Action、pre-commit | 无 | 有 |

## 可行性自评（尽量挑毛病）
- **能确定做到的**：每条规则只看文档结构或纯文本，可以确定性地判断。3 个上游 issue 场景都做成了 fixture，并且在测试里确认这些模板放进 docxtpl 0.20.2 渲染确实会报错，同时 linter 能给出位置。干净模板既能通过 lint，也能正常渲染。
- **风险 1：误报**
  - 以 `{%-` / `-%}` 写法刻意把标签跨段写的模板会被报 DTL001。目前在 README 里说明，后续考虑加一个 `--allow-cross-paragraph` 开关。
  - 变量只要在模板里出现就会算进去，不区分是否在 `{% if x is defined %}` 这样的守卫里面，可能导致 DTL301 误报。
- **风险 2：作用域分析不完整**：`macro`、`call`、`include`、`import` 没有分析，只是跳过。
- **风险 3：DTL201 可能过时**：它依据的是 docxtpl 当前的正则 `[^}%]*`。如果上游合并了 PR #645，这条规则需要按 docxtpl 版本来开关。
- **风险 4：星数天花板**：这是窄众工具。现实目标是 100–300 星，前提是上游 issue 里有人主动推荐。要超过 1k 星，需要被 docxtpl 官方文档收录。
- **还没做到的**：
  - 位置无法反向映射到 Word 页码（docx 本身没有分页信息）；
  - 批注（comments.xml）没有扫描；
  - README 里还没有 GIF。

## 推广计划（发布之后，需要老板确认才执行）
1. 在 docxtpl 的 #378、#603、#644 下，以“我做了个工具可以定位这个问题”为内容各留一条回复（这属于对外发言，必须先确认）。
2. 给 docxtpl 文档的 FAQ 提 PR，加一节 “Linting templates”。
3. 用 asciinema 或 vhs 录一段彩色输出的 GIF，放进 README。

## 里程碑
- v0.1（已完成，仅在本地）：12 条规则、26 个测试、ruff 检查通过、能构建 wheel。
- v0.2：`--allow-cross-paragraph` 开关、SARIF 输出（GitHub code scanning 可以直接标注）、扫描批注、录 GIF。
- v0.3：可选的 `--docxtpl-version` 开关，按版本切换规则行为。
