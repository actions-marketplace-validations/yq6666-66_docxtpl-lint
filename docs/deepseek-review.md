# DeepSeek 原始回复

下面是 DeepSeek API 的原样输出，未作修改。我对每条意见的采纳情况见 [decisions.md](decisions.md)。

## 第 1 轮：计划评审（deepseek-reasoner）

# docxtpl-lint 计划评审

先给结论：**方向和切入点是对的**（docx 不能 grep、docxtpl 只抛第一个错且没位置，这是真痛点），**但计划里有 3 处自相矛盾/过度宣称、2 条规则（DTL205/206）大概率没做真机验证、以及一个会在发布首日就爆的误报源（DTL001 跨段落默认报 error）**。下面按你要的四块 + 纠错来写。

---

## 一、星数潜力 & 怎么提高

1. **现实预期**：这个定位（窄众 + 上游只有 2.7k 星 + 没有官方背书）第一年 **150–400 star** 是合理区间，不是 100–300。超过 1k 只有三种路径：被 docxtpl 官方文档收录、有浏览器 Playground、或者扩展到「OOXML 里的 Jinja」泛用（pptx/xlsx）。

2. **最高杠杆：GIF 必须进 v0.1，不能放 v0.2。** CLI linter 的 README 转化率几乎全由那段 3 秒动画决定。现在计划把 GIF 排在 v0.2，等于把发布时最重要的资产推后了。

3. **第二杠杆：中文渠道，优先级应高于英文渠道。** docxtpl 的真实使用量很大一块在中国（报表/合同自动化）。一篇「docxtpl 模板报错找不到位置？我把定位做到了单元格」发到掘金/知乎/V2EX，带来的 star 大概率超过 Show HN。计划里完全没写中文发布渠道，只写了去上游 issue 留言（风险最高、收益最低的一种）。

4. **第三杠杆：被上游「收编」而不是「借名」。** 与其起名 `docxtpl-lint` 蹭搜索词，更稳的是同时提供一个可被上游接受的接口（见第五节第 5 条）。被写进 docxtpl README/FAQ 是唯一能让星数上 1k 的单点。

5. **第四杠杆：Playground。** docx 是二进制，用户没法把模板贴进 gist/issue 求助。一个纯前端（JSZip 解压 + 同一套规则移植，或 wasm）的「拖进去就出报告」页面，是这个品类独有的传播武器，比 SARIF 值钱得多。

6. **第五杠杆：`--format github` 而不是 SARIF。** 见第四节第 6 条。二者投入产出比差一个数量级。

7. **加分但成本可控的**：一份 `docxtpl-lint` GitHub Actions 的 marketplace 收录 + 一个「故意写坏的模板」demo 仓库 + 每个规则的 `help_url`。

---

## 二、建议补充的规则（确定性）

现有 12 条里 1xx/3xx 是通用 Jinja，2xx 是 docxtpl 特有，**2xx 只有 6 条明显不够，docxtpl 特有的坑远不止这些**：

1. **`{%tc %}` 的对称规则（当前完全缺失）**：`{%tc for%}` / `{%tc endfor%}` 必须同一行（tr 有 DTL206，tc 没有）；必须同一张表；`{%tc%}` 块不能跨 `{%tr%}` 块边界。这三条和 DTL204/205/206 一一对应。
2. **`{%r %}` 规则**：`{%r%}` 的开闭必须落在同一段落（甚至同一 run）；`{%r%}` 挂在空 run 上；`{%r%}` 与 `{%p%}` 混用。
3. **`{%p%}` 用在表格单元格里唯一的那个 `<w:p>`** —— 删掉后 `<w:tc>` 没有子 `<w:p>`，OOXML 非法，docxtpl 渲染出来 Word 打不开。这是确定性的结构判断。
4. **不存在的/写错的前缀**：`{{p ... }}`、`{{tr ... }}`、`{{tc ... }}`、`{%pr ... %}`。docxtpl 只认 `{%p/tr/tc/r%}` 和 `{{r}}`，其余是纯文本，会原样留在文档里。确定性强、几乎零误报。
5. **空标签**：`{% %}`、`{{ }}`、`{# #}`、`{##}`（DTL103 可能抓不到 `{# #}`，因为它不是语句）。
6. **分隔符错配的专用规则**：`{{ x %}` / `{% x }}`。现在会被 DTL001 兜住，但消息是「`{{` 没有闭合 `}}`」，用户看到「我明明写了 `%}`」会困惑。
7. **Jinja 扩展语法**：`{% do %}`、`{% break %}`、`{% continue %}`。docxtpl 默认 `jinja2.Environment()` **不启用** `do`/`loopcontrols`（见第三节第 5 条），这几条在 docxtpl 里必炸。这是一条你现在的实现会**漏报**的规则。
8. **`{% end if %}`（关键字中间带空格）、`{% endif }}`、`{% endfi %}`**：给专门消息而不是笼统 DTL102/103。
9. **Word 转义实体**：用户在 Word 里打 `<`，OOXML 里存的是 `&lt;`，`{% if a &lt; b %}` 传给 Jinja 就是语法错。需要先确认 docxtpl 是否 unescape；如果不 unescape，这是**最高频的真实坑之一**，值得单开一条规则。
10. **内联抑制**：支持 `{# docxtpl-lint: ignore DTL301 #}`。docx 里没有注释语法，但用 Jinja 注释做载体天然可行，用户会非常需要。
11. **`--data` 侧的确定性规则（比 DTL301/302 更有价值）**：
    - DTL303：`{% for x in v %}` 而样例数据里 `v` 不是 list/dict → 「不可迭代」，而不是「不存在」。
    - DTL304：`items[].price` 而 `items` 是 `["a","b"]` → 「类型不匹配」。现在 `_lookup` 会退化成 DTL301「不存在」，消息是错的。
    - DTL305：`_lookup` 只在**所有**元素都缺字段时才报。列表里 10 个元素有 1 个缺 `price` 不报 → 这是漏报，要么报 warning，要么在 README 里明确写清。
    - DTL306：定义了但从未调用的 `{% macro %}`、赋值了但从未使用的 `{% set %}`（warning）。
12. **文件类型规则**：`.doc` / 加密 docx / 损坏 zip / `.dotx` 的支持与否，走 exit 2 并给人话。

---

## 三、误报风险（按严重度排序）

1. **DTL001 跨段落默认报 error —— 这是最可能毁掉首日口碑的一条。** docxtpl 的 `patch_xml` 会「strip all xml tags inside `{% %}`/`{{ }}`」，所以**跨段落的标签其实能正常渲染**，只是段落结构被吃掉。也就是说这是语义告警、不是语法错误。计划里承认了这点，但方案是「README 说明 + 后续加 `--allow-cross-paragraph` 关掉」——方向反了。应该默认降为 warning，或者拆成 DTL002（error：整篇都没有闭合；warning：在后续段落闭合）。`{%- ... -%}` 是 Jinja 官方推荐的空白控制写法，用它跨段是常见操作，默认 error 会撞一脸。

2. **`{% raw %}` 没被跳过。** `check_blocks` 的 `BLOCKS` 里有 `raw`，但 `scan_tags` 照样会去扫 raw 里的内容：`{% raw %}...{% if x %}...{% endraw %}` 会产出 DTL101/102/103 三条误报，而且 `check_syntax` 拼出来的源码里那段 `{% if x %}` 还会再炸一次。

3. **`{% set x %}...{% endset %}` 块必然误报 DTL103。** `build_jinja_source` 是「一个标签一行、丢掉正文」拼源码的，`{% set x %}` 单独一行在 Jinja 里是 `expected token '='`。讽刺的是 `check_blocks` 里专门把 `set` 改名为 `set_block` 处理了它，说明作者知道这个结构，但 `check_syntax` 忘了。

4. **`scan_tags` 给 `{% tr for ... %}` 强行赋了 `prefix="tr"`**，导致同一条标签同时触发 DTL202 和 DTL204/205/206。从 docxtpl 视角它就是 body 为 `tr for ...` 的普通语句（必然报 unknown tag），报一条 DTL202 就够了，多报是噪音。

