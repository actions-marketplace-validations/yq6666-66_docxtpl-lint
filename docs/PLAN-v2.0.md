# PLAN v2.0: consistency, deprecation cleanup

The only behavioural break is D133 (verify honours the project config), backed by a reproduced false DTL402. The rest are announced removals, deprecations and additive fields.

- D133–D135: verify = lint's parser + render; config except `data`.
- D136–D139: removals, deprecations, fingerprints, diff --fail-on.
- docs/MIGRATION-2.0.md; docs/api.md updated.
- Tests: tests/test_v20.py (11).
