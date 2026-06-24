from datetime import date
from pathlib import Path, PureWindowsPath
from typing import Dict, List


VocabularyEntry = Dict[str, str]
HARD_WORDS_FILENAME = "hard_words.csv"
HARD_WORDS_CHAPTER_TITLE = "\u4e0d\u6613\u8a18\u4f4f\u55ae\u5b57"


PUBLIC_COLUMNS = [
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


def build_markdown(entries: List[VocabularyEntry], target_date: date) -> str:
    lines = [
        f"# Daily Vocabulary - {target_date.isoformat()}",
        "",
        "航太 / 航電 / EMC 工程英文每日學習稿",
        "",
    ]
    for index, entry in enumerate(entries, start=1):
        lines.extend(
            [
                f"## {index}. {entry.get('word', '')}",
                "",
                f"**Pronunciation:** {entry.get('pronunciation', '')}",
                "",
                f"**Chinese meaning:** {entry.get('chinese_meaning', '')}",
                "",
                f"**Category:** {entry.get('category', '')}",
                "",
                f"**Difficulty:** {entry.get('difficulty', '')}",
                "",
                "**Example 1**",
                "",
                entry.get("example_1_en", ""),
                "",
                entry.get("example_1_zh", ""),
                "",
                "**Example 2**",
                "",
                entry.get("example_2_en", ""),
                "",
                entry.get("example_2_zh", ""),
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def build_daily_payload(
    entries: List[VocabularyEntry],
    target_date: date,
    per_word_audio: Dict[str, str],
    combined_audio: str,
) -> dict:
    words = []
    for index, entry in enumerate(entries, start=1):
        public_entry = {column: entry.get(column, "") for column in PUBLIC_COLUMNS}
        public_entry["index"] = index
        public_entry["audio"] = per_word_audio.get(
            audio_key_for_entry(entry),
            per_word_audio.get(entry.get("id", ""), ""),
        )
        words.append(public_entry)

    return {
        "date": target_date.isoformat(),
        "title": f"Daily Vocabulary - {target_date.isoformat()}",
        "combined_audio": combined_audio,
        "words": words,
    }


def build_chapter_payload(
    entries: List[VocabularyEntry],
    target_date: date,
    segment_audio: Dict[str, Dict[str, dict]],
    hard_words_write_url: str = "",
) -> dict:
    chapters = []
    chapters_by_source: Dict[str, dict] = {}
    flat_words = []

    for entry in entries:
        source_file = entry.get("_source_file", "")
        chapter_key = source_file or "vocabulary.csv"
        if chapter_key not in chapters_by_source:
            chapter = {
                "id": _chapter_id(chapter_key),
                "title": _chapter_title(chapter_key),
                "source_file": _source_name(chapter_key),
                "is_hard_words": _is_hard_words_source(chapter_key),
                "word_count": 0,
                "words": [],
            }
            chapters_by_source[chapter_key] = chapter
            chapters.append(chapter)

        chapter = chapters_by_source[chapter_key]
        public_entry = {column: entry.get(column, "") for column in PUBLIC_COLUMNS}
        public_entry["index"] = len(chapter["words"]) + 1
        public_entry["audio_segments"] = segment_audio.get(audio_key_for_entry(entry), {})
        chapter["words"].append(public_entry)
        chapter["word_count"] = len(chapter["words"])
        flat_words.append(public_entry)

    payload = {
        "date": target_date.isoformat(),
        "title": f"EVD Vocabulary Chapters - {target_date.isoformat()}",
        "mode": "chapters",
        "chapters": chapters,
        "words": flat_words,
    }
    if hard_words_write_url:
        payload["hard_words"] = {"write_url": hard_words_write_url}
    return payload


def audio_key_for_entry(entry: VocabularyEntry) -> str:
    source_file = entry.get("_source_file")
    row_number = entry.get("_row_number")
    if source_file and row_number is not None:
        return f"{source_file}#{row_number}"
    return entry.get("id", "")


def _chapter_title(source_file: str) -> str:
    if _is_hard_words_source(source_file):
        return HARD_WORDS_CHAPTER_TITLE
    return _source_path(source_file).stem or "vocabulary"


def _chapter_id(source_file: str) -> str:
    if _is_hard_words_source(source_file):
        return "hard-words"
    value = _chapter_title(source_file).lower()
    slug = "".join(character if character.isalnum() else "-" for character in value)
    return "-".join(part for part in slug.split("-") if part) or "vocabulary"


def _source_name(source_file: str) -> str:
    return _source_path(source_file).name or "vocabulary.csv"


def _is_hard_words_source(source_file: str) -> bool:
    return _source_name(source_file).lower() == HARD_WORDS_FILENAME


def _source_path(source_file: str):
    if "\\" in source_file:
        return PureWindowsPath(source_file)
    return Path(source_file)