5. **`Environment(extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"])` 与 docxtpl 默认环境不一致。** docxtpl 默认 `jinja2.Environment()`，这两个扩展默认关闭。结果是 `{% do %}` / `{% break %}` 在 linter 里通过、在 docxtpl 里报错 —— 系统性漏报。要么对齐默认环境，要么加 `--jinja-extensions` 并补一条规则。

6. **DTL202 对 `{{ tr }}` / `{{ tr x }}` 误报。** `_SPACED_PREFIX = r"\{[%{]-?\s+(tr|tc)\s"` 不区分 `{%` 和 `{{`，而 docxtpl 没有 `{{tr }}` 这种前缀。一条变量名叫 `tr`（或 `tr` 开头的英文单词后跟空格）的模板会无故报错。

7. **`collect_paths` 的三类 DTL301 误报**：
   - 本地宏：`{% macro m() %}{% endmacro %}{{ m() }}` → `m` 不在 scope，被当成数据变量 → DTL301。
   - `{% import "a.html" as f %}{{ f.x }}` → `f.x` → DTL301。计划「风险 2：macro/call/include/import 只是跳过」低估了后果，跳过 import 恰恰造成了误报，而 `nodes.Macro` 的 `visit` 直接 `return` 也漏掉了 `m` 本身。
   - `{{ x | default(y) }}`、`{{ x | d("") }}`、`{{ x is defined }}` —— 这些写法恰恰是**为了处理缺字段**而存在的，现在全部报 DTL301。

8. **DTL206 是最危险的一条规则，且很可能没做真机验证。** 计划里说「3 个上游 issue 场景（#644/#603/#378）做成了 fixture 并用 docxtpl 0.20.2 验证过」，也就是 12 条规则里只有约 3 条被真实渲染验证。DTL206 断言「`{%tr for%}` 和 `{%tr endfor%}` 在同一行会吃掉整行」。请务必拿 docxtpl 官方文档里的行循环示例跑一遍 —— 如果官方推荐写法正好是行首单元格放 `{%tr for%}`、行尾单元格放 `{%tr endfor%}`（同一行），这条规则就是灾难性误报。**DTL205/206 必须先有 fixture + 真机渲染结果再发布。**

9. **`¶N` 是 linter 自己的段落序号，和用户在 Word 里数出来的段落不是一回事。** 表格单元格末尾必须有的空 `<w:p>`、`w:txbxContent`、`w:sdt`、被修订删除的内容，都会让编号漂移。用户第一件事就是拿这个序号去 Word 里找，找不到 → 「这工具定位不准」→ 一星差评。缓解：始终打印原文 snippet（现在有），最好再打印前一段的简短上下文。

10. **修订标记（`w:ins`/`w:del`）。** 如果 reader 把 `w:del` 里的文本也算进去，用户会在一个「Word 里看起来没有标签」的位置看到报错。

11. **DTL302 在共享 `sample.json` 场景下必然全是噪音**（一份数据文件服务多个模板）。它现在是 warning，但配合 `--warnings-as-errors` 会直接让 CI 红。建议默认关闭，或只在单文件检查时开启。

12. **DTL201 依赖上游私有正则**（见第五节第 1 条），一旦上游改了就静默失效/误报。至少要在 CI 里 nightly 跑上游 master 对齐。

13. `check_syntax` 的行号兜底 `kept[min(max(ln,0), len(kept)-1)]` 会把越界/EOF 错误一律指到**最后一个标签**（通常是 `{% endfor %}` 之类），位置完全错。`Unexpected end of template` 这类错误必然指错。

14. `check_syntax` 只在 `block` 为空时才跑，且 DTL103 只报第一个错误 —— 见下面第五节第 2 条。

15. 次要但值得记：`inner.strip(" -+")` 会 strip 掉正文结尾合法的 `-`/`+`（只该剥离 `{%-`/`-%}` 的空白控制符）；`scan_tags` 在 DTL001 后 `break`，一段里多个未闭合标签只报第一个；DTL301/302 是 sort 之后 append 的，JSON 输出顺序不稳定。

---

## 四、README / 发布改进

1. **消息不要中英混排。** 现在是 `"`{% if %}` 未闭合，缺少 `{% endif %}`（直到文档末尾 / until end of part）/ unclosed block"` —— 一行三种语言，非常不专业，也让 JSON 消费方难以解析。改成 `--lang en|zh`（或语言包），默认英文。
2. **顶部加免责声明**：`Not affiliated with python-docx-template.`。包名直接借用了上游关键词，不主动澄清会被当成官方或山寨，也会让上游维护者不舒服。
3. **「上游 issue → 规则」对照表**比规则表更有说服力，也是上游愿意链接你的理由。现在这个映射只散落在 Why 段落里：#644→DTL201、#603→DTL204、#378→？（#378 对应哪条规则，README 里看不出来）。
4. **对 lintxtpl 别写成贬低式对比。** 「锁死 0.20.2 的 patch_xml」这种描述读起来是攻击；而且对比表里写的事实如果不是逐条核实过，一旦有偏差就是声誉事故。改成「致敬 + 差异」，并在 README 里致谢。
5. **中文文档拆成 `README.zh.md`**，不要在同一个文件底部堆一半。对英文读者是噪音，对搜索引擎也不友好。
6. **加 `--format github`，把 SARIF 降到最低优先级。** docx 是二进制，SARIF 需要 `startLine >= 1`，你只能编行号，Code Scanning 的展示效果很差。而 `::error file=x.docx,line=1,col=1::DTL201 ...` 会直接出现在 PR 的日志注解里，几十行代码就够。
7. **补「什么叫干净」的输出、`--list-rules` 的示例、性能数字**（40 页合同 X 秒）、`[tool.docxtpl-lint]` 配置文件示例、`--select`/`--ignore` 是否支持 `DTL2xx` 通配、`--warnings-as-errors` 的退出码。这些是用户第一次打开 README 就想找的。
8. **加一节「本工具不检查什么」**：不检查运行时错误（缺 filter、`attr` 失败、类型错误、`include` 目标不存在、宏签名不匹配）。这是用户最容易误解、也最容易给差评的点，主动写出来能省掉一半 issue。
9. **加「如何新增一条规则」文档 + 规则注册表**。窄众工具靠贡献者续命，插件化是最便宜的续命方式。
10. **写清维护承诺**：维护者是谁、响应时间、issue 模板、支持范围。企业背景做 OSS，最怕「发了就没人管」。
11. **GIF 从 v0.2 提到 v0.1；Playground 作为 v0.2 的头号项**（比 SARIF 和批注扫描值钱得多）。
12. **行动清单里删掉「去 3 个 issue 里留言」这种形式**，换成：先给 docxtpl 提一个**改善错误消息的 PR**（把出错标签的原文带进 `TemplateSyntaxError`），在 PR 描述里提这个 linter；只在**活跃且未关闭**的 issue 里、明确标注「我是作者」、先给出对该 issue 的具体分析再附链接。
13. **`action.yml` 的坑**：glob 展开、带空格的文件名、Python 版本固定、`--format github` 输出注解、是否 fail-on-warning。**pre-commit hook** 需要 `files: \.docx$` 或 `types_or: [zip]`，并说明 `.dotx/.docm` 的支持情况。

---

## 五、我认为计划里明确错了的地方

