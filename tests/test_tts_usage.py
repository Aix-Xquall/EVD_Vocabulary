import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from config import Settings
from tts_usage import (
    build_azure_tts_quota_summary,
    build_google_tts_quota_summary,
    record_tts_synthesis_usage,
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


class TtsUsageTests(unittest.TestCase):
    def test_record_tts_synthesis_usage_accumulates_monthly_provider_characters(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(output_dir=Path(temp_dir))

            record_tts_synthesis_usage(settings, "google", 12, date(2026, 6, 26))
            record_tts_synthesis_usage(settings, "google", 8, date(2026, 6, 26))
            record_tts_synthesis_usage(settings, "azure", 5, date(2026, 6, 26))

            payload = json.loads(
                (Path(temp_dir) / "data" / "tts_usage.json").read_text(encoding="utf-8")
            )

        self.assertEqual(payload["months"]["2026-06"]["providers"]["google"]["characters"], 20)
        self.assertEqual(payload["months"]["2026-06"]["providers"]["azure"]["characters"], 5)

    def test_google_quota_summary_uses_tracked_monthly_usage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(output_dir=Path(temp_dir))
            record_tts_synthesis_usage(settings, "google", 1234, date(2026, 6, 26))

            summary = build_google_tts_quota_summary(settings, date(2026, 6, 26))

        self.assertEqual(summary, "998,766 字元 / 額度 1,000,000 字元")

    def test_azure_quota_summary_queries_monitor_metrics_when_configured(self):
        settings = Settings(
            azure_tenant_id="tenant",
            azure_client_id="client",
            azure_client_secret="secret",
            azure_subscription_id="sub",
            azure_speech_resource_group="rg",
            azure_speech_resource_name="speech",
        )
        responses = [
            FakeResponse({"access_token": "token"}),
            FakeResponse(
                {
                    "value": [
                        {
                            "name": {"value": "SynthesizedCharacters"},
                            "timeseries": [
                                {
                                    "data": [
                                        {"total": 1200},
                                        {"total": 300},
                                    ]
                                }
                            ],
                        }
                    ]
                }
            ),
        ]

        with patch("tts_usage.urllib.request.urlopen", side_effect=responses):
            summary = build_azure_tts_quota_summary(settings, date(2026, 6, 26))

        self.assertEqual(summary, "498,500 字元 / 額度 500,000 字元")


if __name__ == "__main__":
    unittest.main()
