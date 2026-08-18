import tempfile
import unittest
from pathlib import Path

from abbreviation_expander import expand_abbreviations_for_speech
from vocabulary_loader import REQUIRED_COLUMNS, load_vocabulary


def write_csv(path: Path, rows: str) -> None:
    path.write_text(
        "id,word,pronunciation,chinese_meaning,example_1_en,example_1_zh,"
        "example_2_en,example_2_zh,category,difficulty,review_count,last_review_date\n"
        + rows,
        encoding="utf-8",
    )


class VocabularyLoaderTests(unittest.TestCase):
    def test_load_vocabulary_reads_all_csv_files_and_tracks_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            write_csv(
                tmp_path / "a.csv",
                "1,impedance,/im/,阻抗,Example one,例句一,Example two,例句二,EMC,4,0,\n",
            )
            write_csv(
                tmp_path / "b.csv",
                "2,coupling,/cup/,耦合,Example one,例句一,Example two,例句二,EMC,3,2,2026-06-01\n",
            )
            (tmp_path / "ignore.txt").write_text("not csv", encoding="utf-8")

            entries = load_vocabulary(tmp_path)

            self.assertEqual([entry["word"] for entry in entries], ["impedance", "coupling"])
            self.assertTrue(all(entry["_source_file"].endswith(".csv") for entry in entries))

    def test_hard_word_uses_latest_formal_translation_and_examples(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            write_csv(
                directory / "chapter.csv",
                "1,bonding,/bond/,搭接,Formal example one,正式翻譯一,"
                "Formal example two,正式翻譯二,EMC,4,0,\n",
            )
            (directory / "hard_words.csv").write_text(
                "id,word,pronunciation,chinese_meaning,example_1_en,example_1_zh,"
                "example_2_en,example_2_zh,category,difficulty,review_count,last_review_date,status\n"
                "1,bonding,/old/,old meaning,Old example one,old translation one,"
                "Old example two,old translation two,EMC,2,0,,active\n",
                encoding="utf-8",
            )

            entries = load_vocabulary(directory)

            hard_word = next(
                entry for entry in entries if Path(entry["_source_file"]).name == "hard_words.csv"
            )
            self.assertEqual(hard_word["chinese_meaning"], "搭接")
            self.assertEqual(hard_word["example_1_zh"], "正式翻譯一")
            self.assertEqual(hard_word["example_2_zh"], "正式翻譯二")
            self.assertTrue(all(entry["_row_number"] == 1 for entry in entries))

    def test_load_vocabulary_expands_known_abbreviations_and_skips_duplicate_words(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            write_csv(
                tmp_path / "a.csv",
                "1,EMC,/emc/,meaning,EMC must satisfy MIL-STD-461.,EMC 測試,EPDS supports E3.,EPDS 與 E3,EMC / E3,4,0,\n",
            )
            write_csv(
                tmp_path / "b.csv",
                "2,Electromagnetic Compatibility (EMC),/emc/,duplicate,duplicate,duplicate,duplicate,duplicate,EMC,4,0,\n",
            )

            entries = load_vocabulary(tmp_path)

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["word"], "Electromagnetic Compatibility (EMC)")
            self.assertIn("Military Standard 461 (MIL-STD-461)", entries[0]["example_1_en"])
            self.assertIn("Electronic Power Distribution System (EPDS)", entries[0]["example_2_en"])
            self.assertIn("Electromagnetic Environmental Effects (E3)", entries[0]["example_2_en"])
            self.assertEqual(entries[0]["category"], "Electromagnetic Compatibility (EMC) / Electromagnetic Environmental Effects (E3)")

    def test_load_vocabulary_can_preserve_duplicate_words_for_annotation_coverage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            write_csv(
                tmp_path / "a.csv",
                "1,impedance,/im/,阻抗,First example,例句一,Second example,例句二,EMC,4,0,\n",
            )
            write_csv(
                tmp_path / "b.csv",
                "2,impedance,/im/,阻抗,Third example,例句三,Fourth example,例句四,EMC,4,0,\n",
            )

            entries = load_vocabulary(tmp_path, deduplicate_words=False)

            self.assertEqual(len(entries), 2)
            self.assertEqual(
                [entry["example_1_en"] for entry in entries],
                ["First example", "Third example"],
            )

    def test_load_vocabulary_expands_ems_only_in_english_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            write_csv(
                tmp_path / "ems.csv",
                "1,EMS,/ems/,EMS 測試,EMS applies to receiver immunity.,中文 EMS 不展開,"
                "The EMS margin is low.,EMC 與 EMS 都保留縮寫,EMC,4,0,\n",
            )

            entries = load_vocabulary(tmp_path)

            self.assertEqual(entries[0]["word"], "Electromagnetic Susceptibility (EMS)")
            self.assertIn("Electromagnetic Susceptibility (EMS) applies", entries[0]["example_1_en"])
            self.assertIn("Electromagnetic Susceptibility (EMS) margin", entries[0]["example_2_en"])
            self.assertEqual(entries[0]["chinese_meaning"], "EMS 測試")
            self.assertEqual(entries[0]["example_1_zh"], "中文 EMS 不展開")
            self.assertEqual(entries[0]["example_2_zh"], "EMC 與 EMS 都保留縮寫")

    def test_load_vocabulary_expands_daq_in_english_and_shortens_chinese_terms(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            write_csv(
                tmp_path / "daq.csv",
                "1,DAQ,/daq/,Data Acquisition 數據擷取,"
                "DAQ records EMC data.,Electromagnetic Compatibility 測試資料,"
                "The DAQ channel is stable.,Radio Frequency 訊號穩定,DAQ,4,0,\n",
            )

            entries = load_vocabulary(tmp_path)

            self.assertEqual(entries[0]["word"], "Data Acquisition (DAQ)")
            self.assertIn("Data Acquisition (DAQ) records", entries[0]["example_1_en"])
            self.assertIn("Data Acquisition (DAQ) channel", entries[0]["example_2_en"])
            self.assertEqual(entries[0]["chinese_meaning"], "DAQ 數據擷取")
            self.assertEqual(entries[0]["example_1_zh"], "EMC 測試資料")
            self.assertEqual(entries[0]["example_2_zh"], "RF 訊號穩定")

    def test_load_vocabulary_expands_requested_aerospace_abbreviations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            write_csv(
                tmp_path / "aerospace.csv",
                "1,HERO,/hero/,HERO 危害,EEDs connect to the FTS and create EMI.,EED、FTS 與 EMI,"
                "GNSS can be affected by P-static in the external EME.,GNSS、P-static 與 EME,HERO,5,0,\n",
            )

            entries = load_vocabulary(tmp_path)

            self.assertEqual(
                entries[0]["word"],
                "Hazards of Electromagnetic Radiation to Ordnance (HERO)",
            )
            self.assertEqual(
                entries[0]["example_1_en"],
                "Electro-Explosive Devices (EEDs) connect to the Flight Termination System (FTS) "
                "and create Electromagnetic Interference (EMI).",
            )
            self.assertEqual(
                entries[0]["example_2_en"],
                "Global Navigation Satellite System (GNSS) can be affected by Precipitation Static "
                "(P-static) in the external Electromagnetic Environment (EME).",
            )
            self.assertEqual(entries[0]["chinese_meaning"], "HERO 危害")
            self.assertEqual(entries[0]["example_1_zh"], "EED、FTS 與 EMI")
            self.assertEqual(entries[0]["example_2_zh"], "GNSS、P-static 與 EME")

    def test_unrequested_abbreviations_remain_compact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            write_csv(
                tmp_path / "compact.csv",
                "1,CAN bus,/can/,CAN 匯流排,RF uses DC power.,RF 使用 DC 電源,"
                "ESD protection uses a TVS.,ESD 使用 TVS,EMC,4,0,\n",
            )

            entries = load_vocabulary(tmp_path)

            self.assertEqual(entries[0]["word"], "CAN bus")
            self.assertEqual(entries[0]["example_1_en"], "RF uses DC power.")
            self.assertEqual(entries[0]["example_2_en"], "ESD protection uses a TVS.")

    def test_requested_abbreviations_are_spoken_as_full_terms(self):
        text = (
            "Hazards of Electromagnetic Radiation to Ordnance (HERO), "
            "Electro-Explosive Device (EED), Flight Termination System (FTS), "
            "Global Navigation Satellite System (GNSS), Electromagnetic Environment (EME), "
            "Electromagnetic Interference (EMI), and Precipitation Static (P-static)."
        )

        self.assertEqual(
            expand_abbreviations_for_speech(text),
            "Hazards of Electromagnetic Radiation to Ordnance, Electro-Explosive Device, "
            "Flight Termination System, Global Navigation Satellite System, "
            "Electromagnetic Environment, Electromagnetic Interference, and Precipitation Static.",
        )

    def test_load_vocabulary_allows_hard_words_to_duplicate_normal_chapters(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            write_csv(
                tmp_path / "chapter.csv",
                "1,EMS,/ems/,EMS 測試,Example one,例句一,Example two,例句二,EMC,4,0,\n",
            )
            (tmp_path / "hard_words.csv").write_text(
                "id,word,pronunciation,chinese_meaning,example_1_en,example_1_zh,"
                "example_2_en,example_2_zh,category,difficulty,review_count,last_review_date,status\n"
                "1,EMS,/ems/,EMS 測試,Example one,例句一,Example two,例句二,EMC,4,0,,active\n"
                "2,EMS,/ems/,duplicate,Example one,例句一,Example two,例句二,EMC,4,0,,active\n"
                "3,E3,/e3/,removed,Example one,例句一,Example two,例句二,EMC,4,0,,removed\n",
                encoding="utf-8",
            )

            entries = load_vocabulary(tmp_path)

            self.assertEqual(
                [entry["word"] for entry in entries],
                [
                    "Electromagnetic Susceptibility (EMS)",
                    "Electromagnetic Susceptibility (EMS)",
                ],
            )
            self.assertEqual(Path(entries[1]["_source_file"]).name, "hard_words.csv")

    def test_load_vocabulary_rejects_missing_required_columns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            (tmp_path / "bad.csv").write_text("id,word\n1,impedance\n", encoding="utf-8")

            with self.assertRaises(ValueError) as context:
                load_vocabulary(tmp_path)

            message = str(context.exception)
            self.assertIn("missing required columns", message)
            self.assertIn("pronunciation", message)
            self.assertGreaterEqual(set(REQUIRED_COLUMNS), {"id", "word", "difficulty"})


if __name__ == "__main__":
    unittest.main()
