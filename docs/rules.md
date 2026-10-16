# Rules

`docxtpl-lint` checks `.docx` templates for constructs that `docxtpl` (python-docx-template) either rejects at render time or silently mishandles. Every finding carries a stable rule id, a severity (`error` or `warning`) and a message that can be rendered in English or Chinese (`--lang zh`). The rule id links to the section below, e.g. `DTL001` → `#dtl001`.

The "docxtpl behaviour" notes were verified by rendering with docxtpl 0.20.2 (see `tests/test_docxtpl_behaviour.py`; CI re-checks them weekly against docxtpl's latest release and master).

Rules can be suppressed for a whole file with a Jinja comment:

```jinja
{# docxtpl-lint: disable=DTL301,DTL002 #}
```

or for one paragraph (ids or prefixes such as `DTL2`):

```jinja
{%p if n % 2 == 0 %} {# docxtpl-lint: disable-line=DTL201 #}
{#p docxtpl-lint: disable-next=DTL209 #}
```

`disable-line` covers the paragraph the comment is in; `disable-next` covers the next paragraph of the same part. Write `disable-next` as a `{#p … #}` comment: docxtpl removes that whole paragraph when rendering, while a plain `{# … #}` alone in a paragraph leaves an empty line. A suppression that matches nothing is reported as DTL005.

| Rule | Severity | Summary |
| --- | --- | --- |
| [DTL001](#dtl001) | error | tag never closed |
| [DTL002](#dtl002) | warning | tag spans several paragraphs |
| [DTL003](#dtl003) | error | template code inside a tracked deletion |
| [DTL005](#dtl005) | warning | unused or unknown suppression comment |
| [DTL101](#dtl101) | error | unclosed block |
| [DTL102](#dtl102) | error | stray end/else/elif |
| [DTL103](#dtl103) | error | Jinja2 syntax error |
| [DTL104](#dtl104) | error | unknown Jinja filter |
| [DTL105](#dtl105) | error | unknown Jinja test |
| [DTL106](#dtl106) | error | loop variable used outside its loop |
| [DTL201](#dtl201) | error | `%` or `}` inside a {%p/tr/tc/r %} tag (docxtpl #644) |
| [DTL202](#dtl202) | error | space before tr/tc prefix |
| [DTL203](#dtl203) | error | tr/tc tag outside a table |
| [DTL204](#dtl204) | error | prefix mismatch between opening and closing tag (docxtpl #603) |
| [DTL205](#dtl205) | error | {%tr %} block spans two tables |
| [DTL206](#dtl206) | error | {%tr %} open and close in the same row |
| [DTL207](#dtl207) | error | {%tc %} block must stay inside one row |
| [DTL208](#dtl208) | error | cellbg/colspan/vm/hm tag outside a table cell |
| [DTL209](#dtl209) | error | other content next to a {%p/tr/tc %} tag is silently dropped |
| [DTL210](#dtl210) | error | {%p %} open and close in the same paragraph |
| [DTL301](#dtl301) | error | variable missing from --data |
| [DTL302](#dtl302) | warning | data key never used (--report-unused-data) |
| [DTL303](#dtl303) | error | loop over a non-iterable value from --data |
| [DTL304](#dtl304) | error | variable not declared in --schema |
| [DTL305](#dtl305) | error | loop over a value the --schema declares as non-iterable |
| [DTL306](#dtl306) | error | list filter applied to a non-list value from --data |
| [DTL307](#dtl307) | warning | plain value for a {{r}} / {{p}} tag |
| [DTL308](#dtl308) | error | data value with & or < printed without escaping |
| [DTL401](#dtl401) | error | verify: output silently lost when rendered by docxtpl |
| [DTL402](#dtl402) | error | verify: docxtpl fails to render the template |

<a id="dtl001"></a>
## DTL001 — tag never closed

**What it means.** A `{{`, `{%` or `{#` is opened but its `}}`, `%}` or `#}` never comes, not even in a later paragraph of the same document part (body, header, footer, footnotes).

**Bad**

```jinja
Hello {{ name
```

**Fix**

```jinja
Hello {{ name }}
```

**docxtpl behaviour.** raises `TemplateSyntaxError`.

<a id="dtl002"></a>
## DTL002 — tag spans several paragraphs

**What it means.** A tag opens in one paragraph and only closes in a later paragraph. `docxtpl` merges those paragraphs into one, so the per-paragraph formatting is lost.

**Bad**

```jinja
{{ name
}}
```

**Fix**

```jinja
{{ name }}
```

**docxtpl behaviour.** renders, paragraphs merged (formatting lost); silence with `--allow-cross-paragraph`.

<a id="dtl003"></a>
## DTL003 — template code inside a tracked deletion

**What it means.** The file still has unaccepted tracked changes (Review → Track Changes), and a deletion (`w:del`, or the source side of a move, `w:moveFrom`) contains `{{`, `{%` or `{#`. docxtpl works on the raw XML. Deleted text is still there, so the code inside it is still executed and its rendered output ends up in the revision history of every generated document. A customer can see it with "Show markup".

**Fix.** In Word: Review → Accept (or Reject) → All Changes, then save the template.

**docxtpl behaviour.** `{{ old }}` inside a deletion renders: the generated file contains `<w:delText>` with the value of `old`. A moved `{{ a }}` renders twice (once in `moveFrom`, once in `moveTo`).

<a id="dtl005"></a>
## DTL005 — unused or unknown suppression comment

**What it means.** A `disable-line` / `disable-next` comment names a rule that reports nothing in that paragraph, or a rule id that does not exist. Stale suppressions would hide the next real problem in that paragraph (same idea as ruff's RUF100). Suppressions of data rules (DTL3xx) and verify rules (DTL4xx) are not reported, because those findings depend on `--data`, `--schema` or `verify`.

**Bad**

```jinja
{{ total }} {# docxtpl-lint: disable-line=DTL201 #}
```

**Fix**

```jinja
{{ total }}
```

**docxtpl behaviour.** the comment itself is harmless (docxtpl drops Jinja comments); the warning is about lint hygiene.

<a id="dtl101"></a>
## DTL101 — unclosed block

**What it means.** A block tag such as `{% if %}` or `{% for %}` is never closed: the matching `{% end… %}` is missing.

**Bad**

```jinja
{% if user %}
Hello
```

**Fix**

```jinja
{% if user %}
Hello
{% endif %}
```

**docxtpl behaviour.** raises with no location.

<a id="dtl102"></a>
## DTL102 — stray end/else/elif

**What it means.** A closing or branch tag (`{% end… %}`, `{% else %}`, `{% elif %}`) appears without a matching opening block.

**Bad**

```jinja
Hello
{% endif %}
```

**Fix**

```jinja
{% if user %}
Hello
{% endif %}
```

**docxtpl behaviour.** raises with no location.

<a id="dtl103"></a>
## DTL103 — Jinja2 syntax error

**What it means.** The tag is not valid Jinja2 syntax, so the template cannot be parsed.

**Bad**

```jinja
{{ name | }}
```

**Fix**

```jinja
{{ name }}
```

**docxtpl behaviour.** raises (includes `{% do %}` / `{% break %}`: jinja extensions not enabled by default docxtpl).

<a id="dtl104"></a>
## DTL104 — unknown Jinja filter

**What it means.** The template uses a filter that docxtpl's default `jinja2.Environment()` does not have. Custom filters only work if you pass your own `jinja_env` to `render()`; declare them with `--filters money,date`, `filters = [...]` in `[tool.docxtpl-lint]`, or `--jinja-env myapp.reports:jinja_env` (imports your module).

**Bad**

```jinja
{{ total|money }}
```

**Fix**

```jinja
{{ "%.2f"|format(total) }}
```

**docxtpl behaviour.** raises `TemplateAssertionError: No filter named 'money'` before anything is rendered.

<a id="dtl105"></a>
## DTL105 — unknown Jinja test

**What it means.** `is name` refers to a test that the default environment does not define. Declare custom tests with `--tests`, `tests = [...]` or `--jinja-env`.

**Bad**

```jinja
{% if code is valid_vat %}…{% endif %}
```

**docxtpl behaviour.** raises `TemplateRuntimeError: No test named 'valid_vat' found.` when the expression is evaluated.

<a id="dtl106"></a>
## DTL106 — loop variable used outside its loop

**What it means.** A name that only exists inside a `for` body (the loop variable, `loop`, or a variable assigned with `set` inside the loop) is used after the loop. Jinja does not leak loop scope. Names that are also used as top-level data elsewhere in the template are not reported. To carry a value out of a loop, use `namespace()`.

**Bad**

```jinja
{% for i in items %}{% set last = i %}{% endfor %}Last: {{ last }}
```

**Fix**

```jinja
{% set ns = namespace(last=None) %}{% for i in items %}{% set ns.last = i %}{% endfor %}Last: {{ ns.last }}
```

**docxtpl behaviour.** `{{ last }}` renders empty without an error; `{{ i.n }}` raises `UndefinedError: 'i' is undefined`.

<a id="dtl201"></a>
## DTL201 — `%` or `}` inside a {%p/tr/tc/r %} tag (docxtpl #644)

**What it means.** The expression of a `{%p … %}`, `{%tr … %}`, `{%tc … %}` or `{%r … %}` tag contains `%` or `}}`, which `docxtpl` cannot parse.

**Bad**

```jinja
{%tr if 100 % 3 == 1 %}
```

**Fix**

```jinja
{% set rem = 100 % 3 %}
{%tr if rem == 1 %}
```

**docxtpl behaviour.** raises (issue #644).

<a id="dtl202"></a>
## DTL202 — space before tr/tc prefix

**What it means.** A space between `{%` and the `tr`/`tc`/`p`/`r` prefix: docxtpl only recognises `{%tr`, so `{% tr` reaches Jinja as an unknown tag `tr`.

**Bad**

```jinja
{% tr if user %}
```

**Fix**

```jinja
{%tr if user %}
```

**docxtpl behaviour.** raises 'unknown tag'.

<a id="dtl203"></a>
## DTL203 — tr/tc tag outside a table

**What it means.** A tag uses the `tr` or `tc` prefix but is not inside a table cell, where `docxtpl` expects it.

**Bad**

```jinja
{%tr if user %}
```

**Fix**

```jinja
{% if user %}
```

**docxtpl behaviour.** raises.

<a id="dtl204"></a>
## DTL204 — prefix mismatch between opening and closing tag (docxtpl #603)

**What it means.** An opening tag and its closing tag use different prefixes (e.g. a plain `{% for %}` closed by `{%tr endfor %}`), so `docxtpl` only removes the row or paragraph for one of them.

**Bad**

```jinja
row 1: {% for c in comments %}
row 2: {{ c }}
row 3: {%tr endfor %}
```

**Fix**

```jinja
row 1: {%tr for c in comments %}
row 2: {{ c }}
row 3: {%tr endfor %}
```

**docxtpl behaviour.** renders silently but loses loop rows (#603).

<a id="dtl205"></a>
## DTL205 — {%tr %} block spans two tables

**What it means.** A `{%tr %}` block opens in one table and closes in another. `docxtpl` renders without error but the rows are silently lost.

**Bad**

```jinja
{%tr if user %}
… (table 2) …
{%tr endif %}
```

**Fix**

```jinja
{%tr if user %}
… (same table) …
{%tr endif %}
```

**docxtpl behaviour.** renders silently, rows lost.

<a id="dtl206"></a>
## DTL206 — {%tr %} open and close in the same row

**What it means.** A `{%tr %}` block opens and closes in the same row. `docxtpl` replaces the whole row with the first tag and the template fails.

**Bad**

```jinja
row 2: | {%tr for l in lines %}{{ l.name }} | {{ l.qty }}{%tr endfor %} |
```

**Fix**

```jinja
row 2: | {%tr for l in lines %}           |                |
row 3: | {{ l.name }}                     | {{ l.qty }}    |
row 4: | {%tr endfor %}                   |                |
```

**docxtpl behaviour.** raises.

<a id="dtl207"></a>
## DTL207 — {%tc %} block must stay inside one row

**What it means.** A `{%tc %}` block opens and closes in different rows or tables, which corrupts the generated table.

**Bad**

```jinja
{%tc if user %} … (row 2) … {%tc endif %}
```

**Fix**

```jinja
{%tc if user %} … (same row) … {%tc endif %}
```

**docxtpl behaviour.** renders silently, table corrupt.

<a id="dtl208"></a>
## DTL208 — cellbg/colspan/vm/hm tag outside a table cell

**What it means.** A `{% cellbg %}`, `{% colspan %}`, `{% vm %}` or `{% hm %}` tag is used outside a table cell. `docxtpl` only rewrites these tags inside table cells; elsewhere Jinja sees an unknown tag.

**Bad** (in a normal paragraph)

```jinja
{% cellbg 'FFFF00' %}Total
```

**Fix** (move it into the table cell it should colour)

```jinja
cell: {% cellbg 'FFFF00' %}Total
```

**docxtpl behaviour.** raises 'unknown tag' (cellbg/colspan/vm/hm are only rewritten inside table cells).

<a id="dtl209"></a>
## DTL209 — other content next to a {%p/tr/tc %} tag is silently dropped

**What it means.** docxtpl replaces the *whole* paragraph (`{%p`), table row (`{%tr`) or table cell (`{%tc`) with the bare tag. Any other text or `{{ … }}` in the same paragraph is removed from the output, without an error. Found with `docxtpl-lint verify`, then turned into this static rule. Checked: the tag's own paragraph, the other cells of a `{%tr` row, and the other paragraphs of a `{%tc` cell. Comments (`{# … #}`) and whitespace do not count.

**Bad**

```jinja
Total: {{ total }} {%p if show_details %}
{%p endif %}
```

**Fix**

```jinja
Total: {{ total }}
{%p if show_details %}
{%p endif %}
```

**docxtpl behaviour.** renders without error, but `Total: …` is missing from the output.

<a id="dtl210"></a>
## DTL210 — {%p %} open and close in the same paragraph

**What it means.** `{%p if %}` and `{%p endif %}` (or any `{%p` block) are in the same paragraph. docxtpl replaces the paragraph with the first tag, so the closing tag disappears.

**Bad**

```jinja
{%p if show %}Shown{%p endif %}
```

**Fix** (inline condition, or one paragraph per tag)

```jinja
{% if show %}Shown{% endif %}
```

**docxtpl behaviour.** raises `TemplateSyntaxError: Encountered unknown tag 'endif'`.

<a id="dtl301"></a>
## DTL301 — variable missing from --data

**What it means.** A variable path used by the template is missing from every data file passed with `--data`. Nested fields and loop items are checked (`items[*].price`); paths guarded by `is defined` or `| default(...)` are skipped, and an empty list cannot prove a field missing.

**Bad** (`--data sample.json` with `{"user": {"email": "a@b.c"}}`)

```jinja
{{ user.name }}
```

**Fix**: add `"name"` to the sample data, or guard it in the template:

```jinja
{{ user.name | default('') }}
```

**docxtpl behaviour.** (only with `--data`) missing value renders empty or raises.

<a id="dtl302"></a>
## DTL302 — data key never used (--report-unused-data)

**What it means.** A key in the data file is never referenced by the template. Reported only with `--report-unused-data`, and only for top-level keys.

**Example**: `{"user": {...}, "legacy_id": 7}` with a template that never mentions `legacy_id`. Fix: remove the key from the sample data, or ignore the rule when one data file serves several templates.

**docxtpl behaviour.** (only with `--report-unused-data`) n/a.

<a id="dtl303"></a>
## DTL303 — loop over a non-iterable value from --data

**What it means.** A `{% for %}` loop iterates over a value that is a number, boolean or null in the data file, which cannot be iterated.

**Bad**

```jinja
{% for item in count %}
{{ item }}
{% endfor %}
```

**Fix**

```jinja
{% for item in items %}
{{ item }}
{% endfor %}
```

**docxtpl behaviour.** (only with `--data`) raises at render time (number/boolean/null not iterable; strings are not flagged).

<a id="dtl304"></a>
## DTL304 — variable not declared in --schema

**What it means.** With `--schema contract.json` (for example produced by `docxtpl-lint infer`), a path the template uses is not declared in the schema's `properties` / `items`. Guarded paths (`is defined`, `| default`) are skipped.

**Bad** (schema declares only `customer.name`)

```jinja
{{ customer.adress }}
```

**Fix**

```jinja
{{ customer.address }}   {# and declare it in the schema #}
```

**docxtpl behaviour.** (only with `--schema`) the data producer does not know it must send this value; docxtpl renders an empty string.

<a id="dtl305"></a>
## DTL305 — loop over a value the --schema declares as non-iterable

**What it means.** `{% for … in x %}` but the schema declares `x` as a number, boolean or null.

**Bad** (schema: `"count": {"type": "number"}`)

```jinja
{% for i in count %}{{ i }}{% endfor %}
```

**Fix**

```jinja
{% for i in range(count) %}{{ i }}{% endfor %}
```

**docxtpl behaviour.** (only with `--schema`) raises `TypeError` at render time with data that follows the schema.

<a id="dtl306"></a>
## DTL306 — list filter applied to a non-list value from --data

**What it means.** A filter that needs a list (`join`, `sum`, `sort`, `unique`, `map`, `select`, `reject`, `selectattr`, `rejectattr`, `batch`, `slice`, `groupby`) is applied to a value that is a number, boolean, null or string in `--data`.

**Bad** (`"tags": "urgent"` in the data)

```jinja
{{ tags|join(", ") }}
```

**docxtpl behaviour.** a number raises `TypeError: 'int' object is not iterable`. A string is split into characters (`u, r, g, e, n, t`) without any error.

<a id="dtl307"></a>
## DTL307 — plain value for a {{r}} / {{p}} tag

**What it means.** `{{r x }}` expects a `docxtpl.RichText` and `{{p x }}` a `Subdoc`, but the value of `x` in `--data` is a plain string or number. JSON cannot hold these objects, so this warning tells you that your Python code must build them before rendering. If you meant plain text, use `{{ x }}`.

**docxtpl behaviour.** `A {{r x }} B` with `x = "plain"` renders `A  B`: the value disappears silently. `{{p x }}` with a string removes the paragraph.

<a id="dtl308"></a>
## DTL308 — data value with & or < printed without escaping

**What it means.** A string in `--data` contains `&` or `<` and the template prints it without `|e`. `DocxTemplate.render()` uses `autoescape=False` by default, so the raw character goes into the XML.

**Fix.** Render with `doc.render(context, autoescape=True)` and tell the linter with `--autoescape` (or `autoescape = true` in `[tool.docxtpl-lint]`), or escape the value: `{{ customer.name|e }}`.

**docxtpl behaviour.** `Smith & Co` renders as `Smith  Co`; `<b>bold</b>` cuts off everything after it in the paragraph. No error is raised. `>` and quotes are harmless.

<a id="dtl401"></a>
## DTL401 — verify: output silently lost when rendered by docxtpl

**What it means.** Reported only by `docxtpl-lint verify`. The template is rendered by the real docxtpl with sentinel data (every printed value gets a unique token such as `DTLV3Q`, every list gets one item). An unconditional `{{ path }}` whose token is missing from the rendered document was lost. Outputs inside `if`/`else`, `for … if`, loop `else` and `x if y else z`, filtered outputs, `{{r …}}`/`{{p …}}`, numbers and objects are not checked: a DTL401 is always real, but no DTL401 is not a proof.

**Bad**

```jinja
{%tr for i in items %} {{ i.name }}      (same cell)
```

**Fix**

```jinja
{%tr for i in items %}                   (row of its own)
{{ i.name }}
{%tr endfor %}
```

**docxtpl behaviour.** renders without error; the value is missing from the output.

<a id="dtl402"></a>
## DTL402 — verify: docxtpl fails to render the template

**What it means.** Reported only by `docxtpl-lint verify`: rendering with the inferred sample data (or `--data`) raised an exception. Typical causes: custom filters or functions that must be passed in `jinja_env`/the context, or a value used as a number that the inference could not see.

**Bad**

```jinja
{{ money(total) }}      (money() comes from your Python code)
```

**Fix**

```jinja
pass `--data` with real values, or ignore DTL402 for templates that need Python objects
```

**docxtpl behaviour.** raises at render time.