1. **自相矛盾：差异表写「不依赖 docxtpl 内部实现」，而 DTL201 恰恰建立在 docxtpl 的正则 `[^}%]*` 上。** 这是最依赖上游实现的一条规则。要么承认，要么改掉 DTL201 的触发条件。
2. **过度宣称：差异表写「语法错误只报第一个 | 全部」，但你自己也只报第一个 DTL103**，而且 `block` 非空时 `check_syntax` 整段跳过。README 的「Reports every error at once」必须限定为「块配对错误一次报全，Jinja 语法错误仍只报第一个（与 docxtpl 一致）」。
3. **DTL206（乃至 DTL205）没有真机验证。** 计划里只提了 3 个上游 issue 场景做了 fixture，而 12 条规则里 2xx 有 6 条。发布前**每条 2xx 规则都必须有 good/bad fixture + docxtpl 真实渲染结果**，否则第一条负面反馈就会出现在这里。
4. **`--allow-cross-paragraph` 的方向错了**（详见第三节第 1 条）。默认应该是 warning，而不是「默认 error + 一个关掉它的开关」。
5. **命名策略有风险，且「现实目标 100–300 星」的归因错了。** 星数由「被上游文档收录 + GIF + 中文社区」决定，不是由「issue 里有人推荐」决定。更稳的做法：包名保留 `docxtpl-lint`（明确声明非官方），**同时**提供 `docxtpl.lint` 兼容层，主动提议让上游收编 —— 这才是上 1k 的唯一单点。
6. **`--docxtpl-version` 排在 v0.3 太晚。** DTL201 从 v0.1 起就绑定具体版本，v0.1 就应该在 README 写 `Tested with docxtpl 0.11–0.20.2`，并在 CI 里 nightly 跑上游 master + 全部 fixture，否则规则会静默失效或误报。
7. **26 个测试对 12 条规则太薄。** 每条规则至少 good/bad 两个 fixture；再加一个「对语料库里的任意 .docx 不崩溃」的 smoke/fuzz 测试；再加一个「每个 fixture 都能被 docxtpl 渲染」的集成测试。这是这个项目唯一真正的护城河。
8. **扫描范围只写了正文/页眉/页脚/脚注**，漏了 endnotes、`comments.xml`、`w:txbxContent`、`w:sdt`。笔记里说「批注没有扫描」放在「还没做到」里可以，但 endnotes 应该在 v0.1 就覆盖（和 footnotes 同一套代码路径）。
9. **没有许可证/合规检查。** 如果参考过 lintxtpl 的规则文案或实现，先确认它的 license；MIT 声明里建议加 `Not affiliated with python-docx-template`。
10. **`action.yml` 里 `files: "templates/**/*.docx"` + `args: "--data ..."` 的字符串拼接**在带空格的路径下会碎，需要在 action 里做数组化处理。
11. **小 bug（说明测试覆盖不够）**：`_data_paths` 是死代码；DTL301/302 在排序后 append，JSON 顺序不稳定；`Tag.col` 与 `Location.column` 都按 1-based 但表格位置的格式 `... ¶1]:1:` 少了一个可读的列标签。
12. **`--data` 只支持 JSON**，且没有 schema 版本号、没有 `--data` 的多 context 支持、没有 `--context` 从 fixture 目录取。JSON 输出也应该带 `"schema_version"`，否则下游 CI 解析会碎。

---

**如果只能改三件事**：① 把 DTL205/206 拿去用真 docxtpl 渲染验证，不通过就删；② DTL001 跨段落默认降为 warning；③ GIF + `--format github` 进 v0.1，SARIF 推到 v0.3。这三件事决定了首发当天是「哇」还是「误报太多」。

## 第 2 轮：DeepSeek 对我实测结论的反驳（deepseek-chat）

<details><summary>我发出的提示词</summary>

```text
你之前评审了 docxtpl-lint 的计划（下面附上你的评审结论摘要）。我用 docxtpl 0.20.2 把你的说法逐条跑了一遍，下面是我的决定。请逐条反驳或同意，用中文回答，简短、编号。如果某条你认为我错了，请给出能在 docxtpl 里验证的反例。

实测结果（真实渲染）：
- {%tr for%} 和 {%tr endfor%} 在同一行 -> TemplateSyntaxError（DTL206 确认是真问题）
- tr for/endfor 跨两张表 -> 不报错，但表格内容被静默清空（DTL205 保留，消息改为“会静默损坏”）
- {%tc for%}/{%tc endfor%} 在同一行 -> 正常；在不同行 -> 不报错但单元格结构错乱 -> 新增 DTL207
- 跨段落标签 "{{ client." / "email }}" -> 渲染成功，只是段落被合并（你说对了）
- {% do %} / {% break %} -> docxtpl 里报 unknown tag（你说对了，linter 改用默认 Environment）
- {% raw %}{% if x %}{% endraw %} -> 渲染成功（你说对了，raw 内容要跳过）
- {% set x %}..{% endset %} -> 我的一标签一行拼接方式 Jinja 解析正常（你说错了）
- {% if a < b %}（Word 存成 &lt;）-> 正常渲染，patch_xml 会反转义（这条规则不需要）
- {{p x}} / {{tr x}} / {{tc x}} -> 是合法的：docxtpl 正则 ({%|{{)p ... 也认 {{ 前缀（你说的“写错前缀”规则大部分不成立）
- 修订删除的文字存在 w:delText 里，reader 只读 w:t，所以不会误报
- 宏 m() 被报为 DTL301 -> 是 bug，修复

我的决定：
采纳：DTL001 拆分（跨段落但最终闭合 -> DTL002 warning；到文档末尾都没闭合 -> DTL001 error）；跳过 raw；默认 Environment；DTL202 只匹配 {%；宏/import 名加入作用域；is defined / default 守卫；--lang en|zh（默认 en），消息不再中英混排；README.zh.md 单独一份；加 Not affiliated 声明；issue->规则对照表；--format github 注解；JSON 加 schema_version；文件级抑制 {# docxtpl-lint: disable=DTL301 #}；DTL303（for 迭代对象不是 list/dict）；DTL302 改为显式开启（--report-unused-data）；“本工具不检查什么”章节；用 rich 导出 SVG 做 README 演示（静态 SVG 代替 GIF）；CI 加一个 docxtpl 最新版的 job；每条 2xx 规则配 good/bad fixture，并测试 docxtpl 的实际行为。
拒绝：浏览器 Playground（要移植到 JS，超出 v0.1 范围，放进路线图）；“p 是单元格里唯一段落”规则（实测渲染成功，没证据证明会坏）；DTL304/305 类型推断（单份样例数据推不出类型，误报风险高）；去掉 SARIF（已经写好且有测试，留着，另加 github 格式）；提供 docxtpl.lint 兼容层（单方面猜测上游意愿）；未使用的 set/macro 警告（低价值）；改包名（保留 docxtpl-lint，加声明）。
其他：DTL103 的 EOF 定位问题——只有在块配对检查通过后才会跑语法检查，所以 EOF 类错误已经先被 DTL101 拦住。
```
</details>

下面逐条回应。**同意/反驳**按你的编号走。

## 一、你实测推翻我的地方（我认错）

1. **`{% set x %}...{% endset %}` 我错了。** 你说得对：docxtpl 的 `patch_xml` 会把标签之间的正文剥掉再拼，`{% set x %}` 单独成行在 Jinja 里确实能解析（`set` 块语法在 Jinja 里 `{% set x %}` 后跟 `{% endset %}` 是合法的，不需要 `=`）。我把它和「`{% set x = 1 %}` 单行」搞混了。**同意你的处理**：不报 DTL103。

2. **`{{p x}}` / `{{tr x}}` / `{{tc x}}` 我错了。** docxtpl 的 `_SPACED_PREFIX` 是 `r"\{[%{]-?\s+(tr|tc|p|r)\s"` 之类，`{{` 前缀确实被认。**同意**：删掉「写错前缀」规则里针对 `{{p/tr/tc}}` 的部分。但 `{%pr ... %}`、`{% p x %}`（`p` 后跟非 `%}`）这类仍值得保留——你实测里没覆盖，建议补 fixture 再定。

3. **`{% if a &lt; b %}` 我错了。** `patch_xml` 会 unescape，这条规则不需要。**同意删除**。

4. **跨段落标签我方向说反了。** 你实测「渲染成功，只是段落被合并」，那 DTL002 warning 是对的，DTL001 只留给「到文档末尾都没闭合」。**同意你的拆分**，这比我原来的「默认 error + 开关」正确。

