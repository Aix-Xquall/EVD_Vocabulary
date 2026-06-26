import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    return int(value)


def _text_env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip()


@dataclass(frozen=True)
class Settings:
    vocabulary_dir: Path = Path(_text_env("EVD_VOCABULARY_DIR", str(BASE_DIR / "vocabulary")))
    output_dir: Path = Path(_text_env("EVD_OUTPUT_DIR", str(BASE_DIR / "output")))
    daily_word_count: int = _int_env("EVD_DAILY_WORD_COUNT", 20)
    speech_rate: str = _text_env("EVD_SPEECH_RATE", "0%")
    include_chinese_in_audio: bool = _bool_env("EVD_INCLUDE_CHINESE_AUDIO", True)
    repeat_each_word: bool = _bool_env("EVD_REPEAT_EACH_WORD", True)
    generate_audio: bool = _bool_env("EVD_GENERATE_AUDIO", True)
    max_audio_segments_per_run: int = _int_env("EVD_MAX_AUDIO_SEGMENTS_PER_RUN", 0)

    tts_provider: str = _text_env("EVD_TTS_PROVIDER", "azure")
    azure_speech_key: str = _text_env("AZURE_SPEECH_KEY")
    azure_speech_region: str = _text_env("AZURE_SPEECH_REGION")
    azure_request_timeout_seconds: int = _int_env("EVD_AZURE_REQUEST_TIMEOUT_SECONDS", 60)
    english_voice: str = _text_env("EVD_ENGLISH_VOICE", "en-US-JennyNeural")
    chinese_voice: str = _text_env("EVD_CHINESE_VOICE", "zh-TW-HsiaoChenNeural")
    google_english_voice: str = _text_env("GOOGLE_ENGLISH_VOICE", "en-US-Neural2-J")
    google_chinese_voice: str = _text_env("GOOGLE_CHINESE_VOICE", "cmn-TW-Wavenet-A")
    google_request_timeout_seconds: int = _int_env("EVD_GOOGLE_REQUEST_TIMEOUT_SECONDS", 60)

    line_channel_access_token: str = _text_env("LINE_CHANNEL_ACCESS_TOKEN")
    line_user_id: str = _text_env("LINE_USER_ID")
    site_url: str = _text_env("EVD_SITE_URL")

    hard_words_sheet_csv_url: str = _text_env("HARD_WORDS_SHEET_CSV_URL")
    hard_words_read_token: str = _text_env("HARD_WORDS_READ_TOKEN")
    hard_words_write_url: str = _text_env("HARD_WORDS_WRITE_URL")


DEFAULT_SETTINGS = Settings()
