import json
import urllib.error
import urllib.request
from typing import Iterable

from config import Settings


def send_daily_line_notification(
    settings: Settings,
    target_date: str,
    words: Iterable[str],
) -> bool:
    """Send a LINE push message to one configured user."""
    if not settings.line_channel_access_token or not settings.line_user_id:
        return False

    word_preview = ", ".join(list(words)[:8])
    link = settings.site_url or "GitHub Pages site URL is not configured."
    message = (
        f"今日航太 / 航電 / EMC 英文單字已更新\n\n"
        f"日期：{target_date}\n"
        f"單字：{word_preview}\n\n"
        f"開始練習：\n{link}"
    )
    payload = {
        "to": settings.line_user_id,
        "messages": [{"type": "text", "text": message}],
    }
    request = urllib.request.Request(
        "https://api.line.me/v2/bot/message/push",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.line_channel_access_token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return 200 <= response.status < 300
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LINE notification failed: {exc}") from exc
