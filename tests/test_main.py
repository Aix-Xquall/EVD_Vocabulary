import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from config import Settings
from main import run_daily_generation


class MainWorkflowTests(unittest.TestCase):
    def test_line_notification_failure_does_not_block_daily_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            vocabulary_path = workspace / "vocabulary.csv"
            output_dir = workspace / "output"
            _write_vocabulary(vocabulary_path)
            settings = Settings(
                vocabulary_dir=workspace,
                output_dir=output_dir,
                daily_word_count=1,
                generate_audio=False,
                line_channel_access_token="bad-token",
                line_user_id="user-id",
            )

            with patch("main.send_daily_line_notification", side_effect=RuntimeError("401 Unauthorized")):
                result = run_daily_generation(
                    settings=settings,
                    target_date=date(2026, 6, 17),
                    update_review=False,
                    notify_line=True,
                )

            self.assertEqual(result["date"], "2026-06-17")
            self.assertTrue((output_dir / "scripts" / "2026-06-17_daily_vocabulary.md").exists())
            self.assertTrue((output_dir / "data" / "2026-06-17_daily_vocabulary.json").exists())
            self.assertTrue((output_dir / "data" / "latest.json").exists())

    def test_daily_generation_publishes_all_csv_files_as_chapters(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            output_dir = workspace / "output"
            _write_vocabulary(workspace / "chapter-a.csv", word="impedance")
            _write_vocabulary(workspace / "chapter-b.csv", word="coupling")
            settings = Settings(
                vocabulary_dir=workspace,
                output_dir=output_dir,
                daily_word_count=1,
                generate_audio=False,
            )

            result = run_daily_generation(
                settings=settings,
                target_date=date(2026, 6, 17),
                update_review=False,
                notify_line=False,
            )

            payload = json.loads((output_dir / "data" / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(result["word_count"], 2)
            self.assertEqual(payload["mode"], "chapters")
            self.assertEqual([chapter["title"] for chapter in payload["chapters"]], ["chapter-a", "chapter-b"])
            self.assertEqual([chapter["word_count"] for chapter in payload["chapters"]], [1, 1])


def _write_vocabulary(path: Path, word: str = "impedance") -> None:
    fieldnames = [
        "id",
        "word",
        "pronunciation",
        "chinese_meaning",
        "example_1_en",
        "example_1_zh",
        "example_2_en",
        "example_2_zh",
        "category",
        "difficulty",
        "review_count",
        "last_review_date",
    ]
    row = {
        "id": "1",
        "word": word,
        "pronunciation": "/im-PEE-dance/",
        "chinese_meaning": "阻抗",
        "example_1_en": "The impedance must be controlled.",
        "example_1_zh": "阻抗必須受控。",
        "example_2_en": "Cable impedance affects signal integrity.",
        "example_2_zh": "線纜阻抗會影響訊號完整性。",
        "category": "EMC",
        "difficulty": "5",
        "review_count": "0",
        "last_review_date": "",
    }
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)


if __name__ == "__main__":
    unittest.main()
