from threading import Thread

from flask import Blueprint, Response, current_app, jsonify, redirect, render_template, request, session, url_for

from .services.benchmark import DATASET_CATALOG, estimate_max_cost, load_cases, run_benchmark
from .services.evaluation_store import message_digest
from .services.model_catalog import MODEL_BY_ID, MODEL_PROFILES
from .services.openrouter_client import get_key_status
from .services.pipeline import analyse_message
from .services.retriever import corpus_summary
from .services.telemetry import telemetry_store


bp = Blueprint("main", __name__)


def _evaluation_store():
    return current_app.extensions["scamlens_evaluation_store"]


def _developer_mode() -> bool:
    return bool(
        current_app.config["SCAMLENS_ALLOW_DEV_MODE"]
        and session.get("developer_mode", False)
    )


def _llm_settings() -> dict:
    configured_model = current_app.config["SCAMLENS_LLM_MODEL"]
    selected_model = configured_model
    if _developer_mode() and session.get("developer_llm_model") in MODEL_BY_ID:
        selected_model = session["developer_llm_model"]
    profile = MODEL_BY_ID.get(selected_model)
    return {
        "api_key": current_app.config["OPENROUTER_API_KEY"],
        "model": selected_model,
        "max_output_tokens": current_app.config["SCAMLENS_LLM_MAX_OUTPUT_TOKENS"],
        "timeout_seconds": current_app.config["SCAMLENS_LLM_TIMEOUT_SECONDS"],
        "budget_usd": current_app.config["SCAMLENS_LLM_BUDGET_USD"],
        "input_cost_per_million": (
            profile["input_cost_per_million"]
            if profile
            else current_app.config["SCAMLENS_LLM_INPUT_COST_PER_MILLION"]
        ),
        "output_cost_per_million": (
            profile["output_cost_per_million"]
            if profile
            else current_app.config["SCAMLENS_LLM_OUTPUT_COST_PER_MILLION"]
        ),
    }


def _llm_settings_for_model(model_id: str) -> dict:
    profile = MODEL_BY_ID[model_id]
    return {
        "api_key": current_app.config["OPENROUTER_API_KEY"],
        "model": model_id,
        "max_output_tokens": current_app.config["SCAMLENS_LLM_MAX_OUTPUT_TOKENS"],
        "timeout_seconds": current_app.config["SCAMLENS_LLM_TIMEOUT_SECONDS"],
        "budget_usd": current_app.config["SCAMLENS_LLM_BUDGET_USD"],
        "input_cost_per_million": profile["input_cost_per_million"],
        "output_cost_per_million": profile["output_cost_per_million"],
    }


def _record_assessment(*, source: str, message: str, result: dict) -> None:
    _evaluation_store().record_assessment(
        source=source,
        message_hash=message_digest(message, current_app.config["SECRET_KEY"]),
        result=result,
    )


@bp.get("/")
def index():
    return render_template("index.html", result=None, llm_requested=False)


@bp.post("/analyse")
def analyse():
    message = request.form.get("message", "").strip()
    if not message:
        return render_template(
            "index.html",
            result=None,
            error="Paste a message before running the assessment.",
        ), 400

    use_llm = request.form.get("use_llm") == "on"
    result = analyse_message(
        message=message,
        clicked_link=request.form.get("clicked_link") == "on",
        shared_credentials=request.form.get("shared_credentials") == "on",
        transferred_money=request.form.get("transferred_money") == "on",
        use_llm=use_llm,
        developer_mode=_developer_mode(),
        llm_settings=_llm_settings(),
    )
    _record_assessment(source="web", message=message, result=result)
    return render_template(
        "index.html",
        result=result,
        original_message=message,
        llm_requested=use_llm,
    )


