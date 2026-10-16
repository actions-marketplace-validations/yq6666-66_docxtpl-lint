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


## 第 5 轮：v0.2 计划（提示词）

````
docxtpl-lint v0.1.0 已发布（GitHub，0 star，PyPI 还没发）。下面是 v0.2 的计划草案，目标是推广增长和质量。请用中文、编号作答：逐条判断要做、不做还是降级，说明理由，并指出遗漏的高杠杆项和风险。不要为了说好话而同意。

新的事实：我用 v0.1.0 跑了 docxtpl 官方仓库 tests/templates 下的 40 个真实模板：
- 7 条是误报：
  - docxtpl 自有的单元格标签 {% cellbg x %}、{% colspan n %}、{% vm %}、{% hm %} 被报成 unknown tag（DTL103），实际上 patch_xml 会改写它们；
  - 智能引号：patch_xml 会把标签内的 ‘’“” 换成普通引号，而我们报成 syntax error。
- 1 条是真问题：template_error_tpl.docx 里多了一个 {% endif %}，这个模板本来就是故意写错的。

草案（按我认为的优先级）：
P0 质量
  a. 修上面的误报：识别 cellbg/colspan/vm/hm，并新增 DTL208 检查这些标签是否在表格单元格里；标签内的智能引号先归一化再解析。
  b. 基准：CI 每周拉取 docxtpl 官方的测试模板跑一遍，要求“0 误报，template_error 必须报出”；README 写上基准结果。
P1 增长
  c. 浏览器 Playground：GitHub Pages + Pyodide，直接加载我们的 wheel（lxml 和 jinja2 在 Pyodide 里都有），拖入 docx 就在本地出报告，文件不上传。
  d. 用 vhs 录一段更好的 GIF？还是继续用静态 SVG？
  e. 文档站点（mkdocs）？
P1 工程
  f. Action 升级到 Node24 版本：checkout@v7、setup-python@v7。
  g. 准备好 PyPI Trusted Publishing 的发布工作流（release 发布时触发，环境名 pypi），但不主动触发。
  h. 配置文件：pyproject 里的 [tool.docxtpl-lint] 段（select/ignore/data/allow-cross-paragraph 等）。
  i. --context N：多打印出错位置前后几段的文字，不用打开 Word 就能定位（“无需 Word 的位置预览”）。
P2 待定
  j. --fix-safe：自动修复，比如把 `{% tr` 改成 `{%tr`、把智能引号改成直引号。我倾向不做：v0.1 承诺过只读；而且改写 docx 时 run 拆分和格式很难保真。
  k. 跨段落开关：v0.1 已经有 --allow-cross-paragraph 了。
  l. VS Code 扩展：docx 是二进制，VS Code 里看不了，价值存疑。

````

### DeepSeek 回复（原文）

下面逐条判断。先说一个总体判断：**这份草案把"质量"和"增长"的优先级排反了，而且 P0 里混进了一个不该在 v0.2 做的检查项。** 另外，你手上这 40 个模板的基准数据，价值远大于草案里任何一条增长项，但草案只把它当成"CI 跑一下"。

---

## 逐条判断

**a. 修误报（cellbg/colspan/vm/hm + 智能引号归一化）—— 做，但拆开**

- 智能引号归一化：**必做，P0 最高**。这是纯 bug，patch_xml 的行为是 docxtpl 的既定语义，你的 linter 不识别就是错的。而且实现简单（解析前对标签内字符做一次映射），风险低。
- 识别 cellbg/colspan/vm/hm：**做，但只做"识别 + 不报 DTL103"**，也就是把它们加入已知标签白名单。
- **DTL208（这些标签必须在表格单元格里）—— 降级到 P2 或直接砍掉。** 理由：
  1. 这是 docxtpl 的语义约束，不是 lint 的核心价值。你的工具定位是"发现模板错误"，不是"复刻 docxtpl 的全部运行时校验"。
  2. 你只有 1 个真问题样本（还是故意写错的），没有任何证据表明用户会犯这个错。
  3. 每加一条检查就多一份误报风险和维护成本。v0.1 已经因为"自作聪明"产生了 7 条误报，教训应该吸取。
  4. 如果真要做，也应该先收集用户反馈，而不是拍脑袋加。

**b. CI 每周拉官方模板跑基准 —— 做，但升级为 v0.2 的头号任务**

这是整个草案里**最高杠杆**的一条，但草案把它排在 a 之后、当成"顺带做"。

- 应该做成：`benchmark` 子命令 + 一个独立的 GitHub Actions workflow，每周 + 每次 release 跑。
- 输出应该是机器可读的（JSON），CI 里断言"误报数 == 0"。
- README 上放 badge + 结果表格。
- **但要注意一个陷阱**：docxtpl 官方模板会变。如果哪天官方加了一个新标签，你的 CI 会红。所以断言应该是"误报数 == 0 且 template_error 被报出"，而不是"输出完全一致"。同时要允许一个 `known_false_positives` 白名单文件，出问题时能快速 pin。

**c. 浏览器 Playground（Pyodide）—— 降级，别在 v0.2 做**

