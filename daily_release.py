import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PureWindowsPath
from typing import Iterable


MSFC_CHAPTER_PREFIX = "MSFC-HDBK-3697_"
STATE_FILENAME = "msfc_daily_release_state.json"


@dataclass(frozen=True)
class DailyReleaseResult:
    entries: list[dict]
    released_today: list[dict]
    state_path: Path
    new_word_keys: set[str]


def apply_daily_release(
    entries: Iterable[dict],
    previous_payload: dict | None,
    output_dir: Path,
    target_date: date,
    daily_word_count: int,
    release_new_words: bool = True,
) -> DailyReleaseResult:
    """Publish at most one new MSFC batch per date while retaining released words."""
    entry_list = list(entries)
    curriculum_entries = [entry for entry in entry_list if is_msfc_curriculum_entry(entry)]
    if not curriculum_entries:
        return DailyReleaseResult(entry_list, [], output_dir / "data" / STATE_FILENAME, set())

    state_path = output_dir / "data" / STATE_FILENAME
    state = _read_state(state_path)
    released_words = set(state.get("released_words", []))
    released_at = {
        normalize_word(word): str(released_date)
        for word, released_date in (state.get("released_at", {}) or {}).items()
        if normalize_word(word) and str(released_date)
    }

    # Version 1 stored only the latest batch. Preserve that batch as unread-capable
    # without marking every previously published handbook word as new.
    legacy_release_date = str(state.get("last_release_date") or "")
    if legacy_release_date:
        for word in state.get("released_today", []):
            key = normalize_word(word)
            if key:
                released_at.setdefault(key, legacy_release_date)

    if not state:
        released_words.update(_previous_formal_words(previous_payload or {}))

    released_today = []
    target_date_text = target_date.isoformat()
    if (
        release_new_words
        and state.get("last_release_date") != target_date_text
        and daily_word_count > 0
    ):
        for entry in curriculum_entries:
            key = normalize_word(entry.get("word", ""))
            if not key or key in released_words:
                continue
            released_words.add(key)
            released_at[key] = target_date_text
            released_today.append(entry)
            if len(released_today) >= daily_word_count:
                break

    visible_entries = [
        entry
        for entry in entry_list
        if not is_msfc_curriculum_entry(entry)
        or normalize_word(entry.get("word", "")) in released_words
    ]

    next_state = {
        "version": 2,
        "last_release_date": (
            target_date_text if release_new_words else state.get("last_release_date", "")
        ),
        "released_words": sorted(released_words),
        "released_today": [normalize_word(entry.get("word", "")) for entry in released_today],
        "released_at": dict(sorted(released_at.items())),
    }
    _write_state(state_path, next_state)
    return DailyReleaseResult(visible_entries, released_today, state_path, set(released_at))


def is_msfc_curriculum_entry(entry: dict) -> bool:
    return _source_name(entry.get("_source_file", "")).startswith(MSFC_CHAPTER_PREFIX)


def normalize_word(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _previous_formal_words(payload: dict) -> set[str]:
    words = set()
    for chapter in payload.get("chapters", []):
        if chapter.get("is_hard_words"):
            continue
        for word in chapter.get("words", []):
            key = normalize_word(word.get("word", ""))
            if key:
                words.add(key)
    return words


def _read_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Daily release state warning: {exc}")
        return {}
    return value if isinstance(value, dict) else {}


def _write_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _source_name(value: str) -> str:
    source = str(value or "")
    if "\\" in source:
        return PureWindowsPath(source).name
    return Path(source).name
