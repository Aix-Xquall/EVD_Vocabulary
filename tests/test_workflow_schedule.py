from pathlib import Path
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]


class WorkflowScheduleTests(unittest.TestCase):
    def test_daily_workflow_runs_at_0630_taipei_time(self):
        workflow = (PROJECT_DIR / ".github" / "workflows" / "daily-vocabulary.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn('cron: "30 22 * * *"', workflow)

    def test_daily_workflow_generates_formal_english_audio_at_08x_rate(self):
        workflow = (PROJECT_DIR / ".github" / "workflows" / "daily-vocabulary.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn('EVD_SPEECH_RATE: "-20%"', workflow)
        self.assertIn('EVD_MAX_AUDIO_SEGMENTS_PER_RUN: "200"', workflow)

    def test_daily_workflow_passes_hard_words_sync_settings(self):
        workflow = (PROJECT_DIR / ".github" / "workflows" / "daily-vocabulary.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("HARD_WORDS_SHEET_CSV_URL: ${{ secrets.HARD_WORDS_SHEET_CSV_URL }}", workflow)
        self.assertIn("HARD_WORDS_READ_TOKEN: ${{ secrets.HARD_WORDS_READ_TOKEN }}", workflow)
        self.assertIn("HARD_WORDS_WRITE_URL: ${{ secrets.HARD_WORDS_WRITE_URL }}", workflow)


if __name__ == "__main__":
    unittest.main()
