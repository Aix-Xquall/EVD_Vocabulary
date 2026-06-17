import html
import re
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple

from config import Settings
from script_builder import audio_key_for_entry


VocabularyEntry = Dict[str, str]


def expected_audio_paths(
    entries: List[VocabularyEntry],
    target_date: date,
    output_dir: Path,
) -> Tuple[Dict[str, str], str]:
    date_text = target_date.isoformat()
    per_word = {}
    for index, entry in enumerate(entries, start=1):
        filename = f"{index:03d}_{_safe_filename(entry.get('word', 'word'))}.mp3"
        per_word[audio_key_for_entry(entry)] = f"audio/{date_text}/{filename}"
    combined = f"audio/{date_text}_daily_vocabulary.mp3"
    return per_word, combined


def generate_audio_files(
    entries: List[VocabularyEntry],
    target_date: date,
    settings: Settings,
) -> Tuple[Dict[str, str], str]:
    per_word_paths, combined_path = expected_audio_paths(entries, target_date, settings.output_dir)
    if not settings.generate_audio:
        return per_word_paths, combined_path

    if not settings.azure_speech_key or not settings.azure_speech_region:
        raise RuntimeError(
            "Azure Speech is enabled, but AZURE_SPEECH_KEY or AZURE_SPEECH_REGION is missing."
        )

    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError as exc:
        raise RuntimeError(
            "Azure Speech SDK is not installed. Run: pip install -r requirements.txt"
        ) from exc

    date_text = target_date.isoformat()
    word_audio_dir = settings.output_dir / "audio" / date_text
    word_audio_dir.mkdir(parents=True, exist_ok=True)

    for index, entry in enumerate(entries, start=1):
        relative_path = per_word_paths[audio_key_for_entry(entry)]
        output_file = settings.output_dir / relative_path
        output_file.parent.mkdir(parents=True, exist_ok=True)
        ssml = _entry_ssml(entry, settings)
        _synthesize_ssml(speechsdk, settings, ssml, output_file)

    combined_output = settings.output_dir / combined_path
    combined_output.parent.mkdir(parents=True, exist_ok=True)
    combined_ssml = _combined_ssml(entries, settings)
    _synthesize_ssml(speechsdk, settings, combined_ssml, combined_output)
    return per_word_paths, combined_path


def _synthesize_ssml(speechsdk, settings: Settings, ssml: str, output_file: Path) -> None:
    speech_config = speechsdk.SpeechConfig(
        subscription=settings.azure_speech_key,
        region=settings.azure_speech_region,
    )
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )
    audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_file))
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config,
    )
    result = synthesizer.speak_ssml_async(ssml).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        details = speechsdk.SpeechSynthesisCancellationDetails(result)
        raise RuntimeError(
            "Azure Speech synthesis failed for: "
            f"{output_file}; reason={result.reason}; "
            f"cancellation_reason={details.reason}; "
            f"error_code={details.error_code}; "
            f"error_details={details.error_details}"
        )


def _combined_ssml(entries: List[VocabularyEntry], settings: Settings) -> str:
    english_voice = html.escape(settings.english_voice)
    content = "\n<break time=\"1000ms\"/>\n".join(
        _entry_content(entry, settings) for entry in entries
    )
    body = "\n".join([f'<voice name="{english_voice}">', content, "</voice>"])
    return _wrap_ssml(body)


def _entry_ssml(entry: VocabularyEntry, settings: Settings) -> str:
    return _wrap_ssml(_entry_body(entry, settings))


def _entry_body(entry: VocabularyEntry, settings: Settings) -> str:
    english_voice = html.escape(settings.english_voice)
    return "\n".join(
        [
            f'<voice name="{english_voice}">',
            _entry_content(entry, settings),
            "</voice>",
        ]
    )


def _entry_content(entry: VocabularyEntry, settings: Settings) -> str:
    rate = html.escape(settings.speech_rate)

    parts = [
        f'<prosody rate="{rate}">{_escape(entry.get("word", ""))}</prosody>',
        '<break time="350ms"/>',
        f'<prosody rate="{rate}">{_escape(entry.get("pronunciation", ""))}</prosody>',
    ]
    if settings.include_chinese_in_audio:
        parts.extend(
            [
                '<break time="350ms"/>',
                f'<lang xml:lang="zh-TW"><prosody rate="{rate}">{_escape(entry.get("chinese_meaning", ""))}</prosody></lang>',
            ]
        )

    parts.extend(
        [
            '<break time="500ms"/>',
            f'<prosody rate="{rate}">{_escape(entry.get("example_1_en", ""))}</prosody>',
        ]
    )
    if settings.include_chinese_in_audio:
        parts.extend(
            [
                '<break time="350ms"/>',
                f'<lang xml:lang="zh-TW"><prosody rate="{rate}">{_escape(entry.get("example_1_zh", ""))}</prosody></lang>',
            ]
        )

    parts.extend(
        [
            '<break time="500ms"/>',
            f'<prosody rate="{rate}">{_escape(entry.get("example_2_en", ""))}</prosody>',
        ]
    )
    if settings.include_chinese_in_audio:
        parts.extend(
            [
                '<break time="350ms"/>',
                f'<lang xml:lang="zh-TW"><prosody rate="{rate}">{_escape(entry.get("example_2_zh", ""))}</prosody></lang>',
            ]
        )

    if settings.repeat_each_word:
        parts.extend(
            [
                '<break time="600ms"/>',
                f'<prosody rate="{rate}">{_escape(entry.get("word", ""))}</prosody>',
            ]
        )
    return "\n".join(parts)


def _wrap_ssml(body: str) -> str:
    return (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">'
        f"{body}</speak>"
    )


def _escape(value: str) -> str:
    return html.escape(str(value or "").strip())


def _safe_filename(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return name.strip("_") or "word"
