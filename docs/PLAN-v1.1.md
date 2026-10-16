# docxtpl-lint v1.1 计划（定稿）

依据两份评估：`docs/eval/deepseek-eval.md`（DeepSeek 设计的 86 个对抗用例 + UX 评审）和 `docs/eval/self-eval.md`（从 GitHub tag 全新安装后，在接近真实的模板上逐个测试子命令）。两份评估的分歧通过 docxtpl 0.20.2 实验裁决（第 10 轮，记录在 `docs/decisions.md` D58–D72）。

## 优先级与状态

| 优先级 | 事项 | 来源 | 状态 |
|---|---|---|---|
| P0 | `}}` 出现在字符串字面量里时误报 DTL103：扫描器按 Jinja 的方式跳过引号内的内容 | DeepSeek 用例（E5） | 已完成 |
| P0 | 缺少一个 `}` 会把后面的段落全部吞掉，只报 DTL002 警告：现在遇到新标签就报 DTL001 错误，并从那里继续扫描 | 自评 | 已完成；`fix` 会建议补上 `}` |
| P0 | `{% raw %}` 没有闭合时不报错：现在报 DTL101 | DeepSeek 用例 | 已完成 |
| P0 | DTL209 把 `{# 注释 #}` 当成会丢失的文字（误报） | DeepSeek 用例（E4） | 已完成 |
| P0 | DTL209 只看标签所在的段落：现在也检查 `{%tr` 所在行的其他单元格、`{%tc` 所在单元格的其他段落 | DeepSeek 用例（E2），实验确认整行内容都会丢 | 已完成；在官方基准模板上误报仍为 0 |
| P0 | 新增 DTL210：`{%p if %}…{%p endif %}` 写在同一段里，docxtpl 会报错 | 裁决分歧时发现 | 已完成，用例已对照真实 docxtpl 验证 |
| P0 | 已有 DTL201/202/203 报错时，不再额外报 DTL209 | 两份评估都提到 | 已完成 |
| P1 | `--data` / `--schema` 的 JSON 文件带 BOM（Windows 记事本保存的格式）时被拒绝 | 自评 | 已完成 |
| P1 | `verify` / `infer` / `diff` / `fix` 遇到不是 docx 的文件时抛出 traceback：现在返回退出码 2 并给出一行提示 | 自评 | 已完成 |
| P1 | `--explain DTLxxx` 查看单条规则说明 | DeepSeek UX 建议 | 已完成 |
| P1 | `infer` 只有一个模板时不再输出 `x-docxtpl-templates` | DeepSeek UX 建议 | 已完成 |
| P1 | 86 个对抗用例 + 裁决后的预期结果纳入测试（`scripts/adversarial.py`，CI 会跑） | 本轮 | 已完成 |
| P2 | 重写 `--data` 的帮助文字；在线试用页加载超过 30 秒时给出提示 | DeepSeek UX 建议 | 已完成 |

## 不做的事项（附理由）

- **GitHub 输出里不再把 `%` 转义成 `%25`**：GitHub 的 workflow 命令规范要求这样转义，DeepSeek 同意不改。
- **`fix --apply` 直接改写 docx**：Word 会把文字拆成多个 run，直接改写不安全（D48）。
- **`infer` 输出里去掉父级路径**：`items`、`user` 这些父级节点本身就是数据契约的一部分，DeepSeek 同意保留。
- **`--quiet` / `--verbose`**：退出码和 `--format json` 已经能满足需求。
- **彩色输出 / 支持 NO_COLOR**：已经有了（终端里自动上色，有 `--no-color`）。DeepSeek 提这条是因为没注意到这个功能已存在。
- **diff 改用新的符号表示**：当前输出可读性尚可，推迟。

## 待用户确认的发布操作（都还没做）

1. `git push origin main && git push origin v1.1.0`
2. `gh release create v1.1.0 dist/* --title v1.1.0 --notes-file <CHANGELOG 中 1.1.0 那一节>`
3. 推送到 main 后，Pages 会自动重新部署在线试用页，部署后需要验证页面能正常加载。
4. （可选）上传 PyPI：需要先配置 trusted publisher，然后手动触发 `publish-pypi.yml`。
