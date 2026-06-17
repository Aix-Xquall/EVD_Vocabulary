import argparse
import json
import shutil
from datetime import date, datetime
from pathlib import Path

from config import DEFAULT_SETTINGS, Settings
from daily_selector import select_daily_words
from line_notifier import send_daily_line_notification
from review_updater import update_review_files
from script_builder import build_daily_payload, build_markdown
from tts_generator import expected_audio_paths, generate_audio_files
from vocabulary_loader import load_vocabulary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate daily EVD vocabulary learning files.")
    parser.add_argument("--date", help="Target date in YYYY-MM-DD format. Defaults to today.")
    parser.add_argument("--skip-audio", action="store_true", help="Skip Azure Speech MP3 generation.")
    parser.add_argument("--skip-line", action="store_true", help="Skip LINE notification.")
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
    )
    print(f"Generated {len(result['words'])} words for {result['date']}")
    print(f"Markdown: {result['markdown_path']}")
    print(f"JSON: {result['json_path']}")


def run_daily_generation(
    settings: Settings,
    target_date: date,
    update_review: bool = True,
    notify_line: bool = True,
) -> dict:
    entries = load_vocabulary(settings.vocabulary_dir)
    selected = select_daily_words(entries, settings.daily_word_count, target_date)

    if settings.generate_audio:
        per_word_audio, combined_audio = generate_audio_files(selected, target_date, settings)
    else:
        per_word_audio, combined_audio = expected_audio_paths(selected, target_date, settings.output_dir)

    markdown = build_markdown(selected, target_date)
    payload = build_daily_payload(selected, target_date, per_word_audio, combined_audio)

    output_paths = _write_outputs(settings.output_dir, target_date, markdown, payload)
    _copy_web_files(settings.output_dir)

    if update_review:
        update_review_files(selected, target_date)

    if notify_line:
        send_daily_line_notification(
            settings,
            target_date.isoformat(),
            [entry.get("word", "") for entry in selected],
        )

    return {
        "date": target_date.isoformat(),
        "words": selected,
        "markdown_path": str(output_paths["markdown"]),
        "json_path": str(output_paths["json"]),
    }


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
