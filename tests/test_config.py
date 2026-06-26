import unittest

from config import DEFAULT_SETTINGS


class ConfigTests(unittest.TestCase):
    def test_default_vocabulary_directory_is_dedicated_vocabulary_folder(self):
        self.assertEqual(DEFAULT_SETTINGS.vocabulary_dir.name, "vocabulary")

    def test_default_tts_provider_keeps_existing_azure_behavior(self):
        self.assertEqual(DEFAULT_SETTINGS.tts_provider, "azure")
        self.assertEqual(DEFAULT_SETTINGS.google_english_voice, "en-US-Neural2-J")
        self.assertEqual(DEFAULT_SETTINGS.google_chinese_voice, "cmn-TW-Wavenet-A")


if __name__ == "__main__":
    unittest.main()
