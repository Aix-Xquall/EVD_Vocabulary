# Daily Vocabulary Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a daily aerospace/avionics/EMC vocabulary generator that publishes web-ready data, per-word MP3 files, one combined MP3, Markdown scripts, and optional LINE self-notifications.

**Architecture:** Python reads all vocabulary CSV files, selects daily words by review priority, generates Markdown/JSON/audio outputs, updates review fields, and optionally sends a LINE Messaging API push message. A static GitHub Pages frontend reads `output/data/latest.json` and plays the generated online MP3 files with practice UI.

**Tech Stack:** Python standard library, Azure Cognitive Services Speech SDK, requests, pytest, HTML/CSS/JavaScript, GitHub Actions.

---

### Task 1: Tests

**Files:**
- Create: `tests/test_daily_selector.py`
- Create: `tests/test_vocabulary_loader.py`
- Create: `tests/test_review_updater.py`
- Create: `tests/test_script_builder.py`

- [ ] Write tests for selection priority, CSV loading, review updates, and Markdown/JSON script behavior.
- [ ] Run tests and verify they fail because implementation modules do not exist yet.

### Task 2: Python Core

**Files:**
- Create: `config.py`
- Create: `vocabulary_loader.py`
- Create: `daily_selector.py`
- Create: `review_updater.py`
- Create: `script_builder.py`
- Create: `tts_generator.py`
- Create: `line_notifier.py`
- Create: `main.py`

- [ ] Implement settings with environment variable overrides.
- [ ] Implement CSV discovery/loading with source file tracking.
- [ ] Implement deterministic daily selection based on low `review_count`, old `last_review_date`, high `difficulty`, and stable date shuffle.
- [ ] Implement Markdown and JSON output generation.
- [ ] Implement review count/date updates only after outputs are written.
- [ ] Implement Azure Speech MP3 generation with per-word and combined output paths.
- [ ] Implement optional LINE push notification for one user.

### Task 3: Static Web UI

**Files:**
- Create: `web/index.html`
- Create: `web/styles.css`
- Create: `web/app.js`

- [ ] Implement online playback from `output/data/latest.json`.
- [ ] Require one user click before audio playback to satisfy browser autoplay rules.
- [ ] Add controls for start, pause, previous, next, repeat all, and repeat current word.
- [ ] Add practice UI: English-to-Chinese, Chinese-to-English, and answer reveal mode.
- [ ] Store local daily progress in browser `localStorage`.

### Task 4: GitHub Automation And Docs

**Files:**
- Create: `.github/workflows/daily-vocabulary.yml`
- Create: `requirements.txt`
- Create: `README.md`
- Use CSV files under `vocabulary/` as the vocabulary source.

- [ ] Add GitHub Actions workflow with manual and scheduled triggers.
- [ ] Configure workflow to install dependencies, run tests, generate daily outputs, commit changes, and deploy GitHub Pages-compatible files.
- [ ] Document local Windows setup, GitHub Pages, GitHub Secrets, Azure Speech, and LINE Messaging API setup.

### Task 5: Verification

**Files:**
- Use all project files.

- [ ] Run Python tests.
- [ ] Run a dry generation without Azure audio to verify CSV/Markdown/JSON/update behavior.
- [ ] Confirm generated JSON paths match web app expectations.
- [ ] Report any local Python or network credential blocker clearly.
