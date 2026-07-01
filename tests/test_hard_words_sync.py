import csv
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import hard_words_sync

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

    def test_sync_snapshot_preserves_mastered_and_removed_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_text = (
                HEADER
                + "1,EMS,/ems/,meaning,Example one,translation,Example two,translation,EMC,4,0,,chapter,1,2026-06-24,active,\n"
                + "2,EMC,/emc/,meaning,Example one,translation,Example two,translation,EMC,4,0,,chapter,2,2026-06-24,mastered,\n"
                + "3,E3,/e3/,meaning,Example one,translation,Example two,translation,EMC,4,0,,chapter,3,2026-06-24,removed,\n"
            )

            result = sync_hard_words_from_csv_text(csv_text, temp_dir)
            written_rows = list(
                csv.DictReader(result.path.read_text(encoding="utf-8-sig").splitlines())
            )

            self.assertEqual(result.row_count, 3)
            self.assertEqual(
                [row["status"] for row in written_rows],
                ["active", "mastered", "removed"],
            )

    def test_sync_snapshot_sorts_newest_rows_before_deduplication(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_text = (
                HEADER
                + "1,old word,/old/,old,Example,翻譯,Example,翻譯,EMC,2,0,,chapter,1,2026-06-01T08:00:00Z,active,\n"
                + "2,duplicate word,/old duplicate/,old duplicate,Example,翻譯,Example,翻譯,EMC,2,0,,chapter,2,2026-05-01T08:00:00Z,active,\n"
                + "3,undated word,/undated/,undated,Example,翻譯,Example,翻譯,EMC,2,0,,chapter,3,not-a-date,active,\n"
                + "4,new word,/new/,new,Example,翻譯,Example,翻譯,EMC,2,0,,chapter,4,2026-07-01T08:00:00Z,active,\n"
                + "5,duplicate word,/new duplicate/,new duplicate,Example,翻譯,Example,翻譯,EMC,2,0,,chapter,5,2026-07-02T08:00:00Z,active,\n"
            )

            result = sync_hard_words_from_csv_text(csv_text, temp_dir)
            written_rows = list(
                csv.DictReader(result.path.read_text(encoding="utf-8-sig").splitlines())
            )

            self.assertEqual(
                [row["word"] for row in written_rows],
                ["duplicate word", "new word", "old word", "undated word"],
            )
            self.assertEqual(written_rows[0]["chinese_meaning"], "new duplicate")

    def test_load_mastered_word_statuses_reads_cloud_snapshot_states(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot = Path(temp_dir) / HARD_WORDS_FILENAME
            snapshot.write_text(
                HEADER
                + "1,EMS,/ems/,meaning,Example one,translation,Example two,translation,EMC,4,0,,chapter,1,2026-06-24,mastered,\n"
                + "2,EMC,/emc/,meaning,Example one,translation,Example two,translation,EMC,4,0,,chapter,2,2026-06-24,mastered_active,\n"
                + "3,E3,/e3/,meaning,Example one,translation,Example two,translation,EMC,4,0,,chapter,3,2026-06-24,active,\n",
                encoding="utf-8-sig",
            )

            statuses = hard_words_sync.load_mastered_word_statuses(temp_dir)

            self.assertEqual(
                statuses,
                {"ems": "mastered", "emc": "mastered_active"},
            )

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

    def test_sync_hard_words_keeps_existing_snapshot_when_remote_text_is_not_csv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vocabulary_dir = Path(temp_dir)
            snapshot = vocabulary_dir / HARD_WORDS_FILENAME
            snapshot.write_text(
                HEADER
                + "1,EMS,/ems/,EMS 皜祈岫,Example one,靘銝,Example two,靘鈭?EMC,4,0,,chapter,1,2026-06-24,active,\n",
                encoding="utf-8-sig",
            )
            settings = SimpleNamespace(
                hard_words_sheet_csv_url="https://script.google.com/macros/s/example/exec",
                hard_words_read_token="",
                vocabulary_dir=vocabulary_dir,
            )

            with patch("hard_words_sync._fetch_csv_text", return_value="ok,error\nfalse,Invalid read token.\n"):
                result = sync_hard_words(settings)

            self.assertEqual(result.row_count, 1)
            self.assertFalse(result.used_remote)
            self.assertIn("EMS", snapshot.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
