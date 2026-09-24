from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.pipeline import analyse_message  # noqa: E402
from app.services.rules_analyser import analyse_with_rules  # noqa: E402


GOLD_PATH = ROOT / "data" / "eval" / "message_gold_test_v0.1.jsonl"
OUTPUT_DIR = ROOT / "outputs" / "evaluation"
JSONL_PATH = OUTPUT_DIR / "deployed_predictions_v0.2.jsonl"
CSV_PATH = OUTPUT_DIR / "deployed_predictions_review_v0.2.csv"


def label_for(level: str) -> str:
    return {"high": "scam", "medium": "ambiguous", "low": "legitimate"}[level]


def priority(gold: dict, trained: dict) -> str:
    predicted = label_for(trained["risk_level"])
    if gold["risk_label"] == "scam" and trained["risk_level"] == "low":
        return "critical_false_reassurance"
    if gold["risk_label"] == "legitimate" and trained["risk_level"] in {"medium", "high"}:
        return "false_positive_review"
    if gold["risk_label"] == "ambiguous" and trained["risk_level"] != "medium":
        return "ambiguous_case_miss"
    if gold["risk_label"] == "scam" and trained["primary_type"] != gold["primary_type"]:
        return "type_error"
    if predicted != gold["risk_label"]:
        return "conservative_abstention"
    return "correct"


def main() -> None:
    gold_records = [json.loads(line) for line in GOLD_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for gold in gold_records:
        trained = analyse_message(message=gold["message"])
        rules = analyse_with_rules(gold["message"])
        predicted_label = label_for(trained["risk_level"])
        rows.append(
            {
                "id": gold["id"],
                "message": gold["message"],
                "gold_risk_label": gold["risk_label"],
                "rules_risk_level": rules["risk_level"],
                "trained_risk_level": trained["risk_level"],
                "trained_risk_score": trained["risk_score"],
                "trained_risk_label": predicted_label,
                "gold_primary_type": gold["primary_type"],
                "rules_primary_type": rules["primary_type"],
                "trained_primary_type": trained["primary_type"],
                "risk_correct": predicted_label == gold["risk_label"],
                "type_correct": trained["primary_type"] == gold["primary_type"] if gold["risk_label"] == "scam" else "",
                "ambiguous_probability": trained["risk_probabilities"]["ambiguous"],
                "legitimate_probability": trained["risk_probabilities"]["legitimate"],
                "scam_probability": trained["risk_probabilities"]["scam"],
                "url_count": len(gold["urls"]),
                "review_priority": priority(gold, trained),
                "student_assessment": "",
                "review_notes": "",
            }
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    JSONL_PATH.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    fields = list(rows[0])
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    counts = {}
    for row in rows:
        counts[row["review_priority"]] = counts.get(row["review_priority"], 0) + 1
    print(json.dumps({"records": len(rows), "review_priorities": counts}, indent=2))


if __name__ == "__main__":
    main()
