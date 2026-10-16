# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.1.0] - 2026-10-16

Found by an adversarial run (86 cases designed by DeepSeek, disputes settled by rendering with docxtpl) and a
self-evaluation from a fresh install (docs/eval/).

### Added
- DTL210: `{%p %}` block opened and closed in the same paragraph (docxtpl raises).
- `--explain RULE`.
- `fix` suggests the missing `}` of a `{{ … }` tag.
- `scripts/adversarial.py` + `benchmark/adversarial_adjudicated.json`: the 86 cases run in the test-suite.
- `scripts/realworld.py`: invoice / Chinese contract / broken / 3000-paragraph templates used by the self-evaluation.

### Fixed
- `}}` or `%}` inside a string literal no longer ends the tag (false DTL103).
- A tag missing its closing brace no longer swallows the following paragraphs (it was only a DTL002 warning and
  hid later errors); it is reported as DTL001 and scanning continues at the next tag.
- Unclosed `{% raw %}` is reported (DTL101).
- DTL209: comments are not counted as lost text; text in other cells of a `{%tr %}` row and in other paragraphs of a
  `{%tc %}` cell is now checked; no DTL209 next to DTL201/202/203 or a same-paragraph `{%p %}` pair.
- `--data` / `--schema` JSON with a UTF-8 BOM (Windows Notepad) is accepted.
- `infer` / `verify` / `diff` / `fix` exit with code 2 and a one-line message on unreadable input instead of a traceback.
- Playground: the 1.0.0 page failed to load (escaped newlines in the embedded Python); the Pyodide smoke test now runs
  the page's own code. A hint appears if loading takes over 30 s.
- `fix` diff headers: no `a//tmp/...` double slash.

### Changed
- `infer` writes `x-docxtpl-templates` only when several templates are merged.
- Clearer `--data` help text.

## [1.0.0] - 2026-10-16

### Added
- `docxtpl-lint infer`: data contract of one or more templates as JSON Schema (2020-12) plus sample data; lists from
  `for` loops, numbers from `round`/`int`/`float`/`abs`, arithmetic and numeric comparisons, objects from `.items()`,
  optional fields from `is defined`/`default`; merged schemas list the templates using each field
  (`x-docxtpl-templates`).
- `docxtpl-lint verify` (optional extra `[render]`): render with the real docxtpl and sentinel data; DTL401 = rendered
  value silently missing from the output, DTL402 = render fails.
- `docxtpl-lint diff old.docx new.docx [--fail-on-breaking]`: data contract changes between template versions,
  with rename hints.
- `--schema schema.json`: DTL304 (variable not declared), DTL305 (loop over a non-iterable type).
- `docxtpl-lint fix`: fix suggestions as unified diffs of the paragraph text for DTL202, DTL203, DTL204, DTL102 (stray tag
  or misspelt opening tag), DTL103 (unknown tag) and DTL301 (with `--data`); conservative matching (≤ 2 edits, no ties).
- DTL209: text next to a `{%p %}`/`{%tr %}`/`{%tc %}` tag is silently dropped by docxtpl (found with `verify`).
- Playground: fix suggestions, inferred JSON Schema and sample data.
- Benchmark runs `verify` on docxtpl's 40 templates (37 render with inferred data, 0 false DTL401).

### Changed
- Pages deploy runs on pushes to `main` (the `release` trigger ran on the tag ref, which the `github-pages` environment
  rejects).
- Development status: Production/Stable.

## [0.2.0] - 2026-10-16

### Added
- Browser playground (Pyodide, runs fully client-side), deployed to GitHub Pages by `pages.yml`.
- `[tool.docxtpl-lint]` configuration in `pyproject.toml` (`--config`, `--no-config`); unknown keys are errors.
- `--context N`: show neighbouring paragraphs next to each issue (default 1 on a terminal, 0 otherwise).
- DTL208: `cellbg`/`colspan`/`vm`/`hm` tag outside a table cell.
- `docs/rules.md` with one anchor per rule; `help_url` in JSON output and `helpUri` in SARIF.
- Benchmark against docxtpl's own 40 test templates (`scripts/benchmark.py`, CI job); stale allow-list entries fail it.
- Manual-only PyPI Trusted Publishing workflow (`publish-pypi.yml`).

### Fixed
- False positives on docxtpl cell tags (`{% cellbg %}`, `{% colspan %}`, `{% vm %}`, `{% hm %}`) and on Word smart quotes inside tags: 7 → 0 on the benchmark.

### Changed
- GitHub Actions updated to Node 24 versions (`checkout@v7`, `setup-python@v7`, ...); the composite action uses `setup-python@v7`.
- New dependency on Python < 3.11: `tomli`.

## [0.1.0] - 2026-10-16

### Added
- First release.
- Locations down to the table cell (`T1 R2 C2 > T2 R2 C1`, nested tables) for body, headers, footers and footnotes.
- Tag and block rules: DTL001 (tag never closed), DTL002 (tag spans paragraphs, warning), DTL101 (unclosed block),
  DTL102 (stray end/else), DTL103 (other Jinja2 syntax errors, using docxtpl's default environment).
- docxtpl tag rules: DTL201 (`%`/`}` in prefixed tags, #644), DTL202 (space before prefix), DTL203 (tr/tc outside
  a table), DTL204 (prefix mismatch, #603), DTL205 (tr block spans tables), DTL206 (tr open/close in the same row),
  DTL207 (tc block spans rows).
- Data rules with `--data` (repeatable): DTL301 (missing path, nested and loop-aware, respects `is defined` /
  `| default`), DTL302 (unused key, with `--report-unused-data`), DTL303 (loop over a non-iterable).
- `--format text|json|github|sarif`, `--lang en|zh`, `--select`, `--ignore`, `--warnings-as-errors`, `--list-vars`,
  `--list-rules`, `--allow-cross-paragraph`; exit codes 0/1/2.
- File-level suppression comment `{# docxtpl-lint: disable=… #}`.
- GitHub Action, pre-commit hook, and test cases checked against real docxtpl 0.20.2 rendering.

[Unreleased]: https://github.com/yq6666-66/docxtpl-lint/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/yq6666-66/docxtpl-lint/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/yq6666-66/docxtpl-lint/compare/v0.2.0...v1.0.0
[0.2.0]: https://github.com/yq6666-66/docxtpl-lint/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/yq6666-66/docxtpl-lint/releases/tag/v0.1.0
