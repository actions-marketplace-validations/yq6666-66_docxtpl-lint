# Self-evaluation of docxtpl-lint 1.0.0 (independent of DeepSeek)

Date: 2026-10-16. Everything below can be reproduced:

```sh
python3 -m venv /tmp/fresh
/tmp/fresh/bin/pip install "docxtpl-lint[render] @ git+https://github.com/yq6666-66/docxtpl-lint@v1.0.0" python-docx
/tmp/fresh/bin/python scripts/realworld.py /tmp/rw      # invoice, invoice_v2, 合同 模板.docx, broken, big, data*.json
cd /tmp/rw && docxtpl-lint …                            # commands in self-eval-transcript-v1.0.0.txt
```

Installed from the tag: docxtpl-lint 1.0.0, docxtpl 0.20.2, Jinja2 3.1.6, lxml 6.1.3 (Python 3.13, Linux).

## Templates

| file | content |
|---|---|
| `invoice.docx` | header + footer variables, `{%tr for %}` line items, `'%.2f' % x`, `round`, `{%p if … is defined and … > 0 %}`, `default` |
| `invoice_v2.docx` | same, plus `invoice.po_number` and a `notes` loop (for `diff`) |
| `合同 模板.docx` | Chinese text, a space in the file name, `{%p for %}` clauses with `loop.index`, a nested table with `{%tr for %}` and `{% cellbg %}`, smart quotes outside tags |
| `broken.docx` | `{% tr for` (space), `{{ i.price }` (missing brace), `{%tr endfro %}`, text next to `{%p if %}`, unclosed `if` in the footer |
| `big.docx` | 3000 paragraphs with 6000 tags + a 302-row table (document.xml 332 KB) |

## Results

| check | result |
|---|---|
| lint / `--data` / `--lang zh` / `--format json` on the realistic templates | correct; Chinese file name and text OK |
| `infer` two templates → `--schema` on v1 (clean) and v2 (3 × DTL304) | correct |
| `verify` invoice + Chinese contract | clean, and they really render (header, footer, nested table, cellbg) |
| `diff invoice invoice_v2 --fail-on-breaking` | 2 breaking additions, exit 1 — correct |
| `--format sarif` / `github` | valid; GitHub escapes `%` as `%25` as the workflow-command spec requires |
| performance, big.docx (fresh process each) | lint 0.65 s, infer 0.64 s, fix 0.64 s, verify 1.34 s |
| `PYTHONIOENCODING=ascii`, `LC_ALL=C` | no crash (¶ and Chinese become `?`) |
| Pyodide smoke test (CI job `playground` and locally) | passes |

## Bugs found (1.0.0)

1. **`--data` file with a UTF-8 BOM is rejected** (exit 2: "Unexpected UTF-8 BOM"). That is what Windows Notepad / PowerShell 5 write. `data_bom_crlf.json` reproduces it.
2. **`verify`, `infer`, `diff` crash with a traceback (exit 1) on a non-docx file.** Plain lint handles it (exit 2, one-line message). This breaks the documented exit codes: 2 = unreadable input.
3. **A missing `}` hides the rest of the document.** `{{ i.price }` in `broken.docx` is joined with the next paragraphs until a later `}}`. That produces only a DTL002 *warning*, and the `{%tr endfro %}` typo and the real cause are never reported. The real Jinja would fail. As a result, `fix` offers only 1 suggestion instead of 2.
4. (From the adversarial run, confirmed with docxtpl) **`}}` inside a string literal** (`{{ 'a }} b' }}`) gives a false DTL103, although docxtpl renders it.
5. (Adversarial run) **An unclosed `{% raw %}`** is not reported, although docxtpl raises.
6. (Adversarial run) **DTL209 false positives:**
   - a `{# comment #}` next to a `{%p %}` tag (comments render to nothing);
   - an extra DTL209 next to DTL201/DTL203, where docxtpl raises anyway (noise).
7. (Adversarial run) **DTL209 misses** text in *other cells* of a `{%tr %}` row. docxtpl replaces the whole `<w:tr>`.

## Pros
- Locations with table paths, plus the context lines, make problems findable without Word.
- infer → `--schema` → `diff` works end to end on realistic templates: the data contract workflow is real.
- `verify` rendered the Chinese contract with nested tables and cellbg from inferred data alone.
- Fast enough for CI: 3000 paragraphs in under 1 s, including interpreter start.
- Honest ground truth: every rule case and the benchmark are rendered with the real docxtpl.

## Cons
- The bugs above. #1–#3 hit ordinary users (Windows data files, a typo'd brace).
- `infer` prints `x-docxtpl-templates` on every property even for a single template (noise).
- `diff` text output: `+`/`-` with "BREAKING"/"ok" is readable, but a rename hint is shown only on the added path.
- Windows paths are only covered by the CI matrix (windows-latest, 3.12); not tested by hand here (no Windows machine).

## Re-run after the v1.1 fixes

`self-eval-transcript-v1.1.0.txt` (same templates, current code):
- BOM data → clean, exit 0.
- `broken.docx` → 6 errors, and no more DTL002 warning. The missing `}` is now DTL001, and the `{%tr endfro %}` typo appears as DTL102.
- `fix broken.docx` → 3 suggestions (was 1): `{%tr`, `}}`, `endfor`.
- `verify fake.docx` → one-line message, exit 2.
- Adversarial suite: 86/86 against the adjudicated expectations. Benchmark: still 0 false positives, and verify still renders 37/40.
