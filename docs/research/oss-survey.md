# OSS survey for v1.2 (2026-10-16)

Activity checked with `gh api repos/<r> -q .pushed_at` on 2026-10-16. Per the project rule, projects with no
push for 6+ months are skipped unless the idea is uniquely valuable.

| Project | Last push | Status |
|---|---|---|
| [splittist/lintxtpl](https://github.com/splittist/lintxtpl) | 2026-07-11 | active |
| [djlint/djLint](https://github.com/djlint/djLint) | 2026-10-16 | active |
| [thibaudcolas/curlylint](https://github.com/thibaudcolas/curlylint) | 2024-01-28 | **stale – skipped** (its ideas are covered by djLint) |
| [aristanetworks/j2lint](https://github.com/aristanetworks/j2lint) | 2026-10-16 | active |
| [astral-sh/ruff](https://github.com/astral-sh/ruff) | 2026-10-16 | active |
| [eslint/eslint](https://github.com/eslint/eslint) | 2026-10-16 | active |
| [open-xml-templating/docxtemplater](https://github.com/open-xml-templating/docxtemplater) | 2026-10-15 | active |
| [elapouya/python-docx-template](https://github.com/elapouya/python-docx-template) | 2026-07-07 | active |
| [Sayi/poi-tl](https://github.com/Sayi/poi-tl) | 2026-10-13 | active |
| [carboneio/carbone](https://github.com/carboneio/carbone) | 2026-04-07 | **stale (>6 months) – skipped** |
| [plutext/docx4j](https://github.com/plutext/docx4j) | 2026-10-16 | active |
| [python-jsonschema/jsonschema](https://github.com/python-jsonschema/jsonschema) | 2026-10-12 | active |
| [koxudaxi/datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator) | 2026-10-16 | active |
| [reviewdog/reviewdog](https://github.com/reviewdog/reviewdog) | 2026-10-16 | active |
| [microsoft/sarif-sdk](https://github.com/microsoft/sarif-sdk) | 2026-10-16 | active |
| [pre-commit/pre-commit](https://github.com/pre-commit/pre-commit) | 2026-10-13 | active |
| [mwilliamson/python-mammoth](https://github.com/mwilliamson/python-mammoth) | 2026-09-26 | active |
| [ShayHill/docx2python](https://github.com/ShayHill/docx2python) | 2026-10-12 | active |
| [pyodide/pyodide](https://github.com/pyodide/pyodide) | 2026-10-15 | active |

## Candidate features

Value and cost are each rated L, M or H.

| # | Feature | Source | What docxtpl-lint has today | Value for us | Cost |
|---|---|---|---|---|---|
| F1 | Per-line suppression comments that name a rule (`# noqa: E501`, `{# djlint:off #}`) | ruff [noqa](https://docs.astral.sh/ruff/linter/#error-suppression), djLint [ignoring code](https://www.djlint.com/docs/ignoring-code/) | file-level `{# docxtpl-lint: disable=… #}` only | H: a template author can accept one known case (e.g. a `%` that is fine once docxtpl #645 lands) without turning the rule off for the whole file | L |
| F2 | Unused-suppression report (ruff RUF100) | ruff | – | M: stale suppressions hide new bugs | L |
| F3 | `--statistics` (count per rule) | ruff `--statistics` | – | M: triage of large template folders | L |
| F4 | Baseline / bulk suppressions file with `--prune` (`eslint-suppressions.json`) | ESLint [bulk suppressions](https://eslint.org/docs/latest/use/suppressions) | – | H: adopt in CI on a legacy folder of 100 templates without fixing everything first | M |
| F5 | Fix safety levels (safe / unsafe) | ruff [fix safety](https://docs.astral.sh/ruff/linter/#fix-safety) | `fix` only prints diffs and never writes | L: we never apply fixes, so the label adds little | L |
| F6 | Annotated copy of the .docx with Word comments at each error | lintxtpl | text, SARIF and GitHub annotations | H: the people who edit templates often work only in Word and never read CI logs; this is unique to lintxtpl | M |
| F7 | Pydantic model generation from the inferred schema | datamodel-code-generator | `infer` writes JSON Schema | M–H: typed render data in Python backends; the user can already run `datamodel-codegen` on our schema. Doing it natively removes a dependency and keeps docxtpl-specific names | L–M |
| F8 | Per-template rule disable at the top of the file | j2lint | already done (file-level disable) | – | – |
| F9 | Variable manifest across a batch, noting which template uses each variable | lintxtpl | `--list-vars`, `infer` with `x-docxtpl-templates` | – (already have it) | – |
| F10 | Inspect module / tag listing | docxtemplater [InspectModule](https://docxtemplater.com/docs/api/#inspect-module) | `--list-vars`, `infer` | – | – |
| F11 | Support for other engines' syntaxes (docxtemplater `{#loop}`, poi-tl `{{#table}}`, docx4j content-control bindings) | docxtemplater, poi-tl, docx4j | docxtpl only | L: different engines with different semantics; it would dilute the tool's accuracy, which comes from modelling docxtpl's `patch_xml` | H |
| F12 | reviewdog integration | reviewdog (reads SARIF, rdjson) | SARIF output exists | M: zero code, only a documented recipe (`reviewdog -f=sarif`) | L (docs only) |
| F13 | pre-commit hook | pre-commit | already shipped (`.pre-commit-hooks.yaml`) | – | – |
| F14 | Parse with mammoth / docx2python | mammoth, docx2python | own lxml reader with cell paths | L: we need run/paragraph/cell geometry and docxtpl's exact XML view; these libraries normalise it away | M |
| F15 | Pyodide in-browser playground | Pyodide | playground already on Pages | – | – |
| F16 | Multi-error report instead of first-error | docxtemplater [multi error](https://docxtemplater.com/docs/errors/) | already reports all issues | – | – |

## Decision (after the DeepSeek debate, see docs/decisions.md D74–D86)

| # | Decision |
|---|---|
| F1, F2 | **Adopted**: `disable-line` / `disable-next` + DTL005 |
| F3 | **Adopted**: `--statistics` |
| F4 | **Adopted**: `--baseline` / `--write-baseline`, key = part + cell path + paragraph-text hash, counted |
| F6 | **Adopted**: `--annotate DIR` (copy only; D54 revised) |
| F7 | **Adopted**: `infer --pydantic` (whole tree: our contract only has objects, arrays, numbers, mappings and `Any`) |
| F12 | **Adopted (docs only)**: reviewdog recipe |
| F5, F11, F14 | **Rejected** (see D82–D84) |
| F8, F9, F10, F13, F15, F16 | already present |
| curlylint, Carbone | skipped as stale (>6 months without a push) |
