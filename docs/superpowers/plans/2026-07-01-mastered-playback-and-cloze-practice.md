# Mastered Playback and Cloze Practice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep mastered words in playback with one English repetition, replace multiple-choice practice with example cloze input, place newest hard words first, and hide YouGlish URLs.

**Architecture:** Add one dependency-free browser helper file containing pure learning rules that can be tested with Node's built-in test runner. Keep DOM orchestration in the existing `web/app.js`, and sort Google Sheet snapshot rows in `hard_words_sync.py` before deduplication.

**Tech Stack:** Vanilla JavaScript, Node.js built-in `node:test`, Python 3 `unittest`, GitHub Actions, GitHub Pages.

---

## File Map

- Create `web/learning_helpers.js`: pure playback, cloze, answer, and pronunciation helpers.
- Create `tests/learning_helpers.test.js`: behavioral tests for the pure JavaScript helpers.
- Modify `web/app.js`: connect helpers to playback, practice, and local hard-word ordering.
- Modify `web/index.html`: load the helper and replace multiple-choice controls with cloze input controls.
- Modify `web/styles.css`: style the cloze form.
- Modify `hard_words_sync.py`: order snapshot rows by newest `added_at`.
- Modify `tests/test_hard_words_sync.py`: verify dated and malformed row ordering.
- Modify `tests/test_web_assets.py`: verify UI integration and removal of skip-mastered behavior.
- Modify `.github/workflows/daily-vocabulary.yml`: run JavaScript tests and publish the helper asset.

### Task 1: Pure Learning Rules

**Files:**
- Create: `web/learning_helpers.js`
- Create: `tests/learning_helpers.test.js`

- [ ] **Step 1: Write failing Node tests**

Test these public functions:

```javascript
const {
  buildClozeCandidates,
  isCorrectClozeAnswer,
  repeatCountForWord,
  sanitizePronunciation,
} = require("../web/learning_helpers.js");

test("mastered words use one English repetition", () => {
  assert.equal(repeatCountForWord(true, 5), 1);
  assert.equal(repeatCountForWord(false, 5), 5);
});

test("cloze candidates blank exact target phrases", () => {
  const candidates = buildClozeCandidates([{
    word: "galvanic corrosion",
    example_1_en: "Galvanic corrosion can damage the joint.",
    example_1_zh: "電偶腐蝕可能損壞接合處。",
  }]);
  assert.equal(candidates[0].clozeText, "_____ can damage the joint.");
  assert.equal(candidates[0].hint, "電偶腐蝕可能損壞接合處。");
});

test("answers ignore case and outer whitespace only", () => {
  assert.equal(isCorrectClozeAnswer("  Galvanic Corrosion ", "galvanic corrosion"), true);
  assert.equal(isCorrectClozeAnswer("galvanic  corrosion", "galvanic corrosion"), false);
});

test("pronunciation omits YouGlish suffix", () => {
  assert.equal(
    sanitizePronunciation("/test/ | https://youglish.com/pronounce/test/english"),
    "/test/",
  );
});
```

- [ ] **Step 2: Run tests and confirm RED**

Run:

```powershell
node --test tests/learning_helpers.test.js
```

Expected: FAIL because `web/learning_helpers.js` does not exist.

- [ ] **Step 3: Implement the pure helpers**

Implement:

```javascript
function repeatCountForWord(mastered, configuredCount) {
  return mastered ? 1 : Math.max(1, Number(configuredCount) || 1);
}

function sanitizePronunciation(value) {
  return String(value || "").split("|", 1)[0].trim();
}

function normalizeClozeAnswer(value) {
  return String(value || "").trim().toLocaleLowerCase("en-US");
}

function isCorrectClozeAnswer(answer, expected) {
  return normalizeClozeAnswer(answer) === normalizeClozeAnswer(expected);
}
```

Add escaped, case-insensitive exact phrase matching for both examples. Return one candidate per usable example and exclude examples that do not contain the complete target.

Export the functions through both `window.EvdLearningHelpers` and `module.exports`.

- [ ] **Step 4: Run tests and confirm GREEN**

Run:

```powershell
node --test tests/learning_helpers.test.js
```

Expected: all helper tests pass.

### Task 2: Cloud Hard-Word Ordering

**Files:**
- Modify: `tests/test_hard_words_sync.py`
- Modify: `hard_words_sync.py`

- [ ] **Step 1: Write a failing ordering test**

Add a CSV fixture containing active rows in old/new/malformed order and assert:

