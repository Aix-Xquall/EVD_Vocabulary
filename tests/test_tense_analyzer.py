import tempfile
import unittest
from pathlib import Path

from config import Settings
from script_builder import audio_key_for_entry
from tense_analyzer import analyze_tenses_for_entries


class TenseAnalyzerTests(unittest.TestCase):
    def test_analyze_tenses_caches_missing_examples_and_reuses_cache(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            entry = {
                "id": "1",
                "word": "monitoring",
                "example_1_en": "The controller is monitoring bus voltage.",
                "example_2_en": "",
            }
            settings = Settings(
                output_dir=Path(tmp_dir) / "output",
                tense_cache_path=Path(tmp_dir) / "output" / "data" / "tense_cache.json",
            )
            calls = []

            def fake_analyzer(sentence):
                calls.append(sentence)
                return {
                    "name_zh": "現在進行式",
                    "formula": "S + am / is / are + V-ing",
                    "highlights": ["is monitoring"],
                    "confidence": 0.96,
                }

            first = analyze_tenses_for_entries([entry], settings, analyzer=fake_analyzer)
            second = analyze_tenses_for_entries([entry], settings, analyzer=fake_analyzer)

            key = audio_key_for_entry(entry)
            self.assertEqual(calls, ["The controller is monitoring bus voltage."])
            self.assertEqual(first[key]["example_1"]["name_zh"], "現在進行式")
            self.assertEqual(second[key]["example_1"]["highlights"], ["is monitoring"])
            self.assertTrue(settings.tense_cache_path.exists())

    def test_without_openai_key_uses_existing_cache_only(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_path = Path(tmp_dir) / "output" / "data" / "tense_cache.json"
            settings = Settings(output_dir=Path(tmp_dir) / "output", tense_cache_path=cache_path, openai_api_key="")
            entry = {"id": "1", "word": "check", "example_1_en": "Check the harness.", "example_2_en": ""}

            result = analyze_tenses_for_entries([entry], settings)

            self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()