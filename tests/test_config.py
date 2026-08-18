import unittest

from config import DEFAULT_SETTINGS


class ConfigTests(unittest.TestCase):
    def test_default_vocabulary_directory_is_dedicated_vocabulary_folder(self):
        self.assertEqual(DEFAULT_SETTINGS.vocabulary_dir.name, "vocabulary")

    def test_default_tts_provider_uses_selectable_google_voices(self):
        self.assertEqual(DEFAULT_SETTINGS.tts_provider, "google")
        self.assertEqual(DEFAULT_SETTINGS.google_english_voice, "en-US-Neural2-J")
        self.assertEqual(DEFAULT_SETTINGS.google_male_voice, "en-US-Neural2-J")
        self.assertEqual(DEFAULT_SETTINGS.google_female_voice, "en-US-Wavenet-H")
        self.assertEqual(
            DEFAULT_SETTINGS.google_selectable_voices,
            (
                "en-US-Neural2-J",
                "en-US-Neural2-A",
                "en-US-Neural2-D",
                "en-US-Wavenet-H",
                "en-US-Neural2-C",
                "en-US-Neural2-E",
                "en-US-Neural2-F",
                "en-US-Neural2-H",
            ),
        )
        self.assertEqual(DEFAULT_SETTINGS.google_chinese_voice, "cmn-TW-Wavenet-A")
        self.assertEqual(DEFAULT_SETTINGS.google_tts_parallel_workers, 4)

    def test_default_tense_annotations_are_outside_vocabulary_folder(self):
        self.assertEqual(DEFAULT_SETTINGS.tense_annotations_path.name, "tense_annotations.csv")
        self.assertEqual(DEFAULT_SETTINGS.tense_annotations_path.parent.name, "annotations")

    def test_default_example_sources_are_outside_vocabulary_folder(self):
        self.assertEqual(DEFAULT_SETTINGS.example_sources_path.name, "example_sources.csv")
        self.assertEqual(DEFAULT_SETTINGS.example_sources_path.parent.name, "annotations")


if __name__ == "__main__":
    unittest.main()
