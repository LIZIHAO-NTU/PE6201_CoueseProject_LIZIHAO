from __future__ import annotations

import json
import statistics
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse

from .evaluation_store import EvaluationStore, message_digest
from .pipeline import analyse_message
from .retriever import RETRIEVER_VERSION, retrieve_evidence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_CATALOG = {
    "gold-v0.1": {
        "name": "Independent student-reviewed gold test",
        "path": PROJECT_ROOT / "data" / "eval" / "message_gold_test_v0.1.jsonl",
        "evidence_level": "Independent frozen evidence",
    },
    "sanity-v0.2": {
        "name": "AI-assisted regression sanity check",
        "path": PROJECT_ROOT / "data" / "eval" / "message_sanity_test_v0.2.jsonl",
        "evidence_level": "Regression/demo evidence only",
    },
}

COUNTERFACTUAL_TYPE = {
    "government_impersonation": "e_commerce",
    "investment": "job",
    "job": "government_impersonation",
    "e_commerce": "investment",
    "uncertain": "job",
}


class BenchmarkBudgetReached(RuntimeError):
    pass


def load_cases(dataset_id: str, limit: int | None = None) -> list[dict]:
    dataset = DATASET_CATALOG.get(dataset_id)
    if dataset is None:
        raise ValueError("Unsupported evaluation dataset")
    cases = [
        json.loads(line)
        for line in dataset["path"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return cases[:limit] if limit else cases


def estimate_max_cost(
    *,
    case_count: int,
    model_settings: list[dict],
    assumed_input_tokens: int = 1800,
) -> float:
    total = 0.0
    for settings in model_settings:
        total += case_count * (
            assumed_input_tokens / 1_000_000 * float(settings["input_cost_per_million"])
            + int(settings["max_output_tokens"])
            / 1_000_000
            * float(settings["output_cost_per_million"])
        )
    return round(total, 4)


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 1)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    value = ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
    return round(value, 1)


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def calculate_metrics(rows: list[dict]) -> dict:
    by_variant: dict[str, list[dict]] = {}
    for row in rows:
        by_variant.setdefault(row["system_variant"], []).append(row)

    summaries = []
    for variant, items in by_variant.items():
        scams = [row for row in items if row["gold_risk_label"] == "scam"]
        legitimate = [row for row in items if row["gold_risk_label"] == "legitimate"]
        ambiguous = [row for row in items if row["gold_risk_label"] == "ambiguous"]
        latencies = [
            float(row["total_latency_ms"])
            for row in items
            if row.get("total_latency_ms") is not None
        ]
        llm_rows = [row for row in items if row.get("llm_status")]
        summary = {
            "variant": variant,
            "model": items[0].get("model"),
            "cases": len(items),
            "exact_three_way_accuracy": _safe_ratio(
                sum(bool(row["exact_correct"]) for row in items), len(items)
            ),
            "operational_scam_recall": _safe_ratio(
                sum(row["predicted_risk_level"] in {"medium", "high"} for row in scams),
                len(scams),
            ),
            "high_risk_scam_recall": _safe_ratio(
                sum(row["predicted_risk_level"] == "high" for row in scams), len(scams)
            ),
            "legitimate_false_positive_rate": _safe_ratio(
                sum(row["predicted_risk_level"] in {"medium", "high"} for row in legitimate),
                len(legitimate),
            ),
            "ambiguous_abstention_recall": _safe_ratio(
                sum(row["predicted_risk_level"] == "medium" for row in ambiguous),
                len(ambiguous),
            ),
            "scam_type_accuracy": _safe_ratio(
                sum(bool(row["type_correct"]) for row in scams), len(scams)
            ),
            "critical_false_reassurance_count": sum(
                row["predicted_risk_level"] == "low" for row in scams
            ),
            "structured_output_success_rate": (
                _safe_ratio(sum(row["llm_status"] == "success" for row in llm_rows), len(llm_rows))
                if llm_rows
                else None
            ),
            "fallback_rate": (
                _safe_ratio(sum(row["llm_status"] != "success" for row in llm_rows), len(llm_rows))
                if llm_rows
                else None
            ),
            "average_latency_ms": round(statistics.mean(latencies), 1) if latencies else None,
            "p50_latency_ms": _percentile(latencies, 0.50),
            "p95_latency_ms": _percentile(latencies, 0.95),
            "prompt_tokens": sum(int(row.get("prompt_tokens") or 0) for row in items),
            "completion_tokens": sum(int(row.get("completion_tokens") or 0) for row in items),
            "total_tokens": sum(
                int(row.get("prompt_tokens") or 0) + int(row.get("completion_tokens") or 0)
                for row in items
            ),
            "estimated_cost_usd": round(
                sum(float(row.get("estimated_cost_usd") or 0) for row in items), 6
            ),
        }
        summaries.append(summary)
    return {"variants": summaries}


def evaluate_retrieval() -> dict:
    path = PROJECT_ROOT / "data" / "eval" / "retrieval_eval_v0.2.jsonl"
    cases = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = []
    for case in cases:
        results = retrieve_evidence(
            case["query"],
            case["primary_type"],
            limit=3,
            user_state=case.get("user_state"),
        )
        ids = [item["id"] for item in results]
        expected = set(case["expected_top1_ids"])
        reciprocal_rank = next(
            (1 / (rank + 1) for rank, item_id in enumerate(ids) if item_id in expected), 0.0
        )
        rows.append(
            {
                "top1": ids[0] in expected,
                "top3": bool(expected.intersection(ids)),
                "category": any(
                    case["required_scam_type"] in item["scam_types"] for item in results
                ),
                "action_stage": (
                    not case.get("required_action_stage")
                    or any(
                        case["required_action_stage"] in item["action_stages"]
                        for item in results
                    )
                ),
                "has_required_action_stage": bool(case.get("required_action_stage")),
                "reciprocal_rank": reciprocal_rank,
                "provenance": all(
                    item.get("last_verified_date")
                    and item.get("source_domain")
                    and item.get("match_reasons")
                    and urlparse(item["url"]).scheme == "https"
                    for item in results
                ),
            }
        )

    def sensitivity(mode: str) -> dict:
        top1 = 0
        top3 = 0
        for case in cases:
            supplied_type = (
                "" if mode == "without_type" else COUNTERFACTUAL_TYPE[case["primary_type"]]
            )
            ids = [
                item["id"]
                for item in retrieve_evidence(
                    case["query"],
                    supplied_type,
                    limit=3,
                    user_state=case.get("user_state"),
                )
            ]
            expected = set(case["expected_top1_ids"])
            top1 += ids[0] in expected
            top3 += bool(expected.intersection(ids))
        return {
            "top1_accuracy": round(top1 / len(cases), 4),
            "top3_coverage": round(top3 / len(cases), 4),
        }

    stage_rows = [row for row in rows if row["has_required_action_stage"]]
    return {
        "benchmark": "retrieval_eval_v0.2",
        "retriever_version": RETRIEVER_VERSION,
        "case_count": len(rows),
        "top1_acceptable_accuracy": round(sum(row["top1"] for row in rows) / len(rows), 4),
        "top3_expected_coverage": round(sum(row["top3"] for row in rows) / len(rows), 4),
        "top3_category_coverage": round(sum(row["category"] for row in rows) / len(rows), 4),
        "top3_action_stage_coverage": round(
            sum(row["action_stage"] for row in stage_rows) / len(stage_rows), 4
        ) if stage_rows else None,
        "mean_reciprocal_rank": round(
            sum(row["reciprocal_rank"] for row in rows) / len(rows), 4
        ),
        "provenance_completeness": round(
            sum(row["provenance"] for row in rows) / len(rows), 4
        ),
        "without_assessed_type": sensitivity("without_type"),
        "counterfactual_wrong_type": sensitivity("wrong_type"),
    }


def _prediction_row(*, case: dict, variant: str, result: dict) -> dict:
    expected_level = {"scam": "high", "ambiguous": "medium", "legitimate": "low"}[
        case["risk_label"]
    ]
    llm = result.get("llm_analysis") or {}
    return {
        "case_id": case["id"],
        "message_hash": message_digest(case["message"]),
        "system_variant": variant,
        "model": llm.get("model"),
        "gold_risk_label": case["risk_label"],
        "gold_primary_type": case.get("primary_type", "uncertain"),
        "predicted_risk_level": result["risk_level"],
        "predicted_primary_type": result["primary_type"],
        "exact_correct": result["risk_level"] == expected_level,
        "operationally_flagged": result["risk_level"] in {"medium", "high"},
        "type_correct": (
            result["primary_type"] == case.get("primary_type")
            if case["risk_label"] == "scam"
            else True
        ),
        "total_latency_ms": result.get("performance", {}).get("total_latency_ms"),
        "llm_latency_ms": llm.get("latency_ms"),
        "prompt_tokens": int(llm.get("prompt_tokens") or 0),
        "completion_tokens": int(llm.get("completion_tokens") or 0),
        "estimated_cost_usd": float(llm.get("estimated_cost_usd") or 0),
        "llm_status": llm.get("status"),
        "fallback_reason": llm.get("fallback_reason"),
        "evidence_ids": [item["id"] for item in result.get("evidence", [])],
        "model_version": result["model_version"],
        "safety_policy_version": result["safety_policy_version"],
        "retriever_version": result["retriever_version"],
        "prompt_version": result.get("prompt_version"),
    }


def run_benchmark(
    *,
    store: EvaluationStore,
    run_id: str,
    dataset_id: str,
    case_limit: int,
    variants: list[str],
    settings_by_model: dict[str, dict],
    budget_cap_usd: float,
    llm_transport=None,
) -> None:
    try:
        cases = load_cases(dataset_id, case_limit)
        # Exclude one-off process/model loading from steady-state latency comparisons.
        analyse_message(message="Benchmark warm-up case.", use_llm=False)
        spent = 0.0
        budget_stopped = False
        for case in cases:
            for variant in variants:
                if variant != "local" and spent >= budget_cap_usd:
                    budget_stopped = True
                    raise BenchmarkBudgetReached("Per-run LLM budget cap reached")
                started = perf_counter()
                if variant == "local":
                    result = analyse_message(message=case["message"], use_llm=False)
                else:
                    result = analyse_message(
                        message=case["message"],
                        use_llm=True,
                        llm_settings=settings_by_model[variant],
                        llm_transport=llm_transport,
                    )
                result.setdefault("performance", {})["total_latency_ms"] = round(
                    (perf_counter() - started) * 1000, 1
                )
                row = _prediction_row(case=case, variant=variant, result=result)
                store.record_benchmark_result(run_id=run_id, row=row)
                spent += row["estimated_cost_usd"]
    except BenchmarkBudgetReached:
        budget_stopped = True
    except Exception as error:  # The background task must leave an auditable terminal state.
        store.fail_benchmark(run_id=run_id, message=str(error) or error.__class__.__name__)
        return

    rows = store.benchmark_results(run_id)
    summary = calculate_metrics(rows)
    summary.update(
        {
            "dataset_id": dataset_id,
            "dataset_name": DATASET_CATALOG[dataset_id]["name"],
            "evidence_level": DATASET_CATALOG[dataset_id]["evidence_level"],
            "retrieval": evaluate_retrieval(),
            "latency_mode": "Warm-process end-to-end latency; one unrecorded local warm-up precedes scoring.",
            "privacy": "No raw benchmark messages are stored in SQLite or exports.",
        }
    )
    store.complete_benchmark(
        run_id=run_id,
        summary=summary,
        status="budget_stopped" if budget_stopped else "completed",
    )
