import csv
from collections import defaultdict
from pathlib import Path
import re
import unittest

from vocabulary_loader import REQUIRED_COLUMNS


PROJECT_DIR = Path(__file__).resolve().parents[1]
VOCABULARY_DIR = PROJECT_DIR / "vocabulary"
MSFC_PATH = VOCABULARY_DIR / "MSFC-HDBK-3697.csv"
CONSULTANT_PATH = VOCABULARY_DIR / "EMC顧問回覆與系統整合詞彙.csv"
EMC_ONE_PATH = VOCABULARY_DIR / "EMC航電詞彙整合1.csv"


def read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


class VocabularyDataTests(unittest.TestCase):
    def test_daq_word_and_examples_use_full_name_with_abbreviation(self):
        rows = read_rows(EMC_ONE_PATH)
        daq_row = next(row for row in rows if "(DAQ)" in row["word"])

        self.assertEqual(daq_row["word"], "Data Acquisition (DAQ)")
        self.assertIn("Data Acquisition (DAQ)", daq_row["example_1_en"])
        self.assertIn("Data Acquisition (DAQ)", daq_row["example_2_en"])

        for path in sorted(VOCABULARY_DIR.glob("*.csv")):
            if path.name == "hard_words.csv":
                continue
            for row in read_rows(path):
                for column in ("word", "example_1_en", "example_2_en"):
                    if re.search(r"\bDAQ\b", row[column]):
                        self.assertIn("Data Acquisition (DAQ)", row[column])

    def test_consultant_chapter_contains_requested_new_terms(self):
        rows = read_rows(CONSULTANT_PATH)
        words = {row["word"].strip().casefold() for row in rows}
        expected = {
            "refer to",
            "approach",
            "harsh",
            "appear",
            "exposure",
            "evidence",
            "disturb",
            "instead of",
            "accumulate",
            "contamination",
            "establishes",
        }

        self.assertTrue(expected.issubset(words))
        self.assertNotIn("distrub", words)

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
        self.assertEqual([row["id"] for row in rows[84:]], [str(index) for index in range(97, 138)])
        self.assertTrue(MSFC_PATH.read_bytes().startswith(b"\xef\xbb\xbf"))

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

        self.assertEqual(len(appended_rows), 41)
        self.assertNotIn("individual", msfc_words)
        self.assertEqual(appended_duplicates, {})


if __name__ == "__main__":
    unittest.main()
