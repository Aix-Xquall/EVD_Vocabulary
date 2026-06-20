import argparse
import hashlib
import html
import json
from pathlib import Path

from config import DEFAULT_SETTINGS, Settings
from tts_generator import SEGMENT_FIELDS, _combine_audio_files, _speech_text_for_audio, _synthesize_ssml, _voice_segment, _wrap_ssml
from vocabulary_loader import load_vocabulary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a small Azure TTS audio sample for listening tests.")
    parser.add_argument("--chapter", help="CSV chapter stem, for example EMC航電詞彙整合2.")
    parser.add_argument("--chapter-index", type=int, help="One-based index of the CSV chapter after filename sorting.")
    parser.add_argument("--limit", type=int, default=10, help="Number of words from the selected chapter.")
    parser.add_argument("--speech-rate", default="-20%", help="Azure prosody rate for English, e.g. -20% for about 0.8x.")
    parser.add_argument("--repeat-count", type=int, default=3, help="English segment repeat count in the combined sample.")
    parser.add_argument("--output-name", default="audio_sample", help="Folder name under output/audio_tests.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = _replace_setting(DEFAULT_SETTINGS, speech_rate=args.speech_rate)
    all_entries = load_vocabulary(settings.vocabulary_dir)
    if args.chapter_index:
        entries = select_chapter_entries_by_index(all_entries, args.chapter_index, args.limit)
    elif args.chapter:
        entries = select_chapter_entries(all_entries, args.chapter, args.limit)
    else:
        raise ValueError("Either --chapter or --chapter-index is required.")
    output_dir = settings.output_dir / "audio_tests" / args.output_name
    result = generate_audio_sample(entries, output_dir, settings, args.repeat_count)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def select_chapter_entries(entries: list[dict], chapter: str, limit: int) -> list[dict]:
    selected = [
        entry for entry in entries
        if Path(entry.get("_source_file", "")).stem == chapter
    ]
    if not selected:
        raise ValueError(f"No entries found for chapter: {chapter}")
    return selected[:limit]


def select_chapter_entries_by_index(entries: list[dict], chapter_index: int, limit: int) -> list[dict]:
    chapter_names = []
    for entry in entries:
        chapter_name = Path(entry.get("_source_file", "")).stem
        if chapter_name and chapter_name.lower() != "sample vocabulary" and chapter_name not in chapter_names:
            chapter_names.append(chapter_name)
    if chapter_index < 1 or chapter_index > len(chapter_names):
        raise ValueError(f"Chapter index {chapter_index} is outside 1..{len(chapter_names)}.")
    return select_chapter_entries(entries, chapter_names[chapter_index - 1], limit)


def estimate_synthesized_characters(entries: list[dict]) -> int:
    unique_segments = _unique_audio_segments(entries, DEFAULT_SETTINGS)
    return sum(len(_speech_text_for_audio(text, language)) for _, text, language in unique_segments)


def generate_audio_sample(entries: list[dict], output_dir: Path, settings: Settings, repeat_count: int) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    segments_dir = output_dir / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    segment_files = {}
    synthesized_characters = 0
    for role, text, language in _unique_audio_segments(entries, settings):
        filename = _segment_filename(role, text, language, settings)
        output_file = segments_dir / filename
        segment_files[(role, text, language)] = output_file
        synthesized_characters += len(_speech_text_for_audio(text, language))
        if output_file.exists() and output_file.stat().st_size > 0:
            continue
        _synthesize_ssml(settings, _sample_segment_ssml(text, language, settings), output_file)

    sequence = _playback_sequence(entries, repeat_count)
    combined_files = [segment_files[item] for item in sequence if item in segment_files]
    combined_path = output_dir / "emc2_first10_0_8.mp3"
    _combine_audio_files(combined_files, combined_path)
    _write_sample_page(output_dir, combined_path.name, entries, settings, repeat_count, synthesized_characters)

    return {
        "words": len(entries),
        "unique_segments": len(segment_files),
        "estimated_synthesized_characters": synthesized_characters,
        "combined_audio": str(combined_path),
        "page": str(output_dir / "index.html"),
    }


def _unique_audio_segments(entries: list[dict], settings: Settings) -> list[tuple[str, str, str]]:
    seen = set()
    segments = []
    for entry in entries:
        for role, field_name, language in SEGMENT_FIELDS:
            text = entry.get(field_name, "")
            if not text:
                continue
            key = (role, _speech_text_for_audio(text, language), language)
            if key in seen:
                continue
            seen.add(key)
            segments.append((role, text, language))
    return segments


def _playback_sequence(entries: list[dict], repeat_count: int) -> list[tuple[str, str, str]]:
    sequence = []
    for entry in entries:
        sequence.extend(_repeated_english_with_chinese(entry, "word", "word", "meaning", "chinese_meaning", repeat_count))
        sequence.extend(_repeated_english_with_chinese(entry, "example_1_en", "example_1_en", "example_1_zh", "example_1_zh", repeat_count))
        sequence.extend(_repeated_english_with_chinese(entry, "example_2_en", "example_2_en", "example_2_zh", "example_2_zh", repeat_count))
    return sequence


def _repeated_english_with_chinese(
    entry: dict,
    english_role: str,
    english_field: str,
    chinese_role: str,
    chinese_field: str,
    repeat_count: int,
) -> list[tuple[str, str, str]]:
    sequence = []
    english_text = entry.get(english_field, "")
    chinese_text = entry.get(chinese_field, "")
    if english_text:
        sequence.append((english_role, english_text, "en"))
    if chinese_text:
        sequence.append((chinese_role, chinese_text, "zh"))
    for _ in range(max(1, repeat_count) - 1):
        if english_text:
            sequence.append((english_role, english_text, "en"))
    return sequence


def _sample_segment_ssml(text: str, language: str, settings: Settings) -> str:
    if language == "zh":
        body = _voice_segment(text, settings.chinese_voice, "0%", "700ms", "zh-TW")
    else:
        body = _voice_segment(text, settings.english_voice, settings.speech_rate, "700ms")
    return _wrap_ssml(body)


def _segment_filename(role: str, text: str, language: str, settings: Settings) -> str:
    rate = "0%" if language == "zh" else settings.speech_rate
    key = f"{role}|{language}|{rate}|{_speech_text_for_audio(text, language)}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"{role}_{language}_{digest}.mp3"


def _write_sample_page(
    output_dir: Path,
    audio_filename: str,
    entries: list[dict],
    settings: Settings,
    repeat_count: int,
    synthesized_characters: int,
) -> None:
    items = "\n".join(
        f"<li><strong>{html.escape(entry.get('word', ''))}</strong> - {html.escape(entry.get('chinese_meaning', ''))}</li>"
        for entry in entries
    )
    html_text = f"""<!doctype html>
<html lang=\"zh-Hant\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>EVD Audio Test</title>
  </head>
  <body>
    <h1>EMC航電詞彙整合2 前 10 個 0.8 語速測試</h1>
    <p>English Azure prosody rate: {html.escape(settings.speech_rate)}. English repeat count: {repeat_count}. Estimated synthesized characters: {synthesized_characters}.</p>
    <audio controls preload=\"metadata\" src=\"{html.escape(audio_filename)}\"></audio>
    <ol>{items}</ol>
  </body>
</html>
"""
    (output_dir / "index.html").write_text(html_text, encoding="utf-8")


def _replace_setting(settings: Settings, **changes) -> Settings:
    values = settings.__dict__.copy()
    values.update(changes)
    return Settings(**values)


if __name__ == "__main__":
    main()
