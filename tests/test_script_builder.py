import unittest
from datetime import date

from script_builder import audio_key_for_entry, build_daily_payload, build_markdown


def sample_entry():
    return {
        "id": "1",
        "word": "impedance",
        "pronunciation": "/ɪmˈpiːdəns/",
        "chinese_meaning": "阻抗",
        "example_1_en": "The impedance must be controlled.",
        "example_1_zh": "阻抗必須被控制。",
        "example_2_en": "Cable impedance affects signal integrity.",
        "example_2_zh": "電纜阻抗會影響訊號完整性。",
        "category": "EMC",
        "difficulty": "4",
        "review_count": "0",
        "last_review_date": "",
    }


class ScriptBuilderTests(unittest.TestCase):
    def test_build_markdown_contains_daily_learning_script(self):
        markdown = build_markdown([sample_entry()], date(2026, 6, 17))

        self.assertIn("# Daily Vocabulary - 2026-06-17", markdown)
        self.assertIn("## 1. impedance", markdown)
        self.assertIn("**Pronunciation:** /ɪmˈpiːdəns/", markdown)
        self.assertIn("The impedance must be controlled.", markdown)
        self.assertIn("阻抗必須被控制。", markdown)

    def test_build_daily_payload_contains_audio_paths_and_words(self):
        payload = build_daily_payload(
            [sample_entry()],
            date(2026, 6, 17),
            per_word_audio={"1": "output/audio/2026-06-17/001_impedance.mp3"},
            combined_audio="output/audio/2026-06-17_daily_vocabulary.mp3",
        )

        self.assertEqual(payload["date"], "2026-06-17")
        self.assertEqual(payload["combined_audio"], "output/audio/2026-06-17_daily_vocabulary.mp3")
        self.assertEqual(payload["words"][0]["word"], "impedance")
        self.assertEqual(payload["words"][0]["audio"], "output/audio/2026-06-17/001_impedance.mp3")

    def test_build_daily_payload_handles_duplicate_ids_from_different_files(self):
        first = sample_entry()
        first["_source_file"] = "a.csv"
        first["_row_number"] = 1
        second = sample_entry()
        second["_source_file"] = "b.csv"
        second["_row_number"] = 1
        second["word"] = "coupling"

        payload = build_daily_payload(
            [first, second],
            date(2026, 6, 17),
            per_word_audio={
                audio_key_for_entry(first): "output/audio/2026-06-17/001_impedance.mp3",
                audio_key_for_entry(second): "output/audio/2026-06-17/002_coupling.mp3",
            },
            combined_audio="output/audio/2026-06-17_daily_vocabulary.mp3",
        )

        self.assertEqual(payload["words"][0]["audio"], "output/audio/2026-06-17/001_impedance.mp3")
        self.assertEqual(payload["words"][1]["audio"], "output/audio/2026-06-17/002_coupling.mp3")


if __name__ == "__main__":
    unittest.main()
