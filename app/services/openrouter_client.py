from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
KEY_STATUS_URL = "https://openrouter.ai/api/v1/key"


class OpenRouterError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


def _safe_error(error: Exception) -> str:
    if isinstance(error, HTTPError):
        return f"OpenRouter returned HTTP {error.code}"
    if isinstance(error, URLError):
        return "OpenRouter could not be reached"
    if isinstance(error, TimeoutError):
        return "OpenRouter request timed out"
    return "OpenRouter returned an invalid response"


def send_chat_completion(*, payload: dict, api_key: str, timeout: float) -> tuple[dict, float]:
    request = Request(
        CHAT_COMPLETIONS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost/scamlens-sg",
            "X-Title": "ScamLens SG student prototype",
        },
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        retryable = (
            isinstance(error, (URLError, TimeoutError))
            or isinstance(error, HTTPError) and (error.code == 429 or error.code >= 500)
        )
        raise OpenRouterError(_safe_error(error), retryable=retryable) from error
    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    if not isinstance(body, dict) or not body.get("choices"):
        raise OpenRouterError("OpenRouter returned an invalid response")
    return body, latency_ms


def get_key_status(*, api_key: str, timeout: float = 8.0) -> dict:
    request = Request(
        KEY_STATUS_URL,
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        return {"status": "unavailable", "message": _safe_error(error)}
    data = body.get("data", {}) if isinstance(body, dict) else {}
    return {
        "status": "available",
        "label": data.get("label"),
        "limit": data.get("limit"),
        "limit_remaining": data.get("limit_remaining"),
        "usage": data.get("usage"),
        "is_free_tier": data.get("is_free_tier"),
    }
