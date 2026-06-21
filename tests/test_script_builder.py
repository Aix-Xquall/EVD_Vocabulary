import unittest
from datetime import date

from script_builder import (
    audio_key_for_entry,
    build_chapter_payload,
    build_daily_payload,
    build_markdown,
)


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
            per_word_audio={"1": "audio/2026-06-17/001_impedance.mp3"},
            combined_audio="audio/2026-06-17_daily_vocabulary.mp3",
        )

        self.assertEqual(payload["date"], "2026-06-17")
        self.assertEqual(payload["combined_audio"], "audio/2026-06-17_daily_vocabulary.mp3")
        self.assertEqual(payload["words"][0]["word"], "impedance")
        self.assertEqual(payload["words"][0]["audio"], "audio/2026-06-17/001_impedance.mp3")

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
                audio_key_for_entry(first): "audio/2026-06-17/001_impedance.mp3",
                audio_key_for_entry(second): "audio/2026-06-17/002_coupling.mp3",
            },
            combined_audio="audio/2026-06-17_daily_vocabulary.mp3",
        )

        self.assertEqual(payload["words"][0]["audio"], "audio/2026-06-17/001_impedance.mp3")
        self.assertEqual(payload["words"][1]["audio"], "audio/2026-06-17/002_coupling.mp3")

    def test_build_chapter_payload_groups_words_by_source_csv(self):
        first = sample_entry()
        first["_source_file"] = r"C:\workspace\chapter-a.csv"
        first["_row_number"] = 1
        second = sample_entry()
        second["_source_file"] = r"C:\workspace\chapter-b.csv"
        second["_row_number"] = 1
        second["word"] = "coupling"

        payload = build_chapter_payload(
            [first, second],
            date(2026, 6, 17),
            segment_audio={
                audio_key_for_entry(first): {
                    "word": {"src": "audio/segments/en/word.mp3", "language": "en"},
                    "meaning": {"src": "audio/segments/zh/meaning.mp3", "language": "zh"},
                },
                audio_key_for_entry(second): {
                    "word": {"src": "audio/segments/en/coupling.mp3", "language": "en"},
                },
            },
        )

        self.assertEqual(payload["mode"], "chapters")
        self.assertEqual([chapter["title"] for chapter in payload["chapters"]], ["chapter-a", "chapter-b"])
        self.assertEqual(payload["chapters"][0]["word_count"], 1)
        self.assertEqual(payload["chapters"][0]["words"][0]["audio_segments"]["meaning"]["language"], "zh")
        self.assertEqual(payload["chapters"][1]["words"][0]["audio_segments"]["word"]["src"], "audio/segments/en/coupling.mp3")

    def test_build_chapter_payload_includes_complete_chapter_audio_when_available(self):
        entry = sample_entry()
        entry["_source_file"] = r"C:\workspace\chapter-a.csv"
        entry["_row_number"] = 1

        payload = build_chapter_payload(
            [entry],
            date(2026, 6, 17),
            segment_audio={},
            chapter_audio={r"C:\workspace\chapter-a.csv": "audio/chapters/chapter-a.mp3"},
        )

        self.assertEqual(payload["chapters"][0]["chapter_audio"], "audio/chapters/chapter-a.mp3")


if __name__ == "__main__":
    unittest.main()