5. **`{% do %}` / `{% break %}` 我方向对但结论要修正。** 我说「docxtpl 默认不启用 do/loopcontrols」——你实测 docxtpl 里报 unknown tag，说明 docxtpl 用的确实是裸 `Environment()`。**同意 linter 改用默认 Environment**。但注意：这意味着 linter 会**漏报**用户自己 `Environment(extensions=[...])` 的场景，README 里要写清「本工具按 docxtpl 默认环境检查」。

6. **`{% raw %}` 我方向对。** 你实测渲染成功，raw 内容要跳过。**同意**。

7. **DTL206 我方向对。** 你实测 `{%tr for%}`/`{%tr endfor%}` 同行报 `TemplateSyntaxError`（DTL206 确认）。**同意保留**。但请把「官方文档行循环示例」也做成 fixture——如果官方示例正好同行，那 docxtpl 自己文档就是错的，这条规则要加 `help_url` 指向 issue。

8. **DTL205 我方向对但消息要改。** 你实测跨表不报错但静默清空。**同意**保留 + 消息改「会静默损坏」。

## 二、你拒绝我的地方（我部分同意，部分保留）

9. **Playground 拒绝——同意。** v0.1 不做，路线图里放。但**GIF/SVG 进 v0.1** 这条我坚持：你采纳了「rich 导出 SVG」，等于同意了，只是形式从 GIF 换成静态 SVG。OK。

10. **「p 是单元格唯一段落」拒绝——同意。** 你实测渲染成功，我没证据证明会坏。删。

11. **DTL304/305 类型推断拒绝——同意。** 单份样例推不出类型，误报风险高。删。

12. **SARIF 保留——同意。** 已写好且有测试，留着，加 `--format github`。我原来「SARIF 降到最低优先级」是错的，应该「两个都留」。

13. **`docxtpl.lint` 兼容层拒绝——同意。** 单方面猜上游意愿确实不妥。改成：README 里写「如果上游愿意收编，欢迎联系」，不主动造兼容层。

14. **未使用 set/macro 警告拒绝——同意。** 低价值。

15. **改包名拒绝——同意。** 保留 `docxtpl-lint` + Not affiliated 声明。

## 三、我保留意见的地方（请再确认）

16. **DTL202 只匹配 `{%`——同意你的修正**，但请确认 `{% p x %}`（`p` 后跟空格再跟非 `%}`）在 docxtpl 里到底是 unknown tag 还是被 `_SPACED_PREFIX` 吃掉。这决定 DTL202 的边界。

17. **DTL103 EOF 定位——你说「已被 DTL101 拦住」，部分对。** 块配对通过后，`{% if x %}` 单标签不闭合是 DTL101 拦；但 `{% if x %}{% endif %}{% endif %}` 这种**多余闭合**、或 `{% for %}` 里 `{% break %}`（默认环境 unknown tag）仍会走到 `check_syntax`，EOF 定位问题还在。建议：`check_syntax` 的 `kept[min(max(ln,0), len(kept)-1)]` 越界时**不要兜底到最后一个标签**，直接报「位置未知」+ 原文 snippet。

18. **DTL303 采纳——但注意**：`{% for x in v %}` 里 `v` 是字符串时 Jinja 会按字符迭代，不报错。你的规则要区分「不可迭代」（int/None）和「可迭代但可能非预期」（str）。建议 str 只 warning。

19. **DTL302 显式开启——同意**，但 `--warnings-as-errors` 下 DTL302 默认关闭后，CI 里用户要显式 `--report-unused-data` 才会红，这个交互要在 README 写清。

20. **`--lang en|zh` 默认 en——同意**，但中文用户占比高，建议 README 顶部第一行就给 `README.zh.md` 链接，别让中文用户翻到底。

## 四、我原来评审里你还没回应的点

21. **`scan_tags` 给 `{% tr for %}` 赋 `prefix="tr"` 导致 DTL202 + DTL204/205/206 重复报**——你采纳了 DTL202 只匹配 `{%`，但没提这个重复报的问题。建议：`{% tr for %}` 只报 DTL202（unknown tag），不再报 204/205/206，因为 docxtpl 根本不会把它当 tr 指令处理。

22. **`collect_paths` 的三类 DTL301 误报**（本地 macro、`{% import as f %}`、`| default` / `is defined`）——你采纳了「宏/import 名加入作用域」和「is defined / default 守卫」，但**本地 macro 调用 `{{ m() }}`** 这条要确认：`m` 是 macro 名不是数据变量，加进 scope 后要标记为「已定义」，否则仍报 DTL301。

23. **`¶N` 段落序号和 Word 里数出来的不一致**——你没回应。建议：输出里同时给「前一段 snippet」做锚点，或改用「表格 T 行 R 列」这种结构化定位。

24. **`w:delText` 你实测 reader 只读 `w:t` 不误报——同意**，但 `w:ins`（修订插入）里的 `w:t` 会被读到，如果用户开着修订模式写模板，标签会被重复计算。建议加 fixture。

25. **`--data` 多 context / `--context` 从 fixture 目录取**——你没回应。JSON 加 `schema_version` 你采纳了，但多 context 支持建议进 v0.1，否则共享 sample.json 场景下 DTL301 全是噪音。

26. **`action.yml` 带空格路径字符串拼接**——你没回应。这个在 Windows 用户里必炸，建议 v0.1 就修。

27. **`--docxtpl-version` 排 v0.3 太晚**——你没回应。DTL201 从 v0.1 就绑版本，README 里至少要写 `Tested with docxtpl 0.11–0.20.2`，CI nightly 跑上游 master。

## 五、总结

你的实测把 3 条我明确说错的（set 块、`{{p}}` 前缀、`&lt;` 转义）纠正了，我认。DTL001 拆分、raw 跳过、默认 Environment、DTL202 只匹配 `{%`、宏/import 入 scope、is defined/default 守卫——这些采纳都对。

**我唯一坚持的**：DTL206 的 fixture 必须包含 docxtpl 官方文档的行循环示例，如果官方示例同行且报错，这条规则要加 `help_url` 指向上游 issue，否则用户会以为是你误报。

**我建议你补的**：第 17（EOF 兜底）、21（`{% tr for %}` 重复报）、22（本地 macro 调用）、24（`w:ins` 修订插入）、25（多 context）、26（action.yml 空格路径）这 6 条，你还没明确回应。

## 第 3 轮：代码找 bug（deepseek-chat，回复被 max_tokens 截断）

（deepseek-reasoner 那一次调用返回了空内容，所以改用 deepseek-chat 重试。）

## (A) 可确认的真实 bug

1. **`_part_label` 对 `word/header1.xml` 之外的多位数编号处理正确，但对 `word/header.xml`（无数字）会返回 `"header"`，而 `_sort_key` 里 `re.sub(r"\d+$", "", "header")` 得到 `"header"`，`order` 里有 `"header"`，没问题——但 `_part_label` 对 `word/footnotes.xml` 返回 `"footnotes"`，`_sort_key` 里 `kind = re.sub(r"\d+$", "", "footnotes")` = `"footnotes"`，OK。** 这条其实没问题，跳过。

2. **`_para_text` 会把 `w:delText` 之外的东西也算进去吗？** `_para_text` 只迭代 `w:t`、`w:tab`、`w:br`。`w:delText` 是独立标签，不会被计入——这是正确的。但 **`w:ins` 里的 `w:t` 会被计入**（因为 `w:ins` 是 `w:r` 的父级，`w:t` 的祖先链会经过 `w:ins` 再到 `w:p`，`anc is p` 成立）。这是期望行为。**不是 bug。**

3. **`_para_text` 对 `w:tab`/`w:br` 的祖先检查有 bug**：`w:tab` 和 `w:br` 通常直接在 `w:r` 里，祖先链是 `w:r → w:p`，没问题。但 **`w:br` 在 `w:r` 里时，`el.getparent()` 是 `w:r`，`w:r` 的 parent 是 `w:p`**，OK。**不是 bug。**