- 技术上可行，但**成本被严重低估**：lxml 在 Pyodide 里能装，但 wheel 体积大、首次加载慢（几十 MB），用户体验差；docxtpl 本身依赖 python-docx，链式依赖在 Pyodide 里踩坑概率高。
- 更关键的是：**你现在 0 star，没有用户，Playground 是给"已经有流量"的项目做转化用的，不是用来获客的。** 没人会因为一个 Playground 发现你的项目。
- 建议：v0.2 先不做。等有 50+ star、有人提 issue 说"想在线试"再做。或者做一个更轻的替代：**一个静态 HTML 页面，展示"输入模板片段 → 输出报告"的示例**，零依赖，5 分钟能做完。

**d. vhs GIF vs 静态 SVG —— 做，但优先级低于 b**

- 静态 SVG 的问题是"看不出这是工具在跑"。GIF/视频对 README 转化率确实有提升。
- 但 vhs 录 GIF 有个坑：终端字体、配色、时长都要调，容易做成"自嗨 demo"。**建议先做一个 15 秒的 GIF，展示"拖入 docx → 出报告 → 定位到错误行"这一个核心流程**，别贪多。
- 优先级：低于 b，高于 c/e。

**e. mkdocs 文档站 —— 降级**

- 你现在 README 就够用。文档站是给"功能多到 README 放不下"的项目做的。
- v0.2 的正确做法是：**把 README 写扎实**（安装、用法、检查项列表、基准结果、已知限制），而不是搭一个空壳文档站。
- 等检查项超过 15 条、或者有多个子命令时再上 mkdocs。

**f. Action 升级到 Node24（checkout@v7、setup-python@v7）—— 做，但注意**

- **先确认这两个版本号是否存在。** 截至我知识截止，checkout 最新是 v4，setup-python 最新是 v5。v7 大概率是你记错了或者不存在。**不要写不存在的版本号，CI 会直接挂。**
- 如果确实有 Node24 版本，升级是低风险高收益的（避免 deprecation warning）。但这不是 v0.2 的卖点，别写进 release notes 当亮点。

**g. PyPI Trusted Publishing 工作流 —— 做，P0**

- 这是**发布基础设施**，不是"增长项"。你 PyPI 还没发，这是 v0.2 的硬前提。
- 用 `pypa/gh-action-pypi-publish` + OIDC，环境名 `pypi`，触发条件 `on: release: types: [published]`。
- **建议 v0.2 就正式发 PyPI**，别只"准备好不触发"。0 star 的项目，PyPI 上的存在感比 GitHub 更重要——很多人是 `pip install` 搜到的。

**h. pyproject 配置文件 —— 做，但砍掉一半选项**

- `select` / `ignore`：**做**，这是 linter 的标配，用户会要。
- `data`（模板变量数据）：**不做**。这会让 linter 变成"模板渲染器"，职责膨胀。用户要验证变量，应该用 docxtpl 自己渲染一遍。
- `allow-cross-paragraph`：**做**，因为 v0.1 已经有 CLI flag，配置文件里对应上是一致性要求。
- 原则：**配置文件只放"检查行为"相关的，不放"渲染行为"相关的。**

**i. --context N —— 做，P1 里性价比最高的一条**

- 这是真正解决用户痛点的功能：报错说"第 3 段有语法错误"，用户还得打开 Word 找。给出上下文直接定位。
- 实现简单（python-docx 读段落文本），风险低。
- **建议默认开启 N=2**，而不是让用户手动加 flag。默认体验好才是增长。

**j. --fix-safe —— 同意不做，但理由要更硬**

- 你的理由（只读承诺、run 拆分）都对，但**最硬的理由是：自动修复会掩盖 bug**。用户跑了 `--fix-safe`，以为修好了，结果模板里还有别的错，最后怪你的工具。
- 如果将来要做，应该是 `--fix-suggest`（输出 diff，不写文件），而不是 `--fix-safe`。

**k. 跨段落开关 —— 已经是 v0.1 功能，v0.2 只需在配置文件里对应上（见 h）**

**l. VS Code 扩展 —— 不做，理由你说对了一半**

- 你说"docx 是二进制看不了"——对，但更根本的问题是：**VS Code 扩展的维护成本极高**（要跟 VS Code API 版本、要发 marketplace、要处理各种 edge case），而你的用户量根本撑不起。
- 如果真要做，应该是"右键 docx → 运行 lint → 在 Problems 面板显示结果"，而不是"在编辑器里看 docx"。但这是 v1.0 之后的事。

---

## 遗漏的高杠杆项

1. **PyPI 正式发布 + 版本号策略**。草案 g 说"准备好但不触发"，这是错的。0 star 项目最需要的是"能被 pip install 到"。v0.2 应该正式发 PyPI，并且想清楚版本号（0.2.0 还是 0.1.1）。

2. **错误信息质量**。你只说了"修误报"，但没说"改错误信息"。v0.1 的错误信息长什么样？有没有给出"文件 → 段落 → 字符位置 → 建议"？这比加新检查项重要得多。**建议 v0.2 把每条 DTL 错误信息都过一遍，确保包含：位置、原因、修复建议。**

3. **退出码语义**。CI 用户最关心的是 `exit 0/1/2` 分别代表什么。有没有 `--strict` 模式？有没有 `--format json`？这些是"能不能进 CI"的关键，比 Playground 重要 100 倍。

4. **一个真实的"用户故事"**。README 现在大概率是"功能列表"。应该改成"我有一个 docxtpl 模板，跑了一下，发现了 X 问题，修好了"。**这是 0 star 项目最缺的东西。**

