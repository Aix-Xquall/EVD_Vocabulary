import unittest

from audio_sample_generator import _playback_sequence, estimate_synthesized_characters, select_chapter_entries


class AudioSampleGeneratorTests(unittest.TestCase):
    def test_select_chapter_entries_keeps_only_requested_chapter_limit(self):
        entries = [
            {"word": "a", "_source_file": "vocabulary/chapter-a.csv"},
            {"word": "b", "_source_file": "vocabulary/chapter-b.csv"},
            {"word": "c", "_source_file": "vocabulary/chapter-b.csv"},
        ]

        selected = select_chapter_entries(entries, "chapter-b", 1)

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


if __name__ == "__main__":
    unittest.main()