4. **`_walk_part` 中 `w:tr` 的处理**：`if tag == f"{_W}tr" and stack:` —— 但 `w:tr` 也可能出现在 `w:tbl` 之外（比如 `w:sdt` 里嵌套的表格）。如果 `stack` 为空（不在表格里），`w:tr` 不会被计数，但也不会出错。**不是 bug。**

5. **`_walk_part` 中 `w:tc` 的处理**：`elif tag == f"{_W}tc" and stack:` —— 同样问题。但注意 **`w:tc` 的 `elif` 链**：如果 `tag == w:tr` 且 `stack` 为空，会走到 `elif tag == w:tc` 吗？不会，因为 `tag == w:tr` 为真，第一个 `if` 分支进入但条件 `and stack` 为假，整个 `if` 不执行，然后 **因为这是 `if/elif` 链，`elif` 不会被执行**。所以 `w:tr` 在 stack 为空时不会误入 `w:tc` 分支。**不是 bug。**

6. **`_walk_part` 的计数器 `counters["p"]` 是跨整个 part 的，但 `stack[-1][3]`（cell_para）在进入嵌套表格时会被重置**。问题：**当嵌套表格结束时，外层表格的 `cell_para` 计数器不会恢复**。看代码：进入 `w:tbl` 时 `stack.append([..., 0])`，退出时 `stack.pop()`。外层表格的 `stack[-1][3]` 在嵌套表格期间不会被修改（因为 `w:p` 处理时用的是 `stack[-1]`，即嵌套表格的条目）。所以嵌套表格结束后，外层 `stack[-1][3]` 保持原值。**不是 bug。**

7. **`scan_tags` 中 `carry` 的 `offset` 计算**：`offset = len(prev[0]) if prev else 0`。`prev[0]` 是上一段未闭合的文本。当标签跨段时，`tag_col = start + 1 - offset`。如果 `start == 0`（标签正好从 carry 文本开头开始），会走 `if prev is not None and start == 0` 分支用 `prev[2]`。**但如果 `start > 0` 且 `prev is not None`**，`tag_col = start + 1 - offset`，这里 `start` 是 `t` 中的位置，`t = prev[0] + p.text`，所以 `start - offset` 是 `p.text` 中的位置，`+1` 转 1-based。**看起来对。** 但 **`tag_para = p`**，而标签实际开始于 `prev[1]`（上一段）——如果标签在上一段开始、在这一段结束，`tag_para` 应该是 `prev[1]` 而不是 `p`。看代码：`if prev is not None and start == 0: tag_para, tag_col = prev[1], prev[2]`，**只有 `start == 0` 时才用 `prev`**。如果标签在上一段中间开始（比如 `{% if x` 在上一段末尾），`carry = (t[start:], tag_para, tag_col)` 其中 `tag_para` 是上一段的 `p`（因为此时 `start > 0`，走 `else` 分支 `tag_para = p`，但 `p` 是当前段！）。**这是 bug**：跨段标签的起始位置被记录为当前段而非起始段。

   触发模板：段落1文本 `"hello {% if x"`，段落2文本 `" %}world{% endif %}"`。`scan_tags` 处理段落1时，`{% if x` 未闭合，`carry = ("{% if x", p1, col)`，其中 `p1` 是段落1（因为 `start > 0`，走 `else`，`tag_para = p`，此时 `p` 就是段落1）。等等，处理段落1时 `prev` 是 `None`，所以 `offset = 0`，`t = p1.text`，`start` 是 `{%` 在段落1中的位置，`tag_para = p1`。**这是对的。** 处理段落2时，`prev = ("{% if x", p1, col)`，`offset = len("{% if x") = 7`，`t = "{% if x" + " %}world{% endif %}"`。`opener.search(t, 0)` 找到 `{%` 在位置 0，`start = 0`，走 `if prev is not None and start == 0` 分支，`tag_para = p1`。**对的。** 所以这条不是 bug。

8. **`check_docxtpl_tags` 的 DTL201 检测**：`_PREFIXED_RAW = re.compile(r"(\{%|\{\{)(tr|tc|p|r) ")`。这匹配 `{%tr ` 或 `{{tr `。但 docxtpl 的语法是 `{%tr ... %}`（无空格）或 `{% tr ... %}`（有空格）。`_PREFIXED_RAW` 匹配的是 `{%tr `（无空格），这是 docxtpl 的"紧凑"形式。然后检查 `body` 里是否有 `%` 或 `}`。**问题**：`{%tr if x %}` 的 `body` 是 `"if x "`，没有 `%` 或 `}`，不报 DTL201。但 `{%tr if x %}...{%tr endif %}` 这种嵌套里，如果 body 里有 `%`（比如 `{%tr if x % 2 == 0 %}`），会报 DTL201。**这是设计意图。** 但 **`{{tr x }}` 的 `close` 是 `}}`，`body` 是 `"x "`，OK。** 不是 bug。

9. **`check_docxtpl_tags` 的 DTL202 检测**：`_SPACED_PREFIX = re.compile(r"\{%-?\s+(tr|tc|p|r)\s")`。这匹配 `{% tr `（有空格）。但 **`{%- tr `（带 `-` 空白控制）也会匹配**，因为 `-?` 允许 `-`。然后 `end = p.text.find("%}", m.start())`，如果找不到 `%}`，`end = -1`，`p.text[m.start():end+2]` = `p.text[m.start():1]`，**这是空字符串或错误切片**。触发：段落文本 `"{% tr if x"`（未闭合）。`m.start()` 是 0，`end = -1`，`p.text[0:1]` = `"{"`。**这是 bug**：snippet 错误。

10. **`check_syntax` 的 `lineno` 映射**：`build_jinja_source` 为每个 tag 生成一行，但 **Jinja2 的 `lineno` 是 1-based，`ln = exc.lineno - 1`**。如果 `exc.lineno` 是 0（某些错误），`ln = -1`，`0 <= ln` 为假，走 `Location(file, kept[0].para.part, 0)`。**OK。**

11. **`analyse` 的 `visit` 对 `nodes.Name` 的处理**：`if isinstance(n, nodes.Name) and n.ctx == "load" and n.name in scope and scope[n.name] is None: return`。这跳过局部变量。但 **`scope` 是可变字典，在 `visit` 递归中会被修改**（比如 `Assign` 分支 `scope[nm] = None`）。这可能导致 **同一作用域内的后续引用被错误跳过**。触发：`{% set x = 1 %}{{ x }}{{ y }}`。`x` 被加入 scope，`{{ x }}` 被跳过（正确），`{{ y }}` 不在 scope，被记录（正确）。**但如果 `{% set x = 1 %}{{ x.y }}`**，`x.y` 是 `Getattr`，`path_of` 返回 `scope.get("x", "x")` = `None`，`f"{None}.y"` = `"None.y"`？看 `path_of`：`base = path_of(n.node, scope)`，`n.node` 是 `Name("x")`，`scope.get("x", "x")` = `None`，`return scope.get(n.name, n.name)` = `None`。然后 `Getattr` 分支 `return f"{base}.{n.attr}" if base else None`，`base` 是 `None`，返回 `None`。**OK，不会产生 `"None.y"`。**

12. **`_resolve` 的 `[]` 处理**：`nxt = [x for v in nxt if isinstance(v, list) for x in v] + [v for v in nxt if isinstance(v, dict)]`。这会把 list 展开，把 dict 保留。但 **如果 `nxt` 里既有 list 又有 dict，顺序会变**（先所有 list 元素，再所有 dict）。**不是 bug，只是顺序问题。**

13. **`check_data` 的 `roots` 计算**：`roots.add(path.split(".")[0].removesuffix("[]"))`。对于 `items[].name`，`path.split(".")[0]` = `"items[]"`，`removesuffix("[]")` = `"items"`。**OK。** 但对于 `items[0].name`（数字索引），`path.split(".")[0]` = `"items[0]"`，`removesuffix("[]")` 不变，`roots` 里是 `"items[0]"`，而 context 的 key 是 `"items"`，**DTL302 会误报 `items` 未使用**。触发：`{{ items[0].name }}` + context `{"items": [{"name": "a"}]}`。**这是 bug。**