5. **issue 模板 + CONTRIBUTING**。如果有人提"误报"，你希望他提供什么？模板文件、docxtpl 版本、你的工具版本。没有这个，你收到的 issue 都是"它报错了"。

6. **和 docxtpl 上游的关系**。你有没有在 docxtpl 的 issue/discussion 里提过这个工具？有没有可能被 docxtpl README 链接？**这是 0 star 项目最现实的获客渠道**，比 Playground 有效得多。

---

## 风险

1. **误报是这类工具的头号杀手**。你已经有 7 条误报，说明"猜 docxtpl 语义"这条路很危险。v0.2 的每一条新检查都要问：**有没有真实样本证明用户会犯这个错？** 没有就不加。

2. **基准测试的脆弱性**。官方模板会变，你的 CI 会红。要有 pin 机制和白名单。

3. **Pyodide 的隐藏成本**。如果 c 做了，你会发现 80% 的时间花在"为什么 lxml 在这个版本装不上"，而不是"Playground 好不好用"。

4. **配置文件格式的兼容性**。一旦发了 `[tool.docxtpl-lint]`，改字段名就是 breaking change。v0.2 定字段时要保守，宁可少放几个。

5. **"只读"承诺**。j 不做是对的，但要在 README 里**明确写出来**："本工具只读，不会修改你的文件。" 这是信任基础。

6. **版本号跳跃**。v0.1.0 → v0.2.0 意味着"有 breaking change 或新功能"。如果你只是修 bug + 加配置，其实应该是 v0.1.1。**别为了显得"有进展"而跳版本号**，用户会困惑。

---

## 建议的 v0.2 范围（重排后）

**必做**：
- a（只做智能引号 + 白名单，砍 DTL208）
- b（基准测试，升级为头号任务）
- g（PyPI 正式发布，不是"准备好"）
- h（配置文件，砍掉 data）
- i（--context，默认开启）
- 错误信息质量 + 退出码 + JSON 输出（草案遗漏）
- README 重写（用户故事 + 基准结果 + 已知限制）

**可做**：
- d（GIF，15 秒，一个流程）
- f（确认版本号存在再升）

**不做**：
- c（Playground）
- e（mkdocs）
- j（--fix-safe）
- l（VS Code 扩展）

**v0.3 再考虑**：
- DTL208
- Playground
- mkdocs

一句话：**v0.2 的目标应该是"让第一个真实用户能顺利装上、跑通、看懂报告、提 issue"，而不是"看起来功能很多"。**


## 第 6 轮：我的反驳（提示词）

````
你上一轮评审了 docxtpl-lint 的 v0.2 计划。下面是我核实之后的决定。请用中文逐条回应：同意，或给出能验证的反驳。要简短。
1. DTL208：你建议砍掉。我保留。理由：已用 docxtpl 0.20.2 实测，在普通段落里写 {% cellbg 'FF0000' %} 确实会抛 TemplateSyntaxError（unknown tag）；规则是纯结构判断，基准测试的 40 个模板里误报为 0。
2. Playground：你说 lxml 有几十 MB、链式依赖会踩坑。实测：Pyodide 314.0.7 自带 lxml 6.1.3 的 wheel，只有 2.1 MB；我们不依赖 docxtpl，也不依赖 python-docx，micropip 用 deps=False 安装。Node 冒烟测试 3 秒内跑完，Playwright 里真实浏览器也跑通了，中英文都正常。所以做，并在 CI 里加了 pyodide 冒烟测试。你说的“0 star 时它不能获客”我同意一半：它是给发帖、README 做转化用的，成本只有一个静态 HTML。
3. 你说 checkout@v7 / setup-python@v7 不存在：已用 GitHub API 核实，最新版本分别是 v7.0.1 和 v7.0.0，action.yml 里写的都是 using: node24。你说错了。
4. 关于 PyPI 正式发布：用户要求发布前必须由他确认，所以只准备好工作流，做成 workflow_dispatch 手动触发，不会在发 release 时自动发布。
5. 配置文件：你建议不放 data。我放了。--data 只做存在性检查，不渲染，CLI 本来就有这个选项；配置文件里路径相对 pyproject.toml。遇到未知键直接报错退出（exit 2），这条采纳了你的建议。
6. --context：你建议默认 N=2。我改成在终端里默认 1、非终端（CI 日志、管道）默认 0，避免 CI 日志刷屏。
7. 版本号：你说应该是 0.1.1。新功能有配置文件、--context、DTL208、Playground，按 semver 算 minor，所以是 0.2.0。
8. 退出码、JSON、issue 模板、CONTRIBUTING、只读声明：v0.1 已经都有了（你不知道这些）。新增的是：每条规则的 help_url，以及 docs/rules.md（每条都有错例、修法和 docxtpl 实际行为）。
9. 基准测试：已经做成 scripts/benchmark.py 和 benchmark/expected.json（包含 must_report 和 known_false_positives 白名单），并加进 CI。v0.1.0 在 40 个官方模板上有 7 条误报，v0.2 是 0 条，template_error 那个故意写错的模板仍然能报出。
10. GIF：不用 vhs。README 改为放 Playground 截图，加上可以重新生成的 SVG。mkdocs、VS Code 扩展、--fix-safe 都不做，同意你的意见。
11. 去上游推广：属于对外发言，需要用户确认，已列入待办。
还有什么我漏掉、而且现在就该改的吗？

