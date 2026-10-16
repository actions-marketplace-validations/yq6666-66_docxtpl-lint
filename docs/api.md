# Python API (stable since 1.9)

```python
from docxtpl_lint import lint, check_context, infer_schema, Result, TemplateLintError
```

| Function | What it does |
|---|---|
| `lint(template, data=None, *, contexts=None, schema=None, jinja_env=None, filters=(), tests=(), autoescape=False, select=None, ignore=())` | Static lint; never runs docxtpl |
| `check_context(template, context, *, jinja_env=None, filters=(), tests=(), autoescape=False, render=True)` | Lint with the context as data, then render it once in memory (DTL402 on failure). `Result.rendered` says whether the render ran |
| `infer_schema(paths, title=...)` | JSON Schema 2020-12 of the data the templates need |
| `effective_autoescape(jinja_env=None, autoescape=False)` | The autoescape docxtpl will really use |

- `template`: a path (`str` is always a path), `bytes`/`bytearray` or a binary file object (read fully into memory, not closed).
- `jinja_env`: its filters/tests are added to `filters`/`tests`; its autoescape counts (a callable is called with `None`, as docxtpl compiles with `from_string`). The env is never modified.
- `Result`: `file`, `issues` (`Issue`: `rule`, `severity`, `message`, `location`), `errors`, `warnings`, `ok` (no errors), `variables` (sorted data paths referenced), `rendered`, `raise_for_errors(fail_on="error"|"warning")`, `to_dict(lang)` (same as one `files[]` entry of `--format json`).
- Thread safety: no global state; safe to call concurrently with distinct inputs.

## Stability policy

Covered by semver: names above, parameter names/defaults, `Result` attributes, `to_dict()` keys, rule ids and severities only change in a major release, after at least one minor release with a `DeprecationWarning` (Python) or stderr notice (CLI). Not covered: message wording, `repr`, other modules (`core`, `verify`, … are internal).
