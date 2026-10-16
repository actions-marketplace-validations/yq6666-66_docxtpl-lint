# docxtpl-lint v0.2 计划（定稿）

目标：让更多人用起来（更多 star），同时提高质量。计划草案交给 DeepSeek 质疑了两轮（第 5、6 轮，原文见 `docs/deepseek-review.md`），各项决定记在 `docs/decisions.md`。

## 优先级与状态

| 优先级 | 事项 | 状态 |
|---|---|---|
| P0 | 用 docxtpl 官方仓库的 40 个测试模板做基准测试（`scripts/benchmark.py`，CI 每次都跑） | 已完成：误报 7 → 0，故意出错的模板仍能检出 |
| P0 | 修掉基准测试里发现的误报：单元格标签 cellbg/colspan/vm/hm，以及 Word 智能引号 | 已完成 |
| P0 | 新增 DTL208：单元格标签写在表格外面（docxtpl 会直接报错） | 已完成，并用真实 docxtpl 渲染验证 |
| P1 | 浏览器 Playground（Pyodide + GitHub Pages，文件不出本机） | 已完成；在 Node 和真实浏览器里都验证过；冒烟测试要求输出和 CPython 逐字一致 |
| P1 | `pyproject.toml` 配置文件（`[tool.docxtpl-lint]`，未知键直接报错） | 已完成 |
| P1 | `--context N`：在问题下方显示前后段落，不用打开 Word 也能定位 | 已完成（在终端里默认 1，其他情况默认 0） |
| P1 | 规则文档 `docs/rules.md` + JSON/SARIF 里的帮助链接 | 已完成（DeepSeek 起草，我改过） |
| P1 | GitHub Actions 升级到 Node 24 版本 | 已完成（版本号通过 GitHub API 核实） |
| P1 | PyPI Trusted Publishing 工作流 | 已准备好，只能手动触发，**没有运行** |
| P2 | 演示图 | 重新生成了 SVG 演示图（带上下文行），加了 Playground 截图 |

## 不做的事项及原因

- **--fix-safe 自动修复**：能"安全"自动修的问题很少，而改写 docx 有损坏文件的风险，也会降低大家对这个工具的信任。
- **跨段落检查参数**：v0.1 已经有 `--allow-cross-paragraph`，不需要新增。
- **mkdocs 文档站**：README 加 `docs/rules.md` 已经够用，Playground 本身就是门面。
- **VS Code 插件**：维护成本高；用 `--context` 加 SARIF（GitHub 代码扫描）就能看到问题位置。
- **用 vhs 录 GIF 演示**：用 Playground 截图和能重新生成的 SVG 代替，不会二进制文件越积越多。

## 待用户确认的发布操作（都还没做）

1. `git push origin main && git push origin v0.2.0`
2. `gh release create v0.2.0 dist/* --title v0.2.0 --notes-file <CHANGELOG 中 0.2.0 那一节>`
3. 仓库 Settings → Pages → Source 选 "GitHub Actions"；发布 release 后会自动部署，也可以手动执行 `gh workflow run pages.yml`
4. （可选）PyPI：先在 pypi.org 添加 pending trusted publisher（owner yq6666-66、repo docxtpl-lint、workflow publish-pypi.yml、environment pypi），再执行 `gh workflow run publish-pypi.yml -f tag=v0.2.0`
5. （可选）对外推广（上游 issue 回复、中文社区文章）：每一条都要单独确认
