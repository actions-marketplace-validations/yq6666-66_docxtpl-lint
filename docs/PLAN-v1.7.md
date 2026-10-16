# PLAN v1.7 — fix --write

## Scope

- `docxtpl-lint fix a.docx --write a.fixed.docx`; with several templates: `--write DIR` (`<name>.fixed.docx`).
- Edits go inside the existing `<w:t>` runs. Paragraphs with tabs/breaks in the edited span, tracked deletions or field codes are skipped.
- Safe by default; `--unsafe` for intent-guessing fixes; the text diff output marks unsafe ones (D112).
- Passes are repeated until nothing applies, and a pass is kept only if the number of findings drops (D113).

## Verification (tests/test_v17.py)

- A broken invoice (a tag split over runs with a missing brace, a misspelt `endfro`, `{% tr`): after the fixes it lints clean and renders the right rows; the bold run is kept; the original file's bytes are unchanged.
- Unsafe fixes need `--unsafe`. The fixed copy opens in LibreOffice.
