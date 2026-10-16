# PLAN v1.8 — CI ecosystem

## Scope

- `--format markdown`, `--format gitlab`; SARIF `partialFingerprints`; `--output`, `--report FORMAT:FILE` (D116–D119).
- Action inputs `summary`, `baseline`, `sarif`, `annotate`. CI dogfoods them on the failing examples: the step must fail, the SARIF must carry fingerprints, and the annotated copies are uploaded (D120).
- README: GitLab CI snippet.

## Verification

- tests/test_v18.py: fingerprints survive inserted paragraphs; output and extra reports work.
- The `action` CI job.
