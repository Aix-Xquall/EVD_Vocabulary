import csv
import io
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from vocabulary_loader import REQUIRED_COLUMNS


HARD_WORDS_FILENAME = "hard_words.csv"
TRACKING_COLUMNS = ["source_chapter", "source_id", "added_at", "status", "note"]
OUTPUT_COLUMNS = REQUIRED_COLUMNS + TRACKING_COLUMNS
MASTERED_STATUSES = {"mastered", "mastered_active"}


@dataclass(frozen=True)
class HardWordsSyncResult:
    path: Path
    row_count: int
    used_remote: bool


def sync_hard_words(settings) -> HardWordsSyncResult | None:
    """Refresh the local hard words CSV snapshot when a valid remote CSV URL is configured."""
    vocabulary_dir = Path(settings.vocabulary_dir)
    snapshot_path = vocabulary_dir / HARD_WORDS_FILENAME
    if not settings.hard_words_sheet_csv_url:
        if snapshot_path.exists():
            return HardWordsSyncResult(snapshot_path, _count_csv_rows(snapshot_path), False)
        return None

    try:
        csv_text = _fetch_csv_text(settings.hard_words_sheet_csv_url, settings.hard_words_read_token)
        return sync_hard_words_from_csv_text(csv_text, vocabulary_dir, used_remote=True)
    except (OSError, urllib.error.URLError, ValueError) as exc:
        print(f"Hard words sync warning: {exc}")
        if snapshot_path.exists():
            return HardWordsSyncResult(snapshot_path, _count_csv_rows(snapshot_path), False)
        return None


def sync_hard_words_from_csv_text(
    csv_text: str,
    vocabulary_dir: Path | str,
    used_remote: bool = False,
) -> HardWordsSyncResult:
    vocabulary_path = Path(vocabulary_dir)
    vocabulary_path.mkdir(parents=True, exist_ok=True)
    reader = csv.DictReader(io.StringIO(csv_text))
    _validate_remote_csv_columns(reader.fieldnames or [])
    rows = list(reader)
    snapshot_rows = _deduplicate_hard_word_rows(rows)

    snapshot_path = vocabulary_path / HARD_WORDS_FILENAME
    with snapshot_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in snapshot_rows:
            writer.writerow({column: row.get(column, "") for column in OUTPUT_COLUMNS})

    return HardWordsSyncResult(snapshot_path, len(snapshot_rows), used_remote)


def filter_hard_word_rows(rows: Iterable[dict]) -> list[dict]:
    filtered = []
    seen_words = set()
    for row in rows:
        status = str(row.get("status") or "").strip().lower()
        if status and status != "active":
            continue
        word = str(row.get("word") or "").strip()
        if not word:
            continue
        word_key = word.casefold()
        if word_key in seen_words:
            continue
        seen_words.add(word_key)
        filtered.append(row)
    return filtered


def load_mastered_word_statuses(vocabulary_dir: Path | str) -> dict[str, str]:
    snapshot_path = Path(vocabulary_dir) / HARD_WORDS_FILENAME
    if not snapshot_path.exists():
        return {}

    with snapshot_path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = csv.DictReader(file)
        return {
            str(row.get("word") or "").strip().casefold(): status
            for row in rows
            if (status := str(row.get("status") or "").strip().lower()) in MASTERED_STATUSES
            and str(row.get("word") or "").strip()
        }


def _deduplicate_hard_word_rows(rows: Iterable[dict]) -> list[dict]:
    deduplicated = []
    seen_words = set()
    sorted_rows = sorted(rows, key=_added_at_timestamp, reverse=True)
    for row in sorted_rows:
        word = str(row.get("word") or "").strip()
        if not word:
            continue
        word_key = word.casefold()
        if word_key in seen_words:
            continue
        seen_words.add(word_key)
        deduplicated.append(row)
    return deduplicated


def _added_at_timestamp(row: dict) -> float:
    value = str(row.get("added_at") or "").strip()
    if not value:
        return float("-inf")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return float("-inf")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _fetch_csv_text(url: str, read_token: str = "") -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "EVD-Vocabulary"})
    if read_token:
        request.add_header("Authorization", f"Bearer {read_token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8-sig")


def _validate_remote_csv_columns(fieldnames: list[str]) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Hard words remote CSV missing required columns: {joined}")


def _count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return sum(1 for _ in csv.DictReader(file))
