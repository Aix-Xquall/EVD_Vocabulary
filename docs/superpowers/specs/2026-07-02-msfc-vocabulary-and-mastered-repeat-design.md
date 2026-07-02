# MSFC Vocabulary and Mastered Repeat Design

## Goal

Merge the newly supplied MSFC vocabulary into the existing chapter without losing prior entries or publishing duplicate words, and change mastered English playback from one repetition to two.

## MSFC Data Merge

- Treat the committed `vocabulary/MSFC-HDBK-3697.csv` as the existing 84-row chapter.
- Treat the current working copy of that file as a 35-row import source.
- Preserve all 84 existing rows.
- Add 34 import rows.
- Exclude `individual` because the normalized word already exists in `EMC航電詞彙整合2.csv`.
- The merged `MSFC-HDBK-3697.csv` must contain 118 rows.
- Preserve the existing 12-column CSV schema and UTF-8 BOM encoding.
- Preserve the existing row order, then append the new rows in their supplied order.
- Preserve all existing IDs so existing content-addressed audio remains reusable.
- Assign IDs 97 through 130 to the 34 appended rows.
- Do not modify existing vocabulary content; only remove the duplicate `individual` import row.
- Continue using case-insensitive, trimmed word comparison for duplicate detection.
- Preserve the 15 pre-existing duplicate groups in other formal CSV files; the existing loader continues to remove them from the published website.
- Do not allow any of the 34 appended MSFC rows to introduce a new cross-chapter duplicate.

## Playback Behavior

- A word with status `mastered` or `mastered_active` uses two English repetitions.
- The English word, English example 1, and English example 2 each use the same two-repetition rule.
- The Chinese meaning and each Chinese example translation continue to play once.
- Non-mastered words continue to use the configurable English repetition count.
- This rule applies to direct word playback and full-chapter playback.
- The existing mastered synchronization statuses and Google Sheet format remain unchanged.

## Components

- `vocabulary/MSFC-HDBK-3697.csv`
  - Contains the merged 118-row chapter.
- `web/learning_helpers.js`
  - Changes `repeatCountForWord` so mastered words return 2 instead of 1.
- `tests/learning_helpers.test.js`
  - Verifies mastered and non-mastered repetition counts.
- `tests/test_vocabulary_data.py`
  - Verifies MSFC row count, preserved existing IDs, appended IDs 97 through 130, required columns, and that appended rows introduce no new cross-chapter duplicates.

## Data Flow

1. Read the committed 84-row MSFC CSV through Git.
2. Read the user's 35-row working-copy CSV as the import source.
3. Build a normalized-word set from all formal vocabulary chapters.
4. Exclude the import row `individual`.
5. Append the remaining 34 rows to the original 84 rows.
6. Preserve the existing IDs, assign IDs 97 through 130 to appended rows, and write the merged CSV using the existing schema.
7. GitHub Actions regenerates chapter payloads and deploys GitHub Pages.

## Error Handling

- Abort the merge if either source does not contain the required 12 columns.
- Abort if the result is not exactly 118 rows.
- Abort if existing IDs change or appended IDs are not 97 through 130.
- Abort if an appended MSFC word duplicates any word in another formal chapter.
- Do not alter the source data if validation fails before the final write.

## Testing and Deployment

- First add failing tests for mastered repeat count and MSFC merged data expectations.
- Implement the smallest playback change and structured CSV merge.
- Run the complete Python and Node test suites.
- Confirm the generated website reports `MSFC-HDBK-3697 (1/118)` when that chapter is selected initially.
- Push `main` and wait for GitHub Actions deployment.
- Keep the current push behavior unchanged: deployment runs with `--skip-line`, so this update does not force a LINE message.

## Compatibility and Risks

- No CSV column, Apps Script, Google Sheet, TTS provider, or browser storage migration is required.
- Existing audio files are reused by content-addressed paths.
- Missing audio is generated only under the project's existing TTS quota rules.
- The main risk is accidentally treating the user's 35-row import as the whole chapter; the 118-row count test prevents that regression.
