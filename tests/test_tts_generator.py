import unittest
from xml.etree import ElementTree

from config import Settings
from tts_generator import _entry_ssml


class TtsGeneratorTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
