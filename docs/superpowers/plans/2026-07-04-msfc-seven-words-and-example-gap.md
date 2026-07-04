# MSFC Seven Words and Example Gap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add seven PDF-grounded words to the MSFC chapter and wait two seconds between the complete example 1 and example 2 playback groups.

**Architecture:** Preserve the existing CSV schema and append-only ID strategy. Keep audio as reusable language segments and implement the new silence in the browser queue by assigning a start delay to the first available segment of example 2.

**Tech Stack:** Python 3 `unittest`, CSV, vanilla JavaScript, Node.js test runner, GitHub Actions, GitHub Pages

---

### Task 1: Add MSFC Vocabulary Regression Tests

**Files:**
- Modify: `tests/test_vocabulary_data.py`
- Test: `tests/test_vocabulary_data.py`

- [ ] **Step 1: Update the MSFC row and ID expectations**

Change the existing row test to require 125 rows and appended IDs through 137:

```python
def test_msfc_chapter_has_125_rows_with_preserved_and_appended_ids(self):
    with MSFC_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    self.assertEqual(reader.fieldnames, REQUIRED_COLUMNS)
    self.assertEqual(len(rows), 125)
    missing_existing_ids = {2, 31, 32, 35, 57, 67, 68, 69, 74, 81, 82, 90}
    expected_existing_ids = [
        str(index) for index in range(1, 97) if index not in missing_existing_ids
    ]
    self.assertEqual([row["id"] for row in rows[:84]], expected_existing_ids)
    self.assertEqual(
        [row["id"] for row in rows[84:]],
        [str(index) for index in range(97, 138)],
    )
    self.assertTrue(MSFC_PATH.read_bytes().startswith(b"\xef\xbb\xbf"))
```

- [ ] **Step 2: Add exact-word and cloze suitability assertions**

Add this test:

```python
def test_latest_msfc_rows_contain_requested_words_and_usable_examples(self):
    rows = read_rows(MSFC_PATH)
    expected_words = [
        "rely on",
        "accidental",
        "treated like",
        "ignition",
        "intermittent",
        "specific",
        "weakens",
    ]
    new_rows = rows[-len(expected_words):]

    self.assertEqual([row["word"] for row in new_rows], expected_words)
    for row in new_rows:
        word = row["word"].casefold()
        examples = [
            row["example_1_en"].casefold(),
            row["example_2_en"].casefold(),
        ]
        self.assertTrue(
            any(word in example for example in examples),
            f"{row['word']} needs an exact cloze example",
        )
```

- [ ] **Step 3: Expand duplicate checking to all appended rows**

Keep the existing first 84 rows as the historical baseline and change:

```python
self.assertEqual(len(appended_rows), 41)
```

The existing duplicate scan must continue to require:

```python
self.assertEqual(appended_duplicates, {})
```

- [ ] **Step 4: Run the focused tests and verify RED**

Run:

```powershell
python -m unittest tests.test_vocabulary_data -v
```

Expected: FAIL because the CSV still has 118 rows, IDs end at 130, and the seven words are absent.

### Task 2: Append the Seven Vocabulary Rows

**Files:**
- Modify: `vocabulary/MSFC-HDBK-3697.csv`
- Test: `tests/test_vocabulary_data.py`

- [ ] **Step 1: Append IDs 131 through 137**

Append these rows without modifying the existing 118 rows:

