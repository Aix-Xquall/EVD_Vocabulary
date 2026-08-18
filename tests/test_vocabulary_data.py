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


def normalized_word_key(word: str) -> str:
    """Ignore case, spaces, and punctuation when checking duplicate terms."""
    return re.sub(r"[^a-z0-9]+", "", str(word or "").strip().casefold())


class VocabularyDataTests(unittest.TestCase):
    def test_formal_chapters_have_no_duplicate_words(self):
        seen = {}
        duplicates = []
        row_count = 0

        for path in sorted(VOCABULARY_DIR.glob("*.csv")):
            if path.name == "hard_words.csv":
                continue
            for row in read_rows(path):
                row_count += 1
                word_key = normalized_word_key(row.get("word") or "")
                if word_key in seen:
                    duplicates.append((row["word"], seen[word_key], path.name))
                else:
                    seen[word_key] = path.name

        self.assertEqual(row_count, 663)
        self.assertEqual(duplicates, [])

    def test_all_formal_examples_have_chinese_translations(self):
        missing = []
        untranslated_terms = []
        target_pattern = re.compile(
            r"\b(?:bond|bonding|shock mounts?|shield|shielding)\b",
            re.IGNORECASE,
        )
        for path in sorted(VOCABULARY_DIR.glob("*.csv")):
            if path.name == "hard_words.csv":
                continue
            for row in read_rows(path):
                for example_number in (1, 2):
                    translation = str(row.get(f"example_{example_number}_zh") or "").strip()
                    if not translation:
                        missing.append((path.name, row["id"], example_number))
                    if target_pattern.search(translation):
                        untranslated_terms.append(
                            (path.name, row["id"], example_number, translation)
                        )

        self.assertEqual(missing, [])
        self.assertEqual(untranslated_terms, [])

    def test_shock_mount_example_uses_aerospace_chinese_translation(self):
        rows = read_rows(MSFC_PATH)
        row = next(row for row in rows if row["word"] == "realistically")

        self.assertIn("shock mounts", row["example_1_en"])
        self.assertIn("隔振座", row["example_1_zh"])
        self.assertIn("RF 搭接", row["example_1_zh"])

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

    def test_rf_transmit_terms_use_compact_letter_name_pronunciation(self):
        rows = {row["word"]: row for row in read_rows(CONSULTANT_PATH)}

        self.assertEqual(
            rows["RF transmit mode"]["pronunciation"].split("|", 1)[0].strip(),
            "/ɑːr ef trænzˈmɪt moʊd/",
        )
        self.assertEqual(
            rows["RF transmit inhibit"]["pronunciation"].split("|", 1)[0].strip(),
            "/ɑːr ef trænzˈmɪt ɪnˈhɪbɪt/",
        )

    def test_msfc_chapter_preserves_ids_after_moving_foundational_terms(self):
        with MSFC_PATH.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            rows = list(reader)

        self.assertEqual(reader.fieldnames, REQUIRED_COLUMNS)
        self.assertEqual(len(rows), 118)
        missing_existing_ids = {2, 3, 17, 18, 31, 32, 35, 57, 67, 68, 69, 74, 81, 82, 90}
        moved_ids = {19, 20, 21, 22}
        expected_ids = {
            str(index)
            for index in range(1, 138)
            if index not in missing_existing_ids | moved_ids
        }
        self.assertEqual({row["id"] for row in rows}, expected_ids)
        self.assertEqual(len({row["id"] for row in rows}), len(rows))
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
        rows_by_word = {row["word"]: row for row in rows}
        new_rows = [rows_by_word[word] for word in expected_words]

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
        appended_rows = [row for row in msfc_rows if int(row["id"]) >= 97]
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

    def test_electrical_foundations_precede_derived_terms(self):
        emc_rows = read_rows(EMC_ONE_PATH)
        emc_words = [row["word"] for row in emc_rows]
        msfc_words = {row["word"] for row in read_rows(MSFC_PATH)}
        foundational_words = {
            "resistance",
            "inductance",
            "capacitance",
            "reactance",
            "impedance",
            "coupling",
        }

        self.assertTrue(foundational_words.issubset(emc_words))
        self.assertTrue(foundational_words.isdisjoint(msfc_words))
        self.assertLess(emc_words.index("impedance"), emc_words.index("low-impedance path"))
        self.assertLess(emc_words.index("resistance"), emc_words.index("bonding resistance"))


if __name__ == "__main__":
    unittest.main()
