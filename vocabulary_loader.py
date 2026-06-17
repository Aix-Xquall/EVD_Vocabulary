import csv
from pathlib import Path
from typing import Dict, List


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
    for csv_file in csv_files:
        with csv_file.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            _validate_columns(csv_file, reader.fieldnames or [])
            for row_number, row in enumerate(reader, start=1):
                normalized = {column: (row.get(column) or "").strip() for column in REQUIRED_COLUMNS}
                normalized["_source_file"] = str(csv_file)
                normalized["_row_number"] = row_number
                entries.append(normalized)
    return entries


def _validate_columns(csv_file: Path, fieldnames: list[str]) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"{csv_file} missing required columns: {joined}")
