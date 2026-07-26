import csv
import json
import tempfile
import unittest
from pathlib import Path

from config import Settings
from script_builder import audio_key_for_entry
from tense_analyzer import (
    ANNOTATION_COLUMNS,
    TENSE_DISPLAY_NAMES,
    TENSE_FORMULAS,
    extract_modal_structure,
    export_pending_annotations,
    import_completed_annotations,
    load_tense_annotations_for_entries,
    sentence_key,
    validate_annotations_three_passes,
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
    def test_twelve_tenses_use_requested_display_names_and_formulas(self):
        expected = {
            "現在簡單式": ("現在簡單", "S + V / V-s"),
            "現在進行式": ("現在進行", "S + am/is/are + V-ing"),
            "現在完成式": ("現在完成", "S + have/has + p.p."),
            "現在完成進行式": ("現在完成進行", "S + have/has been + V-ing"),
            "過去簡單式": ("過去簡單", "S + V-ed"),
            "過去進行式": ("過去進行", "S + was/were + V-ing"),
            "過去完成式": ("過去完成", "S + had + p.p."),
            "過去完成進行式": ("過去完成進行", "S + had been + V-ing"),
            "未來簡單式": ("未來簡單", "S + will + V"),
            "未來進行式": ("未來進行", "S + will be + V-ing"),
            "未來完成式": ("未來完成", "S + will have + p.p."),
            "未來完成進行式": (
                "未來完成進行",
                "S + will have been + V-ing",
            ),
        }

        self.assertEqual(
            {
                name: (TENSE_DISPLAY_NAMES[name], TENSE_FORMULAS[name])
                for name in expected
            },
            expected,
        )

    def test_extract_modal_structure_uses_concrete_modal_and_base_verb(self):
        cases = [
            (
                "The consultant should review our grounding concept.",
                {"modal_verb": "should", "base_verb": "review"},
            ),
            (
                "The scope must clearly define what is included.",
                {"modal_verb": "must", "base_verb": "define"},
            ),
            (
                "The structure may not provide enough conductivity.",
                {"modal_verb": "may not", "base_verb": "provide"},
            ),
            (
                "The assembly must be checked before launch.",
                {"modal_verb": "must", "base_verb": "be"},
            ),
            (
                "Could we have a table for five?",
                {"modal_verb": "could", "base_verb": "have"},
            ),
            (
                "Can my child try this on?",
                {"modal_verb": "can", "base_verb": "try"},
            ),
            (
                "My kids cannot eat spicy food.",
                {"modal_verb": "cannot", "base_verb": "eat"},
            ),
        ]

        for sentence, expected in cases:
            with self.subTest(sentence=sentence):
                self.assertEqual(extract_modal_structure(sentence), expected)

        self.assertIsNone(extract_modal_structure("The controller monitors bus voltage."))

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
            self.assertEqual(analysis[key]["example_1"]["display_name_zh"], "現在進行")
            self.assertEqual(
                analysis[key]["example_1"]["display_formula"],
                "S + am/is/are + V-ing",
            )
            self.assertEqual(analysis[key]["example_1"]["highlights"], ["is monitoring"])
            self.assertEqual(analysis[key]["example_2"]["name_zh"], "現在完成式")

    def test_special_modal_uses_only_concrete_modal_display(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            annotations_path = Path(tmp_dir) / "annotations.csv"
            entry = sample_entry()
            entry["example_1_en"] = "The assembly should be checked before launch."
            entry["example_2_en"] = ""
            _write_rows(
                annotations_path,
                [
                    _completed_row(
                        entry["example_1_en"],
                        "特殊句型/需確認",
                        "S + modal + be + past participle",
                        ["should be checked"],
                        "0.98",
                    )
                ],
            )

            analysis = load_tense_annotations_for_entries(
                [entry],
                Settings(tense_annotations_path=annotations_path),
            )
            result = analysis[audio_key_for_entry(entry)]["example_1"]

            self.assertEqual(result["name_zh"], "特殊句型/需確認")
            self.assertEqual(result["display_name_zh"], "情態動詞")
            self.assertEqual(
                result["display_formula"],
                "should + 原形動詞：be",
            )

    def test_three_pass_validation_accepts_matching_explicit_tense(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            annotations_path = Path(tmp_dir) / "annotations.csv"
            entry = sample_entry()
            _write_rows(
                annotations_path,
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

            reports = validate_annotations_three_passes([entry], annotations_path)

            self.assertEqual([report["pass"] for report in reports], [1, 2, 3])
            self.assertTrue(all(not report["errors"] for report in reports))

    def test_three_pass_validation_reports_explicit_tense_conflict(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            annotations_path = Path(tmp_dir) / "annotations.csv"
            entry = sample_entry()
            entry["example_2_en"] = ""
            _write_rows(
                annotations_path,
                [
                    _completed_row(
                        entry["example_1_en"],
                        "過去進行式",
                        "S + was / were + V-ing",
                        ["is monitoring"],
                        "0.96",
                    )
                ],
            )

            reports = validate_annotations_three_passes([entry], annotations_path)

            self.assertEqual(len(reports[2]["errors"]), 1)
            self.assertIn("現在進行式", reports[2]["errors"][0])

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
