# PLAN v1.5 — a more precise data contract

## Scope (tests/test_v15.py, every claim rendered)

1. List filters → array; with `--data`, DTL306 for a non-list value (D101).
2. Attribute filters → item fields; `sum(attribute=…)` → number (D102).
3. Loops over item-preserving filter chains keep the item scope (D103).
4. `{{r}}` / `{{p}}` → RichText / Subdoc in schema, Pydantic and diff; DTL307 for plain values in `--data` (D104).

## Rejected

- "String" types from string filters (D100).
