from __future__ import annotations

import os
from hmac import compare_digest
from pathlib import Path
from secrets import token_urlsafe

from flask import Flask, abort, current_app, request, session


APP_VERSION = "2.0"


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
        SCAMLENS_CSRF_ENABLED=_env_bool("SCAMLENS_CSRF_ENABLED", True),
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

    def csrf_token() -> str:
        token = session.get("_csrf_token")
        if not token:
            token = token_urlsafe(32)
            session["_csrf_token"] = token
        return token

    @app.before_request
    def verify_csrf_token():
        """Protect browser forms while leaving the JSON API available to API clients."""
        if (
            not current_app.config["SCAMLENS_CSRF_ENABLED"]
            or request.method != "POST"
            or request.endpoint == "main.analyse_api"
        ):
            return None
        expected = session.get("_csrf_token", "")
        provided = request.form.get("_csrf_token", "") or request.headers.get(
            "X-CSRF-Token", ""
        )
        if not expected or not provided or not compare_digest(
            str(expected), str(provided)
        ):
            abort(400, description="Invalid or missing CSRF token.")
        return None

    @app.after_request
    def apply_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), geolocation=(), microphone=()"
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; base-uri 'none'; connect-src 'self'; "
            "font-src 'self' https://fonts.gstatic.com; frame-ancestors 'none'; "
            "form-action 'self'; img-src 'self' data:; script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        )
        return response

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
            "csrf_token": csrf_token(),
            "app_version": APP_VERSION,
        }

    return app
