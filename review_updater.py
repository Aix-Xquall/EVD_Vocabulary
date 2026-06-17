import csv
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, Iterable


VocabularyEntry = Dict[str, str]


def update_review_files(selected_entries: Iterable[VocabularyEntry], review_date: date) -> None:
    """Increment review metadata in the original CSV files for selected words."""
    selected_by_file: dict[Path, set[int]] = defaultdict(set)
    for entry in selected_entries:
        source_file = entry.get("_source_file")
        row_number = entry.get("_row_number")
        if not source_file or row_number is None:
            raise ValueError("Selected entries must include _source_file and _row_number")
        selected_by_file[Path(source_file)].add(int(row_number))

    for csv_file, row_numbers in selected_by_file.items():
        _update_one_file(csv_file, row_numbers, review_date)


def _update_one_file(csv_file: Path, row_numbers: set[int], review_date: date) -> None:
    with csv_file.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    for row_number, row in enumerate(rows, start=1):
        if row_number in row_numbers:
            row["review_count"] = str(_safe_int(row.get("review_count", "")) + 1)
            row["last_review_date"] = review_date.isoformat()

    with csv_file.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _safe_int(value: str | None) -> int:
    try:
        return int(str(value or "").strip())
    except ValueError:
        return 0
