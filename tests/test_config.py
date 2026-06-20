import unittest

from config import DEFAULT_SETTINGS


class ConfigTests(unittest.TestCase):
    def test_default_vocabulary_directory_is_dedicated_vocabulary_folder(self):
        self.assertEqual(DEFAULT_SETTINGS.vocabulary_dir.name, "vocabulary")


if __name__ == "__main__":
    unittest.main()
