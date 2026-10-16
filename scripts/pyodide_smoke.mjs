// Smoke test: run the built wheel inside Pyodide (Node), exactly like the playground.
// usage: npm i pyodide && node scripts/pyodide_smoke.mjs _site
import { loadPyodide } from "pyodide";
import fs from "fs";
import path from "path";

const site = process.argv[2] || "_site";
const { wheel } = JSON.parse(fs.readFileSync(path.join(site, "wheel.json")));
const py = await loadPyodide();
await py.loadPackage(["micropip", "lxml", "jinja2"]);
py.FS.writeFile("/tmp/" + wheel, fs.readFileSync(path.join(site, wheel)));
py.FS.writeFile("/tmp/t.docx", fs.readFileSync(path.join(site, "examples", "issue378_unclosed.docx")));
const text = await py.runPythonAsync(`
import micropip
await micropip.install("emfs:/tmp/${wheel}", deps=False)
from docxtpl_lint import lint_path
from docxtpl_lint.cli import render_text
rep = lint_path("/tmp/t.docx")
rep.file = "issue378_unclosed.docx"
render_text([rep], context=1)
`);
const expected = fs.readFileSync(path.join(site, "expected.txt"), "utf8");
if (text !== expected) {
  console.error("Pyodide output differs from CPython:\n--- pyodide\n" + text + "\n--- cpython\n" + expected);
  process.exit(1);
}
py.FS.writeFile("/tmp/s.docx", fs.readFileSync(path.join(site, "examples", "issue603_table_loop.docx")));
const schema = await py.runPythonAsync(`
import json
from docxtpl_lint.contract import infer_tree, to_schema
s = to_schema(infer_tree(["/tmp/s.docx"]))
json.dumps(s, indent=2).replace('"s.docx"', '"issue603_table_loop.docx"')
`);
const expSchema = fs.readFileSync(path.join(site, "expected_schema.json"), "utf8");
if (schema !== expSchema) {
  console.error("Pyodide schema differs from CPython:\n" + schema + "\n---\n" + expSchema);
  process.exit(1);
}
console.log("pyodide smoke OK: lint output and inferred schema identical to CPython");
