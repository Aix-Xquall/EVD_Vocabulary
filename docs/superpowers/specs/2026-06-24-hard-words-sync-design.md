# Hard Words Sync And Abbreviation Expansion Design

## Goal

Add two related improvements to the EVD Vocabulary project:

1. Expand engineering abbreviations in English-facing fields as `Full Term (ABBR)`.
2. Add a cross-platform "hard words" feature so the learner can mark difficult words from phone, PC, or another device and practice them as a separate chapter.

The design keeps the existing GitHub Pages + GitHub Actions publishing model. Google Sheets and Google Apps Script provide the cloud write path for hard words, avoiding GitHub tokens in the public web page.

## Abbreviation Rules

English-facing fields should expand abbreviations using one centralized mapping:

- `EMS` -> `Electromagnetic Susceptibility (EMS)`
- `EMC` -> `Electromagnetic Compatibility (EMC)`
- `E3` -> `Electromagnetic Environmental Effects (E3)`
- `EPDS` -> `Electronic Power Distribution System (EPDS)`
- `MIL-STD-461` -> `Military Standard 461 (MIL-STD-461)`

The expansion applies only to English fields:

- `word`
- `example_1_en`
- `example_2_en`

Chinese fields remain unchanged:

- `chinese_meaning`
- `example_1_zh`
- `example_2_zh`

This keeps Chinese text readable and lets Chinese TTS pronounce abbreviations such as `EMS` and `EMC` as abbreviations instead of reading the full English phrase.

For English speech, the TTS input should use the full term without the parenthesized abbreviation where possible. For example, `Electromagnetic Susceptibility (EMS)` is spoken as `Electromagnetic Susceptibility`. This avoids awkward repeated acronym reading in English audio.

## Hard Words Data Model

The project will add a CSV-compatible hard words record format. It should stay compatible with the existing vocabulary CSV schema so hard words can be loaded as another chapter without a separate display model.

Required vocabulary-compatible columns:

```csv
id,word,pronunciation,chinese_meaning,example_1_en,example_1_zh,example_2_en,example_2_zh,category,difficulty,review_count,last_review_date
```

Additional tracking fields may exist in Google Sheets and should be ignored by the normal vocabulary loader unless explicitly needed:

```csv
source_chapter,source_id,added_at,status,note
```

Only rows with `status` empty or `active` are included in the generated hard words chapter. Rows with `removed` are kept for history but not shown.

The canonical local file will be:

```text
vocabulary/hard_words.csv
```

The public chapter title will be the Traditional Chinese label requested by the user: "hard to remember words". This avoids a non-ASCII filename while still showing the expected Chinese UI label.

This file acts as a repo-backed snapshot and fallback. The daily workflow may refresh it from Google Sheets before building the site.

## Cloud Sync Architecture

The web page remains a static GitHub Pages site. It does not store a GitHub token and does not directly write to the repo.

The write flow is:

1. User opens the GitHub Pages vocabulary page on any device.
2. User taps the hard-word action button on a word.
3. The page sends the selected word payload to a Google Apps Script Web App.
4. Apps Script validates a simple passcode and appends or updates the row in Google Sheets.
5. Google Sheets becomes the cross-device source of truth for hard words.
6. GitHub Actions reads the Google Sheet CSV export during the daily build.
7. The build writes or refreshes `vocabulary/hard_words.csv`.
8. The generated `latest.json` includes a top-level hard words chapter.

This is like a shared cloud notebook: each device writes to the same notebook, and the daily published site reads from that notebook.

## Web UI

The top chapter selector will include a hard words chapter when hard words exist.

Each normal word view gets a small action button to add the current word to the hard words list.

Recommended behavior:

- If the current word is already in the hard words list, show an already-added state.
- Avoid duplicate writes by checking the current generated hard words chapter and local pending state before sending.
- If the device has no saved passcode, prompt for it once and store it in localStorage.
- If Apps Script returns an error, show a short failure message and keep playback usable.
- Do not block audio practice if hard-word sync fails.

The hard words chapter should use the same playback controls, repeat settings, Wake Lock, Media Session, and practice quiz behavior as other chapters.

## GitHub Actions Integration

The workflow will add optional environment variables or repository secrets:

- `HARD_WORDS_SHEET_CSV_URL`: CSV export or Apps Script read URL for active hard words.
- `HARD_WORDS_READ_TOKEN`: optional token if the read endpoint is protected.

If `HARD_WORDS_SHEET_CSV_URL` is missing, the build continues using the local `vocabulary/hard_words.csv` if present. If neither exists, the build continues without the hard words chapter.

If Google Sheets is unreachable, the build should not fail the whole site unless strict mode is added later. It should warn and continue with the existing local snapshot.

## Deduplication

Existing global deduplication by normalized `word.casefold()` should remain.

For hard words:

- Deduplicate inside the hard words list by the expanded display word.
- When hard words are loaded as a chapter, they may duplicate words from normal chapters. This is intentional for practice convenience.
- Normal chapters should keep their existing deduplication behavior.

This means a word can appear in its original chapter and also in the hard words chapter, but should not appear twice inside the hard words chapter.

## Security

The Google Apps Script write endpoint should use a simple passcode. The passcode is not bank-grade security, but it is suitable for a personal vocabulary notebook.

The public web page must not contain:

- GitHub Personal Access Tokens
- Azure Speech keys
- LINE tokens
- Google account credentials

The passcode may be entered by the user in the browser and saved locally. If a device is shared or untrusted, the user should not save the passcode there.

## Testing

Add or update tests for:

- Abbreviation expansion only affects English fields.
- Chinese fields retain abbreviations unchanged.
- `EMS` expands for display and full-term speech.
- Hard words CSV rows are loaded into a separate chapter.
- Removed hard words are excluded.
- Duplicate hard words are collapsed inside the hard words chapter.
- Missing Google Sheet configuration does not break the build.

Manual verification should cover:

- PC and mobile UI still render chapters correctly.
- The hard-word action button does not interrupt playback.
- Hard words chapter plays with existing segmented audio or browser fallback.
- GitHub Actions can build with and without the Google Sheet URL.

## Implementation Scope

The first implementation should stay small:

1. Update abbreviation expansion behavior.
2. Add hard words CSV support and chapter generation.
3. Add web UI button and Apps Script POST integration.
4. Add README setup steps for Google Sheet, Apps Script, and GitHub secret.

Do not add a database, user accounts, or direct GitHub repo writes in this iteration.