@bp.post("/api/v1/analyse")
def analyse_api():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    if not message:
        return jsonify({"error": "The message field is required."}), 400

    result = analyse_message(
        message=message,
        clicked_link=bool(payload.get("clicked_link", False)),
        shared_credentials=bool(payload.get("shared_credentials", False)),
        transferred_money=bool(payload.get("transferred_money", False)),
        use_llm=bool(payload.get("use_llm", False)),
        developer_mode=False,
        llm_settings=_llm_settings(),
    )
    _record_assessment(source="api", message=message, result=result)
    return jsonify(result)


@bp.get("/evaluation")
def evaluation():
    runs = _evaluation_store().list_benchmarks(limit=10)
    latest_completed = next(
        (run for run in runs if run["status"] in {"completed", "budget_stopped"}), None
    )
    return render_template(
        "evaluation.html",
        frozen_benchmark=_evaluation_store().latest_frozen_benchmark(),
        latest_benchmark=latest_completed,
    )


@bp.get("/about")
def about():
    return render_template("about.html")


@bp.post("/developer/toggle")
def toggle_developer_mode():
    if not current_app.config["SCAMLENS_ALLOW_DEV_MODE"]:
        return redirect(url_for("main.index"))
    session["developer_mode"] = not bool(session.get("developer_mode", False))
    if session["developer_mode"]:
        return redirect(url_for("main.developer"))
    return redirect(url_for("main.index"))


@bp.get("/developer")
def developer():
    if not _developer_mode():
        return redirect(url_for("main.index"))
    settings = _llm_settings()
    benchmarks = _evaluation_store().list_benchmarks(limit=10)
    started_run_id = request.args.get("benchmark_started")
    return render_template(
        "developer.html",
        telemetry=telemetry_store.snapshot(),
        persistent_telemetry=_evaluation_store().persistent_overview(),
        benchmarks=benchmarks,
        latest_benchmark=next(
            (run for run in benchmarks if run["summary"] is not None), None
        ),
        started_benchmark=(
            _evaluation_store().get_benchmark(started_run_id) if started_run_id else None
        ),
        dataset_catalog=DATASET_CATALOG,
        api_status=session.get("openrouter_api_status"),
        runtime={
            "model": settings["model"],
            "api_key_configured": bool(current_app.config["OPENROUTER_API_KEY"]),
            "max_output_tokens": current_app.config["SCAMLENS_LLM_MAX_OUTPUT_TOKENS"],
            "timeout_seconds": current_app.config["SCAMLENS_LLM_TIMEOUT_SECONDS"],
            "local_budget_usd": current_app.config["SCAMLENS_LLM_BUDGET_USD"],
            "benchmark_max_cases": current_app.config["SCAMLENS_BENCHMARK_MAX_CASES"],
            "benchmark_max_budget_usd": current_app.config[
                "SCAMLENS_BENCHMARK_MAX_BUDGET_USD"
            ],
            "rag": corpus_summary(),
        },
        model_profiles=MODEL_PROFILES,
    )


@bp.post("/developer/model")
def select_developer_model():
    if not _developer_mode():
        return redirect(url_for("main.index"))
    model_id = request.form.get("llm_model", "")
    if model_id not in MODEL_BY_ID:
        return jsonify({"error": "Unsupported developer model selection."}), 400
    session["developer_llm_model"] = model_id
    return redirect(url_for("main.developer"))


@bp.post("/developer/refresh-openrouter")
def refresh_openrouter_status():
    if not _developer_mode():
        return redirect(url_for("main.index"))
    api_key = current_app.config["OPENROUTER_API_KEY"]
    if api_key:
        session["openrouter_api_status"] = get_key_status(api_key=api_key)
    else:
        session["openrouter_api_status"] = {
            "status": "unavailable",
            "message": "OPENROUTER_API_KEY is not configured",
        }
    return redirect(url_for("main.developer"))


