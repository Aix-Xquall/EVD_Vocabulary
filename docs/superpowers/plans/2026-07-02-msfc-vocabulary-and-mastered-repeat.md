# MSFC Vocabulary and Mastered Repeat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge 34 unique imported words into the existing MSFC chapter without adding new duplicate groups, and make mastered English content play twice.

**Architecture:** Preserve the user's 35-row working copy as an ignored import artifact, then create an isolated worktree from the committed 84-row source. Add data-contract tests before performing a one-time structured CSV merge, and update the existing pure playback helper through its Node test.

**Tech Stack:** Python 3 CSV library, Python `unittest`, vanilla JavaScript, Node.js built-in `node:test`, Git worktrees, GitHub Actions.

---

## File Map

- Create `tests/test_vocabulary_data.py`: validates the merged MSFC chapter and prevents appended rows from adding cross-chapter duplicates.
- Modify `vocabulary/MSFC-HDBK-3697.csv`: contains 84 existing rows plus 34 imported rows.
- Modify `tests/learning_helpers.test.js`: expects mastered repetition count 2.
- Modify `web/learning_helpers.js`: returns 2 repetitions for mastered words.
- Modify `README.md`: records the mastered two-repeat behavior.

### Task 1: Preserve Import Data and Establish Baseline

**Files:**
- Read: `vocabulary/MSFC-HDBK-3697.csv`
- Create outside tracked files: `.worktrees/msfc-import-2026-07-02.csv`

- [ ] **Step 1: Copy the user's import source**

Use PowerShell `Copy-Item -LiteralPath` to preserve the current 35-row working copy under the ignored `.worktrees` directory before creating the feature worktree.

- [ ] **Step 2: Create isolated worktree**

Create branch `feature/msfc-vocabulary-update` at `.worktrees/msfc-vocabulary-update`, verify the target is ignored, and run:

```powershell
python -m unittest discover -s tests
node --test tests/learning_helpers.test.js
```

Expected: Python 93 tests and Node 5 tests pass before feature changes.

### Task 2: MSFC Data Contract

**Files:**
- Create: `tests/test_vocabulary_data.py`
- Modify: `vocabulary/MSFC-HDBK-3697.csv`

- [ ] **Step 1: Write the failing data tests**

Create tests that read CSV files with `encoding="utf-8-sig"` and assert:

```python
self.assertEqual(len(msfc_rows), 118)
self.assertEqual([row["id"] for row in msfc_rows[:84]], expected_existing_ids)
self.assertEqual([row["id"] for row in msfc_rows[84:]], [str(i) for i in range(97, 131)])
self.assertNotIn("individual", {row["word"].strip().casefold() for row in msfc_rows})
self.assertEqual(appended_cross_chapter_duplicates, {})
```

The duplicate check covers only appended MSFC rows, IDs 85 through 118, against other formal chapters. It excludes `hard_words.csv` and leaves the 15 pre-existing formal duplicate groups unchanged.

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```powershell
python -m unittest tests.test_vocabulary_data -v
```

Expected: FAIL because the committed MSFC chapter still contains 84 rows.

- [ ] **Step 3: Perform the structured merge**

Use Python's `csv.DictReader` and `csv.DictWriter`:

1. Read the worktree's committed 84-row MSFC CSV.
2. Read `.worktrees/msfc-import-2026-07-02.csv`.
3. Build normalized-word keys from all formal chapters.
4. Skip imported `individual`.
5. Append the other 34 rows in source order.
6. Preserve all existing IDs and assign IDs 97 through 130 to appended rows.
7. Write through a temporary file with `encoding="utf-8-sig"` and atomically replace the chapter after validation.

- [ ] **Step 4: Run the focused test and confirm GREEN**

Run:

```powershell
python -m unittest tests.test_vocabulary_data -v
```

Expected: all vocabulary data tests pass.

### Task 3: Mastered English Repetition

**Files:**
- Modify: `tests/learning_helpers.test.js`
- Modify: `web/learning_helpers.js`
- Modify: `README.md`

- [ ] **Step 1: Change the existing test to expect two repetitions**

Use:

```javascript
test("mastered words use two English repetitions", () => {
  assert.equal(repeatCountForWord(true, 5), 2);
  assert.equal(repeatCountForWord(false, 5), 5);
});
```

- [ ] **Step 2: Run the Node test and confirm RED**

Run:

```powershell
node --test tests/learning_helpers.test.js
```

Expected: FAIL because mastered words currently return 1.

- [ ] **Step 3: Implement the minimal playback change**

Change:

```javascript
return mastered ? 2 : Math.max(1, Number(configuredCount) || 1);
```

Update README wording from mastered English playing once to playing twice.

- [ ] **Step 4: Run the Node test and confirm GREEN**

Run:

```powershell
node --test tests/learning_helpers.test.js
```

Expected: all Node tests pass.

### Task 4: Verification and Deployment

**Files:**
- Verify all modified files.

- [ ] **Step 1: Run full verification**

Run:

```powershell
python -m unittest discover -s tests -v
node --test tests/learning_helpers.test.js
node --check web/app.js
node --check web/learning_helpers.js
git diff --check
```

Expected: all tests pass and syntax/diff checks exit successfully.

- [ ] **Step 2: Verify generated data behavior**

Run the normal generation path with LINE disabled and verify the payload contains 118 MSFC words without creating duplicate formal words.

- [ ] **Step 3: Commit and merge**

Commit the feature branch, rebase it onto current `main`, fast-forward merge, rerun tests on `main`, then remove the owned worktree and feature branch.

- [ ] **Step 4: Push and verify GitHub Pages**

Push `main`, wait for `Daily Vocabulary`, and verify:

- The workflow completes successfully.
- The deployed chapter tab reports 118 MSFC words.
- The deployed helper contains `mastered ? 2`.
- The push does not force a LINE notification.
