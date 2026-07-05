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