```csv
131,rely on,/rɪˈlaɪ ɑːn/,依賴；仰賴,Do not rely on the vehicle structure as the primary power return.,不要依賴載具結構作為主要電源回流路徑。,Bonding jumpers should not rely on adjacent parts for their connection.,Bonding jumper 不應依賴相鄰零件形成連接。,Power & Return Path,Intermediate,0,
132,accidental,/ˌæksɪˈdentəl/,意外的；非預期的,An accidental fault may place primary power on the equipment enclosure.,意外故障可能使設備外殼帶有主電源電壓。,Proper bonding provides a safe path for accidental current.,適當的 bonding 可為意外電流提供安全路徑。,Safety & Fault Protection,Intermediate,0,
133,treated like,/ˈtriːtɪd laɪk/,被視同；像……一樣處理,Faying surfaces of bond straps should be treated like other faying surfaces.,Bond strap 的接合面應像其他接合面一樣處理。,Graphite-based composites should be treated like dissimilar metal couples.,石墨基複合材料應像異種金屬組合一樣處理。,Materials & Corrosion,Intermediate,0,
134,ignition,/ɪɡˈnɪʃən/,點燃；著火,Fuel and pyrotechnics should be enclosed by a Faraday cage to provide an adequate margin against ignition.,燃料與火工品應由 Faraday cage 包覆，以提供足夠的防點燃裕度。,A bond must carry lightning current without heating enough to become an ignition hazard.,Bond 必須能承載雷擊電流，且不得因過熱而形成點燃危害。,Lightning & Transients,Advanced,0,
135,intermittent,/ˌɪntərˈmɪtənt/,間歇性的；時有時無的,Movement of a loose bond strap can create an intermittent connection and electrical noise.,鬆動 bond strap 的移動可能造成間歇性連接與電氣雜訊。,An intermittent bond may cause arcing during vibration.,間歇性的 bond 可能在振動期間造成電弧。,Quality & Verification,Intermediate,0,
136,specific,/spəˈsɪfɪk/,特定的；明確的,The handbook helps determine bonding requirements applicable to specific hardware.,本手冊協助判定適用於特定硬體的 bonding 要求。,Program documents may include requirements for a specific project.,計畫文件可能包含特定專案的要求。,Requirements & Process,Basic,0,
137,weakens,/ˈwiːkənz/,削弱；使變弱,Lightning current weakens a fastener when excessive heat develops at the connection.,當連接處產生過多熱量時，雷擊電流會削弱緊固件。,Corrosion weakens the bond and increases electrical resistance.,腐蝕會削弱 bond 並增加電阻。,Lightning & Damage Effects,Intermediate,0,
```

- [ ] **Step 2: Preserve CSV encoding**

Verify:

```powershell
python -c "from pathlib import Path; assert Path('vocabulary/MSFC-HDBK-3697.csv').read_bytes().startswith(b'\xef\xbb\xbf')"
```

Expected: exit code 0.

- [ ] **Step 3: Run focused data tests and verify GREEN**

Run:

```powershell
python -m unittest tests.test_vocabulary_data -v
```

Expected: all vocabulary data tests PASS.

- [ ] **Step 4: Commit the data change**

```powershell
git add tests/test_vocabulary_data.py vocabulary/MSFC-HDBK-3697.csv
git commit -m "feat: add seven MSFC bonding terms"
```

### Task 3: Add Playback Timing Regression Test

**Files:**
- Modify: `tests/test_web_assets.py`
- Test: `tests/test_web_assets.py`

- [ ] **Step 1: Add a structural behavior test**

Add:

```python
def test_example_two_starts_after_two_second_group_delay(self):
    app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

    self.assertIn("const ENGLISH_REPEAT_DELAY_MS = 1500;", app_js)
    self.assertIn("const EXAMPLE_GROUP_DELAY_MS = 2000;", app_js)
    self.assertIn(
        "addRepeatedEnglishWithChinese(queue, segments.example_1_en, "
        "word?.example_1_en, segments.example_1_zh, word?.example_1_zh, "
        "repeatCount);",
        app_js,
    )
    self.assertIn(
        "addRepeatedEnglishWithChinese(queue, segments.example_2_en, "
        "word?.example_2_en, segments.example_2_zh, word?.example_2_zh, "
        "repeatCount, EXAMPLE_GROUP_DELAY_MS);",
        app_js,
    )
    self.assertIn("const groupStartIndex = queue.length;", app_js)
    self.assertIn(
        "queue[groupStartIndex].delayMs = startDelayMs;",
        app_js,
    )
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
python -m unittest tests.test_web_assets.WebAssetsTests.test_example_two_starts_after_two_second_group_delay -v
```

