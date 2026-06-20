import unittest
from datetime import date
from pathlib import Path
import tempfile
from xml.etree import ElementTree

from config import Settings
from tts_generator import (
    _available_segment_audio_paths,
    _combined_ssml,
    _combine_audio_files,
    _entry_ssml,
    _segment_ssml,
    _speech_text_for_audio,
    _should_synthesize_segment,
    expected_audio_paths,
    expected_segment_audio_paths,
)


class TtsGeneratorTests(unittest.TestCase):
    def test_combine_audio_files_concatenates_per_word_mp3_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            first = workspace / "001.mp3"
            second = workspace / "002.mp3"
            combined = workspace / "combined.mp3"
            first.write_bytes(b"first-audio")
            second.write_bytes(b"second-audio")

            _combine_audio_files([first, second], combined)

            self.assertEqual(combined.read_bytes(), b"first-audiosecond-audio")

    def test_expected_audio_paths_are_relative_to_published_site_root(self):
        per_word, combined = expected_audio_paths(
            [{"id": "1", "word": "impedance"}],
            date(2026, 6, 17),
            Settings(generate_audio=False).output_dir,
        )

        self.assertEqual(per_word["1"], "audio/2026-06-17/001_impedance.mp3")
        self.assertEqual(combined, "audio/2026-06-17_daily_vocabulary.mp3")

    def test_expected_segment_audio_paths_are_content_addressed_and_grouped_by_language(self):
        first = {"id": "1", "word": "impedance", "chinese_meaning": "meaning"}
        second = {"id": "2", "word": "impedance", "chinese_meaning": "meaning"}

        paths = expected_segment_audio_paths([first, second], Settings(generate_audio=False))

        self.assertEqual(paths["1"]["word"], paths["2"]["word"])
        self.assertEqual(paths["1"]["word"]["language"], "en")
        self.assertEqual(paths["1"]["meaning"]["language"], "zh")
        self.assertTrue(paths["1"]["word"]["src"].startswith("audio/segments/en/"))
        self.assertTrue(paths["1"]["meaning"]["src"].startswith("audio/segments/zh/"))
        self.assertTrue(paths["1"]["word"]["src"].endswith(".mp3"))

    def test_sample_vocabulary_entries_do_not_receive_audio_segments(self):
        formal = {
            "id": "1",
            "word": "impedance",
            "chinese_meaning": "meaning",
            "_source_file": r"C:\workspace\EMC航電詞彙整合1.csv",
            "_row_number": 1,
        }
        sample = {
            "id": "1",
            "word": "sample",
            "chinese_meaning": "sample meaning",
            "_source_file": r"C:\workspace\sample vocabulary.csv",
            "_row_number": 1,
        }

        paths = expected_segment_audio_paths([formal, sample], Settings(generate_audio=False))

        self.assertIn("word", paths[r"C:\workspace\EMC航電詞彙整合1.csv#1"])
        self.assertEqual(paths[r"C:\workspace\sample vocabulary.csv#1"], {})

    def test_existing_non_empty_segment_is_not_synthesized_again(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            segment = Path(temp_dir) / "segment.mp3"
            segment.write_bytes(b"already-generated")

            self.assertFalse(_should_synthesize_segment(segment))
            self.assertTrue(_should_synthesize_segment(Path(temp_dir) / "missing.mp3"))

    def test_available_segment_audio_paths_only_keeps_existing_mp3_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            existing = output_dir / "audio" / "segments" / "en" / "existing.mp3"
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b"audio")
            settings = Settings(output_dir=output_dir, generate_audio=False)

            available = _available_segment_audio_paths(
                {
                    "1": {
                        "word": {"src": "audio/segments/en/existing.mp3", "language": "en"},
                        "meaning": {"src": "audio/segments/zh/missing.mp3", "language": "zh"},
                    }
                },
                settings,
            )

            self.assertIn("word", available["1"])
            self.assertNotIn("meaning", available["1"])

    def test_english_segment_ssml_uses_configured_rate_but_chinese_segment_keeps_normal_rate(self):
        settings = Settings(generate_audio=False, speech_rate="-20%")

        english_ssml = _segment_ssml("English example.", "en", settings)
        chinese_ssml = _segment_ssml("中文翻譯", "zh", settings)

        self.assertIn('voice name="en-US-JennyNeural"', english_ssml)
        self.assertIn('rate="-20%"', english_ssml)
        self.assertIn('voice name="zh-TW-HsiaoChenNeural"', chinese_ssml)
        self.assertIn('rate="0%"', chinese_ssml)

    def test_chinese_audio_pronounces_ground_character_like_di_not_de(self):
        settings = Settings(generate_audio=False)

        ssml = _segment_ssml("地面接地點", "zh", settings)
        display_path = expected_segment_audio_paths(
            [{"id": "1", "chinese_meaning": "地面接地點"}],
            settings,
        )["1"]["meaning"]["src"]
        spoken_path = expected_segment_audio_paths(
            [{"id": "1", "chinese_meaning": "第面接第點"}],
            settings,
        )["1"]["meaning"]["src"]

        self.assertEqual(_speech_text_for_audio("地面接地點", "zh"), "第面接第點")
        self.assertIn("第面接第點", ssml)
        self.assertNotIn("地面接地點", ssml)
        self.assertEqual(display_path, spoken_path)

    def test_english_audio_expands_known_engineering_abbreviations(self):
        spoken = _speech_text_for_audio("EMC, E3, EPDS, and MIL-STD-461", "en")

        self.assertEqual(
            spoken,
            "Electromagnetic Compatibility, "
            "Electromagnetic Environmental Effects, "
            "Electronic Power Distribution System, and "
            "Military Standard 461",
        )

    def test_entry_ssml_skips_pronunciation_but_keeps_meanings_and_examples(self):
        entry = {
            "word": "impedance",
            "pronunciation": "DO_NOT_READ_THIS_PRONUNCIATION",
            "chinese_meaning": "READ_CHINESE_MEANING",
            "example_1_en": "Read English example one.",
            "example_1_zh": "READ_CHINESE_TRANSLATION_ONE",
            "example_2_en": "Read English example two.",
            "example_2_zh": "READ_CHINESE_TRANSLATION_TWO",
        }

        ssml = _entry_ssml(entry, Settings(generate_audio=False))

        self.assertIn("impedance", ssml)
        self.assertNotIn("DO_NOT_READ_THIS_PRONUNCIATION", ssml)
        self.assertIn("READ_CHINESE_MEANING", ssml)
        self.assertIn("Read English example one.", ssml)
        self.assertIn("READ_CHINESE_TRANSLATION_ONE", ssml)
        self.assertIn("Read English example two.", ssml)
        self.assertIn("READ_CHINESE_TRANSLATION_TWO", ssml)

    def test_entry_ssml_uses_chinese_voice_for_chinese_segments(self):
        entry = {
            "word": "impedance",
            "pronunciation": "/im-PEE-dance/",
            "chinese_meaning": "中文意思",
            "example_1_en": "Read English example one.",
            "example_1_zh": "中文翻譯一",
            "example_2_en": "Read English example two.",
            "example_2_zh": "中文翻譯二",
        }

        ssml = _entry_ssml(entry, Settings(generate_audio=False))

        self.assertIn('voice name="en-US-JennyNeural"', ssml)
        self.assertIn('voice name="zh-TW-HsiaoChenNeural"', ssml)
        self.assertIn("中文意思", ssml)
        self.assertIn("中文翻譯一", ssml)
        self.assertIn("中文翻譯二", ssml)

    def test_entry_ssml_wraps_breaks_inside_voice_node(self):
        entry = {
            "word": "impedance",
            "pronunciation": "/ɪmˈpiːdəns/",
            "chinese_meaning": "阻抗",
            "example_1_en": "The impedance must be controlled.",
            "example_1_zh": "阻抗必須被控制。",
            "example_2_en": "Cable impedance affects signal integrity.",
            "example_2_zh": "電纜阻抗會影響訊號完整性。",
        }

        ssml = _entry_ssml(entry, Settings(generate_audio=False))

        root = ElementTree.fromstring(ssml)
        direct_child_names = [child.tag.split("}", 1)[-1] for child in root]
        self.assertNotIn("break", direct_child_names)
        self.assertIn("voice", direct_child_names)
        self.assertIn("<break", ssml)

    def test_combined_ssml_does_not_place_break_directly_under_speak(self):
        entries = [
            {
                "word": "impedance",
                "pronunciation": "/ɪmˈpiːdəns/",
                "chinese_meaning": "阻抗",
                "example_1_en": "The impedance must be controlled.",
                "example_1_zh": "阻抗必須被控制。",
                "example_2_en": "Cable impedance affects signal integrity.",
                "example_2_zh": "電纜阻抗會影響訊號完整性。",
            },
            {
                "word": "coupling",
                "pronunciation": "/ˈkʌp.lɪŋ/",
                "chinese_meaning": "耦合",
                "example_1_en": "Coupling can introduce noise.",
                "example_1_zh": "耦合可能導入雜訊。",
                "example_2_en": "Cable coupling affects EMC.",
                "example_2_zh": "電纜耦合會影響 EMC。",
            },
        ]

        ssml = _combined_ssml(entries, Settings(generate_audio=False))

        root = ElementTree.fromstring(ssml)
        direct_child_names = [child.tag.split("}", 1)[-1] for child in root]
        self.assertNotIn("break", direct_child_names)
        self.assertTrue(direct_child_names)
        self.assertTrue(all(name == "voice" for name in direct_child_names))


if __name__ == "__main__":
    unittest.main()