```python
self.assertEqual(
    [row["word"] for row in written_rows],
    ["new word", "old word", "undated word"],
)
```

Also verify duplicate words keep the newest row.

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```powershell
python -m unittest tests.test_hard_words_sync -v
```

Expected: FAIL because snapshot rows still preserve source order.

- [ ] **Step 3: Implement stable newest-first ordering**

Parse ISO `added_at` using `datetime.fromisoformat`, treat `Z` as UTC, and assign malformed or empty timestamps the lowest key. Sort rows descending before normalized-word deduplication.

- [ ] **Step 4: Run the focused test and confirm GREEN**

Run:

```powershell
python -m unittest tests.test_hard_words_sync -v
```

Expected: all hard-word synchronization tests pass.

### Task 3: Frontend Integration

**Files:**
- Modify: `tests/test_web_assets.py`
- Modify: `web/app.js`
- Modify: `web/index.html`
- Modify: `web/styles.css`

- [ ] **Step 1: Write failing frontend asset tests**

Assert that:

```python
self.assertNotIn('id="skipMasteredToggle"', index_html)
self.assertNotIn("skipMastered", app_js)
self.assertIn('id="clozeAnswerInput"', index_html)
self.assertIn('id="submitAnswerButton"', index_html)
self.assertIn("buildClozeCandidates", app_js)
self.assertIn("repeatCountForWord(isMasteredWord(word)", app_js)
self.assertIn("sanitizePronunciation(word.pronunciation)", app_js)
self.assertIn("chapter.words.unshift({ ...word })", app_js)
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```powershell
python -m unittest tests.test_web_assets -v
```

Expected: FAIL because the old skip control and multiple-choice practice still exist.

- [ ] **Step 3: Integrate mastered playback**

Remove `skipMastered` state, persistence, control listeners, `playableWords`, and eligible-navigation filtering. Build chapter queues from all current words. In `buildWordQueue`, compute:

```javascript
const repeatCount = repeatCountForWord(isMasteredWord(word), state.englishRepeatCount);
```

Pass `repeatCount` to word and example queue construction.

- [ ] **Step 4: Integrate cloze practice**

Replace `answerOptions` with:

```html
<p id="questionHint" class="question-hint"></p>
<div class="cloze-answer">
  <input id="clozeAnswerInput" type="text" autocomplete="off" spellcheck="false">
  <button id="submitAnswerButton" type="button">送出答案</button>
</div>
```

Use `buildClozeCandidates(currentWords())`, select one random candidate, display its cloze sentence and Chinese hint, and validate the typed answer with `isCorrectClozeAnswer`. Support Enter to submit.

- [ ] **Step 5: Integrate ordering and pronunciation display**

Use:

```javascript
elements.pronunciationText.textContent = sanitizePronunciation(word.pronunciation);
chapter.words.unshift({ ...word });
```

Store new local active hard words at the beginning and restore them without reversing newest-first order.

- [ ] **Step 6: Run focused frontend tests and syntax check**

Run:

```powershell
python -m unittest tests.test_web_assets -v
node --check web/app.js
node --check web/learning_helpers.js
```

Expected: all frontend tests pass and both scripts parse successfully.

### Task 4: Workflow and Full Verification

**Files:**
- Modify: `.github/workflows/daily-vocabulary.yml`
- Modify: `tests/test_workflow_schedule.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing workflow tests**

Assert the workflow contains:

```text
node --test tests/learning_helpers.test.js
cp web/learning_helpers.js output/learning_helpers.js
```

- [ ] **Step 2: Run workflow tests and confirm RED**

Run:

```powershell
python -m unittest tests.test_workflow_schedule -v
```

Expected: FAIL because Node tests and helper publishing are absent.

- [ ] **Step 3: Update workflow and documentation**

Run Node tests after Python tests and copy the helper during static-only publishing. Document mastered one-repeat playback and cloze practice in `README.md`.

- [ ] **Step 4: Run complete verification**

Run:

```powershell
python -m unittest discover -s tests -v
node --test tests/learning_helpers.test.js
node --check web/app.js
node --check web/learning_helpers.js
git diff --check
```

Expected: all tests pass, both scripts parse, and `git diff --check` exits successfully.

- [ ] **Step 5: Commit, push, and verify deployment**

Commit the implementation, push `main`, wait for `Daily Vocabulary`, verify GitHub Pages contains the cloze input and no skip-mastered checkbox, and confirm no LINE notification is sent when no vocabulary was added.
