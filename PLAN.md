# docxtpl-lint 项目计划（v0.1.0 发布版）

## 命名
- 包名、命令名、仓库名统一用 **`docxtpl-lint`**，import 名是 `docxtpl_lint`。
- 2026-10-16 核查：PyPI 上 `docxtpl-lint` 未被占用（404），`docxlint` 已被占用；GitHub 上没有同名仓库。
- README 加了“Not affiliated with python-docx-template”声明（D20）。

## v0.1.0 范围（已全部完成）
| 项 | 状态 |
|---|---|
| 单元格级定位，支持嵌套表；扫描正文、页眉、页脚、脚注（D21） | ✅ |
| DTL001/002 标签闭合（跨段落默认只给 warning，D1） | ✅ |
| DTL101/102/103 块配对和语法检查，按 docxtpl 默认 Environment（D6） | ✅ |
| DTL201–207 docxtpl 专用标签规则，每条都用真实 docxtpl 渲染验证过（D2–D5、D10） | ✅ |
| DTL301/302/303 数据检查：嵌套路径、循环变量、守卫、多份数据（D12、D14–D16） | ✅ |
| `--format text/json/github/sarif`，`--lang en/zh`，规则选择，退出码 0/1/2 | ✅ |
| 文件级抑制注释 `{# docxtpl-lint: disable=… #}` | ✅ |
| 跨段落开关 `--allow-cross-paragraph` | ✅ |
| GitHub Action（路径可含空格，D24）、pre-commit 钩子 | ✅ |
| CI：Python 3.10–3.13 加 Windows；每周用 docxtpl 最新版和 master 回归（D25）；Action 自测；打包检查 | ✅ |
| README 中英双语，配 SVG 演示图（D26）、CHANGELOG、CONTRIBUTING、issue 和 PR 模板 | ✅ |
| 构建出 wheel 和 sdist，并通过 twine check | ✅ |

## 刻意不做
- 自动修复。
- 渲染期才会出现的错误（类型、include、自定义过滤器）。
- 尾注和批注：docxtpl 不渲染这两部分（D21）。
- `&lt;` 规则（D9）、错误前缀规则（D10）、数据类型推断（DTL304/305）。

## 可行性与风险（复核）
- **规则确定性**：每条 2xx 规则都有一个坏例，测试会用真实 docxtpl 0.20.2 渲染，确认确实会出错或输出被破坏；好例必须能正常渲染。这样规则说法和 docxtpl 实际行为对不上的风险很低。
- **剩余风险**
  - DTL201 依赖上游正则。上游的 PR #645 合并后这条要失效，CI 每周回归会把这种变化暴露出来。
  - `¶N` 的段号和用户在 Word 里数的不一致，靠表格路径和原文片段弥补。
  - `--data` 只做存在性检查，不做类型检查。
- **星数预期**：现实区间 150–400。突破 1k 要被 docxtpl 文档收录，或者做出 Playground。

## 路线图
- v0.2：浏览器 Playground（D19，用 pyodide 直接跑现有代码，不移植到 JS）；可选 `--docxtpl-version` 开关；pyproject 里支持 `[tool.docxtpl-lint]` 配置段。
- v0.3：pptx/xlsx 模板（docxtpl 不支持，要看需求）；嵌套 JSON Schema 作为数据契约。

## 发布与推广（每一步都要老板确认）
1. 建 GitHub 仓库并推送，打 tag `v0.1.0`，发 GitHub Release。
2. 发布到 PyPI（推荐 Trusted Publishing，或用 token）。
3. 给 docxtpl 提一个文档 PR，在 FAQ 里加 “Linting templates”；在 #378/#603/#644 下以作者身份留言（先分析问题再附链接）。
4. 中文渠道：掘金、知乎、V2EX 各发一篇“docxtpl 模板报错找不到位置？”的文章，配 demo-zh.svg。
