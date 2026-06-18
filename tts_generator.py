import hashlib
import html
import re
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple

from config import Settings
from script_builder import audio_key_for_entry


VocabularyEntry = Dict[str, str]


SEGMENT_FIELDS = [
    ("word", "word", "en"),
    ("meaning", "chinese_meaning", "zh"),
    ("example_1_en", "example_1_en", "en"),
    ("example_1_zh", "example_1_zh", "zh"),
    ("example_2_en", "example_2_en", "en"),
    ("example_2_zh", "example_2_zh", "zh"),
]


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

    generated_files = []
    for index, entry in enumerate(entries, start=1):
        relative_path = per_word_paths[audio_key_for_entry(entry)]
        output_file = settings.output_dir / relative_path
        output_file.parent.mkdir(parents=True, exist_ok=True)
        ssml = _entry_ssml(entry, settings)
        _synthesize_ssml(speechsdk, settings, ssml, output_file)
        generated_files.append(output_file)

    combined_output = settings.output_dir / combined_path
    combined_output.parent.mkdir(parents=True, exist_ok=True)
    _combine_audio_files(generated_files, combined_output)
    return per_word_paths, combined_path


def expected_segment_audio_paths(
    entries: List[VocabularyEntry],
    settings: Settings,
) -> Dict[str, Dict[str, dict]]:
    paths: Dict[str, Dict[str, dict]] = {}
    for entry in entries:
        entry_segments = {}
        for role, field_name, language in SEGMENT_FIELDS:
            if language == "zh" and not settings.include_chinese_in_audio:
                continue
            text = entry.get(field_name, "")
            if not text:
                continue
            relative_path = _segment_relative_path(text, language, settings)
            entry_segments[role] = {
                "src": relative_path,
                "language": language,
            }
        paths[audio_key_for_entry(entry)] = entry_segments
    return paths


def generate_segment_audio_files(
    entries: List[VocabularyEntry],
    settings: Settings,
) -> Dict[str, Dict[str, dict]]:
    segment_paths = expected_segment_audio_paths(entries, settings)
    if not settings.generate_audio:
        return segment_paths

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

    generated_sources = set()
    for entry in entries:
        for role, field_name, language in SEGMENT_FIELDS:
            segments = segment_paths.get(audio_key_for_entry(entry), {})
            segment = segments.get(role)
            if not segment or segment["src"] in generated_sources:
                continue
            generated_sources.add(segment["src"])
            output_file = settings.output_dir / segment["src"]
            if not _should_synthesize_segment(output_file):
                continue
            output_file.parent.mkdir(parents=True, exist_ok=True)
            ssml = _segment_ssml(entry.get(field_name, ""), language, settings)
            _synthesize_ssml(speechsdk, settings, ssml, output_file)
    return segment_paths


def _should_synthesize_segment(output_file: Path) -> bool:
    return not output_file.exists() or output_file.stat().st_size == 0


def _combine_audio_files(source_files: List[Path], output_file: Path) -> None:
    # Azure rejects a large combined SSML after many English/Chinese voice switches.
    # MP3 frame concatenation works for the Azure MP3 files generated above.
    with output_file.open("wb") as combined:
        for source_file in source_files:
            combined.write(source_file.read_bytes())


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
    separator = _voice_segment("", english_voice, settings.speech_rate, "1000ms")
    body = f"\n{separator}\n".join(_entry_content(entry, settings) for entry in entries)
    return _wrap_ssml(body)


def _entry_ssml(entry: VocabularyEntry, settings: Settings) -> str:
    return _wrap_ssml(_entry_body(entry, settings))


def _segment_ssml(text: str, language: str, settings: Settings) -> str:
    if language == "zh":
        return _wrap_ssml(_voice_segment(text, settings.chinese_voice, "0%", language="zh-TW"))
    return _wrap_ssml(_voice_segment(text, settings.english_voice, settings.speech_rate))


def _entry_body(entry: VocabularyEntry, settings: Settings) -> str:
    return _entry_content(entry, settings)


def _entry_content(entry: VocabularyEntry, settings: Settings) -> str:
    english_voice = html.escape(settings.english_voice)
    chinese_voice = html.escape(settings.chinese_voice)
    rate = settings.speech_rate

    parts = [
        _voice_segment(entry.get("word", ""), english_voice, rate, "350ms"),
    ]
    if settings.include_chinese_in_audio:
        parts.extend(
            [
                _voice_segment(
                    entry.get("chinese_meaning", ""),
                    chinese_voice,
                    rate,
                    "500ms",
                    "zh-TW",
                ),
            ]
        )

    parts.extend(
        [
            _voice_segment(entry.get("example_1_en", ""), english_voice, rate, "350ms"),
        ]
    )
    if settings.include_chinese_in_audio:
        parts.extend(
            [
                _voice_segment(
                    entry.get("example_1_zh", ""),
                    chinese_voice,
                    rate,
                    "500ms",
                    "zh-TW",
                ),
            ]
        )

    parts.extend(
        [
            _voice_segment(entry.get("example_2_en", ""), english_voice, rate, "350ms"),
        ]
    )
    if settings.include_chinese_in_audio:
        parts.extend(
            [
                _voice_segment(
                    entry.get("example_2_zh", ""),
                    chinese_voice,
                    rate,
                    "600ms",
                    "zh-TW",
                ),
            ]
        )

    if settings.repeat_each_word:
        parts.extend(
            [
                _voice_segment(entry.get("word", ""), english_voice, rate),
            ]
        )
    return "\n".join(parts)


def _voice_segment(
    text: str,
    voice: str,
    rate: str,
    break_time: str | None = None,
    language: str | None = None,
) -> str:
    escaped_rate = html.escape(rate)
    escaped_voice = html.escape(voice)
    escaped_text = _escape(text)
    if language:
        content = (
            f'<lang xml:lang="{html.escape(language)}">'
            f'<prosody rate="{escaped_rate}">{escaped_text}</prosody>'
            "</lang>"
        )
    elif escaped_text:
        content = f'<prosody rate="{escaped_rate}">{escaped_text}</prosody>'
    else:
        content = ""
    if break_time:
        content = f'{content}\n<break time="{html.escape(break_time)}"/>'.strip()
    return f'<voice name="{escaped_voice}">{content}</voice>'


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


def _segment_relative_path(text: str, language: str, settings: Settings) -> str:
    voice = settings.chinese_voice if language == "zh" else settings.english_voice
    rate = "0%" if language == "zh" else settings.speech_rate
    key = f"{language}|{voice}|{rate}|{str(text or '').strip()}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return f"audio/segments/{language}/{digest}.mp3"
