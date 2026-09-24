import json

from app.services.benchmark import run_benchmark
from app.services.evaluation_store import EvaluationStore


def _transport(**_kwargs):
    output = {
        "assessment": "likely_scam",
        "scam_type": "government_impersonation",
        "red_flags": ["Requests sensitive action"],
        "missing_context": ["Sender is not independently verified"],
        "evidence_ids_used": ["gov-safe-account-transfer"],
        "plain_language_explanation": "The message should be verified through an official channel.",
        "independent_verification_needed": True,
    }
    return {
        "model": "google/gemini-2.5-flash",
        "choices": [{"message": {"content": json.dumps(output)}}],
        "usage": {"prompt_tokens": 200, "completion_tokens": 50, "cost": 0.0002},
    }, 120.0


def test_cross_model_benchmark_persists_and_summarises_results(tmp_path):
    store = EvaluationStore(tmp_path / "evaluation.sqlite3", tmp_path / "exports")
    store.initialize()
    model = "google/gemini-2.5-flash"
    settings = {
        model: {
            "api_key": "test-key",
            "model": model,
            "max_output_tokens": 400,
            "timeout_seconds": 15,
            "budget_usd": 8.0,
            "input_cost_per_million": 0.30,
            "output_cost_per_million": 2.50,
        }
    }
    run_id = store.create_benchmark(
        dataset_id="sanity-v0.2",
        case_count=2,
        variants=["local", model],
        budget_cap_usd=0.10,
        estimated_max_cost_usd=0.01,
    )

    run_benchmark(
        store=store,
        run_id=run_id,
        dataset_id="sanity-v0.2",
        case_limit=2,
        variants=["local", model],
        settings_by_model=settings,
        budget_cap_usd=0.10,
        llm_transport=_transport,
    )

    run = store.get_benchmark(run_id)
    assert run["status"] == "completed"
    assert run["progress_completed"] == 4
    assert len(run["summary"]["variants"]) == 2
    llm_summary = next(item for item in run["summary"]["variants"] if item["variant"] == model)
    assert llm_summary["structured_output_success_rate"] == 1.0
    assert llm_summary["fallback_rate"] == 0.0
    assert llm_summary["total_tokens"] == 500
    assert llm_summary["estimated_cost_usd"] == 0.0004
    assert (store.export_dir / f"benchmark_{run_id}.json").exists()
