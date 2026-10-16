# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/yq6666-66/docxtpl-lint/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yq6666-66/docxtpl-lint/releases/tag/v0.1.0
