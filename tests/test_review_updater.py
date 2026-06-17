import tempfile
import unittest
from datetime import date
from pathlib import Path

from review_updater import update_review_files
from vocabulary_loader import load_vocabulary


def write_csv(path: Path) -> None:
    path.write_text(
        "id,word,pronunciation,chinese_meaning,example_1_en,example_1_zh,"
        "example_2_en,example_2_zh,category,difficulty,review_count,last_review_date\n"
        "1,impedance,/im/,阻抗,Example one,例句一,Example two,例句二,EMC,4,0,\n"
        "2,coupling,/cup/,耦合,Example one,例句一,Example two,例句二,EMC,3,2,2026-06-01\n",
        encoding="utf-8",
    )


class ReviewUpdaterTests(unittest.TestCase):
    def test_update_review_files_updates_only_selected_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            csv_path = tmp_path / "words.csv"
            write_csv(csv_path)
            entries = load_vocabulary(tmp_path)
            selected = [entries[0]]

            update_review_files(selected, review_date=date(2026, 6, 17))

            updated = load_vocabulary(tmp_path)
            impedance = next(row for row in updated if row["word"] == "impedance")
            coupling = next(row for row in updated if row["word"] == "coupling")

            self.assertEqual(impedance["review_count"], "1")
            self.assertEqual(impedance["last_review_date"], "2026-06-17")
            self.assertEqual(coupling["review_count"], "2")
            self.assertEqual(coupling["last_review_date"], "2026-06-01")


if __name__ == "__main__":
    unittest.main()
