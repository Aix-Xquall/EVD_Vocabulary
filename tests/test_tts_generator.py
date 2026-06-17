import unittest
from datetime import date
from xml.etree import ElementTree

from config import Settings
from tts_generator import _combined_ssml, _entry_ssml, expected_audio_paths


class TtsGeneratorTests(unittest.TestCase):
    def test_expected_audio_paths_are_relative_to_published_site_root(self):
        per_word, combined = expected_audio_paths(
            [{"id": "1", "word": "impedance"}],
            date(2026, 6, 17),
            Settings(generate_audio=False).output_dir,
        )

        self.assertEqual(per_word["1"], "audio/2026-06-17/001_impedance.mp3")
        self.assertEqual(combined, "audio/2026-06-17_daily_vocabulary.mp3")

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
        self.assertEqual(direct_child_names, ["voice"])


if __name__ == "__main__":
    unittest.main()
