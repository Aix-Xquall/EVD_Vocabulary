import tempfile
import unittest
from pathlib import Path

from vocabulary_loader import REQUIRED_COLUMNS, load_vocabulary


def write_csv(path: Path, rows: str) -> None:
    path.write_text(
        "id,word,pronunciation,chinese_meaning,example_1_en,example_1_zh,"
        "example_2_en,example_2_zh,category,difficulty,review_count,last_review_date\n"
        + rows,
        encoding="utf-8",
    )


class VocabularyLoaderTests(unittest.TestCase):
    def test_load_vocabulary_reads_all_csv_files_and_tracks_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            write_csv(
                tmp_path / "a.csv",
                "1,impedance,/im/,阻抗,Example one,例句一,Example two,例句二,EMC,4,0,\n",
            )
            write_csv(
                tmp_path / "b.csv",
                "2,coupling,/cup/,耦合,Example one,例句一,Example two,例句二,EMC,3,2,2026-06-01\n",
            )
            (tmp_path / "ignore.txt").write_text("not csv", encoding="utf-8")

            entries = load_vocabulary(tmp_path)

            self.assertEqual([entry["word"] for entry in entries], ["impedance", "coupling"])
            self.assertTrue(all(entry["_source_file"].endswith(".csv") for entry in entries))
            self.assertTrue(all(entry["_row_number"] == 1 for entry in entries))

    def test_load_vocabulary_rejects_missing_required_columns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            (tmp_path / "bad.csv").write_text("id,word\n1,impedance\n", encoding="utf-8")

            with self.assertRaises(ValueError) as context:
                load_vocabulary(tmp_path)

            message = str(context.exception)
            self.assertIn("missing required columns", message)
            self.assertIn("pronunciation", message)
            self.assertGreaterEqual(set(REQUIRED_COLUMNS), {"id", "word", "difficulty"})


if __name__ == "__main__":
    unittest.main()
