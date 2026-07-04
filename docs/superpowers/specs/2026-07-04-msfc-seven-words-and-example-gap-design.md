# MSFC Seven Words and Example Gap Design

## Goal

Extend the `MSFC-HDBK-3697` chapter with seven requested vocabulary entries and
add a two-second pause between the complete example 1 playback group and the
start of example 2.

## Scope

- Append these words to `vocabulary/MSFC-HDBK-3697.csv`:
  - `rely on`
  - `accidental`
  - `treated like`
  - `ignition`
  - `intermittent`
  - `specific`
  - `weakens`
- Preserve all existing 118 rows and IDs.
- Assign IDs `131` through `137` in the order listed above.
- Keep the existing CSV schema and UTF-8 BOM encoding.
- Do not change the LINE message format or notification policy.
- Let the existing new-vocabulary workflow send one LINE notification after
  deployment.

## Vocabulary Content

Each new row will contain:

- pronunciation
- Traditional Chinese meaning
- two English examples
- two Traditional Chinese translations
- a relevant engineering category and difficulty
- `review_count` set to `0`
- an empty `last_review_date`

At least one English example for every entry must contain the exact requested
word or phrase so the existing cloze practice can create a valid question.

The local `MSFC-HDBK-3697.pdf` is the primary technical source:

- `ignition` follows the lightning, fuel, pyrotechnics, and Faraday cage
  discussion on PDF page 14.
- `specific` follows the handbook's description of bonding requirements for
  specific hardware on PDF page 3.
- `treated like` is adapted from the handbook's `treated the same as` wording
  for faying surfaces on PDF pages 18 and 56.
- `weakens` is adapted from the lightning-current discussion using
  `weakening the fastener` on PDF page 38.
- `rely on`, `accidental`, and `intermittent` are not directly present in the
  extractable PDF text. Their examples will be original sentences grounded in
  the handbook's bonding paths, fault current, arcing, joint movement, and
  connection reliability context.

Adapted examples must not be described as verbatim PDF quotations.

## Playback Behavior

The current segmented playback order is retained:

1. English example 1
2. Chinese translation 1
3. Repeated English example 1, using the current repeat count and 1.5-second
   repeat delay
4. Wait 2 seconds
5. English example 2
6. Chinese translation 2
7. Repeated English example 2, using the current repeat count and 1.5-second
   repeat delay

The two-second delay applies only before the first segment of example 2. It
does not change:

- the word-to-meaning timing
- English-to-Chinese timing inside an example group
- the existing 1.5-second delay before repeated English
- English playback speed
- Chinese playback speed

The delay is implemented in the browser playback queue, so existing MP3
segments do not need to be regenerated solely to add silence.

## Implementation Approach

Extend `addRepeatedEnglishWithChinese` with a named start-delay argument. Pass
zero for the word and example 1 groups, and `2000` milliseconds for example 2.
The start delay is attached to the first available narration item in the
example 2 group, whether playback uses an MP3 segment or browser speech
fallback.

Use constants with separate meanings:

- existing English repeat delay: `1500` milliseconds
- example-group interval: `2000` milliseconds

## Duplicate Handling

Before adding the rows, compare normalized word values against all formal CSV
chapters. None of the seven requested entries may create a cross-chapter
duplicate. Existing unrelated duplicates are outside this change.

## Testing

Add tests before production changes:

- MSFC chapter contains 125 rows.
- Existing IDs remain unchanged and new IDs are `131` through `137`.
- The seven requested words exist in the expected order.
- Every new entry has a usable cloze example containing the exact target.
- The new rows introduce no cross-chapter duplicate.
- Playback code exposes a separate 2000-millisecond example-group interval.
- Example 2 receives the start delay while example 1 does not.
- Existing 1500-millisecond English repeat delay remains unchanged.

Run the complete Python and Node test suites, JavaScript syntax checks, and a
generation smoke test. Verify the deployed GitHub Pages payload contains 125
MSFC words and the public player contains the updated timing behavior.

## Deployment

Commit and push the CSV, playback code, tests, and documentation to `main`.
The existing GitHub Actions workflow will:

- synthesize only missing audio segments for the seven new entries
- update the published data and static assets
- deploy GitHub Pages
- send the normal LINE notification because new vocabulary was added

