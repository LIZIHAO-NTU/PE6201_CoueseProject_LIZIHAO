from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data" / "training" / "message_training_candidates_v0.1.jsonl"
REVIEWS = ROOT / "data" / "training" / "message_training_review_results_v0.1.json"
TRAIN_OUTPUT = ROOT / "data" / "training" / "message_train_v0.1.jsonl"
VALIDATION_OUTPUT = ROOT / "data" / "training" / "message_validation_v0.1.jsonl"
COMBINED_OUTPUT = ROOT / "data" / "training" / "message_modeling_v0.1.jsonl"

# The workbook did not include a corrected-message column. This explicit override
# implements the student's written review note for the single edited record.
MESSAGE_OVERRIDES = {
    "msg_train_gov_001": {
        "message": (
            "ICA: your passport is under investigation. Pay the S$120 clearance charge "
            "today at https://ica-clearance.example.com/pay to avoid travel restrictions."
        ),
        "mechanisms": [
            "urgency_or_threat",
            "payment_request",
            "external_link",
            "brand_impersonation",
            "suspicious_url",
        ],
        "urls": ["https://ica-clearance.example.com/pay"],
        "audit": "Applied reviewer note: added an explicit safe-example payment route.",
    }
}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def mechanisms(value: object) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split("|") if item.strip()]


def stable_key(record_id: str) -> str:
    return hashlib.sha256(f"scamlens-split-v0.1:{record_id}".encode()).hexdigest()


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def main() -> None:
    candidates = {record["id"]: record for record in load_jsonl(CANDIDATES)}
    review_payload = json.loads(REVIEWS.read_text(encoding="utf-8"))
    reviews = {record["id"]: record for record in review_payload["records"]}
    if set(candidates) != set(reviews):
        raise ValueError("Training review IDs do not match candidate IDs")

    approved: list[dict] = []
    incomplete: list[str] = []
    rejected: list[str] = []
    for record_id, candidate in candidates.items():
        review = reviews[record_id]
        decision = str(review.get("student_decision", "")).strip().lower()
        if decision == "reject":
            rejected.append(record_id)
            continue
        if decision not in {"accept", "edit"}:
            incomplete.append(record_id)
            continue

        record = dict(candidate)
        audit_parts = [f"Student review decision: {decision} on 2026-08-12."]
        if decision == "edit":
            corrected_risk = str(review.get("corrected_risk_label", "")).strip()
            corrected_type = str(review.get("corrected_primary_type", "")).strip()
            corrected_mechanisms = mechanisms(review.get("corrected_mechanisms", ""))
            if corrected_risk:
                record["risk_label"] = corrected_risk
            if corrected_type:
                record["primary_type"] = corrected_type
            if corrected_mechanisms:
                record["mechanisms"] = corrected_mechanisms
            override = MESSAGE_OVERRIDES.get(record_id)
            if override:
                record.update({key: value for key, value in override.items() if key != "audit"})
                audit_parts.append(override["audit"])
            elif not any([corrected_risk, corrected_type, corrected_mechanisms]):
                raise ValueError(f"{record_id}: edit has no corrected fields or registered message override")

        review_note = str(review.get("review_notes", "")).strip()
        if review_note:
            audit_parts.append(f"Reviewer note: {review_note}")
        record["review_status"] = "reviewed"
        record["reviewer"] = "Student reviewer"
        record["notes"] = " ".join(part for part in [candidate.get("notes"), *audit_parts] if part)
        approved.append(record)

    if incomplete:
        raise ValueError(f"Review incomplete for: {', '.join(incomplete)}")

    strata: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for record in approved:
        strata[(record["risk_label"], record["primary_type"])].append(record)

    train: list[dict] = []
    validation: list[dict] = []
    for stratum_records in strata.values():
        ordered = sorted(stratum_records, key=lambda item: stable_key(item["id"]))
        validation_count = max(1, round(len(ordered) * 0.2))
        validation.extend(ordered[:validation_count])
        train.extend(ordered[validation_count:])

    for record in train:
        record["split"] = "train"
    for record in validation:
        record["split"] = "validation"
    train.sort(key=lambda item: item["id"])
    validation.sort(key=lambda item: item["id"])

    write_jsonl(TRAIN_OUTPUT, train)
    write_jsonl(VALIDATION_OUTPUT, validation)
    write_jsonl(COMBINED_OUTPUT, train + validation)
    print(f"Approved={len(approved)}, rejected={len(rejected)}, train={len(train)}, validation={len(validation)}")
    for key in sorted(strata):
        train_n = sum((record["risk_label"], record["primary_type"]) == key for record in train)
        val_n = sum((record["risk_label"], record["primary_type"]) == key for record in validation)
        print(f"- {key}: train={train_n}, validation={val_n}")


if __name__ == "__main__":
    main()
