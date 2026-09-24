from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_PATH = ROOT / "data" / "eval" / "message_eval_candidates_v0.1.jsonl"
REVIEWS_PATH = ROOT / "data" / "eval" / "message_eval_review_results_v0.1.json"
OUTPUT_PATH = ROOT / "data" / "eval" / "message_gold_test_v0.1.jsonl"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def split_mechanisms(value: object) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split("|") if item.strip()]


def main() -> None:
    candidates = {record["id"]: record for record in load_jsonl(CANDIDATES_PATH)}
    review_payload = json.loads(REVIEWS_PATH.read_text(encoding="utf-8"))
    reviews = {record["id"]: record for record in review_payload["records"]}

    missing = sorted(set(candidates) - set(reviews))
    extra = sorted(set(reviews) - set(candidates))
    if missing or extra:
        raise ValueError(f"Review/candidate ID mismatch; missing={missing}, extra={extra}")

    promoted: list[dict] = []
    rejected: list[str] = []
    incomplete: list[str] = []
    for record_id, candidate in candidates.items():
        review = reviews[record_id]
        decision = str(review.get("student_decision", "")).strip().lower()
        if decision == "reject":
            rejected.append(record_id)
            continue
        if decision not in {"accept", "edit"}:
            incomplete.append(record_id)
            continue

        gold = dict(candidate)
        if decision == "edit":
            corrected_risk = str(review.get("corrected_risk_label", "")).strip()
            corrected_type = str(review.get("corrected_primary_type", "")).strip()
            if not corrected_risk or not corrected_type:
                raise ValueError(f"{record_id}: edit requires corrected risk label and primary type")
            gold["risk_label"] = corrected_risk
            gold["primary_type"] = corrected_type
            gold["mechanisms"] = split_mechanisms(review.get("corrected_mechanisms", ""))

        gold["split"] = "test"
        gold["review_status"] = "gold"
        gold["reviewer"] = "Student reviewer"
        gold["annotation_confidence"] = "high"
        review_notes = str(review.get("review_notes", "")).strip()
        audit_note = f"Student review decision: {decision} on 2026-08-12."
        gold["notes"] = " ".join(part for part in [candidate.get("notes"), audit_note, review_notes] if part)
        promoted.append(gold)

    if incomplete:
        raise ValueError(f"Review is incomplete for: {', '.join(incomplete)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in promoted),
        encoding="utf-8",
    )
    print(f"Promoted {len(promoted)} records; rejected {len(rejected)}; output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()

