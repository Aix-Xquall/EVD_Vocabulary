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
        self.assertIn('EVD_MAX_AUDIO_SEGMENTS_PER_RUN: "0"', workflow)

    def test_daily_workflow_can_configure_google_tts_provider(self):
        workflow = (PROJECT_DIR / ".github" / "workflows" / "daily-vocabulary.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("GOOGLE_TTS_CREDENTIALS_JSON: ${{ secrets.GOOGLE_TTS_CREDENTIALS_JSON }}", workflow)
        self.assertIn("GOOGLE_APPLICATION_CREDENTIALS=${credentials_path}", workflow)
        self.assertIn("EVD_TTS_PROVIDER: ${{ vars.EVD_TTS_PROVIDER || 'google' }}", workflow)
        self.assertIn("GOOGLE_ENGLISH_VOICE: ${{ vars.GOOGLE_ENGLISH_VOICE || 'en-US-Neural2-F' }}", workflow)
        self.assertIn("GOOGLE_CHINESE_VOICE: ${{ vars.GOOGLE_CHINESE_VOICE || 'cmn-TW-Wavenet-A' }}", workflow)
        self.assertIn("GOOGLE_CLOUD_PROJECT_ID: ${{ vars.GOOGLE_CLOUD_PROJECT_ID || vars.GOOGLE_CLOUD_PROJECT }}", workflow)
        self.assertIn("GOOGLE_TTS_QUOTA_METRIC: ${{ vars.GOOGLE_TTS_QUOTA_METRIC || 'texttospeech.googleapis.com/characters' }}", workflow)
        self.assertIn("EVD_GOOGLE_TTS_FREE_REMAINING: ${{ vars.EVD_GOOGLE_TTS_FREE_REMAINING }}", workflow)
        self.assertIn("EVD_AZURE_SPEECH_FREE_REMAINING: ${{ vars.EVD_AZURE_SPEECH_FREE_REMAINING }}", workflow)
        self.assertIn("AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}", workflow)
        self.assertIn("AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}", workflow)
        self.assertIn("AZURE_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}", workflow)
        self.assertIn("AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}", workflow)
        self.assertIn("AZURE_SPEECH_RESOURCE_GROUP: ${{ secrets.AZURE_SPEECH_RESOURCE_GROUP }}", workflow)
        self.assertIn("AZURE_SPEECH_RESOURCE_NAME: ${{ secrets.AZURE_SPEECH_RESOURCE_NAME }}", workflow)

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

    def test_manual_workflow_can_force_completion_line_notification(self):
        workflow = (PROJECT_DIR / ".github" / "workflows" / "daily-vocabulary.yml").read_text(
            encoding="utf-8"
        )
        smoke_workflow = (PROJECT_DIR / ".github" / "workflows" / "line-smoke-test.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("force_line_notification:", workflow)
        self.assertIn("inputs.force_line_notification", workflow)
        self.assertIn("python main.py --force-line", workflow)
        self.assertIn("python main.py --skip-audio --no-update-review --force-line", smoke_workflow)

    def test_push_workflow_skips_daily_generation_for_static_site_changes(self):
        workflow = (PROJECT_DIR / ".github" / "workflows" / "daily-vocabulary.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("id: scope", workflow)
        self.assertIn('- "apps_script/**"', workflow)
        self.assertIn('- "README.md"', workflow)
        self.assertIn(
            'changed_files="$(git -c core.quotepath=false diff --name-only HEAD^ HEAD || true)"',
            workflow,
        )
        self.assertIn('echo "should_generate=${should_generate}" >> "$GITHUB_OUTPUT"', workflow)
        self.assertIn("if: ${{ steps.scope.outputs.should_generate == 'true' }}", workflow)
        self.assertIn("if: ${{ steps.scope.outputs.should_generate != 'true' }}", workflow)
        self.assertIn("cp web/index.html output/index.html", workflow)
        self.assertIn("cp web/app.js output/app.js", workflow)
        self.assertIn("cp web/styles.css output/styles.css", workflow)

    def test_push_scope_detection_preserves_unicode_file_paths(self):
        workflow = (PROJECT_DIR / ".github" / "workflows" / "daily-vocabulary.yml").read_text(
            encoding="utf-8"
        )

        self.assertEqual(
            workflow.count("git -c core.quotepath=false diff --name-only"),
            2,
        )

    def test_generated_file_commit_rebases_before_pushing(self):
        workflow = (PROJECT_DIR / ".github" / "workflows" / "daily-vocabulary.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("git pull --rebase origin main", workflow)
        self.assertIn("git push", workflow)

    def test_line_smoke_workflow_sends_current_notification_format(self):
        workflow = (PROJECT_DIR / ".github" / "workflows" / "line-smoke-test.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("uses: actions/checkout@v4", workflow)
        self.assertIn("EVD_GOOGLE_TTS_FREE_REMAINING: ${{ vars.EVD_GOOGLE_TTS_FREE_REMAINING }}", workflow)
        self.assertIn("EVD_AZURE_SPEECH_FREE_REMAINING: ${{ vars.EVD_AZURE_SPEECH_FREE_REMAINING }}", workflow)
        self.assertIn("AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}", workflow)
        self.assertIn("AZURE_SPEECH_RESOURCE_NAME: ${{ secrets.AZURE_SPEECH_RESOURCE_NAME }}", workflow)
        self.assertIn("python main.py --skip-audio --no-update-review --force-line", workflow)
        self.assertNotIn("  push:", workflow)


if __name__ == "__main__":
    unittest.main()
