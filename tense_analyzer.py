import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Dict, Iterable

from config import Settings
from script_builder import audio_key_for_entry


TENSE_NAMES_ZH = [
    "現在簡單式",
    "現在進行式",
    "現在完成式",
    "現在完成進行式",
    "過去簡單式",
    "過去進行式",
    "過去完成式",
    "過去完成進行式",
    "未來簡單式",
    "未來進行式",
    "未來完成式",
    "未來完成進行式",
    "特殊句型/需確認",
]

TENSE_FORMULAS = {
    "現在簡單式": "S + V / V-s",
    "現在進行式": "S + am / is / are + V-ing",
    "現在完成式": "S + have / has + p.p.",
    "現在完成進行式": "S + have / has been + V-ing",
    "過去簡單式": "S + V-ed / irregular past",
    "過去進行式": "S + was / were + V-ing",
    "過去完成式": "S + had + p.p.",
    "過去完成進行式": "S + had been + V-ing",
    "未來簡單式": "S + will + V",
    "未來進行式": "S + will be + V-ing",
    "未來完成式": "S + will have + p.p.",
    "未來完成進行式": "S + will have been + V-ing",
    "特殊句型/需確認": "非典型十二時態或需要人工確認",
}

EMPTY_ANALYSIS = {
    "name_zh": "",
    "formula": "",
    "highlights": [],
    "confidence": 0.0,
}

Analyzer = Callable[[str], dict]


def analyze_tenses_for_entries(
    entries: Iterable[dict],
    settings: Settings,
    analyzer: Analyzer | None = None,
) -> Dict[str, Dict[str, dict]]:
    cache_path = settings.tense_cache_path
    cache = _read_cache(cache_path)
    examples = cache.setdefault("examples", {})
    result: Dict[str, Dict[str, dict]] = {}
    missing_count = 0

    for entry in entries:
        entry_key = audio_key_for_entry(entry)
        for example_index in (1, 2):
            text = str(entry.get(f"example_{example_index}_en") or "").strip()
            if not text:
                continue
            cache_key = _cache_key(text)
            cached = examples.get(cache_key)
            if not cached and _can_analyze(settings, analyzer):
                if settings.max_tense_analysis_per_run and missing_count >= settings.max_tense_analysis_per_run:
                    continue
                try:
                    sentence_analyzer = analyzer or (lambda sentence: _openai_analyze_sentence(sentence, settings))
                    analysis = _sanitize_analysis(sentence_analyzer(text), text)
                except RuntimeError as exc:
                    print(f"Tense analysis warning: {exc}")
                    continue
                examples[cache_key] = {"text": text, "analysis": analysis}
                cached = examples[cache_key]
                missing_count += 1
            if cached:
                result.setdefault(entry_key, {})[f"example_{example_index}"] = cached.get("analysis", EMPTY_ANALYSIS)

    if missing_count > 0:
        _write_cache(cache_path, cache)
        print(f"Tense analysis: cached {missing_count} new examples.")
    elif not settings.openai_api_key and analyzer is None:
        print("Tense analysis skipped: OPENAI_API_KEY is not set.")
    return result


def _can_analyze(settings: Settings, analyzer: Analyzer | None) -> bool:
    return settings.analyze_tenses and (analyzer is not None or bool(settings.openai_api_key))


def _openai_analyze_sentence(sentence: str, settings: Settings) -> dict:
    payload = {
        "model": settings.tense_model,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Analyze the main tense of one English engineering example sentence. "
                            "Return Traditional Chinese labels. Choose one of the 12 English tenses when clear. "
                            "If the sentence is imperative, modal-only, passive without clear tense, fragment, or ambiguous, "
                            "use 特殊句型/需確認 instead of forcing a wrong tense. "
                            "highlights must be exact substrings copied from the sentence that show the tense or special pattern."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": sentence}],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "tense_analysis",
                "strict": True,
                "schema": _response_schema(),
            }
        },
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.openai_request_timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"OpenAI request failed: {exc}") from exc

    text = _extract_response_text(data)
    if not text:
        raise RuntimeError("OpenAI response did not include JSON text.")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"OpenAI response was not valid JSON: {text[:200]}") from exc


def _response_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["name_zh", "formula", "highlights", "confidence"],
        "properties": {
            "name_zh": {"type": "string", "enum": TENSE_NAMES_ZH},
            "formula": {"type": "string"},
            "highlights": {
                "type": "array",
                "items": {"type": "string"},
            },
            "confidence": {"type": "number"},
        },
    }


def _extract_response_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                return content["text"]
    return ""


def _sanitize_analysis(value: dict, sentence: str) -> dict:
    if not isinstance(value, dict):
        return EMPTY_ANALYSIS.copy()
    name = str(value.get("name_zh") or "特殊句型/需確認").strip()
    if name not in TENSE_NAMES_ZH:
        name = "特殊句型/需確認"
    formula = str(value.get("formula") or TENSE_FORMULAS[name]).strip() or TENSE_FORMULAS[name]
    highlights = []
    for highlight in value.get("highlights") or []:
        text = str(highlight).strip()
        if text and text in sentence and text not in highlights:
            highlights.append(text)
    try:
        confidence = float(value.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = min(1.0, max(0.0, confidence))
    return {
        "name_zh": name,
        "formula": formula,
        "highlights": highlights,
        "confidence": confidence,
    }


def _cache_key(text: str) -> str:
    normalized = " ".join(text.strip().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _read_cache(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "examples": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Tense cache warning: {exc}")
        return {"version": 1, "examples": {}}
    if not isinstance(data, dict):
        return {"version": 1, "examples": {}}
    data.setdefault("version", 1)
    if not isinstance(data.get("examples"), dict):
        data["examples"] = {}
    return data


def _write_cache(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")