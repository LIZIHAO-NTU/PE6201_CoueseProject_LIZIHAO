from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, current_app, session


def _load_local_env() -> None:
    """Load this prototype's small .env file without adding a runtime dependency."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    allowed = {"OPENROUTER_API_KEY"}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in allowed and not key.startswith("SCAMLENS_"):
            continue
        os.environ.setdefault(key, value.strip().strip("\"'"))


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def create_app(test_config: dict | None = None) -> Flask:
    _load_local_env()
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SCAMLENS_SECRET_KEY", "dev-only-change-before-deployment"),
        MAX_CONTENT_LENGTH=32 * 1024,
        OPENROUTER_API_KEY=os.getenv("OPENROUTER_API_KEY", ""),
        SCAMLENS_LLM_MODEL=os.getenv("SCAMLENS_LLM_MODEL", "google/gemini-2.5-flash"),
        SCAMLENS_LLM_MAX_OUTPUT_TOKENS=int(os.getenv("SCAMLENS_LLM_MAX_OUTPUT_TOKENS", "400")),
        SCAMLENS_LLM_TIMEOUT_SECONDS=float(os.getenv("SCAMLENS_LLM_TIMEOUT_SECONDS", "15")),
        SCAMLENS_LLM_BUDGET_USD=float(os.getenv("SCAMLENS_LLM_BUDGET_USD", "8.0")),
        SCAMLENS_LLM_INPUT_COST_PER_MILLION=float(
            os.getenv("SCAMLENS_LLM_INPUT_COST_PER_MILLION", "0.30")
        ),
        SCAMLENS_LLM_OUTPUT_COST_PER_MILLION=float(
            os.getenv("SCAMLENS_LLM_OUTPUT_COST_PER_MILLION", "2.50")
        ),
        SCAMLENS_ALLOW_DEV_MODE=_env_bool("SCAMLENS_ALLOW_DEV_MODE", True),
        SCAMLENS_EVALUATION_DB=os.getenv(
            "SCAMLENS_EVALUATION_DB",
            str(Path(app.instance_path) / "scamlens_evaluation.sqlite3"),
        ),
        SCAMLENS_EVALUATION_EXPORT_DIR=os.getenv(
            "SCAMLENS_EVALUATION_EXPORT_DIR",
            str(Path(__file__).resolve().parents[1] / "outputs" / "evaluation" / "persistent"),
        ),
        SCAMLENS_BENCHMARK_MAX_CASES=int(os.getenv("SCAMLENS_BENCHMARK_MAX_CASES", "30")),
        SCAMLENS_BENCHMARK_MAX_BUDGET_USD=float(
            os.getenv("SCAMLENS_BENCHMARK_MAX_BUDGET_USD", "2.0")
        ),
        SCAMLENS_BENCHMARK_SYNC=False,
    )
    if test_config:
        app.config.update(test_config)

    from .routes import bp
    from .services.evaluation_store import EvaluationStore

    app.register_blueprint(bp)
    evaluation_store = EvaluationStore(
        app.config["SCAMLENS_EVALUATION_DB"],
        app.config["SCAMLENS_EVALUATION_EXPORT_DIR"],
    )
    evaluation_store.initialize()
    app.extensions["scamlens_evaluation_store"] = evaluation_store

    @app.context_processor
    def inject_runtime_flags() -> dict:
        developer_mode = bool(
            current_app.config["SCAMLENS_ALLOW_DEV_MODE"]
            and session.get("developer_mode", False)
        )
        return {
            "developer_mode": developer_mode,
            "developer_mode_available": current_app.config["SCAMLENS_ALLOW_DEV_MODE"],
            "llm_available": bool(current_app.config["OPENROUTER_API_KEY"]),
            "llm_model_name": current_app.config["SCAMLENS_LLM_MODEL"],
        }

    return app
