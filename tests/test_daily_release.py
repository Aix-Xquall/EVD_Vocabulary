import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from daily_release import STATE_FILENAME, apply_daily_release


def entry(word: str, source: str) -> dict:
    return {"word": word, "_source_file": source, "id": word}


class DailyReleaseTests(unittest.TestCase):
    def test_first_run_retains_previous_words_and_releases_daily_limit(self):
        entries = [
            entry("existing", "MSFC-HDBK-3697_01_scope.csv"),
            entry("new one", "MSFC-HDBK-3697_01_scope.csv"),
            entry("new two", "MSFC-HDBK-3697_02_design.csv"),
            entry("other", "other.csv"),
        ]
        previous = {
            "chapters": [
                {"title": "old", "words": [{"word": "existing"}]},
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            result = apply_daily_release(
                entries, previous, Path(temp_dir), date(2026, 9, 21), 1
            )

            self.assertEqual([item["word"] for item in result.released_today], ["new one"])
            self.assertEqual(
                [item["word"] for item in result.entries],
                ["existing", "new one", "other"],
            )
            self.assertEqual(result.new_word_keys, {"new one"})
            state = json.loads((Path(temp_dir) / "data" / STATE_FILENAME).read_text())
            self.assertEqual(state["version"], 2)
            self.assertEqual(state["released_at"], {"new one": "2026-09-21"})

    def test_same_date_does_not_release_a_second_batch(self):
        entries = [
            entry("one", "MSFC-HDBK-3697_01_scope.csv"),
            entry("two", "MSFC-HDBK-3697_01_scope.csv"),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            first = apply_daily_release(entries, None, output_dir, date(2026, 9, 21), 1)
            second = apply_daily_release(entries, None, output_dir, date(2026, 9, 21), 1)

            self.assertEqual(len(first.released_today), 1)
            self.assertEqual(second.released_today, [])
            self.assertEqual([item["word"] for item in second.entries], ["one"])
            self.assertEqual(second.new_word_keys, {"one"})

    def test_version_one_latest_batch_remains_marked_as_new_after_upgrade(self):
        entries = [
            entry("old", "MSFC-HDBK-3697_01_scope.csv"),
            entry("latest", "MSFC-HDBK-3697_01_scope.csv"),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            state_path = output_dir / "data" / STATE_FILENAME
            state_path.parent.mkdir(parents=True)
            state_path.write_text(json.dumps({
                "version": 1,
                "last_release_date": "2026-09-22",
                "released_words": ["old", "latest"],
                "released_today": ["latest"],
            }))

            result = apply_daily_release(
                entries, None, output_dir, date(2026, 9, 22), 10
            )

            self.assertEqual(result.new_word_keys, {"latest"})

    def test_next_date_continues_in_file_and_row_order(self):
        entries = [
            entry("one", "MSFC-HDBK-3697_01_scope.csv"),
            entry("two", "MSFC-HDBK-3697_01_scope.csv"),
            entry("three", "MSFC-HDBK-3697_02_design.csv"),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            apply_daily_release(entries, None, output_dir, date(2026, 9, 21), 2)
            result = apply_daily_release(entries, None, output_dir, date(2026, 9, 22), 2)

            self.assertEqual([item["word"] for item in result.released_today], ["three"])
            state = json.loads((output_dir / "data" / STATE_FILENAME).read_text())
            self.assertEqual(state["last_release_date"], "2026-09-22")

    def test_daily_batch_continues_into_the_next_chapter(self):
        entries = [
            *[
                entry(f"chapter one {index}", "MSFC-HDBK-3697_01_scope.csv")
                for index in range(1, 5)
            ],
            *[
                entry(f"chapter four {index}", "MSFC-HDBK-3697_04_design.csv")
                for index in range(1, 8)
            ],
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            result = apply_daily_release(
                entries, None, Path(temp_dir), date(2026, 9, 21), 10
            )

            self.assertEqual(len(result.released_today), 10)
            self.assertEqual(
                [item["word"] for item in result.released_today[:4]],
                [f"chapter one {index}" for index in range(1, 5)],
            )
            self.assertEqual(
                [item["word"] for item in result.released_today[4:]],
                [f"chapter four {index}" for index in range(1, 7)],
            )

    def test_hard_word_snapshot_does_not_seed_formal_release(self):
        entries = [entry("hard only", "MSFC-HDBK-3697_01_scope.csv")]
        previous = {
            "chapters": [
                {
                    "title": "hard words",
                    "is_hard_words": True,
                    "words": [{"word": "hard only"}],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            result = apply_daily_release(
                entries, previous, Path(temp_dir), date(2026, 9, 21), 1
            )

            self.assertEqual([item["word"] for item in result.released_today], ["hard only"])

    def test_sync_only_run_does_not_release_or_consume_the_date(self):
        entries = [entry("one", "MSFC-HDBK-3697_01_scope.csv")]
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            sync_result = apply_daily_release(
                entries,
                None,
                output_dir,
                date(2026, 9, 21),
                1,
                release_new_words=False,
            )
            release_result = apply_daily_release(
                entries, None, output_dir, date(2026, 9, 21), 1
            )

            self.assertEqual(sync_result.released_today, [])
            self.assertEqual(sync_result.entries, [])
            self.assertEqual([item["word"] for item in release_result.released_today], ["one"])


if __name__ == "__main__":
    unittest.main()
