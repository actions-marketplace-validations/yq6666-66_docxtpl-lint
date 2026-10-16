#!/usr/bin/env bash
# Build the GitHub Pages playground into _site/ (needs a built wheel in dist/).
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf _site && mkdir -p _site/examples
cp site/index.html _site/
cp examples/*.docx _site/examples/
wheel=$(ls dist/docxtpl_lint-*-py3-none-any.whl | sort -V | tail -1)
cp "$wheel" _site/
printf '{"wheel": "%s"}\n' "$(basename "$wheel")" > _site/wheel.json
# CPython reference output; the Pyodide smoke test must produce exactly the same text
python - <<'PY'
from pathlib import Path
from docxtpl_lint.core import lint_path
from docxtpl_lint.cli import render_text
rep = lint_path("_site/examples/issue378_unclosed.docx")
rep.file = "issue378_unclosed.docx"
Path("_site/expected.txt").write_text(render_text([rep], context=1), encoding="utf-8")
import json
from docxtpl_lint.contract import infer_tree, to_schema
schema = to_schema(infer_tree(["_site/examples/issue603_table_loop.docx"]))
Path("_site/expected_schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
PY
echo "built _site/ with $(basename "$wheel")"
