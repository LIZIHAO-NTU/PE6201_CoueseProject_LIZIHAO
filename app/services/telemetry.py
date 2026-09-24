from __future__ import annotations

from copy import deepcopy
from threading import Lock


class TelemetryStore:
    """Small in-memory telemetry store that never retains raw messages or API keys."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._calls = 0
        self._successes = 0
        self._fallbacks = 0
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._estimated_cost_usd = 0.0
        self._last_run: dict | None = None
        self._by_model: dict[str, dict] = {}

    def record(self, run: dict) -> None:
        safe_run = {
            key: value
            for key, value in run.items()
            if key not in {"api_key", "raw_message", "raw_response"}
        }
        with self._lock:
            self._calls += 1
            if safe_run.get("status") == "success":
                self._successes += 1
            else:
                self._fallbacks += 1
            self._prompt_tokens += int(safe_run.get("prompt_tokens") or 0)
            self._completion_tokens += int(safe_run.get("completion_tokens") or 0)
            self._estimated_cost_usd += float(safe_run.get("estimated_cost_usd") or 0.0)
            self._last_run = deepcopy(safe_run)
            model = str(safe_run.get("model") or "unknown")
            model_stats = self._by_model.setdefault(
                model,
                {
                    "calls": 0,
                    "successes": 0,
                    "fallbacks": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "estimated_cost_usd": 0.0,
                    "latency_total_ms": 0.0,
                    "latency_samples": 0,
                },
            )
            model_stats["calls"] += 1
            if safe_run.get("status") == "success":
                model_stats["successes"] += 1
            else:
                model_stats["fallbacks"] += 1
            model_stats["prompt_tokens"] += int(safe_run.get("prompt_tokens") or 0)
            model_stats["completion_tokens"] += int(safe_run.get("completion_tokens") or 0)
            model_stats["estimated_cost_usd"] += float(safe_run.get("estimated_cost_usd") or 0.0)
            if safe_run.get("latency_ms") is not None:
                model_stats["latency_total_ms"] += float(safe_run["latency_ms"])
                model_stats["latency_samples"] += 1

    def snapshot(self) -> dict:
        with self._lock:
            by_model = []
            for model, stats in self._by_model.items():
                by_model.append(
                    {
                        "model": model,
                        "calls": stats["calls"],
                        "successes": stats["successes"],
                        "fallbacks": stats["fallbacks"],
                        "total_tokens": stats["prompt_tokens"] + stats["completion_tokens"],
                        "estimated_cost_usd": round(stats["estimated_cost_usd"], 6),
                        "average_latency_ms": (
                            round(stats["latency_total_ms"] / stats["latency_samples"], 1)
                            if stats["latency_samples"]
                            else None
                        ),
                    }
                )
            return {
                "calls": self._calls,
                "successes": self._successes,
                "fallbacks": self._fallbacks,
                "prompt_tokens": self._prompt_tokens,
                "completion_tokens": self._completion_tokens,
                "total_tokens": self._prompt_tokens + self._completion_tokens,
                "estimated_cost_usd": round(self._estimated_cost_usd, 6),
                "last_run": deepcopy(self._last_run),
                "by_model": by_model,
            }

    def reset(self) -> None:
        with self._lock:
            self._calls = 0
            self._successes = 0
            self._fallbacks = 0
            self._prompt_tokens = 0
            self._completion_tokens = 0
            self._estimated_cost_usd = 0.0
            self._last_run = None
            self._by_model = {}


telemetry_store = TelemetryStore()
