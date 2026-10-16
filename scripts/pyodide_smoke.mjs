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
console.log("pyodide smoke OK: output identical to CPython");
