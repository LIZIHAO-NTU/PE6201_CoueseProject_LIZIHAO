from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.pipeline import analyse_message  # noqa: E402


VALIDATION_PATH = ROOT / "data" / "training" / "message_validation_v0.1.jsonl"
GOLD_PATH = ROOT / "data" / "eval" / "message_gold_test_v0.1.jsonl"
FROZEN_REPORT_PATH = ROOT / "outputs" / "evaluation" / "trained_model_evaluation_v0.1.json"
REVIEW_PATH = ROOT / "outputs" / "evaluation" / "model_error_review_results_v0.1.json"
JSON_PATH = ROOT / "outputs" / "evaluation" / "post_review_mitigation_evaluation_v0.1.json"
MD_PATH = ROOT / "outputs" / "evaluation" / "post_review_mitigation_evaluation_v0.1.md"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def safe_div(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def label_for(level: str) -> str:
    return {"high": "scam", "medium": "ambiguous", "low": "legitimate"}[level]


def evaluate(records: list[dict]) -> dict:
    rows = []
    for record in records:
        result = analyse_message(message=record["message"])
        rows.append(
            {
                "id": record["id"],
                "gold_risk_label": record["risk_label"],
                "predicted_risk_label": label_for(result["risk_level"]),
                "risk_level": result["risk_level"],
                "risk_score": result["risk_score"],
                "gold_primary_type": record["primary_type"],
                "predicted_primary_type": result["primary_type"],
                "type_resolution_source": result["type_resolution_source"],
                "guardrail_reasons": result["guardrail_reasons"],
            }
        )

    scams = [row for row in rows if row["gold_risk_label"] == "scam"]
    legitimate = [row for row in rows if row["gold_risk_label"] == "legitimate"]
    ambiguous = [row for row in rows if row["gold_risk_label"] == "ambiguous"]
    flagged = [row for row in rows if row["risk_level"] in {"medium", "high"}]
    type_rows = [row for row in rows if row["gold_risk_label"] == "scam"]
    metrics = {
        "n": len(rows),
        "exact_three_way_accuracy": safe_div(
            sum(row["gold_risk_label"] == row["predicted_risk_label"] for row in rows), len(rows)
        ),
        "operational_scam_recall": safe_div(
            sum(row["risk_level"] in {"medium", "high"} for row in scams), len(scams)
        ),
        "high_risk_scam_recall": safe_div(sum(row["risk_level"] == "high" for row in scams), len(scams)),
        "flagged_precision_for_scam": safe_div(
            sum(row["gold_risk_label"] == "scam" for row in flagged), len(flagged)
        ),
        "legitimate_false_positive_rate": safe_div(
            sum(row["risk_level"] in {"medium", "high"} for row in legitimate), len(legitimate)
        ),
        "abstention_rate": safe_div(sum(row["risk_level"] == "medium" for row in rows), len(rows)),
        "ambiguous_abstention_recall": safe_div(
            sum(row["risk_level"] == "medium" for row in ambiguous), len(ambiguous)
        ),
        "deployed_scam_type_accuracy": safe_div(
            sum(row["predicted_primary_type"] == row["gold_primary_type"] for row in type_rows),
            len(type_rows),
        ),
        "low_risk_scam_count": sum(row["gold_risk_label"] == "scam" and row["risk_level"] == "low" for row in rows),
        "guardrail_trigger_count": sum(bool(row["guardrail_reasons"]) for row in rows),
        "type_resolution_sources": dict(Counter(row["type_resolution_source"] for row in rows)),
    }
    return {"metrics": metrics, "rows": rows}


def rounded(value: object) -> object:
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, dict):
        return {key: rounded(item) for key, item in value.items()}
    if isinstance(value, list):
        return [rounded(item) for item in value]
    return value


def percent(value: float) -> str:
    return f"{value:.1%}"