Expected: FAIL because `EXAMPLE_GROUP_DELAY_MS` and `startDelayMs` do not exist.

### Task 4: Implement the Two-Second Example Group Delay

**Files:**
- Modify: `web/app.js`
- Modify: `README.md`
- Test: `tests/test_web_assets.py`

- [ ] **Step 1: Separate the timing constants**

Replace:

```javascript
const EXAMPLE_REPEAT_DELAY_MS = 1500;
```

with:

```javascript
const ENGLISH_REPEAT_DELAY_MS = 1500;
const EXAMPLE_GROUP_DELAY_MS = 2000;
```

- [ ] **Step 2: Apply the group delay only to example 2**

Keep the word and example 1 calls unchanged. Change example 2 to:

```javascript
addRepeatedEnglishWithChinese(queue, segments.example_2_en, word?.example_2_en, segments.example_2_zh, word?.example_2_zh, repeatCount, EXAMPLE_GROUP_DELAY_MS);
```

- [ ] **Step 3: Attach the delay to the first available group segment**

Change the helper signature and body to:

```javascript
function addRepeatedEnglishWithChinese(
  queue,
  englishSegment,
  englishText,
  chineseSegment,
  chineseText,
  repeatCount,
  startDelayMs = 0,
) {
  const groupStartIndex = queue.length;
  addNarration(queue, englishSegment, englishText, "en");
  addNarration(queue, chineseSegment, chineseText, "zh");
  for (let count = 1; count < repeatCount; count += 1) {
    addNarration(queue, englishSegment, englishText, "en", ENGLISH_REPEAT_DELAY_MS);
  }
  if (queue.length > groupStartIndex) {
    queue[groupStartIndex].delayMs = startDelayMs;
  }
}
```

- [ ] **Step 4: Document the playback order**

Update the README playback section to state:

```text
例句 1（含中文與英文重複）完成後等待 2 秒，再播放例句 2；中文後的英文重複仍間隔 1.5 秒。
```

- [ ] **Step 5: Run focused tests and verify GREEN**

Run:

```powershell
python -m unittest tests.test_web_assets.WebAssetsTests.test_example_two_starts_after_two_second_group_delay -v
node --test tests/learning_helpers.test.js
node --check web/app.js
```

Expected: all commands PASS.

- [ ] **Step 6: Commit the timing change**

```powershell
git add README.md tests/test_web_assets.py web/app.js
git commit -m "feat: pause between vocabulary examples"
```

### Task 5: Full Verification and Deployment

**Files:**
- Generated by workflow: `output/data/latest.json`
- Generated by workflow: `output/app.js`
- Generated by workflow: `output/audio/segments/**`

- [ ] **Step 1: Run the complete local verification**

```powershell
python -m unittest discover -s tests -v
node --test tests/learning_helpers.test.js
node --check web/app.js
node --check web/learning_helpers.js
git diff --check
```

Expected: Python and Node tests PASS, syntax checks exit 0, and no whitespace errors.

- [ ] **Step 2: Run a generation smoke test without audio or LINE**

```powershell
python main.py --date 2026-07-04 --skip-audio --skip-line --no-update-review
```

Inspect the generated JSON and require:

```text
MSFC-HDBK-3697 word count: 125
First new word: rely on
Last new word: weakens
```

Restore or remove local generated smoke-test files before integration.

- [ ] **Step 3: Integrate and push**

Fast-forward the verified feature branch into `main`, rerun the complete local
verification on the merged result, and push `main` to GitHub.

- [ ] **Step 4: Verify GitHub Actions**

Require the push-triggered `Daily Vocabulary` run to complete successfully,
including tests, Google Cloud credentials, generation, generated-file commit,
and GitHub Pages deployment.

- [ ] **Step 5: Verify the public site**

Read the cache-busted public assets and require:

```text
MSFC-HDBK-3697 word count: 125
First new word: rely on
Last new word: weakens
EXAMPLE_GROUP_DELAY_MS: 2000
```

Confirm that the workflow ran the existing new-vocabulary LINE notification
path. Do not force a second LINE notification.
