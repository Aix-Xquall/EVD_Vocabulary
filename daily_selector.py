import hashlib
from datetime import date, datetime
from typing import Dict, List


VocabularyEntry = Dict[str, str]


def select_daily_words(
    entries: List[VocabularyEntry],
    count: int,
    today: date | None = None,
) -> List[VocabularyEntry]:
    """Select words by low review count, old review date, high difficulty."""
    target_date = today or date.today()
    ranked = sorted(entries, key=lambda entry: _priority_key(entry, target_date))
    return ranked[:count]


def _priority_key(entry: VocabularyEntry, target_date: date) -> tuple:
    return (
        _safe_int(entry.get("review_count", ""), default=0),
        _safe_date(entry.get("last_review_date", "")),
        -_safe_int(entry.get("difficulty", ""), default=0),
        _stable_daily_tiebreaker(entry, target_date),
    )


def _safe_int(value: str, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _safe_date(value: str) -> date:
    text = str(value or "").strip()
    if not text:
        return date.min
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return date.min


def _stable_daily_tiebreaker(entry: VocabularyEntry, target_date: date) -> str:
    source = f"{target_date.isoformat()}:{entry.get('id', '')}:{entry.get('word', '')}"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()
