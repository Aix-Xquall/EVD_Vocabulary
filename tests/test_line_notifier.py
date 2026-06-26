import json
import unittest
from unittest.mock import patch

from config import Settings
from line_notifier import (
    build_daily_line_message,
    fetch_line_quota_summary,
)


class FakeResponse:
    def __init__(self, body: dict, status: int = 200):
        self.body = body
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.body).encode("utf-8")


class LineNotifierTests(unittest.TestCase):
    def test_message_contains_learning_delta_quotas_and_site_link(self):
        settings = Settings(
            site_url="https://example.test/",
            google_tts_free_remaining="900000 characters",
            azure_speech_free_remaining="45000 characters",
        )

        message = build_daily_line_message(
            settings,
            {
                "new_word_count": 3,
                "new_chapter_names": ["EMC chapter", "Composite chapter"],
                "line_quota_remaining": "剩餘 199 則 / 上限 200 則",
            },
        )

        self.assertIn("新增單字量：3", message)
        self.assertIn("新增章節名稱：EMC chapter, Composite chapter", message)
        self.assertIn("Cloud TTS剩餘量： 900000 characters", message)
        self.assertIn("Azure Free F0 剩餘量： 45000 characters", message)
        self.assertIn("LINE 通知剩餘量：剩餘 199 則 / 上限 200 則", message)
        self.assertIn("網站連結：https://example.test/", message)

    def test_line_quota_summary_uses_line_api_quota_and_consumption(self):
        settings = Settings(
            line_channel_access_token="token",
            line_user_id="user",
        )
        responses = [
            FakeResponse({"type": "limited", "value": 200}),
            FakeResponse({"totalUsage": 1}),
        ]

        with patch("line_notifier.urllib.request.urlopen", side_effect=responses):
            summary = fetch_line_quota_summary(settings)

        self.assertEqual(summary, "剩餘 199 則 / 上限 200 則")


if __name__ == "__main__":
    unittest.main()
