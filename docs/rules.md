# Rules

`docxtpl-lint` checks `.docx` templates for constructs that `docxtpl` (python-docx-template) either rejects at render time or silently mishandles. Every finding carries a stable rule id, a severity (`error` or `warning`) and a message that can be rendered in English or Chinese (`--lang zh`). The rule id links to the section below, e.g. `DTL001` → `#dtl001`.

The "docxtpl behaviour" notes were verified by rendering with docxtpl 0.20.2 (see `tests/test_docxtpl_behaviour.py`; CI re-checks them weekly against docxtpl's latest release and master).

Rules can be suppressed for a whole file with a Jinja comment:

```jinja
{# docxtpl-lint: disable=DTL301,DTL002 #}
```

| Rule | Severity | Summary |
| --- | --- | --- |
| [DTL001](#dtl001) | error | tag never closed |
| [DTL002](#dtl002) | warning | tag spans several paragraphs |
| [DTL101](#dtl101) | error | unclosed block |
| [DTL102](#dtl102) | error | stray end/else/elif |
| [DTL103](#dtl103) | error | Jinja2 syntax error |
| [DTL201](#dtl201) | error | `%` or `}` inside a {%p/tr/tc/r %} tag (docxtpl #644) |
| [DTL202](#dtl202) | error | space before tr/tc prefix |
| [DTL203](#dtl203) | error | tr/tc tag outside a table |
| [DTL204](#dtl204) | error | prefix mismatch between opening and closing tag (docxtpl #603) |
| [DTL205](#dtl205) | error | {%tr %} block spans two tables |
| [DTL206](#dtl206) | error | {%tr %} open and close in the same row |
| [DTL207](#dtl207) | error | {%tc %} block must stay inside one row |
| [DTL208](#dtl208) | error | cellbg/colspan/vm/hm tag outside a table cell |
| [DTL301](#dtl301) | error | variable missing from --data |
| [DTL302](#dtl302) | warning | data key never used (--report-unused-data) |
| [DTL303](#dtl303) | error | loop over a non-iterable value from --data |

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