````

### DeepSeek 回复（原文）

逐条回应：

1. **同意保留 DTL208。** 你的实测（docxtpl 0.20.2 抛 unknown tag）+ 40 模板 0 误报，比我的"结构判断可能误报"猜测更硬。撤回建议。

2. **同意做 Playground。** 2.1 MB wheel + deps=False + 真实浏览器跑通，成本论证成立。我原判断基于"lxml 通常几十 MB"的旧印象，被实测推翻。撤回。

3. **你对，我错。** checkout v7.0.1 / setup-python v7.0.0 存在，node24。我上一轮说"不存在"是错的，道歉。

4. **同意。** workflow_dispatch 手动触发 + 用户确认门禁，正确。

5. **同意放 data。** 只做存在性检查、不渲染、未知键 exit 2，风险可控。撤回"不放 data"。

6. **同意你的方案，比我的好。** isatty 分流（终端 1 / 非终端 0）比统一 N=2 更贴合 CI 场景。

7. **同意 0.2.0。** 配置文件 + --context + DTL208 + Playground 是 feature，minor 正确。我按"修 bug"算 0.1.1 是错的。

8. **收到，无异议。** help_url + docs/rules.md 是合理增量。

9. **同意，且这是最有价值的一条。** 7→0 误报 + 故意错模板仍能报，说明 benchmark 有区分度，不是自证。

10. **同意。**

11. **同意。**

---

**你漏掉、现在就该改的：**

- **DTL208 的 help_url 要指向 docxtpl 版本边界。** 你实测的是 0.20.2。如果用户装 0.19.x，`cellbg` 行为可能不同。docs/rules.md 里应写明"基于 docxtpl ≥0.20.2 实测"，否则规则会随上游漂移而变成误报源。

- **benchmark 的 known_false_positives 白名单要有过期机制。** 白名单是"当前容忍的误报"，不是"永久豁免"。建议每条白名单项带 `expires_version` 或 CI 里断言"白名单条目数不增长"，否则半年后没人敢删。

- **Playground 的 pyodide 版本要 pin。** 你写 314.0.7 自带 lxml 6.1.3。pyodide 升级会换 lxml 版本，DTL 规则若依赖 lxml 解析行为，Playground 结果会和 CLI 漂移。CI 冒烟测试要断言"Playground 对固定模板的输出 == CLI 输出"。

- **配置文件相对 pyproject.toml 解析，但 CLI 直接跑时没有 pyproject.toml。** 需要明确：无 pyproject.toml 时相对 CWD 还是报错？这条现在没定义，会出 bug。

- **--context 非终端默认 0，但 `--context` 显式传 0 和"未传"要能区分。** 用 argparse 的 `default=None` + 运行时判断 isatty，别用 `default=0`，否则用户想强制 0 也做不到。

其余没意见。


### v0.2 委托给 DeepSeek 的任务
- docs/rules.md：DeepSeek 起草，我修了 `{open}` 占位符没替换的问题、DTL204/206/208/301/302 的示例，以及 DTL202 漏掉的 p/r 前缀
- README.zh.md：DeepSeek 重新翻译，我核对了链接和代码块，原样采用


## 第 7 轮：v1.0 创新点候选

