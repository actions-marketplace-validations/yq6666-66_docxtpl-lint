> Written by DeepSeek (deepseek-chat) on 2026-10-16 from the adversarial results in `adversarial_results_v1.0.0.json` and its own UX review; kept verbatim. Disputed verdicts are discussed in `docs/decisions.md` (D58+).

# docxtpl-lint 1.0.0 — Adversarial Evaluation

## Method

I designed 86 test cases targeting docxtpl-lint 1.0.0's rule set (DTL0xx/1xx/2xx/3xx), its `infer` command, and its CLI surface. The maintainer built each case as a real `.docx` and ran both the linter and real docxtpl 0.20.2 against it. docxtpl's behaviour (raises / ok) is the ground truth column; where the linter and docxtpl disagree, I judged whether the tool or my expectation was wrong using that column, not my prior.

Caveat: cases requiring CLI flags (`--schema`, `--report-unused-data`, `--allow-cross-paragraph`) were run **without** those flags by the harness. For those cases the "actual" column reflects default behaviour, so a missing diagnostic is not necessarily a tool bug — it may be a harness gap. I flag this per row.

## Results

**65 / 86 cases matched.** 21 DIFFs:

| Case | Expected | Actual | docxtpl | Verdict |
|---|---|---|---|---|
| raw_block_unclosed | DTL101 | — | raises | **Tool wrong** — unclosed raw is an unclosed block. |
| nested_loops_nested_tables | — | DTL206 | raises (unknown `endfor`) | **Both wrong** — my case is malformed; tool's DTL206 is a misdiagnosis. |
| filter_with_percent_in_p_tag | DTL201 | DTL201, DTL209 | raises | **Tool wrong** — spurious DTL209. |
| string_literal_with_close_brace | — | DTL103 | ok | **Tool wrong** — `}}` in a string literal is legal. |
| smart_quotes_in_tag | DTL103 | — | ok | **My expectation wrong** — docxtpl accepts it. |
| dtl209_whitespace_only_neighbour_nbsp | DTL209 | — | ok | **My expectation wrong** — NBSP is content, not whitespace. |
| tr_tag_outside_table | DTL203 | DTL203, DTL209 | raises | **Tool wrong** — spurious DTL209. |
| infer_nested_loop_paths | items[].name, items[].price | + items | ok | **Tool wrong** — bare `items` is noise. |
| schema_missing_var | DTL304 | — | ok | **Harness gap** — needs `--schema`. |
| schema_loop_over_number | DTL305 | DTL303 | raises (TypeError) | **Tool wrong** — should be DTL305, not DTL303. |
| unused_data_key | DTL302 | — | ok | **Harness gap** — needs `--report-unused-data`. |
| cross_paragraph_allowed | — | DTL002 | ok | **Harness gap** — needs `--allow-cross-paragraph`. |
| header_with_table | DTL203 | DTL203, DTL209 | raises | **Tool wrong** — spurious DTL209. |
| infer_optional_field | user.name | + user | raises | **Tool wrong** — `default()` should suppress the bare parent. |
| infer_defined_guard | user.email | + user | raises | **Tool wrong** — same. |
| dtl209_tr_row_neighbour | DTL209 | — | ok | **My expectation wrong** — docxtpl drops the text silently; no diagnostic warranted. |
| dtl209_tc_cell_neighbour | DTL209 | DTL207, DTL209 | ok | **Tool wrong** — DTL207 is spurious. |
| dtl209_p_tag_with_nbsp | DTL209 | — | ok | **My expectation wrong** — NBSP is content. |
| dtl209_p_tag_with_comment | — | DTL209 | ok | **Tool wrong** — comments render to nothing. |
| dtl209_p_tag_with_whitespace_comment | — | DTL209 | ok | **Tool wrong** — same. |
| dtl209_p_tag_with_whitespace_and_comment_and_whitespace | — | DTL209 | ok | **Tool wrong** — same. |

Pattern: DTL209 is the dominant false-positive source (7 rows), and `infer` over-reports bare parents (3 rows). Two rows were my error; three are harness gaps.

## UX review summary

Locations (`body ¶5 [T1 R2 C2 ¶1]`) and the "docxtpl does X" column are genuinely better than a stack trace. But: `--data` help is a riddle; `diff` glyphs collide with diff semantics and "renamed from" is a guess stated as fact; GitHub format percent-encodes `%` in titles; `fix` prints a non-patchable diff against a `.docx`; `infer` JSON repeats `x-docxtpl-templates` on every node; the playground over-promises then hedges in the footer and has no Pyodide failure path; README buries install; `--context` default is invisible in output.

## Pros

- Precise, structured locations.
- Rule table teaches the *why*.
- `--allow-cross-paragraph` named after intent.
- `fix` never writes the `.docx`.
- Honest benchmark (7 → 0 false positives).

## Cons

- DTL209 false positives on comments and NBSP.
- `infer` emits bare parent paths.
- DTL303/DTL305 conflation.
- DTL103 misses `}}`-in-string; DTL101 misses unclosed raw.
- CLI help and `diff`/`fix` output need rework.
