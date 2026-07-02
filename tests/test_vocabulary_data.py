import csv
from collections import defaultdict
from pathlib import Path
import unittest

from vocabulary_loader import REQUIRED_COLUMNS


PROJECT_DIR = Path(__file__).resolve().parents[1]
VOCABULARY_DIR = PROJECT_DIR / "vocabulary"
MSFC_PATH = VOCABULARY_DIR / "MSFC-HDBK-3697.csv"


def read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


class VocabularyDataTests(unittest.TestCase):
    def test_msfc_chapter_has_118_rows_with_preserved_and_appended_ids(self):
        with MSFC_PATH.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            rows = list(reader)

        self.assertEqual(reader.fieldnames, REQUIRED_COLUMNS)
        self.assertEqual(len(rows), 118)
        missing_existing_ids = {2, 31, 32, 35, 57, 67, 68, 69, 74, 81, 82, 90}
        expected_existing_ids = [
            str(index) for index in range(1, 97) if index not in missing_existing_ids
        ]
        self.assertEqual([row["id"] for row in rows[:84]], expected_existing_ids)
        self.assertEqual([row["id"] for row in rows[84:]], [str(index) for index in range(97, 131)])
        self.assertTrue(MSFC_PATH.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_appended_msfc_rows_add_no_cross_chapter_duplicates(self):
        msfc_rows = read_rows(MSFC_PATH)
        appended_rows = msfc_rows[84:]
        other_sources = defaultdict(list)

        for path in sorted(VOCABULARY_DIR.glob("*.csv")):
            if path.name in {"hard_words.csv", MSFC_PATH.name}:
                continue
            for row in read_rows(path):
                word_key = str(row.get("word") or "").strip().casefold()
                if word_key:
                    other_sources[word_key].append(path.name)

        appended_duplicates = {
            row["word"]: other_sources[str(row.get("word") or "").strip().casefold()]
            for row in appended_rows
            if str(row.get("word") or "").strip().casefold() in other_sources
        }
        msfc_words = {str(row.get("word") or "").strip().casefold() for row in msfc_rows}

        self.assertEqual(len(appended_rows), 34)
        self.assertNotIn("individual", msfc_words)
        self.assertEqual(appended_duplicates, {})


if __name__ == "__main__":
    unittest.main()
