# Singapore Travel Vocabulary Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import the supplied Singapore travel vocabulary as a clean 196-word chapter that supports playback and exact-phrase cloze practice.

**Architecture:** Generate one normalized CSV from the user-provided source with Python's standard `csv` module, then treat that CSV like every existing chapter. Keep all runtime code and APIs unchanged; enforce compatibility through a dedicated data regression test.

**Tech Stack:** Python 3 standard library, `unittest`, CSV, existing vocabulary loader, GitHub Actions, Google Text-to-Speech, GitHub Pages

---

### Task 1: Add Singapore Chapter Data Tests

**Files:**
- Create: `tests/test_singapore_vocabulary_data.py`
- Test: `tests/test_singapore_vocabulary_data.py`

- [ ] **Step 1: Write the missing-file and schema tests**

Create:

```python
import csv
from collections import defaultdict
from pathlib import Path
import re
import unittest

from vocabulary_loader import REQUIRED_COLUMNS


PROJECT_DIR = Path(__file__).resolve().parents[1]
VOCABULARY_DIR = PROJECT_DIR / "vocabulary"
SINGAPORE_PATH = VOCABULARY_DIR / "新加坡旅遊單字.csv"
REQUIRED_VALUE_COLUMNS = [
    column for column in REQUIRED_COLUMNS if column != "last_review_date"
]


def read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def example_contains_exact_target(example: str, target: str) -> bool:
    escaped = re.escape(target)
    return re.search(
        rf"(^|[^A-Za-z0-9]){escaped}(?=$|[^A-Za-z0-9])",
        example,
        flags=re.IGNORECASE,
    ) is not None


class SingaporeVocabularyDataTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(
            SINGAPORE_PATH.exists(),
            f"Missing chapter CSV: {SINGAPORE_PATH.name}",
        )
        self.rows = read_rows(SINGAPORE_PATH)

    def test_schema_encoding_count_and_ids(self):
        with SINGAPORE_PATH.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)
            rows = list(reader)

        self.assertEqual(reader.fieldnames, REQUIRED_COLUMNS)
        self.assertTrue(SINGAPORE_PATH.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertEqual(len(rows), 196)
        self.assertEqual(
            [row["id"] for row in rows],
            [str(index) for index in range(1, 197)],
        )

    def test_required_values_and_exact_cloze_examples(self):
        for row in self.rows:
            for column in REQUIRED_VALUE_COLUMNS:
                self.assertTrue(
                    str(row.get(column) or "").strip(),
                    f"{row.get('word') or row.get('id')} has blank {column}",
                )
            self.assertTrue(
                any(
                    example_contains_exact_target(row[column], row["word"])
                    for column in ("example_1_en", "example_2_en")
                ),
                f"{row['word']} needs an exact cloze example",
            )

    def test_words_are_unique_and_context_conflicts_are_resolved(self):
        words = [row["word"].strip().casefold() for row in self.rows]

        self.assertEqual(len(words), len(set(words)))
        for word in ("luggage", "receipt", "taxi", "towel"):
            self.assertEqual(words.count(word), 1)
        self.assertIn("public bus", words)
        self.assertNotIn("bus", words)
        self.assertIn("elevator", words)
        self.assertIn("lift", words)
        self.assertEqual(words.count("elevator"), 1)
        self.assertNotIn("elevator / lift", words)

    def test_chapter_introduces_no_formal_cross_chapter_duplicates(self):
        other_sources = defaultdict(list)
        for path in sorted(VOCABULARY_DIR.glob("*.csv")):
            if path.name in {"hard_words.csv", SINGAPORE_PATH.name}:
                continue
            for row in read_rows(path):
                key = str(row.get("word") or "").strip().casefold()
                if key:
                    other_sources[key].append(path.name)

        collisions = {
            row["word"]: other_sources[row["word"].strip().casefold()]
            for row in self.rows
            if row["word"].strip().casefold() in other_sources
        }
        self.assertEqual(collisions, {})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
python -m unittest tests.test_singapore_vocabulary_data -v
```

Expected: four failures with `Missing chapter CSV: 新加坡旅遊單字.csv`.

### Task 2: Generate the Normalized Chapter CSV

**Files:**
- Source: `C:\Users\xqual\Downloads\新加坡旅遊單字.csv`
- Create: `vocabulary/新加坡旅遊單字.csv`
- Test: `tests/test_singapore_vocabulary_data.py`

- [ ] **Step 1: Generate the CSV with structured transformations**

Resolve the source path in PowerShell and pass it through an environment
variable so Python source encoding does not depend on the console:

```powershell
$env:SINGAPORE_CSV = (
    Resolve-Path -LiteralPath 'C:\Users\xqual\Downloads\新加坡旅遊單字.csv'
).Path
```

Run this Python transformation:

