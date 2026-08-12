from pathlib import Path
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]


class AppsScriptTests(unittest.TestCase):
    def test_hard_words_apps_script_dispatches_daily_workflow_after_sheet_write(self):
        script = (PROJECT_DIR / "apps_script" / "hard_words_web_app.gs").read_text(
            encoding="utf-8"
        )

        self.assertIn("function doPost(e)", script)
        self.assertIn("function doGet(e)", script)
        self.assertIn("function readPostPayload(e)", script)
        self.assertIn("HARD_WORDS_READ_TOKEN", script)
        self.assertIn("sheetToCsv(sheet)", script)
        self.assertIn("ContentService.MimeType.CSV", script)
        self.assertIn("if (!e || !e.postData || !e.postData.contents)", script)
        self.assertIn("Missing POST body", script)
        self.assertIn("function testTriggerDailyVocabularyWorkflow()", script)
        self.assertIn("sheet.appendRow(row)", script)
        self.assertIn("triggerDailyVocabularyWorkflow(true)", script)
        self.assertIn("triggerDailyVocabularyWorkflow(false)", script)
        self.assertIn("UrlFetchApp.fetch(url, options)", script)
        self.assertIn("/actions/workflows/", script)
        self.assertIn("/dispatches", script)
        self.assertIn("skip_line_notification", script)
        self.assertIn('Authorization": `Bearer ${token}`', script)
        self.assertIn("PropertiesService.getScriptProperties()", script)
        self.assertIn('GITHUB_TOKEN', script)
        self.assertIn('GITHUB_OWNER', script)
        self.assertIn('GITHUB_REPO', script)
        self.assertIn('GITHUB_WORKFLOW_FILE', script)
        self.assertIn('GITHUB_REF', script)

    def test_apps_script_supports_direct_important_example_and_state_sync(self):
        script = (PROJECT_DIR / "apps_script" / "hard_words_web_app.gs").read_text(
            encoding="utf-8"
        )

        self.assertIn('IMPORTANT_EXAMPLES_SHEET_NAME = "ImportantExamples"', script)
        self.assertIn('payload.action === "important_example"', script)
        self.assertIn('action === "client_state"', script)
        self.assertIn("function upsertImportantExample(payload)", script)
        self.assertIn("LockService.getScriptLock()", script)
        self.assertIn("function buildClientState()", script)
        self.assertIn("api_version: 2", script)
        self.assertIn("function javascriptResponse(value, callback)", script)
        self.assertIn("function mergePracticeStateNote", script)
        self.assertIn('payload.status !== PRACTICE_STATS_STATUS', script)

    def test_readme_documents_github_actions_trigger_properties(self):
        readme = (PROJECT_DIR / "README.md").read_text(encoding="utf-8")

        self.assertIn("apps_script/hard_words_web_app.gs", readme)
        self.assertIn("GITHUB_TOKEN", readme)
        self.assertIn("GITHUB_OWNER", readme)
        self.assertIn("GITHUB_REPO", readme)
        self.assertIn("GITHUB_WORKFLOW_FILE", readme)
        self.assertIn("GITHUB_REF", readme)
        self.assertIn("Actions: Read and write", readme)


if __name__ == "__main__":
    unittest.main()
