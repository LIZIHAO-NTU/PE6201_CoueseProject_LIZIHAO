from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.rules_analyser import analyse_with_rules  # noqa: E402


GOLD_PATH = ROOT / "data" / "eval" / "message_gold_test_v0.1.jsonl"
OUTPUT_DIR = ROOT / "outputs" / "evaluation"


def safe_div(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def predicted_label(risk_level: str) -> str:
    return {"high": "scam", "medium": "ambiguous", "low": "legitimate"}[risk_level]


def main() -> None:
    records = [json.loads(line) for line in GOLD_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows: list[dict] = []
    confusion: dict[str, Counter] = defaultdict(Counter)

    for record in records:
        result = analyse_with_rules(record["message"])
        prediction = predicted_label(result["risk_level"])
        gold = record["risk_label"]
        confusion[gold][prediction] += 1
        rows.append(
            {
                "id": record["id"],
                "message": record["message"],
                "gold_risk_label": gold,
                "predicted_risk_label": prediction,
                "risk_level": result["risk_level"],
                "risk_score": result["risk_score"],
                "gold_primary_type": record["primary_type"],
                "predicted_primary_type": result["primary_type"],
                "risk_correct": prediction == gold,
                "type_correct": (
                    result["primary_type"] == record["primary_type"] if gold == "scam" else None
                ),
                "has_url": bool(record["urls"]),
                "predicted_mechanisms": [item["id"] for item in result["mechanisms"]],
                "gold_mechanisms": record["mechanisms"],
            }
        )

    scam_rows = [row for row in rows if row["gold_risk_label"] == "scam"]
    legitimate_rows = [row for row in rows if row["gold_risk_label"] == "legitimate"]
    ambiguous_rows = [row for row in rows if row["gold_risk_label"] == "ambiguous"]
    flagged = [row for row in rows if row["risk_level"] in {"high", "medium"}]
    high_risk = [row for row in rows if row["risk_level"] == "high"]
    medium_risk = [row for row in rows if row["risk_level"] == "medium"]

    metrics = {
        "model_version": "mvp-rules-0.1",
        "dataset": GOLD_PATH.name,
        "n": len(rows),
        "class_counts": dict(Counter(row["gold_risk_label"] for row in rows)),
        "exact_three_way_accuracy": safe_div(sum(row["risk_correct"] for row in rows), len(rows)),
        "operational_scam_recall_flag_medium_or_high": safe_div(
            sum(row["risk_level"] in {"high", "medium"} for row in scam_rows), len(scam_rows)
        ),
        "high_risk_scam_recall": safe_div(
            sum(row["risk_level"] == "high" for row in scam_rows), len(scam_rows)
        ),
        "flagged_precision_for_scam": safe_div(
            sum(row["gold_risk_label"] == "scam" for row in flagged), len(flagged)
        ),
        "high_risk_precision_for_scam": safe_div(
            sum(row["gold_risk_label"] == "scam" for row in high_risk), len(high_risk)
        ),
        "legitimate_false_positive_rate_flag_medium_or_high": safe_div(
            sum(row["risk_level"] in {"high", "medium"} for row in legitimate_rows), len(legitimate_rows)
        ),
        "abstention_rate_medium": safe_div(len(medium_risk), len(rows)),
        "ambiguous_abstention_recall": safe_div(
            sum(row["risk_level"] == "medium" for row in ambiguous_rows), len(ambiguous_rows)
        ),
        "scam_primary_type_accuracy": safe_div(
            sum(bool(row["type_correct"]) for row in scam_rows), len(scam_rows)
        ),
        "url_scam_recall_flag_medium_or_high": safe_div(
            sum(row["risk_level"] in {"high", "medium"} for row in scam_rows if row["has_url"]),
            sum(row["has_url"] for row in scam_rows),
        ),
        "confusion_matrix": {gold: dict(counts) for gold, counts in confusion.items()},
    }

    per_type = {}
    for scam_type in sorted({row["gold_primary_type"] for row in scam_rows}):
        subset = [row for row in scam_rows if row["gold_primary_type"] == scam_type]
        per_type[scam_type] = {
            "n": len(subset),
            "flagged_recall": safe_div(sum(row["risk_level"] in {"high", "medium"} for row in subset), len(subset)),
            "high_risk_recall": safe_div(sum(row["risk_level"] == "high" for row in subset), len(subset)),
            "type_accuracy": safe_div(sum(bool(row["type_correct"]) for row in subset), len(subset)),
        }
    metrics["per_scam_type"] = per_type

    errors = [row for row in rows if not row["risk_correct"] or row["type_correct"] is False]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "baseline_predictions_v0.1.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    (OUTPUT_DIR / "baseline_metrics_v0.1.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# ScamLens SG baseline evaluation v0.1",
        "",
        f"- Model: `{metrics['model_version']}`",
        f"- Gold test records: {metrics['n']}",
        f"- Exact three-way accuracy: {metrics['exact_three_way_accuracy']:.1%}",
        f"- Operational scam recall (medium or high): {metrics['operational_scam_recall_flag_medium_or_high']:.1%}",
        f"- High-risk scam recall: {metrics['high_risk_scam_recall']:.1%}",
        f"- Legitimate false-positive rate (medium or high): {metrics['legitimate_false_positive_rate_flag_medium_or_high']:.1%}",
        f"- Abstention rate (medium): {metrics['abstention_rate_medium']:.1%}",
        f"- Scam type accuracy: {metrics['scam_primary_type_accuracy']:.1%}",
        "",
        "## Interpretation",
        "",
        "Medium is treated as an abstention requiring independent verification. For the operational scam-recall metric, both medium and high count as flagged; exact three-way accuracy requires the model to match scam, legitimate or ambiguous exactly.",
        "",
        "## Per scam type",
        "",
        "| Type | N | Flagged recall | High-risk recall | Type accuracy |",
        "|---|---:|---:|---:|---:|",
    ]
    for scam_type, values in per_type.items():
        lines.append(
            f"| {scam_type} | {values['n']} | {values['flagged_recall']:.1%} | "
            f"{values['high_risk_recall']:.1%} | {values['type_accuracy']:.1%} |"
        )
    lines.extend(["", "## Errors requiring analysis", ""])
    if not errors:
        lines.append("No risk-label or scam-type errors in this small synthetic test set.")
    else:
        lines.extend(
            [
                "| ID | Gold risk | Predicted risk | Gold type | Predicted type | Score |",
                "|---|---|---|---|---|---:|",
            ]
        )
        for row in errors:
            lines.append(
                f"| {row['id']} | {row['gold_risk_label']} | {row['predicted_risk_label']} | "
                f"{row['gold_primary_type']} | {row['predicted_primary_type']} | {row['risk_score']:.3f} |"
            )
    lines.extend(
        [
            "",
            "## Limitation",
            "",
            "This is a deliberately small, mostly synthetic test set. Results establish an auditable baseline but are not a deployment claim. A larger set of naturalistic, independently sourced messages is still required.",
            "",
        ]
    )
    (OUTPUT_DIR / "baseline_evaluation_v0.1.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"Errors requiring analysis: {len(errors)}")


if __name__ == "__main__":
    main()
