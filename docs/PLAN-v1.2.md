# PLAN v1.2 — ideas from other open-source projects

Input: [research/oss-survey.md](research/oss-survey.md). Decisions: [decisions.md](decisions.md) D74–D86.

## Scope

1. Paragraph suppressions `disable-line` / `disable-next` + DTL005 (ruff noqa, RUF100; djLint).
2. Baseline `--write-baseline` / `--baseline` / `baseline =` in pyproject (ESLint bulk suppressions).
3. `--statistics` (ruff).
4. `--annotate DIR`: copies with Word comments (lintxtpl).
5. `infer --pydantic` (datamodel-code-generator).
6. reviewdog recipe in README.
7. Fixes: zh location in DTL204, zh unit in DTL209; `author` in action.yml.

Out of scope: fix safety levels, other template engines, other docx parsers (D82–D84).

## Verification

- tests/test_v12.py, with real docxtpl renders:
  - a `{#p … #}` directive paragraph disappears from the output;
  - Pydantic-validated sample data renders.
- Annotated copy: python-docx reads the same text; LibreOffice converts it and keeps the comments.
- Unchanged:
  - 40 official docxtpl templates: 0 false positives;
  - 86/86 adversarial cases;
  - full test-suite green, ruff clean.

## Release (needs the user's confirmation)

1. `git push origin main && git push origin v1.2.0`
2. `gh release create v1.2.0` with the CHANGELOG section and the built wheel/sdist.
3. `gh workflow run publish-pypi.yml -f tag=v1.2.0`
4. Marketplace: the release form offers to update the listing (v1.2.0 carries `author`).
