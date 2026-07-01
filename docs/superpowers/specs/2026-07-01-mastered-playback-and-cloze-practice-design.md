# Mastered Playback and Cloze Practice Design

## Goal

Improve the vocabulary player so mastered words remain available for review but receive less repetition, and replace the multiple-choice practice with example-based English cloze questions.

## Scope

This change covers four behaviors:

1. Mastered-word playback frequency.
2. Daily cloze practice.
3. Newly added hard-word ordering.
4. Removal of YouGlish URLs from the displayed pronunciation.

The Google Sheet columns, Apps Script write API, CSV schema, audio files, and existing mastered statuses remain compatible.

## Playback Behavior

- Remove the `略過已熟記` control and all skip-mastered filtering.
- Mastered words remain in chapter playback, previous/next navigation, and daily practice.
- For a mastered word:
  - The English word is played once.
  - English example 1 is played once when examples are enabled.
  - English example 2 is played once when examples are enabled.
  - The Chinese meaning and each Chinese example translation are still played once.
- For a non-mastered word, the existing configurable English repeat count remains unchanged.
- Direct playback and full-chapter playback use the same rule.

## Cloze Practice

- Replace the existing English/Chinese multiple-choice question with a text-entry cloze question.
- Select a word from the current chapter and choose one of its usable examples.
- A usable example must contain the complete target word or phrase, matched case-insensitively.
- Replace the matched target with `_____` in the English example.
- Show:
  - The English sentence with the blank.
  - The corresponding Chinese example as the hint.
  - A text input and a submit button.
- Prefer random selection between usable example 1 and example 2.
- If one example does not contain the target, use the other example.
- If neither example contains the target, exclude that word from the practice question pool.
- Answer comparison trims leading and trailing whitespace and ignores case.
- Internal spelling, spaces, punctuation, and word order must otherwise match exactly.
- Correct and incorrect attempts continue to update the existing practice score.
- An incorrect answer displays the expected word or phrase.
- When the chapter has no usable examples, show `本章節沒有可用的填空例句`.

## Hard-Word Ordering

- When a user adds a word to `未熟記單字練習`, insert it at the beginning of the local chapter list.
- The newly added word therefore appears immediately at the top without waiting for GitHub Actions.
- When loading the cloud snapshot, order active hard words by `added_at` descending.
- Rows without a valid `added_at` retain a stable order after dated rows.
- Existing deduplication by normalized word remains unchanged.

## Pronunciation Display

- Display only the pronunciation portion before the first `|`.
- Example:
  - Stored value: `/ɡælˈvænɪk kəˈroʊʒn/ | https://youglish.com/pronounce/galvanic%20corrosion/english`
  - Displayed value: `/ɡælˈvænɪk kəˈroʊʒn/`
- Keep the CSV value unchanged to preserve data compatibility.
- Markdown generation is outside this UI-only display change.

## Components and Data Flow

- `web/app.js`
  - Calculate the English repeat count per word.
  - Build the cloze question pool and validate typed answers.
  - Insert newly added hard words at the top.
  - Sanitize pronunciation for display.
- `web/index.html`
  - Remove the skip-mastered checkbox.
  - Replace multiple-choice answer controls with a text input and submit button.
- `web/styles.css`
  - Style the cloze input and submit controls using the existing visual system.
- `hard_words_sync.py`
  - Sort active cloud rows by newest `added_at` for snapshot order.

## Error Handling

- Missing examples do not create broken questions.
- Missing or malformed `added_at` values do not fail synchronization.
- Empty answers are treated as incorrect without changing stored vocabulary data.
- Existing Google Sheet and LINE notification behavior is unchanged.

## Testing

- Verify mastered words use one English repetition while other words use the configured count.
- Verify the skip-mastered control and filtering are removed.
- Verify cloze construction for either example and exclusion of unusable words.
- Verify answer normalization trims outer whitespace and ignores case.
- Verify newly added hard words are inserted first.
- Verify cloud hard-word rows sort by descending `added_at`.
- Verify pronunciation display removes the YouGlish suffix.
- Run the complete Python test suite and JavaScript syntax check before deployment.

## Compatibility and Risks

- No dependency is added.
- No CSV column or Apps Script deployment change is required.
- The main risk is an example containing a grammatical variation rather than the exact target phrase. Such examples are excluded because accepting variations would require stemming or language-specific matching outside this scope.
