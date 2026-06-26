import json
import urllib.error
import urllib.request

from config import Settings
from tts_usage import build_azure_tts_quota_summary, build_google_tts_quota_summary


LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
LINE_QUOTA_URL = "https://api.line.me/v2/bot/message/quota"
LINE_QUOTA_CONSUMPTION_URL = "https://api.line.me/v2/bot/message/quota/consumption"


def send_daily_line_notification(
    settings: Settings,
    target_date: str,
    report: dict | None = None,
) -> bool:
    """Send one LINE push message to the configured user."""
    if not settings.line_channel_access_token or not settings.line_user_id:
        return False

    notification_report = dict(report or {})
    notification_report.setdefault("google_tts_remaining", build_google_tts_quota_summary(settings))
    notification_report.setdefault("azure_speech_remaining", build_azure_tts_quota_summary(settings))
    notification_report.setdefault("line_quota_remaining", fetch_line_quota_summary(settings))
    message = build_daily_line_message(settings, notification_report, target_date)
    payload = {
        "to": settings.line_user_id,
        "messages": [{"type": "text", "text": message}],
    }
    request = urllib.request.Request(
        LINE_PUSH_URL,
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


def build_daily_line_message(
    settings: Settings,
    report: dict,
    target_date: str | None = None,
) -> str:
    new_chapters = report.get("new_chapter_names") or []
    chapter_text = ", ".join(new_chapters) if new_chapters else "無"
    date_line = f"日期：{target_date}\n" if target_date else ""
    return (
        "EVD Vocabulary 每日更新\n\n"
        f"{date_line}"
        f"新增單字量：{report.get('new_word_count', 0)}\n"
        f"新增章節名稱：{chapter_text}\n"
        f"Cloud Text-to-Speech 免費剩餘量：{_quota_text(report.get('google_tts_remaining') or settings.google_tts_free_remaining)}\n"
        f"Azure Free F0 剩餘量：{_quota_text(report.get('azure_speech_remaining') or settings.azure_speech_free_remaining)}\n"
        f"LINE 通知剩餘量：{report.get('line_quota_remaining') or '無法自動查詢'}\n\n"
        f"網站連結：{settings.site_url or 'GitHub Pages site URL is not configured.'}"
    )


def fetch_line_quota_summary(settings: Settings) -> str:
    if not settings.line_channel_access_token:
        return "未設定 LINE token"
    headers = {"Authorization": f"Bearer {settings.line_channel_access_token}"}
    try:
        quota = _line_get_json(LINE_QUOTA_URL, headers)
        consumption = _line_get_json(LINE_QUOTA_CONSUMPTION_URL, headers)
    except RuntimeError as exc:
        return f"無法自動查詢（{exc}）"

    total_usage = int(consumption.get("totalUsage") or 0)
    if quota.get("type") == "limited":
        monthly_limit = int(quota.get("value") or 0)
        remaining = max(monthly_limit - total_usage, 0)
        return f"剩餘 {remaining} 則 / 本月上限 {monthly_limit} 則"
    if quota.get("type") == "none":
        return f"無上限 / 本月已用 {total_usage} 則"
    return f"本月已用 {total_usage} 則 / quota type: {quota.get('type', 'unknown')}"


def _line_get_json(url: str, headers: dict) -> dict:
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LINE API HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(str(exc)) from exc


def _quota_text(value: str) -> str:
    return value or "未設定（請用 GitHub Variables 手動填入）"
