# PLAN v1.6 — escaping and a stronger verify

## Scope (tests/test_v16.py)

1. DTL308 with `--data`; `--autoescape` / `autoescape = true` (D105–D108).
2. verify:
   - RichText / Subdoc sentinels (D109);
   - repeatable `--data`, `--autoescape`, `--jinja-env`, `--out DIR` (D110).

## Rejected

- A static "every output must use |e" rule: it would fire on 23 of the 40 official templates (D107).
