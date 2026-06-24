import csv
from pathlib import Path
from typing import Dict, List

from abbreviation_expander import expand_abbreviations_for_display


REQUIRED_COLUMNS = [
    "id",
    "word",
    "pronunciation",
    "chinese_meaning",
    "example_1_en",
    "example_1_zh",
    "example_2_en",
    "example_2_zh",
    "category",
    "difficulty",
    "review_count",
    "last_review_date",
]

CHINESE_COLUMNS = {"chinese_meaning", "example_1_zh", "example_2_zh"}
HARD_WORDS_FILENAME = "hard_words.csv"


VocabularyEntry = Dict[str, str]


def load_vocabulary(vocabulary_dir: Path | str) -> List[VocabularyEntry]:
    """Load every CSV file in the vocabulary directory."""
    directory = Path(vocabulary_dir)
    if not directory.exists():
        raise FileNotFoundError(f"Vocabulary directory does not exist: {directory}")

    csv_files = sorted(directory.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in: {directory}")

    entries: List[VocabularyEntry] = []
    seen_words = set()
    for csv_file in csv_files:
        is_hard_words_file = csv_file.name.lower() == HARD_WORDS_FILENAME
        seen_hard_words = set()
        with csv_file.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            _validate_columns(csv_file, reader.fieldnames or [])
            for row_number, row in enumerate(reader, start=1):
                if is_hard_words_file and _is_removed_hard_word(row):
                    continue
                normalized = {
                    column: _normalize_cell(column, row.get(column) or "")
                    for column in REQUIRED_COLUMNS
                }
                word_key = normalized["word"].casefold()
                if is_hard_words_file:
                    if word_key in seen_hard_words:
                        continue
                    seen_hard_words.add(word_key)
                elif word_key in seen_words:
                    continue
                if not is_hard_words_file:
                    seen_words.add(word_key)
                normalized["_source_file"] = str(csv_file)
                normalized["_row_number"] = row_number
                entries.append(normalized)
    return entries


def _validate_columns(csv_file: Path, fieldnames: list[str]) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"{csv_file} missing required columns: {joined}")


def _normalize_cell(column: str, value: str) -> str:
    if column in CHINESE_COLUMNS:
        return str(value or "").strip()
    return expand_abbreviations_for_display(value)


def _is_removed_hard_word(row: dict) -> bool:
    status = str(row.get("status") or "").strip().lower()
    return bool(status and status != "active")
