import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from config import Settings


USAGE_FILE_NAME = "tts_usage.json"
AZURE_TOKEN_SCOPE = "https://management.azure.com/.default"
AZURE_MANAGEMENT_ENDPOINT = "https://management.azure.com"
GOOGLE_CLOUD_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
GOOGLE_MONITORING_ENDPOINT = "https://monitoring.googleapis.com"


def record_tts_synthesis_usage(
    settings: Settings,
    provider: str,
    character_count: int,
    target_date: date | None = None,
) -> None:
    """Record successful TTS synthesis characters for local monthly accounting."""
    if character_count <= 0:
        return

    usage_date = target_date or date.today()
    month_key = usage_date.strftime("%Y-%m")
    provider_key = str(provider or "").strip().lower()
    if not provider_key:
        return

    path = _usage_file_path(settings.output_dir)
    payload = _read_usage_payload(path)
    month = payload.setdefault("months", {}).setdefault(month_key, {"providers": {}})
    provider_payload = month.setdefault("providers", {}).setdefault(
        provider_key,
        {"characters": 0},
    )
    provider_payload["characters"] = int(provider_payload.get("characters") or 0) + int(
        character_count
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_google_tts_quota_summary(settings: Settings, target_date: date | None = None) -> str:
    usage_date = target_date or date.today()
    try:
        used = fetch_google_tts_quota_usage(settings, usage_date)
    except RuntimeError:
        if settings.google_tts_free_remaining:
            return settings.google_tts_free_remaining
        used = _monthly_provider_characters(settings.output_dir, usage_date, "google")
    limit = int(settings.google_tts_free_limit or 0)
    remaining = max(limit - used, 0)
    return f"{_format_number(remaining)} 字元 / 額度 {_format_number(limit)} 字元"


def build_azure_tts_quota_summary(settings: Settings, target_date: date | None = None) -> str:
    if not _has_azure_monitor_settings(settings):
        return settings.azure_speech_free_remaining or "未設定 Azure Monitor 權限"

    usage_date = target_date or date.today()
    try:
        used = fetch_azure_synthesized_characters(settings, usage_date)
    except RuntimeError as exc:
        if settings.azure_speech_free_remaining:
            return settings.azure_speech_free_remaining
        return f"無法自動查詢（{exc}）"

    limit = int(settings.azure_speech_free_limit or 0)
    remaining = max(limit - used, 0)
    return f"{_format_number(remaining)} 字元 / 額度 {_format_number(limit)} 字元"


def fetch_azure_synthesized_characters(settings: Settings, target_date: date) -> int:
    token = _fetch_azure_access_token(settings)
    metrics = _fetch_azure_speech_metrics(settings, token, target_date)
    total = 0
    for metric in metrics.get("value", []):
        for series in metric.get("timeseries", []):
            for point in series.get("data", []):
                total += int(point.get("total") or 0)
    return total


def fetch_google_tts_quota_usage(settings: Settings, target_date: date) -> int:
    """Read actual Google Cloud TTS quota usage from Cloud Monitoring."""
    token, project_id = _fetch_google_access_token_and_project(settings)
    if not project_id:
        raise RuntimeError("Google Cloud project id is not configured")

    metrics = _fetch_google_tts_monitoring_metrics(settings, token, project_id, target_date)
    total = 0
    for series in metrics.get("timeSeries", []):
        for point in series.get("points", []):
            value = point.get("value", {})
            if "int64Value" in value:
                total += int(value["int64Value"])
            elif "doubleValue" in value:
                total += int(float(value["doubleValue"]))
    return total


def _fetch_google_access_token_and_project(settings: Settings) -> tuple[str, str]:
    try:
        import google.auth
        import google.auth.transport.requests
    except ImportError as exc:
        raise RuntimeError("google-auth is not installed") from exc

    try:
        credentials, default_project_id = google.auth.default(scopes=[GOOGLE_CLOUD_SCOPE])
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
    except Exception as exc:  # pragma: no cover - depends on local/cloud credential setup.
        raise RuntimeError(f"Google credentials unavailable: {exc}") from exc

    token = getattr(credentials, "token", "")
    if not token:
        raise RuntimeError("Google credentials did not return an access token")
    project_id = settings.google_cloud_project_id or default_project_id or ""
    return token, project_id


def _fetch_google_tts_monitoring_metrics(
    settings: Settings,
    token: str,
    project_id: str,
    target_date: date,
) -> dict:
    month_start = target_date.replace(day=1)
    next_day = target_date + timedelta(days=1)
    metric_filter = (
        'metric.type="serviceruntime.googleapis.com/quota/rate/net_usage" '
        'AND resource.type="consumer_quota" '
        'AND metric.labels.service="texttospeech.googleapis.com" '
        f'AND metric.labels.quota_metric="{settings.google_tts_quota_metric}"'
    )
    query = urllib.parse.urlencode(
        {
            "filter": metric_filter,
            "interval.startTime": f"{month_start.isoformat()}T00:00:00Z",
            "interval.endTime": f"{next_day.isoformat()}T00:00:00Z",
            "aggregation.alignmentPeriod": "86400s",
            "aggregation.perSeriesAligner": "ALIGN_SUM",
            "aggregation.crossSeriesReducer": "REDUCE_SUM",
        }
    )
    quoted_project_id = urllib.parse.quote(project_id, safe="")
    url = f"{GOOGLE_MONITORING_ENDPOINT}/v3/projects/{quoted_project_id}/timeSeries?{query}"
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    return _urlopen_json(request, "Google Cloud Monitoring metrics")


def _fetch_azure_access_token(settings: Settings) -> str:
    url = f"https://login.microsoftonline.com/{urllib.parse.quote(settings.azure_tenant_id)}/oauth2/v2.0/token"
    body = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": settings.azure_client_id,
            "client_secret": settings.azure_client_secret,
            "scope": AZURE_TOKEN_SCOPE,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    response = _urlopen_json(request, "Azure token")
    token = response.get("access_token")
    if not token:
        raise RuntimeError("Azure token response missing access_token")
    return token


def _fetch_azure_speech_metrics(settings: Settings, token: str, target_date: date) -> dict:
    resource_id = (
        f"/subscriptions/{settings.azure_subscription_id}"
        f"/resourceGroups/{settings.azure_speech_resource_group}"
        f"/providers/Microsoft.CognitiveServices/accounts/{settings.azure_speech_resource_name}"
    )
    month_start = target_date.replace(day=1)
    next_day = target_date + timedelta(days=1)
    query = urllib.parse.urlencode(
        {
            "api-version": "2018-01-01",
            "metricnames": "SynthesizedCharacters",
            "aggregation": "Total",
            "timespan": f"{month_start.isoformat()}T00:00:00Z/{next_day.isoformat()}T00:00:00Z",
        }
    )
    url = f"{AZURE_MANAGEMENT_ENDPOINT}{resource_id}/providers/microsoft.insights/metrics?{query}"
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    return _urlopen_json(request, "Azure Monitor metrics")


def _urlopen_json(request: urllib.request.Request, label: str) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{label} HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{label} request failed: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} returned invalid JSON") from exc


def _monthly_provider_characters(output_dir: Path, target_date: date, provider: str) -> int:
    payload = _read_usage_payload(_usage_file_path(output_dir))
    month = payload.get("months", {}).get(target_date.strftime("%Y-%m"), {})
    provider_payload = month.get("providers", {}).get(provider, {})
    return int(provider_payload.get("characters") or 0)


def _usage_file_path(output_dir: Path) -> Path:
    return output_dir / "data" / USAGE_FILE_NAME


def _read_usage_payload(path: Path) -> dict:
    if not path.exists():
        return {"months": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"months": {}}
    if not isinstance(payload, dict):
        return {"months": {}}
    payload.setdefault("months", {})
    return payload


def _has_azure_monitor_settings(settings: Settings) -> bool:
    return all(
        [
            settings.azure_tenant_id,
            settings.azure_client_id,
            settings.azure_client_secret,
            settings.azure_subscription_id,
            settings.azure_speech_resource_group,
            settings.azure_speech_resource_name,
        ]
    )


def _format_number(value: int) -> str:
    return f"{int(value):,}"