@bp.post("/developer/benchmark")
def start_benchmark():
    if not _developer_mode():
        return redirect(url_for("main.index"))

    dataset_id = request.form.get("dataset_id", "gold-v0.1")
    if dataset_id not in DATASET_CATALOG:
        return jsonify({"error": "Unsupported benchmark dataset."}), 400
    try:
        case_limit = int(request.form.get("case_limit", "10"))
        budget_cap = float(request.form.get("budget_cap_usd", "0.50"))
    except ValueError:
        return jsonify({"error": "Case limit and budget cap must be numeric."}), 400

    available_cases = len(load_cases(dataset_id))
    case_limit = min(case_limit, available_cases)
    if case_limit < 1 or case_limit > current_app.config["SCAMLENS_BENCHMARK_MAX_CASES"]:
        return jsonify({"error": "Case limit is outside the configured safe range."}), 400
    if budget_cap < 0 or budget_cap > current_app.config["SCAMLENS_BENCHMARK_MAX_BUDGET_USD"]:
        return jsonify({"error": "Budget cap is outside the configured safe range."}), 400

    selected_models = list(dict.fromkeys(request.form.getlist("models")))
    if any(model not in MODEL_BY_ID for model in selected_models):
        return jsonify({"error": "Unsupported model in benchmark request."}), 400
    if selected_models and not current_app.config["OPENROUTER_API_KEY"]:
        return jsonify({"error": "Configure OPENROUTER_API_KEY before an LLM benchmark."}), 400
    if selected_models and request.form.get("confirm_paid_calls") != "yes":
        return jsonify({"error": "Confirm the paid API calls before starting."}), 400

    settings_by_model = {
        model: _llm_settings_for_model(model) for model in selected_models
    }
    estimated_cost = estimate_max_cost(
        case_count=case_limit,
        model_settings=list(settings_by_model.values()),
    )
    if estimated_cost > budget_cap:
        return jsonify(
            {
                "error": (
                    f"Estimated maximum cost US${estimated_cost:.4f} exceeds the "
                    f"US${budget_cap:.4f} run cap. Reduce cases/models or raise the cap."
                )
            }
        ), 400

    variants = ["local", *selected_models]
    store = _evaluation_store()
    run_id = store.create_benchmark(
        dataset_id=dataset_id,
        case_count=case_limit,
        variants=variants,
        budget_cap_usd=budget_cap,
        estimated_max_cost_usd=estimated_cost,
    )
    run_kwargs = {
        "store": store,
        "run_id": run_id,
        "dataset_id": dataset_id,
        "case_limit": case_limit,
        "variants": variants,
        "settings_by_model": settings_by_model,
        "budget_cap_usd": budget_cap,
    }
    if current_app.config.get("SCAMLENS_BENCHMARK_SYNC"):
        run_benchmark(**run_kwargs)
    else:
        Thread(target=run_benchmark, kwargs=run_kwargs, daemon=True).start()
    return redirect(url_for("main.developer", benchmark_started=run_id))


@bp.post("/developer/benchmark/<run_id>/freeze")
def freeze_benchmark(run_id: str):
    if not _developer_mode():
        return redirect(url_for("main.index"))
    if not _evaluation_store().freeze_benchmark(run_id):
        return jsonify({"error": "Only a completed benchmark can be frozen."}), 400
    return redirect(url_for("main.developer"))


@bp.get("/developer/benchmark/<run_id>/export.<format_name>")
def export_benchmark(run_id: str, format_name: str):
    if not _developer_mode():
        return redirect(url_for("main.index"))
    if format_name == "json":
        content = _evaluation_store().export_json(run_id)
        mimetype = "application/json"
    elif format_name == "csv":
        content = _evaluation_store().export_csv(run_id)
        mimetype = "text/csv"
    else:
        return jsonify({"error": "Unsupported export format."}), 404
    if content is None:
        return jsonify({"error": "Benchmark run not found."}), 404
    return Response(
        content,
        mimetype=mimetype,
        headers={"Content-Disposition": f'attachment; filename="scamlens-{run_id}.{format_name}"'},
    )
