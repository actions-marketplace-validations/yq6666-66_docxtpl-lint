# PLAN v1.9 — Stable Python API

Goal: a semver-stable, in-process API so applications can guard renders, setting up 2.0's cleanup.

- `docxtpl_lint.api` (D122–D127, D131), docs/api.md with stability policy.
- `--fail-on` + deprecation of `--warnings-as-errors` (D128), the 2.0 removal announced.
- Bugs found while designing (verified by docxtpl render): env mutation (D125), env autoescape ignored / callable autoescape (D126).
- Tests: tests/test_v19.py (15 tests).