````
You are a critical reviewer. Project: docxtpl-lint (static linter for docxtpl / python-docx-template Word templates; Python; lxml walker over body/header/footer/footnotes; rules DTL001-303; JSON/SARIF output; Pyodide playground; benchmark on docxtpl's 40 test templates with 0 false positives). Competitors: lintxtpl (splittist, writes annotated docx of jinja errors), generic jinja2 linters (djlint, j2lint) which don't understand docx XML run-splitting or docxtpl prefixes.
Goal for v1.0: AT LEAST 5 genuinely novel features no competitor has, each must be implementable in ~1 day pure Python, testable against real docxtpl 0.20.2 behaviour, and useful. Candidates:
1. render-equivalence verification: render template with generated sample data via real docxtpl and confirm every {{var}} actually appears in output (detect silently dropped content).
2. schema inference: template -> JSON Schema + sample data (lists from for-loops, nested attrs, numbers from filters).
3. auto-fix suggestions as unified diffs of tag text (e.g. smart quotes, missing endfor, wrong prefix).
4. LSP / editor integration.
5. template diff/regression between two versions (variables added/removed, loops changed -> data contract breaking change).
6. docx visual annotation report (copy of docx with comments/highlights at issue locations).
7. multi-template data contract check: one data JSON against many templates; or template against a JSON Schema.
Critique hard: which are fake-novel, too costly, or unverifiable? Propose a final ranked list of >=5 with concrete scope, CLI flags, and how to test each against real docxtpl. Be concise, max 900 words.

````

### DeepSeek 回复（原文）

# Critique

**1. Render-equivalence — keep, but reframe.** "Every `{{var}}` appears in output" is naive: filters (`|upper`), conditionals, and `{% if %}` legitimately drop content. The *real* novel value is detecting **silently swallowed tags**: docxtpl's `render()` with `autoescape`/`jinja_env` quirks, or tags split across runs that docxtpl *does* rejoin but your linter flags. Verifiable: render with a sentinel-per-variable data dict (`{"v": "SENTINEL_v_42"}`), assert sentinel present. This is genuinely novel — no competitor renders. ~1 day: yes.

**2. Schema inference — keep, highest value.** Nobody does this. `{% for x in items %}{{x.name}}{% endfor %}` → `items: array<{name}>`. Filters imply types (`|round` → number, `|length` → int). Nested `for` → nested arrays. Testable: infer schema from docxtpl's 40 templates, then render each with generated sample data and assert no `UndefinedError`. That round-trip *is* the test. ~1 day for v1 (attrs + loops + basic filters); edge cases (macros, includes) can be `additionalProperties: true`.

**3. Auto-fix diffs — keep, but narrow.** Smart quotes → ASCII, `{{ var }` → `{{ var }}`, `{% endfor %}` missing. Unified diff of *tag text* is fine; don't try to rewrite XML runs. Testable: apply diff, re-lint, assert rule clears. ~1 day. Genuinely useful; lintxtpl only *annotates*, doesn't fix.

**4. LSP — cut for v1.0.** Real LSP is weeks (async, capabilities negotiation, workspace sync). A "diagnostics-only stdio LSP" is ~2 days but low novelty — every linter has one. Defer to v1.1.

**5. Template diff — keep, cheap and novel.** Compare two templates' *variable contracts*: added/removed vars, loop arity changes, filter changes. Output as JSON + human summary. "Breaking change" = removed var or narrowed loop. Testable: mutate a docxtpl template, assert diff catches it. ~0.5 day. No competitor does docx-aware diff.

**6. Visual annotation docx — cut.** lintxtpl already does exactly this. Not novel. Also fiddly (comments API, run splitting) — >1 day.

**7. Multi-template contract check — keep, merge with #2.** `--schema data.schema.json --templates *.docx` → which templates are satisfiable. This is the *product*: schema inference (#2) produces the schema, #7 consumes it. Testable against real docxtpl render. ~1 day combined.

# Final ranked list

**1. Schema inference + sample-data generation** (`docxtpl-lint infer`)
- Scope: walk AST, collect vars/loops/filters, emit JSON Schema (draft 2020-12) + `sample.json`. Loops → arrays with inferred item shape; `|round|int|float` → number; `|length` → integer; `{% if %}` → optional.
- CLI: `docxtpl-lint infer template.docx -o schema.json --sample sample.json`
- Test: for each of docxtpl's 40 templates, `infer` → render with `sample.json` via real `docxtpl.DocxTemplate` → assert exit 0, no `UndefinedError`, no `jinja2.exceptions`. This *is* the benchmark.

**2. Render-equivalence / swallowed-content check** (`docxtpl-lint verify`)
- Scope: sentinel-injection render; flag tags whose sentinel is absent from output *and* not inside a false conditional (detect by rendering with condition forced true via schema-driven data).
- CLI: `docxtpl-lint verify template.docx --data sample.json`
- Test: hand-craft templates with run-split tags, `{% if false %}`, filters; assert correct classification. Cross-check against docxtpl 0.20.2 `render()`.

**3. Data-contract diff** (`docxtpl-lint diff`)
- Scope: two templates → JSON `{added:[], removed:[], changed:[{var, from, to}]}`; `--fail-on breaking` exit code.
- CLI: `docxtpl-lint diff old.docx new.docx --format json`
- Test: git-mutate a docxtpl template (rename var, change loop var), assert diff output. Golden-file tests.

**4. Multi-template / schema conformance** (`docxtpl-lint check`)
- Scope: `--schema` or `--data` against N templates; report per-template satisfiability, missing required vars, type mismatches.
- CLI: `docxtpl-lint check templates/*.docx --schema schema.json`
- Test: reuse #1's inferred schemas; assert self-consistency (infer→check passes). Negative: remove a key, assert failure.

**5. Auto-fix unified diffs** (`docxtpl-lint fix --diff`)
- Scope: DTL001 (smart quotes), DTL002 (unclosed tag), DTL003 (wrong prefix `{{` vs `{`), missing `{% endfor %}`. Emit `--- a/template.docx.xml +++ b/...` on tag text.
- CLI: `docxtpl-lint fix template.docx --diff` (stdout) / `--write`.
- Test: apply diff to extracted XML, re-lint, assert clean. Round-trip on docxtpl fixtures.

**Cut:** LSP (#4, defer), visual annotation (#6, duplicate of lintxtpl).

**Why this set wins:** #1+#4 form a closed loop (infer → check → render) that no competitor can replicate without a docx-aware AST walker. #2 exploits your unique position (you *can* call docxtpl). #3 and #5 are cheap, testable, and absent from lintxtpl/j2lint. All five are pure-Python, ~1 day each, and every one has a concrete test against docxtpl 0.20.2's real renderer — which is your moat.



## 第 8 轮：我的反驳和设计

````
Round 8. My responses to your ranked list; reply AGREE/DISAGREE per point with one-line reason, then any blocking flaw. Max 400 words.
A. Your rule IDs for fixes were wrong: DTL001 = tag never closed, DTL002 = tag spans paragraphs; smart quotes are already normalised (v0.2), not an issue. Fixes I will emit as unified diffs of paragraph text (never rewrite the docx; no --write, docx run-splitting makes that unsafe): DTL202 remove space `{% tr` -> `{%tr`; DTL204 make closing prefix equal opening; DTL203 drop tr/tc prefix outside table; DTL102 delete stray end tag; DTL103 "unknown tag 'endfro'" -> difflib closest Jinja keyword; DTL301 with --data: "did you mean" closest data path. Each validated by rebuilding the docx with the fixed text and rendering with real docxtpl (must render ok).
B. verify: render with sentinel data (each leaf string path gets a unique ASCII token "DTLVnQ", loops get 1 item), read output docx, report DTL401 when an UNCONDITIONAL plain `{{ path }}` sentinel is missing (content silently lost, e.g. {%tr%} loop spanning two tables = DTL205 case), DTL402 when docxtpl raises with the inferred data. Expressions inside if/else are skipped to avoid false positives (no branch forcing in v1). Requires optional extra `docxtpl-lint[render]`; not in Pyodide.
C. infer: JSON Schema 2020-12 + sample; numeric typing only from input filters round/int/float/abs and numeric comparisons; `|length` does NOT imply numeric input. Paths both printed and dereferenced become objects. Multi-template: `infer a.docx b.docx` merges into one contract with `x-docxtpl-templates` per property listing which templates use it. Benchmark: infer+render on docxtpl's 40 templates; templates needing InlineImage/Subdoc/custom filters will be counted and reported, not hidden.
D. check --schema: lint using a schema as the contract: path not in schema -> DTL304, loop over non-array -> DTL303. (merging your #4 into existing --data machinery.)
E. diff old.docx new.docx: added required path = breaking (producers must supply it), removed = non-breaking, type change = breaking; `--fail-on-breaking`.
F. 6th: playground gets an "Infer data schema" button (infer runs in Pyodide, no docxtpl needed). LSP and annotated docx cut as you said.
Version 1.0.0 with subcommands infer/verify/diff/fix plus default lint (backward compatible: `docxtpl-lint file.docx` unchanged).

````

### DeepSeek 回复（原文）

**A. DISAGREE (partially).** Rule IDs are cosmetic; but "smart quotes already normalised" — if true, delete the rule, don't renumber. Unified diffs of paragraph text are the right call; run-splitting makes `--write` genuinely unsafe. DTL103 "closest Jinja keyword" is a weak heuristic — `endfro` → `endfor` is fine, but arbitrary typos will produce confident nonsense; gate on edit distance ≤2.

**B. AGREE with caveat.** Sentinel rendering is the only honest way to detect silent loss. But "unconditional `{{ path }}`" is narrower than you think: `{{ x if y else z }}` is unconditional at top level yet you'll skip it. Document the false-negative surface explicitly or users will trust DTL401 as complete.

**C. AGREE.** `|length` not implying numeric is correct. `x-docxtpl-templates` per-property is the right shape. Benchmark honesty (counting InlineImage/Subdoc/custom-filter templates as unsupported rather than hiding them) is exactly right.

**D. AGREE.** Merging into `--data` machinery avoids a parallel code path. DTL303/304 IDs fine.

**E. AGREE.** Directionality is correct. Add: renamed path (removed+added same type) should be a warning, not two breaking events — otherwise every refactor is "breaking."

**F. AGREE.** Pyodide-only infer button is the right scope. LSP cut is correct — you don't have the bandwidth to do it well.

**Blocking flaw:** B's DTL401 depends on `docxtpl-lint[render]` being installed, but A's fix validation *also* requires real docxtpl rendering. So `fix` silently degrades to "unvalidated diff" without the extra. Either make `[render]` a hard dependency of `fix` (fail loudly if absent) or rename the command to `fix --unvalidated` when the extra is missing. Shipping a fixer that emits diffs it cannot verify is worse than not shipping it — users will apply a diff that renders to a corrupt docx and blame you. Pick one: hard dep, or explicit degraded mode.



## 第 9 轮：代码审查（提示词里附了三个源文件，这里省略）

````
Round 9: final review of the implemented v1.0 (code below). Find real bugs or false-positive risks only, max 400 words, each with file/function and a concrete failing template example. Do not restate features.
Facts verified with docxtpl 0.20.2: verify on docxtpl's 40 test templates: 37 render with inferred data, 0 DTL401 false positives (one early FP on {% cellbg a.bg %} fixed by only checking expr tags). DTL209 cases (text next to {%p if%} and {%tr for%}) confirmed lost in real render. Each fix kind applied+rendered in tests.

````

### DeepSeek 回复（原文）

**1. `verify.py::verify_path` — DTL401 false positive on repeated paths with different sentinels.** `tokens` is keyed by path, so the second occurrence overwrites the first, but `seen` also dedupes outputs by path. If the same path appears in two paragraphs and docxtpl renders only one (e.g. inside a `{%p if%}` block that is false), the surviving token is the *last* one assigned, yet the check looks for `tokens[p]` — which may be the token from the skipped occurrence. Concrete: template with `{{ x }}` in body and `{%p if flag %}{{ x }}{%p endif %}`; `sample` assigns `tokens["x"]` twice (last wins), render emits only the body occurrence, whose text is the *first* token → DTL401 fires on a correct template. Fix: key tokens by `(path, occurrence)` or emit a distinct sentinel per output site.

**2. `contract.py::check_schema` — DTL304 false positive when a guarded ancestor is itself the path.** The skip is `any(path == g or path.startswith(g + ".") for g in an.guarded)`. If `g = "a.b"` and the schema legitimately lacks `a.b` because the template only ever uses it under `{% if a.b %}`, the guard suppresses the check — fine. But the reverse: `g = "a"` and path `a.b` is skipped even though `a` being guarded says nothing about `a.b`'s presence in the schema. Template: `{% if a %}{{ a.b }}{% endif %}` with schema `{properties:{a:{type:"object"}}}` (no `b`) → DTL304 silently missed. That's a false *negative*, not FP; the FP direction is: guarded path `a.b` used *outside* the guard in another paragraph — `an.guarded` is global, so the unguarded use is also skipped. Concrete: `{{ a.b }}` in body plus `{% if a.b %}...{% endif %}` elsewhere → missing `a.b` in schema never reported.

**3. `fixes.py::suggest` DTL301 — `re.sub(rf"\b{re.escape(a)}\b", ...)` can rewrite the wrong segment.** `a` is a bare segment name; `\b` matches inside `[*]`-adjacent text and across `[]`. Template `{{ items[].nmae }}` with known `items[].name`: `a="nmae"`, `b="name"`, `cand` correct. But `{{ user.name }}` vs known `user.names` where `a="name"`, `b="names"`: `\bname\b` also matches the `name` inside `names` if the raw already contained `names` elsewhere — `count=1` picks the first, which may be the wrong occurrence. Low severity but real.

**4. `contract.py::diff` — `parent_present` heuristic misclassifies nested additions.** For `p = "a.b.c"`, `p.rsplit(".",1)[0] = "a.b"`; if `a.b` is new too, `parent_present` is False → `req=False`, so a genuinely required new leaf is reported non-breaking. Template pair: old `{}`, new `{{ a.b.c }}` → `added` with `breaking=False`, but producers must supply it.


### v1.0 委托给 DeepSeek 的任务
- README.zh.md：DeepSeek 翻译，我核对了链接和代码块，并把"演练场"统一改为"在线试用页（Playground）"


## 第 10 轮：对抗用例、UX 评审、评估对比

- 对抗用例的提示词包含 README、rules.md 和 CLI 帮助（约 40 KB，这里省略）。DeepSeek 输出的用例原样保存在 `docs/eval/adversarial_cases.json`；v1.0.0 上的运行结果见 `docs/eval/adversarial_results_v1.0.0.json`（65/86 一致）。
- DeepSeek 写的评估原文见 `docs/eval/deepseek-eval.md`。

### UX 评审（DeepSeek 原文）

# Top 10 UX problems

1. **`--data` help text is a riddle.** "Repeatable: a path is only reported missing if it is missing from every file" — every *file*? You mean every `--data` file. Fix: "Repeatable; a path is reported only if absent from all given contexts."

2. **`diff` output is unreadable and wrong-looking.** `BREAKING + client (renamed from customer?)` then `ok + client.name` — the `+`/`-` glyphs collide with diff semantics, and "renamed from" is a guess presented as fact. Fix: use `~ renamed: customer → client (guess)`, `+ added`, `- removed`, and mark breaking with a `!` column.

3. **GitHub format double-escapes `%`.** `{%25 if %25}` is URL-encoding leaking into a human-readable annotation title. Fix: don't percent-encode in `title`/`message`; only encode the `file=` path.

4. **Text output puts the caret *below* the offending line but the snippet order is confusing.** In the DTL206 block, `¶4` appears after the error line and `¶5` is marked `>` — the reader has to reverse-engineer that `>` = current. Fix: print `¶4`, `¶5 (here)`, `¶6` in order, or prefix with `→`.

5. **`fix` output is a diff against a `.docx`.** Nobody can apply `--- a/foo.docx` with `patch`. Fix: say "suggested edits (not a patchable diff)" or emit a `docxtpl-lint fix --apply` that rewrites the XML.

6. **`infer` JSON is noisy.** `x-docxtpl-templates` is repeated on every node including `items` and `items[*]`. Fix: emit it once at the root as `x-docxtpl-templates: [...]`, or only on leaves that differ.

7. **Playground copy over-promises then hedges.** "Lint a docxtpl Word template in your browser" followed by a footer admitting `--data`, `--schema`, and `verify` are CLI-only. Fix: put the limitation in the drop-zone subtitle, not the footer.

8. **Playground has no error path.** If Pyodide fails to load (offline, CSP, 10 MB timeout), the user sees "Loading Python…" forever. Fix: a timeout with "Couldn't load the linter — [use the CLI]".

9. **README buries the install.** "Not on PyPI yet" is a paragraph; the actual `pip install` is a git URL with a tag. Fix: a one-line `pip install` at the top, and a note that PyPI is pending.

10. **`--context` default is invisible.** "default: 1 in a terminal, 0 otherwise" — a CI user wondering why their logs lack context has to read the help. Fix: print `(context: 0, non-tty)` in the summary line.

# 5 things that are good

1. **Locations are excellent.** `body ¶5 [T1 R2 C2 ¶1]` plus the printed tag text is genuinely better than docxtpl's stack trace.
2. **The "docxtpl does X" column in the rules table** teaches the *why*, not just the rule ID.
3. **`--allow-cross-paragraph` is named after the user's intent**, not the rule (DTL002).
4. **The benchmark table** (false positives 7 → 0) is honest and specific.
5. **`fix` never writes the `.docx`** and says so — the right default for a linter.


### 对比两份评估（提示词）

````
Round 10: we compare your evaluation (deepseek-eval.md) with mine (self-eval.md). I ran experiments with real docxtpl 0.20.2 on disputed verdicts:
E1 nested_loops_nested_tables: your case puts `{%tr for b%}{{ b }}{%tr endfor %}` in ONE row -> docxtpl raises "unknown tag 'endfor'" — DTL206 (tr open/close same row) is the correct diagnosis, not a misdiagnosis. Moving the inner loop to its own rows renders [['p',''],['q','']].
E2 dtl209_tr_row_neighbour: rendering removes the whole row incl. "extra" (output table empty) — silent loss, so a diagnostic IS warranted; your verdict "no diagnostic warranted" contradicts your own rationale. I will extend DTL209 to other cells of a {%tr%} row.
E3 dtl209_tc_cell_neighbour: {%tc if%} in R1, {%tc endif%} in R2 -> output [['y'],['z']]: table shape corrupted, "extra" lost — DTL207 is correct, not spurious.
E4 comment next to {%p%}: renders fine, nothing lost -> DTL209 false positive confirmed; will strip comments.
E5 '}}' inside a string literal: docxtpl renders 'a }} b' -> our DTL103 false positive confirmed; scanner must skip quoted strings.
Also: (a) schema_loop_over_number had --data, not --schema, so DTL303 is right; (b) infer listing parent paths (`items`, `user`) is by design (they are the array/object nodes of the contract); (c) GitHub `%25` is mandated by the workflow-command escaping spec (% -> %25), not a bug; (d) `fix --apply` rejected (docx run splitting).
My bugs: BOM in --data JSON rejected (Windows Notepad); verify/infer/diff traceback on non-docx (exit 1 not 2); a missing `}` swallows following paragraphs and only yields a DTL002 warning, hiding the endfro typo; unclosed {% raw %} not reported; DTL209 noise next to DTL201/203.
Reply: AGREE/DISAGREE per item E1-E5, a-d with one-line reason; then propose a prioritized v1.1 plan (P0/P1/P2, max 12 items) from both evaluations, including which of your UX items to adopt. Max 500 words.

````

### DeepSeek 回复（原文）

**E1 — AGREE.** `{%tr for%}`/`{%tr endfor%}` in one row is genuinely invalid; DTL206 is the right code, my "misdiagnosis" call was wrong.

**E2 — AGREE.** Silent row loss is exactly what a diagnostic is for; my "no diagnostic" verdict contradicted my own rationale. Extending DTL209 to `{%tr%}` neighbours is correct.

**E3 — AGREE.** `{%tc if%}`/`{%tc endif%}` split across rows corrupts shape and drops "extra"; DTL207 is warranted, not spurious.

**E4 — AGREE.** Comments beside `{%p%}` render cleanly; DTL209 there is a false positive. Strip comments before neighbour analysis.

**E5 — AGREE.** `'a }} b'` renders fine; DTL103 must skip quoted string literals. Scanner fix required.

**a — AGREE.** `--data` (not `--schema`) means DTL303 is correct; my flag confusion.

**b — AGREE.** Listing `items`/`user` parent paths is contract-correct (they're the array/object nodes).

**c — AGREE.** `%25` is mandated by GitHub's workflow-command escaping; not a bug.

**d — AGREE.** Rejecting `fix --apply` for run-splitting is the safe call.

---

**v1.1 plan (prioritized)**

**P0 — correctness / data loss**
1. Fix DTL206: detect `{%tr%}` open+close in same row (E1).
2. Extend DTL209 to `{%tr%}`/`{%tc%}` row/cell neighbours; suppress when DTL201/203 already fire (E2, E3, your noise bug).
3. Strip comments before neighbour analysis (E4).
4. Scanner: skip quoted string literals for `}}`/`{%` (E5).
5. Unclosed `{% raw %}` → hard error, not silent (your bug).
6. Missing `}` swallowing paragraphs: escalate DTL002 to error and surface the `endfro` typo (your bug).

**P1 — robustness / UX**
7. BOM-tolerant `--data` JSON parsing (your Windows bug).
8. `verify`/`infer`/`diff` on non-docx → exit 2 with clean message, no traceback (your bug).
9. Adopt my UX item: `--json` output for `verify` (machine-readable diagnostics).
10. Adopt my UX item: `--explain CODE` to print rationale/fix per diagnostic.

**P2 — polish**
11. Adopt my UX item: `--quiet`/`--verbose` verbosity flags.
12. Adopt my UX item: colorized, file:line-prefixed diagnostics (respect `NO_COLOR`).

**Not adopting:** any change to `%25` escaping (c), parent-path listing (b), or `fix --apply` run-splitting (d) — all correct as-is.

Net: your E1–E5 and a–d all stand; my eval had three wrong verdicts (E1, E2, E3) and two flag/UX misreads. v1.1 leads with the six P0 correctness fixes, then robustness, then my UX additions.


说明：它计划里的第 1 条（DTL206）早已实现；第 9 条（verify 的 JSON 输出）和第 12 条（彩色输出）也已经有了，所以这三条不计入 v1.1。
