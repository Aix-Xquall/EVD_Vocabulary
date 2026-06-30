import argparse
import json
import shutil
from datetime import date, datetime
from pathlib import Path

from config import DEFAULT_SETTINGS, Settings
from hard_words_sync import load_mastered_word_statuses, sync_hard_words
from line_notifier import send_daily_line_notification
from script_builder import build_chapter_payload, build_markdown
from tts_generator import expected_segment_audio_paths, generate_segment_audio_files
from vocabulary_loader import load_vocabulary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate daily EVD vocabulary learning files.")
    parser.add_argument("--date", help="Target date in YYYY-MM-DD format. Defaults to today.")
    parser.add_argument("--skip-audio", action="store_true", help="Skip Azure Speech MP3 generation.")
    parser.add_argument("--skip-line", action="store_true", help="Skip LINE notification.")
    parser.add_argument(
        "--force-line",
        action="store_true",
        help="Send LINE even when no new words were added.",
    )
    parser.add_argument("--no-update-review", action="store_true", help="Do not update CSV review metadata.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target_date = _parse_date(args.date) if args.date else date.today()
    settings = DEFAULT_SETTINGS
    if args.skip_audio:
        settings = _replace_setting(settings, generate_audio=False)

    result = run_daily_generation(
        settings=settings,
        target_date=target_date,
        update_review=not args.no_update_review,
        notify_line=not args.skip_line,
        force_line_notification=args.force_line,
    )
    print(f"Generated {result['word_count']} words for {result['date']}")
    print(f"Markdown: {result['markdown_path']}")
    print(f"JSON: {result['json_path']}")


def run_daily_generation(
    settings: Settings,
    target_date: date,
    update_review: bool = True,
    notify_line: bool = True,
    force_line_notification: bool = False,
) -> dict:
    sync_result = sync_hard_words(settings)
    if sync_result:
        source = "remote" if sync_result.used_remote else "local"
        print(f"Hard words snapshot: {sync_result.row_count} rows from {source}")

    entries = load_vocabulary(settings.vocabulary_dir)
    mastered_word_statuses = load_mastered_word_statuses(settings.vocabulary_dir)

    if settings.generate_audio:
        segment_audio = generate_segment_audio_files(entries, settings)
    else:
        segment_audio = expected_segment_audio_paths(entries, settings)

    previous_payload = _read_latest_payload(settings.output_dir)
    markdown = build_markdown(entries, target_date)
    payload = build_chapter_payload(
        entries,
        target_date,
        segment_audio,
        hard_words_write_url=settings.hard_words_write_url,
        mastered_word_statuses=mastered_word_statuses,
    )

    output_paths = _write_outputs(settings.output_dir, target_date, markdown, payload)
    _copy_web_files(settings.output_dir)

    if update_review:
        print("Review metadata is not updated in chapter mode.")

    notification_report = build_notification_report(previous_payload, payload)
    if notify_line and (
        force_line_notification or notification_report["new_word_count"] > 0
    ):
        try:
            send_daily_line_notification(
                settings,
                target_date.isoformat(),
                notification_report,
            )
        except RuntimeError as exc:
            print(f"LINE notification warning: {exc}")
    elif notify_line:
        print("LINE notification skipped: no new vocabulary words.")

    return {
        "date": target_date.isoformat(),
        "words": entries,
        "word_count": len(entries),
        "markdown_path": str(output_paths["markdown"]),
        "json_path": str(output_paths["json"]),
    }


def _read_latest_payload(output_dir: Path) -> dict | None:
    latest_path = output_dir / "data" / "latest.json"
    if not latest_path.exists():
        return None
    try:
        return json.loads(latest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Previous latest.json warning: {exc}")
        return None


def build_notification_report(previous_payload: dict | None, current_payload: dict) -> dict:
    previous_keys = _word_keys_by_chapter(previous_payload or {})
    current_keys = _word_keys_by_chapter(current_payload)
    previous_all = set().union(*previous_keys.values()) if previous_keys else set()
    new_chapter_names = []
    new_word_count = 0

    for chapter in current_payload.get("chapters", []):
        title = chapter.get("title", "")
        keys = current_keys.get(title, set())
        new_keys = keys - previous_all
        new_word_count += len(new_keys)
        if title and title not in previous_keys and keys:
            new_chapter_names.append(title)

    return {
        "new_word_count": new_word_count,
        "new_chapter_names": new_chapter_names,
    }


def _word_keys_by_chapter(payload: dict) -> dict[str, set[str]]:
    chapters = {}
    for chapter in payload.get("chapters", []):
        title = chapter.get("title", "")
        source_file = chapter.get("source_file", "")
        words = set()
        for word in chapter.get("words", []):
            words.add("|".join([source_file, str(word.get("id", "")), word.get("word", "")]))
        chapters[title] = words
    return chapters


def _write_outputs(output_dir: Path, target_date: date, markdown: str, payload: dict) -> dict:
    scripts_dir = output_dir / "scripts"
    data_dir = output_dir / "data"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    date_text = target_date.isoformat()
    markdown_path = scripts_dir / f"{date_text}_daily_vocabulary.md"
    json_path = data_dir / f"{date_text}_daily_vocabulary.json"
    latest_path = data_dir / "latest.json"

    markdown_path.write_text(markdown, encoding="utf-8")
    json_text = json.dumps(payload, ensure_ascii=False, indent=2)
    json_path.write_text(json_text + "\n", encoding="utf-8")
    latest_path.write_text(json_text + "\n", encoding="utf-8")
    return {"markdown": markdown_path, "json": json_path, "latest": latest_path}


def _copy_web_files(output_dir: Path) -> None:
    source_dir = Path(__file__).resolve().parent / "web"
    if not source_dir.exists():
        return
    for source in source_dir.iterdir():
        if source.is_file():
            shutil.copy2(source, output_dir / source.name)


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _replace_setting(settings: Settings, **changes) -> Settings:
    values = settings.__dict__.copy()
    values.update(changes)
    return Settings(**values)


if __name__ == "__main__":
    main()