14. **`check_data` 的 DTL303**：`bad = [v for v in vals if v is None or isinstance(v, bool | int | float)]`。**`isinstance(v, bool | int | float)` 在 Python 3.10+ 才支持 `|` 语法**，但 `bool` 是 `int` 的子类，`isinstance(True, int)` 为真。**OK。** 但 **字符串不会被标记为 bad**（注释说 strings 可迭代），**这是设计意图。**

15. **`lint_path` 的 `parts` 顺序**：`parts = list(dict.fromkeys(p.part for p in paras))`。`iter_paragraphs` 按 `_sort_key` 排序，所以 `parts` 顺序是 body, header1, footer1, footnotes。**OK。**

16. **`lint_path` 的 `issues.sort`**：`key=lambda i: (order.get(i.location.part, 99), i.location.paragraph, i.location.column)`。**DTL302 的 `location.part` 是 `"data"`**，`order.get("data", 99)` = 99，排在最后。**OK。**

17. **`scan_tags` 的 `in_raw` 处理**：`if in_raw: m_end = _ENDRAW_RE.search(t)`。如果 `t` 里有 `{% endraw %}`，`in_raw = False, i = m_end.end()`。但 **`i` 被设置为 `m_end.end()`，然后进入 `while True` 循环**。**OK。** 但如果 `in_raw` 为真且 `m_end` 为 `None`，`continue` 跳过当前段。**OK。**

18. **`scan_tags` 的 `raw` 处理**：`if kind == "stmt" and not prefix and body == "raw": m_end = _ENDRAW_RE.search(t, i); if m_end: i = m_end.end(); continue; in_raw = True; break`。**`break` 跳出 `while True` 循环，然后进入下一段**。但 **`carry` 没有被设置**，所以 `{% raw %}` 之后的文本如果在本段内，会被跳过（因为 `break` 后 `while` 结束，`for p in paras` 继续下一段）。**这是 bug**：`{% raw %}...{% endraw %}` 在同一段内时，`{% endraw %}` 之后的文本不会被扫描。

    触发模板：段落文本 `"{% raw %}{{ x }}{% endraw %}{{ y }}"`。`scan_tags` 处理时，找到 `{% raw %}`，`m_end = _ENDRAW_RE.search(t, i)` 找到 `{% endraw %}`，`i = m_end.end()`，`continue`。然后 `opener.search(t, i)` 找到 `{{ y }}`，正常处理。**等等，`continue` 回到 `while True` 开头，`opener.search(t, i)` 从 `i` 开始找，找到 `{{ y }}`。** 所以 **不是 bug**。我误读了。

19. **`_keyword` 对 `set` 的处理**：`if kw == "set" and "=" not in tg.body: return "set_block"`。**`{% set x %}`（无 `=`）被当作 `set_block`**，但 Jinja2 的 `{% set x %}` 是 block set，需要 `{% endset %}`。**OK。** 但 **`{% set x = 1 %}` 的 `body` 是 `"x = 1"`，有 `=`，返回 `"set"`**，`"set"` 不在 `BLOCKS` 里，所以不会被压栈。**OK。**

20. **`check_blocks` 的 `MIDDLE` 处理**：`elif kw in MIDDLE: if not stack or stack[-1][0] not in MIDDLE[kw]: issues.append(...)`。**`{% else %}` 在 `{% for %}` 里是合法的**，`MIDDLE["else"] = {"if", "for"}`，`stack[-1][0]` 是 `"for"`，在 `MIDDLE["else"]` 里，**不报错。OK。**

21. **`check_blocks` 的 `end` 处理**：`elif kw.startswith("end"): want = "set_block" if kw == "endset_block" else kw[3:]`。**`{% endfor %}` 的 `kw` 是 `"endfor"`，`kw[3:]` = `"for"`。OK。** 但 **`{% endset %}` 的 `kw` 是 `"endset"`，`kw[3:]` = `"set"`，而 `want` 应该是 `"set_block"`**。看代码：`want = "set_block" if kw == "endset_block" else kw[3:]`。**`{% endset %}` 的 `kw` 是 `"endset"`，不等于 `"endset_block"`，所以 `want = "set"`**。但 `set_block` 在栈里是 `"set_block"`，`want = "set"` 不匹配。**这是 bug**：`{% set x %}...{% endset %}` 会被报 DTL101（未闭合）和 DTL102（意外的 endset）。

    触发模板：段落文本 `"{% set x %}hello{% endset %}"`。`_keyword` 对 `{% set x %}` 返回 `"set_block"`，压栈。`{% endset %}` 的 `_keyword` 返回 `"endset"`（因为 `kw == "endset"`，不是 `"endset_block"`），`want = "set"`，栈顶是 `"set_block"`，不匹配，报 DTL102。然后栈里 `"set_block"` 未弹出，报 DTL101。**确认 bug。**

22. **`check_docxtpl_tags` 的 `_pair_issues`**：`if op.prefix != cl.prefix: return [DTL204]`。**`{%p if x %}...{% endif %}` 的 `op.prefix = "p"`，`cl.prefix = ""`，报 DTL204。** 但 docxtpl 的 `{%p if %}` 需要 `{%p endif %}` 吗？**docxtpl 文档说 `{%p if %}` 和 `{%p endif %}` 配对**，所以报 DTL204 是对的。**OK。**

23. **`check_docxtpl_tags` 的 `stack` 处理**：`idx = next((i for i in range(len(stack) - 1, -1, -1) if stack[i][0] == want), None)`。**如果 `idx` 是 `None`，`continue`**。但 **`del stack[idx:]` 会删除 `idx` 及之后的所有元素**，包括不匹配的。**这是设计意图**（跳过中间未闭合的）。**OK。**

24. **`_resolve` 的 `if not nxt: return None if cur else []`**：**`cur` 是上一轮的结果**。如果 `cur` 为空（比如 `[]` 展开后为空），返回 `[]`（无法证明缺失）。**OK。**

25. **`analyse` 的 `visit` 对 `nodes.Getitem` 的处理**：`if isinstance(n, nodes.Getitem) and isinstance(n.arg, nodes.Const) and isinstance(n.arg.value, str): base = path_of(n.node, scope); return f"{base}.{n.arg.value}" if base else None`。**`items[0]` 的 `n.arg` 是 `Const(0)`，`isinstance(0, str)` 为假，返回 `None`**。所以 `items[0].name` 的 `path_of` 返回 `None`，**不会被记录为 use**。**这是 bug**：`{{ items[0].name }}` 不会被 `--list-vars` 列出，也不会被 DTL301 检查。

    触发模板：段落文本 `"{{ items[0].name }}"` + context `{}`。`analyse` 不会记录 `items[0].name`，`check_data` 不会报 DTL301。**确认 bug。**

26. **`_part_label` 对 `word/header1.xml` 返回 `"header1"`，但 `_sort_key` 里 `kind = re.sub(r"\d+$", "", "header1")` = `"header"`，`num = re.findall(r"\d+$", "header1")` = `["1"]`，`int("1")` = 1。** **OK。**

27. **`iter_paragraphs` 的 `names` 排序**：`sorted((n for n in zf.namelist() if _part_label(n)), key=_sort_key)`。**`_sort_key` 对 `word/document.xml` 返回 `(0, 0)`，对 `word/header1.xml` 返回 `(1, 1)`，对 `word/header2.xml` 返回 `(1, 2)`。** **OK。**

28. **`_walk_part` 的 `visit` 对 `w:p` 的处理**：`elif tag == f"{_W}p": counters["p"] += 1; if stack: stack[-1][3] += 1; yield Paragraph(...)`。**`w:p` 在 `w:tc` 里时，`stack[-1][3]` 递增。** 但 **`w:p` 在 `w:txbxContent` 里时，`stack` 可能为空（如果文本框不在表格里），`cell_para = 0`，`cells = ()`。** **OK。**

