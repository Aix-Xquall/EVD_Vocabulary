import csv
import json
import tempfile
import unittest
from pathlib import Path

from config import Settings
from example_source_analyzer import (
    ANNOTATION_COLUMNS,
    generate_annotations,
    is_usable_section,
    load_example_sources_for_entries,
    validate_coverage,
)
from script_builder import audio_key_for_entry


def sample_entry() -> dict:
    return {
        "id": "1",
        "word": "shock mount",
        "example_1_en": "Bonding straps cross shock mounts.",
        "example_2_en": "Inspect the bonding strap after vibration.",
        "_source_file": "MSFC-HDBK-3697.csv",
        "_row_number": 2,
    }


class ExampleSourceAnalyzerTests(unittest.TestCase):
    def test_generate_load_and_validate_example_sources(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            corpus_path = directory / "corpus.jsonl"
            annotations_path = directory / "example_sources.csv"
            corpus_records = [
                {
                    "document": "MSFC-HDBK-3697.pdf",
                    "page": 35,
                    "section": "5.4.6 SHOCK MOUNTS",
                    "text": "Bonding straps cross shock mounts. Inspect each bonding strap after vibration.",
                }
            ]
            corpus_path.write_text(
                "".join(json.dumps(record) + "\n" for record in corpus_records),
                encoding="utf-8",
            )
            entry = sample_entry()

            count = generate_annotations([entry], corpus_path, annotations_path)
            errors = validate_coverage([entry], annotations_path)
            settings = Settings(example_sources_path=annotations_path)
            loaded = load_example_sources_for_entries([entry], settings)

            self.assertEqual(count, 2)
            self.assertEqual(errors, [])
            sources = loaded[audio_key_for_entry(entry)]
            self.assertEqual(sources["example_1"]["section"], "5.4.6 SHOCK MOUNTS")
            self.assertEqual(sources["example_1"]["attribution"], "原文摘錄")
            self.assertEqual(sources["example_2"]["attribution"], "改寫自")

    def test_project_annotations_cover_every_current_example(self):
        project_dir = Path(__file__).resolve().parents[1]
        settings = Settings(
            vocabulary_dir=project_dir / "vocabulary",
            example_sources_path=project_dir / "annotations" / "example_sources.csv",
        )
        from vocabulary_loader import load_vocabulary

        entries = load_vocabulary(settings.vocabulary_dir)
        self.assertEqual(validate_coverage(entries, settings.example_sources_path), [])

        with settings.example_sources_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            self.assertEqual(reader.fieldnames, ANNOTATION_COLUMNS)
            rows = list(reader)
        self.assertTrue(rows)
        self.assertTrue(all(row["reference_section"] for row in rows))

    def test_body_measurements_and_contact_details_are_not_sections(self):
        invalid_sections = [
            "10 V/m from 30 MHz to 18 GHz",
            "461 Since equipment was tested in accordance with MIL-STD-461",
            "4552 Pike Road, Fort George G. Meade, MD 20755. Telephone: 301-677-4440",
            "4 Some firing circuits may be energized during loading and unloading to complete the task",
        ]

        for section in invalid_sections:
            with self.subTest(section=section):
                self.assertFalse(is_usable_section("MIL-STD-464C.pdf", section))


if __name__ == "__main__":
    unittest.main()
