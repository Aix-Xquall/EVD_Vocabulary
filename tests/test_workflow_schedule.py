from pathlib import Path
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]


class WorkflowScheduleTests(unittest.TestCase):
    def test_daily_workflow_runs_at_0630_taipei_time(self):
        workflow = (PROJECT_DIR / ".github" / "workflows" / "daily-vocabulary.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn('cron: "30 22 * * *"', workflow)


if __name__ == "__main__":
    unittest.main()
