import argparse
import hashlib
import html
import json
from pathlib import Path

from config import DEFAULT_SETTINGS, Settings
from tts_generator import SEGMENT_FIELDS, _combine_audio_files, _speech_text_for_audio, _synthesize_segment
from vocabulary_loader import load_vocabulary


GOOGLE_FEMALE_TEST_VOICES = [
    ("Neural2-C", "en-US-Neural2-C"),
    ("Neural2-E", "en-US-Neural2-E"),
    ("Neural2-F", "en-US-Neural2-F"),
    ("Neural2-G", "en-US-Neural2-G"),
    ("Neural2-H", "en-US-Neural2-H"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a small Azure TTS audio sample for listening tests.")
    parser.add_argument("--chapter", help="CSV chapter stem, for example EMC?芷閰??游?2.")
    parser.add_argument("--chapter-index", type=int, help="One-based index of the CSV chapter after filename sorting.")
    parser.add_argument("--limit", type=int, default=10, help="Number of words from the selected chapter.")
    parser.add_argument("--speech-rate", default="-20%", help="Azure prosody rate for English, e.g. -20% for about 0.8x.")
    parser.add_argument("--repeat-count", type=int, default=3, help="English segment repeat count in the combined sample.")
    parser.add_argument("--output-name", default="audio_sample", help="Folder name under output/audio_tests.")
    parser.add_argument("--title", default="", help="Title shown on the generated sample page.")
    parser.add_argument("--google-female-voice-test", action="store_true", help="Generate a five-voice Google female English comparison page.")
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
    title = args.title or f"{Path(entries[0].get('_source_file', '')).stem} first {len(entries)} words 0.8x audio test"
    if args.google_female_voice_test:
        result = generate_google_voice_comparison_sample(
            entries,
            output_dir,
            settings,
            args.repeat_count,
            args.output_name,
            title,
        )
    else:
        result = generate_audio_sample(entries, output_dir, settings, args.repeat_count, args.output_name, title)
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
        if chapter_name and chapter_name not in chapter_names:
            chapter_names.append(chapter_name)
    if chapter_index < 1 or chapter_index > len(chapter_names):
        raise ValueError(f"Chapter index {chapter_index} is outside 1..{len(chapter_names)}.")
    return select_chapter_entries(entries, chapter_names[chapter_index - 1], limit)


def estimate_synthesized_characters(entries: list[dict]) -> int:
    unique_segments = _unique_audio_segments(entries, DEFAULT_SETTINGS)
    return sum(len(_speech_text_for_audio(text, language)) for _, text, language in unique_segments)


def generate_audio_sample(
    entries: list[dict],
    output_dir: Path,
    settings: Settings,
    repeat_count: int,
    output_name: str = "audio_sample",
    title: str = "EVD Audio Test",
) -> dict:
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
        _synthesize_segment(settings, text, language, output_file)

    sequence = _playback_sequence(entries, repeat_count)
    combined_files = [segment_files[item] for item in sequence if item in segment_files]
    combined_path = output_dir / f"{output_name}.mp3"
    _combine_audio_files(combined_files, combined_path)
    _write_sample_page(output_dir, combined_path.name, entries, settings, repeat_count, synthesized_characters, title)

    return {
        "words": len(entries),
        "unique_segments": len(segment_files),
        "estimated_synthesized_characters": synthesized_characters,
        "combined_audio": str(combined_path),
        "page": str(output_dir / "index.html"),
    }


def generate_google_voice_comparison_sample(
    entries: list[dict],
    output_dir: Path,
    settings: Settings,
    repeat_count: int,
    output_name: str,
    title: str,
    voices: list[tuple[str, str]] | None = None,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_voices = voices or GOOGLE_FEMALE_TEST_VOICES
    audio_entries = _english_only_entries(entries)
    voice_results = []
    for label, voice_name in selected_voices:
        voice_settings = _replace_setting(
            settings,
            tts_provider="google",
            google_english_voice=voice_name,
        )
        voice_dir = output_dir / _safe_path_name(voice_name)
        result = generate_audio_sample(
            audio_entries,
            voice_dir,
            voice_settings,
            repeat_count,
            output_name=_safe_path_name(voice_name),
            title=f"{title} - {label} ({voice_name})",
        )
        voice_results.append(
            {
                "label": label,
                "voice": voice_name,
                "audio": f"{_safe_path_name(voice_name)}/{_safe_path_name(voice_name)}.mp3",
                "page": f"{_safe_path_name(voice_name)}/index.html",
                "estimated_synthesized_characters": result["estimated_synthesized_characters"],
            }
        )

    _write_comparison_page(output_dir, entries, title, selected_voices, voice_results, repeat_count)
    return {
        "words": len(entries),
        "voices": voice_results,
        "page": str(output_dir / "index.html"),
    }


def _english_only_entries(entries: list[dict]) -> list[dict]:
    audio_entries = []
    for entry in entries:
        audio_entry = dict(entry)
        audio_entry["chinese_meaning"] = ""
        audio_entry["example_1_zh"] = ""
        audio_entry["example_2_zh"] = ""
        audio_entries.append(audio_entry)
    return audio_entries


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


def _segment_filename(role: str, text: str, language: str, settings: Settings) -> str:
    rate = "0%" if language == "zh" else settings.speech_rate
    provider = str(settings.tts_provider or "azure").strip().lower()
    voice = _voice_name_for_sample(settings, language)
    key = f"{role}|{provider}|{voice}|{language}|{rate}|{_speech_text_for_audio(text, language)}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"{role}_{language}_{digest}.mp3"


def _voice_name_for_sample(settings: Settings, language: str) -> str:
    provider = str(settings.tts_provider or "azure").strip().lower()
    if provider == "google":
        return settings.google_chinese_voice if language == "zh" else settings.google_english_voice
    return settings.chinese_voice if language == "zh" else settings.english_voice


def _write_sample_page(
    output_dir: Path,
    audio_filename: str,
    entries: list[dict],
    settings: Settings,
    repeat_count: int,
    synthesized_characters: int,
    title: str,
) -> None:
    items = "\n".join(
        f"<li><strong>{html.escape(entry.get('word', ''))}</strong> - {html.escape(entry.get('chinese_meaning', ''))}</li>"
        for entry in entries
    )
    provider = html.escape(str(settings.tts_provider or "azure"))
    english_voice = html.escape(_voice_name_for_sample(settings, "en"))
    html_text = f"""<!doctype html>
<html lang=\"zh-Hant\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>EVD Audio Test</title>
  </head>
  <body>
    <h1>{html.escape(title)}</h1>
    <p>Provider: {provider}. English voice: {english_voice}. English rate: {html.escape(settings.speech_rate)}. English repeat count: {repeat_count}. Estimated synthesized characters: {synthesized_characters}.</p>
    <audio controls preload=\"metadata\" src=\"{html.escape(audio_filename)}\"></audio>
    <ol>{items}</ol>
  </body>
</html>
"""
    (output_dir / "index.html").write_text(html_text, encoding="utf-8")


def _write_comparison_page(
    output_dir: Path,
    entries: list[dict],
    title: str,
    voices: list[tuple[str, str]],
    voice_results: list[dict],
    repeat_count: int,
) -> None:
    players = "\n".join(
        (
            "<section>"
            f"<h2>{html.escape(result['label'])} - {html.escape(result['voice'])}</h2>"
            f"<audio controls preload=\"metadata\" src=\"{html.escape(result['audio'])}\"></audio>"
            f"<p><a href=\"{html.escape(result['page'])}\">Open detail page</a></p>"
            "</section>"
        )
        for result in voice_results
    )
    items = "\n".join(
        f"<li><strong>{html.escape(entry.get('word', ''))}</strong> - {html.escape(entry.get('chinese_meaning', ''))}</li>"
        for entry in entries
    )
    voice_text = ", ".join(voice for _, voice in voices)
    html_text = f"""<!doctype html>
<html lang=\"zh-Hant\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>{html.escape(title)}</title>
  </head>
  <body>
    <h1>{html.escape(title)}</h1>
    <p>Google English female voice comparison. Repeat count: {repeat_count}. Voices: {html.escape(voice_text)}.</p>
    {players}
    <h2>Words</h2>
    <ol>{items}</ol>
  </body>
</html>
"""
    (output_dir / "index.html").write_text(html_text, encoding="utf-8")


def _safe_path_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in value).strip("_") or "voice"


def _replace_setting(settings: Settings, **changes) -> Settings:
    values = settings.__dict__.copy()
    values.update(changes)
    return Settings(**values)


if __name__ == "__main__":
    main()
