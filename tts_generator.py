import hashlib
import html
import re
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple

from abbreviation_expander import expand_abbreviations_for_speech
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


class AzureSpeechSynthesisError(RuntimeError):
    def __init__(self, output_file: Path, status_code: int | None, details: str) -> None:
        self.output_file = output_file
        self.status_code = status_code
        self.details = details
        status_text = f"status={status_code}; " if status_code is not None else ""
        super().__init__(
            f"Azure Speech synthesis failed for {output_file}; "
            f"{status_text}details={details}"
        )


class AzureSpeechQuotaExceeded(AzureSpeechSynthesisError):
    pass


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

    date_text = target_date.isoformat()
    word_audio_dir = settings.output_dir / "audio" / date_text
    word_audio_dir.mkdir(parents=True, exist_ok=True)

    generated_files = []
    for index, entry in enumerate(entries, start=1):
        relative_path = per_word_paths[audio_key_for_entry(entry)]
        output_file = settings.output_dir / relative_path
        output_file.parent.mkdir(parents=True, exist_ok=True)
        ssml = _entry_ssml(entry, settings)
        _synthesize_ssml(settings, ssml, output_file)
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

    generated_sources = set()
    pending_segments = []
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
            pending_segments.append((role, field_name, language, entry, output_file))

    if settings.max_audio_segments_per_run > 0:
        pending_segments = pending_segments[: settings.max_audio_segments_per_run]

    total_segments = len(pending_segments)
    for index, (role, field_name, language, entry, output_file) in enumerate(pending_segments, start=1):
        output_file.parent.mkdir(parents=True, exist_ok=True)
        ssml = _segment_ssml(entry.get(field_name, ""), language, settings)
        print(
            f"Synthesizing segment {index}/{total_segments}: "
            f"{language} {role} {entry.get('word', '')}",
            flush=True,
        )
        try:
            _synthesize_ssml(settings, ssml, output_file)
        except AzureSpeechQuotaExceeded as exc:
            print(
                "Azure Speech quota exhausted; stopping this run and publishing "
                f"available audio only. Last error: {exc.details}",
                flush=True,
            )
            break
    return _available_segment_audio_paths(segment_paths, settings)


def _should_synthesize_segment(output_file: Path) -> bool:
    return not output_file.exists() or output_file.stat().st_size == 0


def _available_segment_audio_paths(
    segment_paths: Dict[str, Dict[str, dict]],
    settings: Settings,
) -> Dict[str, Dict[str, dict]]:
    available_paths: Dict[str, Dict[str, dict]] = {}
    for entry_key, segments in segment_paths.items():
        available_segments = {}
        for role, segment in segments.items():
            output_file = settings.output_dir / segment["src"]
            if output_file.exists() and output_file.stat().st_size > 0:
                available_segments[role] = segment
        available_paths[entry_key] = available_segments
    return available_paths


def _combine_audio_files(source_files: List[Path], output_file: Path) -> None:
    # Azure rejects a large combined SSML after many English/Chinese voice switches.
    # MP3 frame concatenation works for the Azure MP3 files generated above.
    with output_file.open("wb") as combined:
        for source_file in source_files:
            combined.write(source_file.read_bytes())


def _synthesize_ssml(settings: Settings, ssml: str, output_file: Path) -> None:
    url = f"https://{settings.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
    request = urllib.request.Request(
        url,
        data=ssml.encode("utf-8"),
        headers={
            "Ocp-Apim-Subscription-Key": settings.azure_speech_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-32kbitrate-mono-mp3",
            "User-Agent": "EVD-Vocabulary",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=settings.azure_request_timeout_seconds,
        ) as response:
            output_file.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        error_detail = exc.read().decode("utf-8", errors="replace")
        error_type = (
            AzureSpeechQuotaExceeded
            if exc.code == 429 or "Quota Exceeded" in error_detail
            else AzureSpeechSynthesisError
        )
        raise error_type(output_file, exc.code, error_detail) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Azure Speech request failed for {output_file}: {exc}") from exc


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
    audio_language = "zh" if language else "en"
    escaped_text = _escape(_speech_text_for_audio(text, audio_language))
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
    key = f"{language}|{voice}|{rate}|{_speech_text_for_audio(text, language)}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return f"audio/segments/{language}/{digest}.mp3"


def _speech_text_for_audio(text: str, language: str) -> str:
    value = str(text or "").strip()
    if language == "zh":
        return value.replace("地", "第")
    return expand_abbreviations_for_speech(value)


