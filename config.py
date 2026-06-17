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


@dataclass(frozen=True)
class Settings:
    vocabulary_dir: Path = Path(os.getenv("EVD_VOCABULARY_DIR", str(BASE_DIR)))
    output_dir: Path = Path(os.getenv("EVD_OUTPUT_DIR", str(BASE_DIR / "output")))
    daily_word_count: int = _int_env("EVD_DAILY_WORD_COUNT", 20)
    speech_rate: str = os.getenv("EVD_SPEECH_RATE", "0%")
    include_chinese_in_audio: bool = _bool_env("EVD_INCLUDE_CHINESE_AUDIO", True)
    repeat_each_word: bool = _bool_env("EVD_REPEAT_EACH_WORD", True)
    generate_audio: bool = _bool_env("EVD_GENERATE_AUDIO", True)

    azure_speech_key: str = os.getenv("AZURE_SPEECH_KEY", "")
    azure_speech_region: str = os.getenv("AZURE_SPEECH_REGION", "")
    english_voice: str = os.getenv("EVD_ENGLISH_VOICE", "en-US-JennyNeural")
    chinese_voice: str = os.getenv("EVD_CHINESE_VOICE", "zh-TW-HsiaoChenNeural")

    line_channel_access_token: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    line_user_id: str = os.getenv("LINE_USER_ID", "")
    site_url: str = os.getenv("EVD_SITE_URL", "")


DEFAULT_SETTINGS = Settings()