```python
import csv
import os
from pathlib import Path

from vocabulary_loader import REQUIRED_COLUMNS


source = Path(os.environ["SINGAPORE_CSV"])
destination = Path("vocabulary") / "新加坡旅遊單字.csv"

with source.open("r", encoding="utf-8-sig", newline="") as file:
    source_rows = list(csv.DictReader(file))

duplicate_words = {"luggage", "receipt", "taxi", "towel"}
normalized_rows = []
row_by_word = {}

for source_row in source_rows:
    row = {column: source_row.get(column, "") for column in REQUIRED_COLUMNS}
    word_key = row["word"].strip().casefold()
    if word_key in duplicate_words and word_key in row_by_word:
        first_row = row_by_word[word_key]
        first_row["example_2_en"] = row["example_1_en"]
        first_row["example_2_zh"] = row["example_1_zh"]
        continue
    normalized_rows.append(row)
    row_by_word[word_key] = row

updates = {
    "dumpling": {
        "example_1_en": "My child would like a dumpling.",
        "example_1_zh": "我的小孩想吃一顆餃子。",
    },
    "poncho": {
        "example_1_en": "We need a poncho for each child.",
        "example_1_zh": "每個小孩都需要一件輕便雨衣。",
    },
    "passport": {
        "example_1_en": "Here is my passport.",
        "example_1_zh": "這是我的護照。",
    },
    "connecting room": {
        "example_1_en": "Can we book a connecting room for our family?",
        "example_1_zh": "我們可以為家人預訂一間連通房嗎？",
    },
    "toothbrush": {
        "example_1_en": "Could we have a toothbrush for each child?",
        "example_1_zh": "可以給每個小孩一支牙刷嗎？",
    },
    "ticket": {
        "example_1_en": "I need a ticket for the show.",
        "example_1_zh": "我需要一張表演門票。",
    },
    "elevator / lift": {
        "word": "lift",
        "pronunciation": "/lɪft/",
        "chinese_meaning": "電梯（英式）",
    },
    "bus": {
        "word": "public bus",
        "pronunciation": "/ˌpʌb.lɪk ˈbʌs/",
        "example_1_en": "Is this the public bus to the zoo?",
        "example_1_zh": "這是去動物園的公車嗎？",
        "example_2_en": "We need to take a public bus after the MRT.",
        "example_2_zh": "我們搭完 MRT 後需要轉乘公車。",
    },
}

for row in normalized_rows:
    row.update(updates.get(row["word"].strip().casefold(), {}))

for index, row in enumerate(normalized_rows, start=1):
    row["id"] = str(index)

with destination.open("w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=REQUIRED_COLUMNS,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(normalized_rows)
```

Expected: `vocabulary/新加坡旅遊單字.csv` contains 196 rows plus the header.

- [ ] **Step 2: Run focused tests and verify GREEN**

Run:

```powershell
python -m unittest tests.test_singapore_vocabulary_data -v
```

Expected: four tests PASS.

- [ ] **Step 3: Inspect the transformed edge cases**

Run a compact structured check that prints:

```text
count=196
first=table
last=medical help
duplicates=[]
public_bus=1
```

Confirm the merged examples for `luggage`, `receipt`, `taxi`, and `towel`
contain two different travel contexts.

- [ ] **Step 4: Commit the chapter and regression tests**

```powershell
git add tests/test_singapore_vocabulary_data.py vocabulary/新加坡旅遊單字.csv
git commit -m "feat: add Singapore travel vocabulary chapter"
```

### Task 3: Verify Generation and Existing Behavior

**Files:**
- Generated temporarily: `output/data/2026-07-05_daily_vocabulary.json`
- Generated temporarily: `output/scripts/2026-07-05_daily_vocabulary.md`

- [ ] **Step 1: Run the complete test suite**

```powershell
python -m unittest discover -s tests -v
node --test tests/learning_helpers.test.js
node --check web/app.js
node --check web/learning_helpers.js
git diff --check
```

Expected: all Python and Node tests PASS, syntax checks exit 0, and no
whitespace errors.

- [ ] **Step 2: Run a generation smoke test without TTS or LINE**

```powershell
python main.py --date 2026-07-05 --skip-audio --skip-line --no-update-review
```

Read the generated JSON and require:

```text
chapter=新加坡旅遊單字
word_count=196
first=table
last=medical help
```

- [ ] **Step 3: Remove smoke-test output changes**

Restore tracked files under `output/` and remove only the newly generated
`2026-07-05` JSON and Markdown files. Verify the feature branch is clean.

### Task 4: Integrate, Generate Audio, Deploy, and Notify

**Files:**
- Generated by workflow: `output/audio/segments/**`
- Generated by workflow: `output/data/latest.json`
- Generated by workflow: `output/data/2026-07-05_daily_vocabulary.json`
- Generated by workflow: `output/scripts/2026-07-05_daily_vocabulary.md`

- [ ] **Step 1: Finish the feature branch**

Use `superpowers:finishing-a-development-branch`. Integrate only after fresh
tests pass. Preserve the worktree if a Pull Request is selected.

- [ ] **Step 2: Monitor the push-triggered Daily Vocabulary workflow**

Require successful completion of:

- tests
- Google Cloud credentials
- daily generation
- generated-file commit
- Pages artifact upload
- Pages deployment

- [ ] **Step 3: Verify public data**

Read cache-busted public assets and require:

```text
chapter=新加坡旅遊單字
word_count=196
public_bus=true
elevator=true
lift=true
```

- [ ] **Step 4: Send one LINE notification**

Because push-triggered generation uses `--skip-line`, use the existing
`LINE Smoke Test` once after Pages deployment. Verify its notification step
completes successfully and its logs contain no `LINE notification warning` or
HTTP error.

