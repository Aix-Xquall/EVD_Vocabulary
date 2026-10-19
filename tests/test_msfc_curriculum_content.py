import csv
from pathlib import Path
import re
import unittest


VOCABULARY_DIR = Path(__file__).resolve().parents[1] / "vocabulary"


class MsfcCurriculumContentTests(unittest.TestCase):
    def test_mating_flange_uses_flange_translation(self):
        path = VOCABULARY_DIR / "MSFC-HDBK-3697_05-1_接合方法.csv"
        with path.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
        mating_flange = next(row for row in rows if row["word"] == "mating flange")
        self.assertEqual("配合法蘭", mating_flange["chinese_meaning"])
        self.assertIn("配合法蘭", mating_flange["example_1_zh"])
        self.assertIn("配合法蘭", mating_flange["example_2_zh"])
        fasteners = next(row for row in rows if row["word"] == "multiple fasteners")
        self.assertIn("配合法蘭", fasteners["example_1_zh"])

    def test_connector_flange_translation_is_consistent(self):
        translations = []
        for path in VOCABULARY_DIR.glob("MSFC-HDBK-3697*.csv"):
            with path.open(encoding="utf-8-sig", newline="") as file:
                for row in csv.DictReader(file):
                    if row["word"] == "connector flange":
                        self.assertEqual(row["chinese_meaning"], "連接器法蘭")
                    for number in (1, 2):
                        if "connector flange" in row[f"example_{number}_en"].lower():
                            translations.append(row[f"example_{number}_zh"])
        self.assertTrue(translations)
        self.assertTrue(all("連接器法蘭" in text for text in translations))

    def test_msfc_examples_do_not_use_handbook_glossary_templates(self):
        for path in VOCABULARY_DIR.glob("MSFC-HDBK-3697*.csv"):
            with self.subTest(chapter=path.name), path.open(
                encoding="utf-8-sig", newline=""
            ) as file:
                for row in csv.DictReader(file):
                    for number in (1, 2):
                        example = row[f"example_{number}_en"].lower()
                        self.assertIsNone(re.search(r"\bthe handbook\b", example))
                        self.assertIsNone(re.search(r"\bthe term\b", example))

    def test_foundational_terms_precede_compounds(self):
        pairs = {
            "MSFC-HDBK-3697_04_接合設計.csv": [("protective device", "upstream protective device")],
            "MSFC-HDBK-3697_05-2_表面與腐蝕.csv": [("solvent", "chlorinated solvent")],
            "MSFC-HDBK-3697_05-3_特殊設備與複合材料.csv": [
                ("gasket", "conductive gasket"),
                ("conductive gasket", "resilient conductive gasket"),
                ("electrical", "alternate electrical path"),
            ],
            "MSFC-HDBK-3697_05-4_驗證.csv": [("workmanship", "workmanship resistance measurement")],
        }
        for filename, chapter_pairs in pairs.items():
            with (VOCABULARY_DIR / filename).open(encoding="utf-8-sig", newline="") as file:
                positions = {row["word"].casefold(): index for index, row in enumerate(csv.DictReader(file))}
            for foundational, compound in chapter_pairs:
                with self.subTest(chapter=filename, words=(foundational, compound)):
                    self.assertLess(positions[foundational], positions[compound])


if __name__ == "__main__":
    unittest.main()
