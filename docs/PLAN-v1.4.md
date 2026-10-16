# PLAN v1.4 — tracked changes and field codes

## Experiments (tests/test_v14.py)

| Construct | docxtpl 0.20.2 | Linter before 1.4 |
|---|---|---|
| `{{ <del>nmae</del><ins>name</ins> }}` | renders `name` | correct |
| `{{ old }}` inside a deletion | rendered into `<w:delText>` (leak) | not seen |
| `{{ a }}` moved (moveFrom/moveTo) | rendered twice | not seen |
| `HYPERLINK "{{ url }}"` (instrText / fldSimple) | rendered | not seen: no variable, no syntax check |
| broken tag in a field code | render fails | "clean" |
| content controls, `w:ins` | fine | fine |

## Scope

- Paragraphs with deletions, field codes or moves: read the text through docxtpl's own patch_xml regexes (D95).
- DTL003 (error): template code inside a tracked deletion.
- Weekly upstream job also runs test_v13/test_v14 (D98).
