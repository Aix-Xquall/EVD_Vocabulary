# Singapore Travel Vocabulary Import Design

## Goal

Add the supplied `新加坡旅遊單字.csv` as a new chapter while preserving the
existing vocabulary schema, removing duplicate display entries, and ensuring
every imported word can be used by the current English cloze practice.

## Source

- Source file: `C:\Users\xqual\Downloads\新加坡旅遊單字.csv`
- Encoding: UTF-8 with BOM
- Source rows: 200
- Columns:
  - `id`
  - `word`
  - `pronunciation`
  - `chinese_meaning`
  - `example_1_en`
  - `example_1_zh`
  - `example_2_en`
  - `example_2_zh`
  - `category`
  - `difficulty`
  - `review_count`
  - `last_review_date`
- Categories:
  - `Food`
  - `Clothing / Shopping`
  - `Hotel / Accommodation`
  - `Transportation / Travel`

The source has no missing required values. All 200 `last_review_date` values
are empty, which is valid for new vocabulary.

## Output

- Create `vocabulary/新加坡旅遊單字.csv`.
- Preserve the existing 12-column schema and UTF-8 BOM.
- Publish it as the independent `新加坡旅遊單字` chapter.
- Produce 196 unique rows with sequential IDs `1` through `196`.
- Preserve `review_count` as `0` and keep `last_review_date` empty.
- Do not modify any existing engineering vocabulary CSV.

## Duplicate Handling

The source contains four duplicate words:

- `luggage`
- `receipt`
- `taxi`
- `towel`

For each duplicate pair:

1. Keep the earlier source row as the base row.
2. Keep its word, pronunciation, meaning, category, difficulty, and first
   English/Chinese example.
3. Replace its second English/Chinese example with the later row's first
   English/Chinese example.
4. Remove the later row.

This retains one representative example from each travel context without
showing the same word twice.

The source word `bus` conflicts with the engineering `bus` entry in
`EMC航電詞彙整合2.csv`. Change the travel entry to:

- word: `public bus`
- meaning: retain the public transportation meaning
- examples: revise both English examples to contain the exact phrase
  `public bus`

After this change, the imported chapter must introduce no normalized-word
duplicates against any formal chapter. The intentionally duplicated hard
words chapter remains outside this check.

## Cloze Compatibility

The current practice requires the exact `word` or phrase to appear in at
least one English example. Apply the following minimum corrections:

- `dumpling`: change one example from plural `dumplings` to singular
  `dumpling`.
- `poncho`: change one example from plural `ponchos` to singular `poncho`.
- `passport`: change one example from plural `passports` to singular
  `passport`.
- `connecting room`: change one example from `connecting rooms` to the exact
  phrase `connecting room`.
- `towel`: the merged earlier row already contains the exact singular
  `towel`; no additional rewrite is required.
- `toothbrush`: change one example from `toothbrushes` to singular
  `toothbrush`.
- `ticket`: change one example from `tickets` to singular `ticket`.
- `elevator / lift`: change the word to `elevator`, retain `lift` as an
  alternate term in the Chinese meaning, and keep an example containing the
  exact word `elevator`.
- `public bus`: both revised examples must contain the exact phrase.

Update each corresponding Chinese translation when an English sentence is
changed. Do not change unrelated source wording.

## Data Flow

The new CSV follows the existing chapter pipeline:

1. `vocabulary_loader.py` discovers the CSV.
2. The chapter builder uses the filename as the chapter title.
3. Google Text-to-Speech generates only missing content-addressed segments.
4. GitHub Actions writes the current JSON and Markdown output.
5. GitHub Pages publishes the updated chapter.

No new runtime dependency, data format, loader API, or web UI component is
required.

## Audio and Quota Impact

The original source contains approximately 18,644 spoken characters across
the word, meaning, and two bilingual examples. The final amount will be close
to this value after deduplication and small sentence corrections.

The workflow must:

- keep the configured Google English and Chinese voices
- synthesize only missing segments
- reuse identical content-addressed segments when available
- retain the current playback speed and repetition behavior

The GitHub Actions run may take longer than a static deployment because this
is a large new chapter.

## LINE Notification

The current push path deploys generated content with `--skip-line`. After the
main deployment succeeds, run the existing `LINE Smoke Test` once to send the
current site summary and link.

Do not alter the LINE message format as part of this import.

## Testing

Add data regression tests that require:

- the new file uses the required schema
- the file starts with a UTF-8 BOM
- there are exactly 196 rows
- IDs are exactly `1` through `196`
- normalized words are unique within the chapter
- the chapter introduces no duplicate against another formal chapter
- `luggage`, `receipt`, `taxi`, and `towel` each appear once
- `public bus` exists and `bus` does not exist in the travel chapter
- `elevator` exists and `elevator / lift` does not exist
- every row has at least one exact cloze-compatible English example
- required fields are populated

Run the complete Python and Node test suites, JavaScript syntax checks, and a
generation smoke test. The smoke test must confirm the published payload has
196 words in the `新加坡旅遊單字` chapter.

## Deployment Verification

After merge:

1. Confirm the push-triggered `Daily Vocabulary` workflow succeeds.
2. Confirm audio generation and Pages deployment succeed.
3. Read the cache-busted public `latest.json`.
4. Confirm the public chapter contains 196 words.
5. Confirm `public bus` and `elevator` are present.
6. Run and verify one `LINE Smoke Test`.

