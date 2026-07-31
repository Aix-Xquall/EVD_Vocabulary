import csv
import io
import json
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
PRACTICE_STATS_WORD = "__EVD_PRACTICE_STATS__"
PRACTICE_STATS_STATUS = "practice_stats"


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


def load_practice_state(vocabulary_dir: Path | str) -> dict:
    """Load practice statistics and synchronized player settings from the sheet snapshot."""
    snapshot_path = Path(vocabulary_dir) / HARD_WORDS_FILENAME
    if not snapshot_path.exists():
        return {"records": {}, "settings": {}, "settings_updated_at": ""}

    with snapshot_path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            word = str(row.get("word") or "").strip()
            status = str(row.get("status") or "").strip().lower()
            if word != PRACTICE_STATS_WORD or status != PRACTICE_STATS_STATUS:
                continue
            return _parse_practice_state_note(str(row.get("note") or ""))
    return {"records": {}, "settings": {}, "settings_updated_at": ""}


def load_practice_stats(vocabulary_dir: Path | str) -> dict[str, dict]:
    """Load only practice counters for callers that do not need synchronized settings."""
    return load_practice_state(vocabulary_dir)["records"]


def _parse_practice_state_note(note: str) -> dict:
    try:
        payload = json.loads(note)
    except (TypeError, json.JSONDecodeError):
        return {"records": {}, "settings": {}, "settings_updated_at": ""}

    records = payload.get("r", []) if isinstance(payload, dict) else []
    parsed = {}
    for record in records:
        if not isinstance(record, list) or len(record) < 4:
            continue
        word = str(record[0] or "").strip()
        if not word:
            continue
        try:
            practice_count = max(0, int(record[1]))
            repeat_current_count = max(0, int(record[2]))
        except (TypeError, ValueError):
            continue
        parsed[word.casefold()] = {
            "word": word,
            "practice_count": practice_count,
            "repeat_current_count": repeat_current_count,
            "last_practiced_at": str(record[3] or ""),
        }
    settings = _parse_practice_settings(payload.get("s", {}) if isinstance(payload, dict) else {})
    return {
        "records": parsed,
        "settings": settings,
        "settings_updated_at": str(payload.get("su") or "") if isinstance(payload, dict) else "",
    }


def _parse_practice_settings(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    settings = {}
    chapter_id = str(value.get("selected_chapter_id") or "").strip()
    if chapter_id:
        settings["selected_chapter_id"] = chapter_id
    for key in ("repeat_all", "repeat_current", "include_examples"):
        if isinstance(value.get(key), bool):
            settings[key] = value[key]
    try:
        playback_rate = float(value.get("playback_rate"))
        if 0.5 <= playback_rate <= 1.5:
            settings["playback_rate"] = playback_rate
    except (TypeError, ValueError):
        pass
    try:
        repeat_count = int(value.get("english_repeat_count"))
        if 1 <= repeat_count <= 5:
            settings["english_repeat_count"] = repeat_count
    except (TypeError, ValueError):
        pass
    return settings


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
