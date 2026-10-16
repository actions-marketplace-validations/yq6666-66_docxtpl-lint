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
// run the exact Python code embedded in index.html (as a JS template literal, like the browser does)
const html = fs.readFileSync(path.join(site, "index.html"), "utf8");
const m = html.match(/runPythonAsync\(`([\s\S]*?)`\);/);
if (!m) { console.error("index.html: Python block not found"); process.exit(1); }
const pageCode = new Function("wheel", "return `" + m[1] + "`;")(wheel).replace(/^import micropip\n.*\n/m, "");
await py.runPythonAsync(pageCode);
const run = py.globals.get("run");
for (const mode of ["lint", "schema", "sample"]) {
  const r = run("/tmp/s.docx", "issue603_table_loop.docx", "zh", mode);
  if (!r || (mode === "lint" && !r.includes("DTL2")) || (mode !== "lint" && !r.trim().startsWith("{"))) {
    console.error("index.html run() failed for mode " + mode + ":\n" + r);
    process.exit(1);
  }
}
if (!run("/tmp/s.docx", "x.docx", "en", "lint").includes("Suggested fixes")) {
  console.error("index.html run(): no fix suggestions for the #603 example");
  process.exit(1);
}
console.log("pyodide smoke OK: lint output and inferred schema identical to CPython; page code runs in all modes");