29. **`_para_text` 对文本框的处理**：`for el in p.iter(f"{_W}t", ...)`。**`p.iter()` 会递归遍历所有后代**，包括 `w:txbxContent` 里的 `w:t`。然后 `anc = el.getparent()`，向上找 `w:p`。**如果 `w:t` 在文本框里，它的祖先链是 `w:t → w:r → w:p(文本框内的) → w:txbxContent → ... → w:p(外层)`**。`anc` 会停在**文本框内的 `w:p`**，`anc is not p`（`p` 是外层段落），所以 `continue`。**这是正确的**：文本框内的文字不会被计入外层段落。**OK。**

30. **`_walk_part` 对文本框的处理**：`visit` 递归遍历所有子元素。**`w:txbxContent` 里的 `w:p` 会被 `visit` 处理**，`counters["p"]` 递增，`stack` 不变（如果文本框不在表格里），`cells = ()`，`cell_para = 0`。**这是正确的**：文本框内的段落单独成段。**OK。**

31. **`scan_tags` 的 `carry` 在 `in_raw` 时的处理**：`if in_raw: m_end = _ENDRAW_RE.search(t); if not m_end: continue`。**`continue` 跳过当前段，但 `carry` 没有被设置**。如果 `{% raw %}` 在上一段，`{% endraw %}` 在下一段，`in_raw` 为真，`t` 是当前段文本（`prev` 是 `None`，因为 `carry` 在 `{% raw %}` 时被 `break` 跳出，没有设置 `carry`）。**等等**：`{% raw %}` 处理时 `in_raw = True; break`，`break` 跳出 `while True`，然后 `for p in paras` 继续下一段。下一段 `prev, carry = carry, None`，`carry` 是 `None`（因为 `{% raw %}` 时没有设置 `carry`），`prev = None`，`t = p.text`。`if in_raw: m_end = _ENDRAW_RE.search(t)`。**如果 `{% endraw %}` 在下一段，`m_end` 找到，`in_raw = False, i = m_end.end()`。** **OK。** 但如果 `{% raw %}` 和 `{% endraw %}` 跨多段，每段都 `continue` 直到找到 `{% endraw %}`。**OK。**

32. **`scan_tags` 的 `carry` 与 `in_raw` 交互**：如果 `{% raw %}` 在段落1，`{% endraw %}` 在段落2，段落2 的 `t` 是 `p2.text`（`prev = None`）。**`{% endraw %}` 之前的文本被跳过**（因为 `in_raw` 为真时只找 `{% endraw %}`）。**OK。**

33. **`check_syntax` 的 `build_jinja_source`**：`lines.append(("{% " + tg.body + " %}") if tg.kind == "stmt" else ("{{ " + tg.body + " }}"))`。**`tg.body` 已经被 `_strip_ws_control` 处理过**，所以 `{%- if x -%}` 的 `body` 是 `"if x"`，重建为 `"{% if x %}"`。**OK。** 但 **`{% raw %}` 和 `{% endraw %}` 不会被加入 `tags`**（因为 `scan_tags` 里 `raw` 被特殊处理，`continue` 或 `break`），所以 `build_jinja_source` 不会包含它们。**OK。**

34. **`check_syntax` 对 `{% set x %}...{% endset %}` 的处理**：`build_jinja_source` 会生成 `{% set x %}` 和 `{% endset %}` 两行。**Jinja2 的 `parse` 会正确处理 `{% set x %}...{% endset %}`**（如果中间有内容）。但 **`build_jinja_source` 只包含 tag，不包含 tag 之间的文本**，所以 `{% set x %}` 和 `{% endset %}` 之间没有内容，Jinja2 会报错吗？**`{% set x %}{% endset %}` 是合法的**（空 block set）。**OK。**

35. **`check_blocks` 对 `{% set x %}...{% endset %}` 的处理**：如上所述，`{% endset %}` 的 `want = "set"`，栈顶是 `"set_block"`，不匹配。**确认 bug（同 #21）。**

36. **`_keyword` 对 `{% endset %}` 的处理**：`kw = "endset"`，`if kw == "set" and "=" not in tg.body` 为假（`kw` 是 `"endset"`），`if kw == "endset"` 为假（代码里没有这个分支），返回 `"endset"`。**然后 `check_blocks` 里 `want = "set_block" if kw == "endset_block" else kw[3:]`，`kw[3:]` = `"set"`。** **确认 bug。**

37. **`check_docxtpl_tags` 的 `stack` 对 `{% set x %}...{% endset %}` 的处理**：`kw = "set_block"`（来自 `_keyword`），在 `BLOCKS` 里，压栈。`{% endset %}` 的 `kw = "endset"`，`want = "set"`，`idx = next(...)` 找不到 `"set"`，`continue`。**所以 DTL204 等不会报，但栈里 `"set_block"` 未弹出。** **OK（不影响 DTL2xx）。**

38. **`analyse` 对 `{% set x %}...{% endset %}` 的处理**：`nodes.AssignBlock` 分支 `for c in n.body: visit(c, scope)`，然后 `for nm in names(n.target): scope[nm] = None`。**OK。**

39. **`_resolve` 对 `path` 里 `[]` 的处理**：`part.endswith("[]")`，`key = part[:-2]`。**`items[].name` 的 `parts` 是 `["items[]", "name"]`。** 第一轮 `key = "items"`，`nxt = [c["items"] for c in cur if ...]`，然后 `is_list` 为真，展开 list。**OK。**

40. **`check_data` 的 `seen` 去重**：`if path in seen or any(path == g or path.startswith(g + ".") for g in an.guarded): continue`。**`path.startswith(g + ".")` 检查 `path` 是否是 `g` 的子路径**。**OK。**

41. **`check_data` 的 DTL301 对 `items[].name` 的处理**：`_resolve(d, "items[].name")`。**如果 `d = {"items": []}`**，第一轮 `key = "items"`，`nxt = [[]]`（`c["items"]` 是 `[]`），`is_list` 为真，`nxt = [] + []` = `[]`，`if not nxt: return []`。**返回 `[]`（空列表），不是 `None`**，所以 `all(_resolve(d, path) is None for d in contexts)` 为假，**不报 DTL301**。**这是设计意图**（空列表无法证明缺失）。**OK。**

42. **`check_data` 的 DTL303 对 `items` 的处理**：`vals = [v for d in contexts for v in (_resolve(d, path) or [])]`。**如果 `_resolve` 返回 `None`，`or []` 变成 `[]`。** **OK。**

43. **`lint_path` 的 `disabled` 处理**：`disabled = disabled_rules(tags)`。**`disabled_rules` 只检查 `tg.kind == "comment"`**。**OK。**

44. **`lint_path` 的 `allow_cross_paragraph`**：`disabled.add("DTL002")`。**OK。**

45. **`lint_path` 的 `rep.variables`**：`sorted({p for p, _ in an.uses})`。**`an.uses` 是 `list[tuple[str, Tag]]`。** **OK。**

46. **`_part_label` 对 `word/header1.xml` 返回 `"header1"`，但 `_PART_PATTERNS` 里 `re.compile(r"^word/header\d*\.xml$")` 匹配 `word/header.xml`（无数字）和 `word/header1.xml`。** **OK。**

47. **`_sort_key` 对 `word/header.xml`（无数字）的处理**：`label = "header"`，`kind = re.sub(r"\d+$", "", "header")` = `"header"`，`num = re.findall(r"\d+$", "header")` = `[]`，`int(num[0]) if num else 0` = 0。**OK。**

48. **`iter_paragraphs` 的 `names` 排序对 `word/header.xml` 和 `word/header1.xml`**：`_sort_key` 分别返回 `(1, 0)` 和 `(1, 1)`。**OK。**

