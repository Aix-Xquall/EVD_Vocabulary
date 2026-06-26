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

    def test_daily_workflow_can_configure_google_tts_provider(self):
        workflow = (PROJECT_DIR / ".github" / "workflows" / "daily-vocabulary.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("GOOGLE_TTS_CREDENTIALS_JSON: ${{ secrets.GOOGLE_TTS_CREDENTIALS_JSON }}", workflow)
        self.assertIn("GOOGLE_APPLICATION_CREDENTIALS=${credentials_path}", workflow)
        self.assertIn("EVD_TTS_PROVIDER: ${{ vars.EVD_TTS_PROVIDER || 'azure' }}", workflow)
        self.assertIn("GOOGLE_ENGLISH_VOICE: ${{ vars.GOOGLE_ENGLISH_VOICE || 'en-US-Neural2-J' }}", workflow)
        self.assertIn("GOOGLE_CHINESE_VOICE: ${{ vars.GOOGLE_CHINESE_VOICE || 'cmn-TW-Wavenet-A' }}", workflow)

    def test_daily_workflow_passes_hard_words_sync_settings(self):
        workflow = (PROJECT_DIR / ".github" / "workflows" / "daily-vocabulary.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("HARD_WORDS_SHEET_CSV_URL: ${{ secrets.HARD_WORDS_SHEET_CSV_URL }}", workflow)
        self.assertIn("HARD_WORDS_READ_TOKEN: ${{ secrets.HARD_WORDS_READ_TOKEN }}", workflow)
        self.assertIn("HARD_WORDS_WRITE_URL: ${{ secrets.HARD_WORDS_WRITE_URL }}", workflow)

    def test_hard_words_dispatch_skips_line_notification(self):
        workflow = (PROJECT_DIR / ".github" / "workflows" / "daily-vocabulary.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("skip_line_notification:", workflow)
        self.assertIn("default: true", workflow)
        self.assertIn('"${{ github.event_name }}" == "schedule"', workflow)
        self.assertIn('inputs.skip_line_notification }}" != "true"', workflow)
        self.assertIn("python main.py --skip-line", workflow)

    def test_push_workflow_skips_daily_generation_for_static_site_changes(self):
        workflow = (PROJECT_DIR / ".github" / "workflows" / "daily-vocabulary.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("id: scope", workflow)
        self.assertIn('- "apps_script/**"', workflow)
        self.assertIn('- "README.md"', workflow)
        self.assertIn('changed_files="$(git diff --name-only HEAD^ HEAD || true)"', workflow)
        self.assertIn('echo "should_generate=${should_generate}" >> "$GITHUB_OUTPUT"', workflow)
        self.assertIn("if: ${{ steps.scope.outputs.should_generate == 'true' }}", workflow)
        self.assertIn("if: ${{ steps.scope.outputs.should_generate != 'true' }}", workflow)
        self.assertIn("cp web/index.html output/index.html", workflow)
        self.assertIn("cp web/app.js output/app.js", workflow)
        self.assertIn("cp web/styles.css output/styles.css", workflow)

    def test_generated_file_commit_rebases_before_pushing(self):
        workflow = (PROJECT_DIR / ".github" / "workflows" / "daily-vocabulary.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("git pull --rebase origin main", workflow)
        self.assertIn("git push", workflow)


if __name__ == "__main__":
    unittest.main()
