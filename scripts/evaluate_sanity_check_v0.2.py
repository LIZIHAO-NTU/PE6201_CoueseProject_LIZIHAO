from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.pipeline import analyse_message  # noqa: E402


DATA_PATH = ROOT / "data" / "eval" / "message_sanity_test_v0.2.jsonl"
OUTPUT_JSON = ROOT / "outputs" / "evaluation" / "sanity_check_evaluation_v0.2.json"
OUTPUT_MD = ROOT / "outputs" / "evaluation" / "sanity_check_evaluation_v0.2.md"


def safe_div(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def label_for(level: str) -> str:
    return {"high": "scam", "medium": "ambiguous", "low": "legitimate"}[level]


def main() -> None:
    records = [json.loads(line) for line in DATA_PATH.read_text(encoding="utf-8").splitlines() if line]
    rows = []
    for record in records:
        result = analyse_message(message=record["message"])
        rows.append({
            "id": record["id"],
            "gold_risk_label": record["risk_label"],
            "predicted_risk_label": label_for(result["risk_level"]),
            "risk_level": result["risk_level"],
            "risk_score": result["risk_score"],
            "gold_primary_type": record["primary_type"],
            "predicted_primary_type": result["primary_type"],
            "risk_correct": label_for(result["risk_level"]) == record["risk_label"],
            "type_correct": result["primary_type"] == record["primary_type"] if record["risk_label"] == "scam" else None,
            "type_resolution_source": result["type_resolution_source"],
            "guardrail_reasons": result["guardrail_reasons"],
        })

    scams = [row for row in rows if row["gold_risk_label"] == "scam"]
    legitimate = [row for row in rows if row["gold_risk_label"] == "legitimate"]
    ambiguous = [row for row in rows if row["gold_risk_label"] == "ambiguous"]
    flagged = [row for row in rows if row["risk_level"] in {"medium", "high"}]
    confusion: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        confusion[row["gold_risk_label"]][row["predicted_risk_label"]] += 1
    metrics = {
        "n": len(rows),
        "exact_three_way_accuracy": safe_div(sum(row["risk_correct"] for row in rows), len(rows)),
        "operational_scam_recall": safe_div(sum(row["risk_level"] in {"medium", "high"} for row in scams), len(scams)),
        "high_risk_scam_recall": safe_div(sum(row["risk_level"] == "high" for row in scams), len(scams)),
        "flagged_precision_for_scam": safe_div(sum(row["gold_risk_label"] == "scam" for row in flagged), len(flagged)),
        "legitimate_false_positive_rate": safe_div(sum(row["risk_level"] in {"medium", "high"} for row in legitimate), len(legitimate)),
        "ambiguous_abstention_recall": safe_div(sum(row["risk_level"] == "medium" for row in ambiguous), len(ambiguous)),
        "deployed_scam_type_accuracy": safe_div(sum(row["type_correct"] is True for row in scams), len(scams)),
        "low_risk_scam_count": sum(row["risk_level"] == "low" for row in scams),
        "confusion_matrix": {label: dict(counts) for label, counts in confusion.items()},
    }
    payload = {
        "evaluation_version": "ai-assisted-sanity-check-0.2",
        "independent_human_review": False,
        "reporting_boundary": "Use for regression/demo only; the 30-case human-reviewed gold test remains the main formal result.",
        "metrics": metrics,
        "rows": rows,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# ScamLens SG AI-assisted sanity-check evaluation v0.2",
        "",
        "> AI assisted with both authoring and pre-model label review. This is a regression/demo benchmark, not independent human-reviewed evidence.",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Exact three-way accuracy | {metrics['exact_three_way_accuracy']:.1%} |",
        f"| Operational scam recall | {metrics['operational_scam_recall']:.1%} |",
        f"| High-risk scam recall | {metrics['high_risk_scam_recall']:.1%} |",
        f"| Flagged precision for scams | {metrics['flagged_precision_for_scam']:.1%} |",
        f"| Legitimate false-positive rate | {metrics['legitimate_false_positive_rate']:.1%} |",
        f"| Ambiguous-case abstention recall | {metrics['ambiguous_abstention_recall']:.1%} |",
        f"| Deployed scam-type accuracy | {metrics['deployed_scam_type_accuracy']:.1%} |",
        f"| Low-risk scams | {metrics['low_risk_scam_count']} |",
        "",
        "The original 30-case human-reviewed gold test remains the main formal performance result.",
        "",
    ]
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