49. **`_walk_part` 的 `visit` 对 `w:tbl` 的处理**：`counters["tbl"] += 1; stack.append([counters["tbl"], 0, 0, 0])`。**嵌套表格的 `tbl` 编号是全局递增的**（`counters["tbl"]` 不重置）。**这是设计意图**（"nested tables counted too"）。**OK。**

50. **`_walk_part` 的 `visit` 对 `w:tr` 的处理**：`if tag == f"{_W}tr" and stack: stack[-1][1] += 1; stack[-1][2] = 0`。**`w:tr` 在 `w:tbl` 里时，`stack[-1]` 是当前表格的条目。** **OK。**

51. **`_walk_part` 的 `visit` 对 `w:tc` 的处理**：`elif tag == f"{_W}tc" and stack: stack[-1][2] += 1; stack[-1][3] = 0`。**`w:tc` 在 `w:tr` 里时，`stack[-1]` 是当前表格的条目。** **OK。**

52. **`_walk_part` 的 `visit` 对 `w:p` 的处理**：`elif tag == f"{_W}p": counters["p"] += 1; if stack: stack[-1][3] += 1; yield Paragraph(...)`。**`w:p` 在 `w:tc` 里时，`stack[-1][3]` 递增。** **OK。**

53. **`_walk_part` 的 `visit` 对 `w:p` 在 `w:txbxContent` 里的处理**：**`w:txbxContent` 不是 `w:tbl`/`w:tr`/`w:tc`，所以 `stack` 不变。** 如果文本框在表格单元格里，`stack` 非空，`stack[-1][3]` 递增（**这是 bug**：文本框内的段落会递增外层单元格的 `cell_para` 计数器）。**确认 bug。**

    触发结构：表格单元格里有一个段落，然后一个文本框（`w:p` → `w:r` → `w:pict`/`w:drawing` → ... → `w:txbxContent` → `w:p`）。文本框内的 `w:p` 会被 `visit` 处理，`stack[-1][3]` 递增，导致外层单元格的 `cell_para` 计数错误。

54. **`_para_text` 对 `w:ins` 的处理**：**`w:ins` 里的 `w:t` 会被计入**（因为 `w:ins` 是 `w:r` 的父级，`w:t` 的祖先链经过 `w:ins` 再到 `w:p`）。**这是期望行为。** **OK。**

55. **`_para_text` 对 `w:delText` 的处理**：**`w:delText` 不是 `w:t`，不会被 `p.iter(f"{_W}t", ...)` 匹配。** **OK。**

56. **`_para_text` 对 `w:del` 里的 `w:t` 的处理**：**`w:del` 里的 `w:t` 会被计入**（因为 `w:del` 是 `w:r

## 第 4 轮：委派 DeepSeek 起草 reader 测试（deepseek-chat）

```python
import copy

from docx import Document
from lxml import etree

from docxtpl_lint.reader import iter_paragraphs

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_W = f"{{{W}}}"


def _save_and_reload(doc, tmp_path, mutate):
    """Save doc, reopen the document.xml part, apply mutate(root), write back, return path."""
    path = tmp_path / "t.docx"
    doc.save(str(path))
    import zipfile

    with zipfile.ZipFile(str(path)) as zf:
        parts = {n: zf.read(n) for n in zf.namelist()}
    root = etree.fromstring(parts["word/document.xml"])
    mutate(root)
    parts["word/document.xml"] = etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    with zipfile.ZipFile(str(path), "w", zipfile.ZIP_DEFLATED) as zf:
        for n, data in parts.items():
            zf.writestr(n, data)
    return path


def _first_body_p(root):
    return root.find(f"{_W}body").find(f"{_W}p")


def test_ins_counted_del_excluded(tmp_path):
    doc = Document()
    doc.add_paragraph("keep")

    def mutate(root):
        p = _first_body_p(root)
        ins = etree.SubElement(p, f"{_W}ins")
        ins.set(f"{_W}id", "1")
        ins.set(f"{_W}author", "a")
        ins.set(f"{_W}date", "2020-01-01T00:00:00Z")
        r_ins = etree.SubElement(ins, f"{_W}r")
        t_ins = etree.SubElement(r_ins, f"{_W}t")
        t_ins.text = "INSERTED"

        dele = etree.SubElement(p, f"{_W}del")
        dele.set(f"{_W}id", "2")
        dele.set(f"{_W}author", "a")
        dele.set(f"{_W}date", "2020-01-01T00:00:00Z")
        r_del = etree.SubElement(dele, f"{_W}r")
        dt = etree.SubElement(r_del, f"{_W}delText")
        dt.text = "DELETED"

    path = _save_and_reload(doc, tmp_path, mutate)
    paras = [p for p in iter_paragraphs(path) if p.part == "body"]
    text = paras[0].text
    assert "INSERTED" in text
    assert "DELETED" not in text


def test_textbox_paragraph_is_separate(tmp_path):
    doc = Document()
    doc.add_paragraph("outer")

    def mutate(root):
        p = _first_body_p(root)
        r = etree.SubElement(p, f"{_W}r")
        t = etree.SubElement(r, f"{_W}t")
        t.text = "OUTER"
        pict = etree.SubElement(r, f"{_W}pict")
        txbx = etree.SubElement(pict, f"{_W}txbxContent")
        inner_p = etree.SubElement(txbx, f"{_W}p")
        inner_r = etree.SubElement(inner_p, f"{_W}r")
        inner_t = etree.SubElement(inner_r, f"{_W}t")
        inner_t.text = "INNERBOX"

    path = _save_and_reload(doc, tmp_path, mutate)
    paras = [p for p in iter_paragraphs(path) if p.part == "body"]
    texts = [p.text for p in paras]
    assert "INNERBOX" in texts
    outer = next(p for p in paras if "OUTER" in p.text)
    assert "INNERBOX" not in outer.text
    inner = next(p for p in paras if "INNERBOX" in p.text)
    assert "OUTER" not in inner.text


def test_nested_table_cells(tmp_path):
    doc = Document()
    doc.add_paragraph("top")

    def mutate(root):
        body = root.find(f"{_W}body")
        tbl = etree.SubElement(body, f"{_W}tbl")
        tr = etree.SubElement(tbl, f"{_W}tr")
        tc = etree.SubElement(tr, f"{_W}tc")
        p = etree.SubElement(tc, f"{_W}p")
        r = etree.SubElement(p, f"{_W}r")
        t = etree.SubElement(r, f"{_W}t")
        t.text = "OUTERCELL"

        inner_tbl = etree.SubElement(tc, f"{_W}tbl")
        inner_tr = etree.SubElement(inner_tbl, f"{_W}tr")
        inner_tc = etree.SubElement(inner_tr, f"{_W}tc")
        inner_p = etree.SubElement(inner_tc, f"{_W}p")
        inner_r = etree.SubElement(inner_p, f"{_W}r")
        inner_t = etree.SubElement(inner_r, f"{_W}t")
        inner_t.text = "INNERCELL"

    path = _save_and_reload(doc, tmp_path, mutate)
    paras = [p for p in iter_paragraphs(path) if p.part == "body"]

    outer = next(p for p in paras if p.text == "OUTERCELL")
    assert len(outer.cells) == 1
    assert (outer.cells[0].table, outer.cells[0].row, outer.cells[0].col) == (1, 1, 1)
    assert outer.cell_para == 1

    inner = next(p for p in paras if p.text == "INNERCELL")
    assert len(inner.cells) == 2
    assert (inner.cells[0].table, inner.cells[0].row, inner.cells[0].col) == (1, 1, 1)
    assert (inner.cells[1].table, inner.cells[1].row, inner.cells[1].col) == (2, 1, 1)
    assert inner.cell_para == 1
```

## 委派任务
- README.zh.md：DeepSeek 翻译，我审阅，原样采用
- CONTRIBUTING.md：DeepSeek 起草，我补了 venv 激活这一步
- tests/test_reader.py：DeepSeek 起草，我审阅，3 个测试全部通过，删掉了一个没用到的 import
