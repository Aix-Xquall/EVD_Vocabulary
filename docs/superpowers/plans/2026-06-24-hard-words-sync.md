# Hard Words Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add centralized English abbreviation expansion and a cross-device hard words chapter synced from Google Sheets / Apps Script.

**Architecture:** Keep the static GitHub Pages frontend. The frontend POSTs selected words to Google Apps Script, while GitHub Actions optionally imports Google Sheet CSV data into a local `vocabulary/hard_words.csv` snapshot before generating the site.

**Tech Stack:** Python 3.11, unittest, CSV files, vanilla JavaScript, GitHub Actions, Google Apps Script.

---

### Task 1: Abbreviation Expansion

**Files:**
- Modify: `abbreviation_expander.py`
- Modify: `vocabulary_loader.py`
- Test: `tests/test_vocabulary_loader.py`

- [ ] Add a failing test proving `EMS` expands in `word`, `example_1_en`, and `example_2_en`.
- [ ] Add a failing test proving `chinese_meaning`, `example_1_zh`, and `example_2_zh` keep `EMS` and `EMC` unchanged.
- [ ] Update the abbreviation expander with `EMS`.
- [ ] Change the loader so only English-facing fields are expanded.
- [ ] Run `python -m unittest tests.test_vocabulary_loader -v`.

### Task 2: Hard Words Import

**Files:**
- Create: `hard_words_sync.py`
- Modify: `config.py`
- Modify: `main.py`
- Test: `tests/test_hard_words_sync.py`
- Test: `tests/test_script_builder.py`

- [ ] Add failing tests for filtering active rows, removing duplicate hard words, and writing `vocabulary/hard_words.csv`.
- [ ] Add settings for `HARD_WORDS_SHEET_CSV_URL` and optional `HARD_WORDS_READ_TOKEN`.
- [ ] Implement a sync helper that reads a Google Sheet CSV URL when configured and writes the local snapshot.
- [ ] Keep build behavior non-fatal when the remote sheet is missing or unreachable.
- [ ] Ensure hard words can appear both in their original chapter and in a hard words chapter.
- [ ] Run `python -m unittest tests.test_hard_words_sync tests.test_script_builder -v`.

### Task 3: Web UI Sync Button

**Files:**
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Test: `node --check web/app.js`

- [ ] Add frontend configuration fields from `latest.json` for the Apps Script write URL.
- [ ] Add a hard-word action button near the current word.
- [ ] Send the selected word payload to Apps Script with a passcode stored locally on the device.
- [ ] Show added, pending, and failure states without interrupting audio playback.
- [ ] Hide the button when no write URL is configured.

### Task 4: Workflow And Docs

**Files:**
- Modify: `.github/workflows/daily-vocabulary.yml`
- Modify: `README.md`
- Test: full unit test run

- [ ] Pass hard words secrets into the daily generation step.
- [ ] Document Google Sheet columns, Apps Script deployment settings, and GitHub secrets.
- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Run `node --check web/app.js`.
- [ ] Run `python main.py --skip-audio --skip-line --no-update-review --date 2026-06-24`.
