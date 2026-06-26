import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch

from audio_sample_generator import (
    _playback_sequence,
    estimate_synthesized_characters,
    generate_audio_sample,
    generate_google_voice_comparison_sample,
    select_chapter_entries,
    select_chapter_entries_by_index,
)
from config import Settings


class AudioSampleGeneratorTests(unittest.TestCase):
    def test_select_chapter_entries_keeps_only_requested_chapter_limit(self):
        entries = [
            {"word": "a", "_source_file": "vocabulary/chapter-a.csv"},
            {"word": "b", "_source_file": "vocabulary/chapter-b.csv"},
            {"word": "c", "_source_file": "vocabulary/chapter-b.csv"},
        ]

        selected = select_chapter_entries(entries, "chapter-b", 1)

        self.assertEqual([entry["word"] for entry in selected], ["b"])

    def test_select_chapter_entries_by_index_uses_sorted_chapter_order(self):
        entries = [
            {"word": "a", "_source_file": "vocabulary/chapter-a.csv"},
            {"word": "b", "_source_file": "vocabulary/chapter-b.csv"},
        ]

        selected = select_chapter_entries_by_index(entries, 2, 10)

        self.assertEqual([entry["word"] for entry in selected], ["b"])

    def test_estimate_synthesized_characters_uses_spoken_text(self):
        entries = [
            {
                "word": "Electromagnetic Compatibility (EMC)",
                "chinese_meaning": "電磁相容性",
                "example_1_en": "MIL-STD-461 applies.",
                "example_1_zh": "標準適用。",
                "example_2_en": "",
                "example_2_zh": "",
            }
        ]

        estimate = estimate_synthesized_characters(entries)

        self.assertEqual(
            estimate,
            len("Electromagnetic Compatibility")
            + len("電磁相容性")
            + len("Military Standard 461 applies.")
            + len("標準適用。"),
        )

    def test_playback_sequence_repeats_english_after_chinese_translation(self):
        entry = {
            "word": "impedance",
            "chinese_meaning": "阻抗",
            "example_1_en": "Example one.",
            "example_1_zh": "例句一。",
            "example_2_en": "",
            "example_2_zh": "",
        }

        sequence = _playback_sequence([entry], repeat_count=3)

        self.assertEqual(
            sequence[:8],
            [
                ("word", "impedance", "en"),
                ("meaning", "阻抗", "zh"),
                ("word", "impedance", "en"),
                ("word", "impedance", "en"),
                ("example_1_en", "Example one.", "en"),
                ("example_1_zh", "例句一。", "zh"),
                ("example_1_en", "Example one.", "en"),
                ("example_1_en", "Example one.", "en"),
            ],
        )

    def test_generate_audio_sample_uses_output_name_for_mp3_and_page_title(self):
        entry = {
            "word": "impedance",
            "chinese_meaning": "阻抗",
            "example_1_en": "",
            "example_1_zh": "",
            "example_2_en": "",
            "example_2_zh": "",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "emc1_first3_0_8"

            with patch("audio_sample_generator._synthesize_segment", side_effect=lambda settings, text, language, output_file: output_file.write_bytes(b"mp3")):
                result = generate_audio_sample(
                    [entry],
                    output_dir,
                    Settings(generate_audio=False, speech_rate="-20%"),
                    repeat_count=1,
                    output_name="emc1_first3_0_8",
                    title="EMC航電詞彙整合1 前 3 個 0.8 語速測試",
                )

            self.assertTrue(result["combined_audio"].endswith("emc1_first3_0_8.mp3"))
            html = (output_dir / "index.html").read_text(encoding="utf-8")
            self.assertIn("EMC航電詞彙整合1 前 3 個 0.8 語速測試", html)

    def test_generate_google_voice_comparison_sample_creates_three_voice_sections(self):
        entry = {
            "word": "impedance",
            "chinese_meaning": "阻抗",
            "example_1_en": "The impedance must be controlled.",
            "example_1_zh": "阻抗必須受到控制。",
            "example_2_en": "",
            "example_2_zh": "",
        }
        voices = [
            ("Neural2-C", "en-US-Neural2-C"),
            ("Neural2-E", "en-US-Neural2-E"),
            ("Neural2-F", "en-US-Neural2-F"),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "google_female_emc1_first10"

            with patch("audio_sample_generator._synthesize_segment", side_effect=lambda settings, text, language, output_file: output_file.write_bytes(b"mp3")):
                result = generate_google_voice_comparison_sample(
                    [entry],
                    output_dir,
                    Settings(generate_audio=False, speech_rate="-20%"),
                    repeat_count=2,
                    output_name="google_female_emc1_first10",
                    title="Google 女聲比較",
                    voices=voices,
                )

            html = (output_dir / "index.html").read_text(encoding="utf-8")
            self.assertEqual(len(result["voices"]), 3)
            self.assertIn("en-US-Neural2-C", html)
            self.assertIn("en-US-Neural2-E", html)
            self.assertIn("en-US-Neural2-F", html)
            self.assertTrue((output_dir / "en-US-Neural2-C" / "en-US-Neural2-C.mp3").exists())


if __name__ == "__main__":
    unittest.main()
