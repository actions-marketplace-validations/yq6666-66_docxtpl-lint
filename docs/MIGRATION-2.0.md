# Migrating from 1.x to 2.0

Most projects need no change. Check these four points.

| If you… | 1.x | 2.0 | Do this |
|---|---|---|---|
| pass `--warnings-as-errors` or set `warnings-as-errors = true` | exit 1 on warnings | exit 2 with a message | `--fail-on warning` / `fail-on = "warning"` (available since 1.9) |
| run `verify` in a project with `[tool.docxtpl-lint]` | config ignored | `jinja-env`, `autoescape`, `select`, `ignore`, `fail-on`, `baseline`, `lang` apply (`data` does not, so DTL401 still runs) | Usually nothing: false DTL402 from custom filters disappear. To get 1.x behaviour: `verify --no-config` |
| call `docxtpl_lint.lint_path(...)` | returns a `Report` | still works, with a `DeprecationWarning`; removed in 3.0 | `docxtpl_lint.lint(path, data)` returns a `Result` (`.issues`, `.ok`, `.raise_for_errors()`); also accepts bytes and file objects |
| use `diff --fail-on-breaking` | exit 1 on breaking change | still works, with a notice; removed in 3.0 | `diff --fail-on breaking` (or `change`) |

## Exit codes (lint and verify)

| Code | Meaning |
|---|---|
| 0 | no finding at the `--fail-on` level (default `error`; `never` = findings never fail) |
| 1 | at least one finding at that level |
| 2 | usage error, unreadable input, bad config, or a removed option |

## Additive changes (no action needed)

- Each JSON issue and `Result.to_dict()` issue has a `fingerprint` (the same id as SARIF `partialFingerprints["docxtplLint/v1"]` and the GitLab `fingerprint`). `schema_version` stays 1. A strict validator that forbids unknown keys must allow it.
- `verify` accepts `--format github|sarif|gitlab|markdown`, `--output`, `--report`, `--select`, `--ignore`, `--fail-on`, `--baseline`, `--write-baseline`, `--annotate`.
