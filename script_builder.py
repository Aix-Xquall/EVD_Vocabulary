from datetime import date
from typing import Dict, List


VocabularyEntry = Dict[str, str]


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


def audio_key_for_entry(entry: VocabularyEntry) -> str:
    source_file = entry.get("_source_file")
    row_number = entry.get("_row_number")
    if source_file and row_number is not None:
        return f"{source_file}#{row_number}"
    return entry.get("id", "")
