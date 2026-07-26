# ChatGPT tense analysis prompt

Upload `tense_review/pending_tense_examples.csv`, then use this prompt:

```text
Analyze every row in the uploaded CSV and return a downloadable CSV with the
same filename structure and the same row order. Do not change sentence_key,
source_file, source_id, word, example_number, or example_en.

Fill these columns:
- tense_name_zh
- formula
- highlights_json
- confidence

tense_name_zh must be exactly one of:
現在簡單式
現在進行式
現在完成式
現在完成進行式
過去簡單式
過去進行式
過去完成式
過去完成進行式
未來簡單式
未來進行式
未來完成式
未來完成進行式
特殊句型/需確認

Use 特殊句型/需確認 for imperatives, modal-only constructions, fragments,
ambiguous sentences, or sentences that cannot be classified reliably as one
of the 12 tenses.

formula must describe the tense structure, for example:
S + am / is / are + V-ing

highlights_json must be a valid JSON array. Every item must be copied exactly
from example_en and must identify the words that express the tense or special
construction. Example:
["is monitoring"]

confidence must be a number from 0 to 1. Use a lower value when the sentence
is ambiguous. Preserve UTF-8 CSV encoding and return all rows.
```
