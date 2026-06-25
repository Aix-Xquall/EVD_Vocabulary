import csv
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from hard_words_sync import (
    HARD_WORDS_FILENAME,
    filter_hard_word_rows,
    sync_hard_words,
    sync_hard_words_from_csv_text,
)


HEADER = (
    "id,word,pronunciation,chinese_meaning,example_1_en,example_1_zh,"
    "example_2_en,example_2_zh,category,difficulty,review_count,last_review_date,"
    "source_chapter,source_id,added_at,status,note\n"
)


class HardWordsSyncTests(unittest.TestCase):
    def test_filter_hard_word_rows_keeps_active_rows_and_deduplicates_words(self):
        rows = list(
            csv.DictReader(
                (
                    HEADER
                    + "1,EMS,/ems/,EMS 測試,Example one,例句一,Example two,例句二,EMC,4,0,,chapter,1,2026-06-24,active,\n"
                    + "2,EMS,/ems/,duplicate,Example one,例句一,Example two,例句二,EMC,4,0,,chapter,1,2026-06-24,active,\n"
                    + "3,EMC,/emc/,removed,Example one,例句一,Example two,例句二,EMC,4,0,,chapter,2,2026-06-24,removed,\n"
                    + "4,E3,/e3/,blank status,Example one,例句一,Example two,例句二,EMC,4,0,,chapter,3,2026-06-24,,\n"
                ).splitlines()
            )
        )

        filtered = filter_hard_word_rows(rows)

        self.assertEqual([row["word"] for row in filtered], ["EMS", "E3"])

    def test_sync_hard_words_from_csv_text_writes_snapshot_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vocabulary_dir = Path(temp_dir)
            csv_text = (
                HEADER
                + "1,EMS,/ems/,EMS 測試,Example one,例句一,Example two,例句二,EMC,4,0,,chapter,1,2026-06-24,active,\n"
            )

            result = sync_hard_words_from_csv_text(csv_text, vocabulary_dir)

            snapshot = vocabulary_dir / HARD_WORDS_FILENAME
            self.assertEqual(result.row_count, 1)
            self.assertEqual(result.path, snapshot)
            self.assertTrue(snapshot.exists())
            written_rows = list(csv.DictReader(snapshot.read_text(encoding="utf-8-sig").splitlines()))
            self.assertEqual(written_rows[0]["word"], "EMS")
            self.assertEqual(written_rows[0]["status"], "active")

    def test_sync_hard_words_from_csv_text_rejects_non_vocabulary_csv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                sync_hard_words_from_csv_text("ok,error\nfalse,Invalid read token.\n", temp_dir)

    def test_sync_hard_words_keeps_existing_snapshot_when_remote_is_invalid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vocabulary_dir = Path(temp_dir)
            snapshot = vocabulary_dir / HARD_WORDS_FILENAME
            snapshot.write_text(
                HEADER
                + "1,EMS,/ems/,EMS 皜祈岫,Example one,靘銝,Example two,靘鈭?EMC,4,0,,chapter,1,2026-06-24,active,\n",
                encoding="utf-8-sig",
            )

            settings = SimpleNamespace(
                hard_words_sheet_csv_url="file-does-not-exist",
                hard_words_read_token="",
                vocabulary_dir=vocabulary_dir,
            )

            result = sync_hard_words(settings)

            self.assertEqual(result.row_count, 1)
            self.assertFalse(result.used_remote)
            self.assertIn("EMS", snapshot.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