def main() -> None:
    validation = evaluate(load_jsonl(VALIDATION_PATH))
    gold = evaluate(load_jsonl(GOLD_PATH))
    frozen = json.loads(FROZEN_REPORT_PATH.read_text(encoding="utf-8"))
    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))

    payload = {
        "evaluation_version": "post-review-mitigation-0.1",
        "safety_policy_version": "behaviour-guardrails-0.1",
        "type_policy": "auditable context resolver with trained-classifier fallback",
        "selection_policy": (
            "The frozen classifier and thresholds were not retrained or tuned on gold. "
            "The off-platform-payment guardrail is grounded in reviewed training mechanisms; "
            "type context precedence was checked on validation."
        ),
        "independence_warning": (
            "Gold results below are a post-review diagnostic because the error review informed mitigation priorities. "
            "They must not be reported as a fresh independent test estimate."
        ),
        "review_summary": review["summary"],
        "validation": rounded(validation),
        "gold_posthoc": rounded(gold),
        "frozen_gold_before_mitigation": frozen["gold_test"],
        "frozen_deployed_scam_type_accuracy": frozen["gold_test_deployed_scam_type_accuracy"],
    }
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    before = frozen["gold_test"]
    after = gold["metrics"]
    lines = [
        "# ScamLens SG post-review mitigation evaluation v0.1",
        "",
        "The reviewed error set contained one critical low-risk false reassurance, ten issues needing mitigation and six acceptable trade-offs. The frozen statistical model and its thresholds remain unchanged.",
        "",
        "## Mitigations",
        "",
        "- Added an auditable medium-risk floor when a message both requests payment and explicitly moves payment outside a marketplace's protected checkout.",
        "- Added a context-based scam-type resolver with job context taking precedence over identity-tool terms such as Singpass, followed by explicit government, investment and e-commerce context. The trained type classifier remains the fallback.",
        "- Added positive and safe-negative regression tests for the new guardrail.",
        "",
        "## Validation result",
        "",
        f"On the unchanged 12-record validation split, operational scam recall is {percent(validation['metrics']['operational_scam_recall'])}, legitimate false-positive rate is {percent(validation['metrics']['legitimate_false_positive_rate'])}, and deployed scam-type accuracy is {percent(validation['metrics']['deployed_scam_type_accuracy'])}.",
        "",
        "## Gold-set post-hoc diagnostic",
        "",
        "> These are not fresh independent test results. The gold error review informed mitigation priorities, so this table is a regression diagnostic only.",
        "",
        "| Metric | Frozen pre-review result | Post-review diagnostic |",
        "|---|---:|---:|",
        f"| Exact three-way accuracy | {percent(before['exact_three_way_accuracy'])} | {percent(after['exact_three_way_accuracy'])} |",
        f"| Operational scam recall | {percent(before['operational_scam_recall'])} | {percent(after['operational_scam_recall'])} |",
        f"| High-risk scam recall | {percent(before['high_risk_scam_recall'])} | {percent(after['high_risk_scam_recall'])} |",
        f"| Legitimate false-positive rate | {percent(before['legitimate_false_positive_rate'])} | {percent(after['legitimate_false_positive_rate'])} |",
        f"| Abstention rate | {percent(before['abstention_rate'])} | {percent(after['abstention_rate'])} |",
        f"| Ambiguous-case abstention recall | {percent(before['ambiguous_abstention_recall'])} | {percent(after['ambiguous_abstention_recall'])} |",
        f"| Deployed scam-type accuracy | {percent(frozen['gold_test_deployed_scam_type_accuracy'])} | {percent(after['deployed_scam_type_accuracy'])} |",
        f"| Low-risk scams | 1 | {after['low_risk_scam_count']} |",
        "",
        "## Interpretation",
        "",
        "The critical failure mode is no longer low risk: the affected behavioural pattern is routed to independent verification. Type explanations are more consistent, but the apparent gold-set gain must be confirmed on a new untouched evaluation set before it is treated as generalisation evidence.",
        "",
    ]
    MD_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"validation": rounded(validation["metrics"]), "gold_posthoc": rounded(gold["metrics"])}, indent=2))


if __name__ == "__main__":
    main()
