import csv
import json
import tempfile
import unittest
from pathlib import Path

from config import Settings
from script_builder import audio_key_for_entry
from tense_analyzer import (
    ANNOTATION_COLUMNS,
    export_pending_annotations,
    import_completed_annotations,
    load_tense_annotations_for_entries,
    sentence_key,
    validate_annotation_coverage,
)


def sample_entry() -> dict:
    return {
        "id": "1",
        "word": "monitoring",
        "example_1_en": "The controller is monitoring bus voltage.",
        "example_2_en": "The controller has completed the check.",
        "_source_file": "chapter-a.csv",
        "_row_number": 1,
    }


class TenseAnalyzerTests(unittest.TestCase):
    def test_export_pending_writes_unique_unannotated_examples(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "pending.csv"
            duplicate = sample_entry()
            duplicate["id"] = "2"
            duplicate["_row_number"] = 2

            count = export_pending_annotations(
                [sample_entry(), duplicate],
                Path(tmp_dir) / "annotations.csv",
                output_path,
            )

            rows = _read_rows(output_path)
            self.assertEqual(count, 2)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["tense_name_zh"], "")
            self.assertEqual(rows[0]["sentence_key"], sentence_key(rows[0]["example_en"]))

    def test_import_validates_merges_and_loads_annotations(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            completed_path = workspace / "completed.csv"
            annotations_path = workspace / "annotations.csv"
            entry = sample_entry()
            _write_rows(
                completed_path,
                [
                    _completed_row(
                        entry["example_1_en"],
                        "現在進行式",
                        "S + am / is / are + V-ing",
                        ["is monitoring"],
                        "0.96",
                    ),
                    _completed_row(
                        entry["example_2_en"],
                        "現在完成式",
                        "S + have / has + p.p.",
                        ["has completed"],
                        "0.95",
                        example_number="2",
                    ),
                ],
            )

            imported_count = import_completed_annotations(
                completed_path,
                annotations_path,
                [entry],
            )
            settings = Settings(tense_annotations_path=annotations_path)
            analysis = load_tense_annotations_for_entries([entry], settings)

            key = audio_key_for_entry(entry)
            self.assertEqual(imported_count, 2)
            self.assertEqual(analysis[key]["example_1"]["name_zh"], "現在進行式")
            self.assertEqual(analysis[key]["example_1"]["highlights"], ["is monitoring"])
            self.assertEqual(analysis[key]["example_2"]["name_zh"], "現在完成式")

    def test_import_rejects_highlight_that_is_not_in_sentence(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            completed_path = Path(tmp_dir) / "completed.csv"
            entry = sample_entry()
            _write_rows(
                completed_path,
                [
                    _completed_row(
                        entry["example_1_en"],
                        "現在進行式",
                        "S + am / is / are + V-ing",
                        ["was monitoring"],
                        "0.90",
                    )
                ],
            )

            with self.assertRaisesRegex(ValueError, "not an exact substring"):
                import_completed_annotations(
                    completed_path,
                    Path(tmp_dir) / "annotations.csv",
                    [entry],
                )

    def test_validation_reports_missing_examples(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            validation, missing = validate_annotation_coverage(
                [sample_entry()],
                Path(tmp_dir) / "annotations.csv",
            )

            self.assertEqual(validation.errors, [])
            self.assertEqual(len(missing), 2)


def _completed_row(
    sentence: str,
    name: str,
    formula: str,
    highlights: list[str],
    confidence: str,
    example_number: str = "1",
) -> dict:
    return {
        "sentence_key": sentence_key(sentence),
        "source_file": "chapter-a.csv",
        "source_id": "1",
        "word": "monitoring",
        "example_number": example_number,
        "example_en": sentence,
        "tense_name_zh": name,
        "formula": formula,
        "highlights_json": json.dumps(highlights),
        "confidence": confidence,
        "reviewed_at": "",
    }


def _write_rows(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=ANNOTATION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


if __name__ == "__main__":
    unittest.main()
