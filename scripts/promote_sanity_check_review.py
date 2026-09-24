from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data" / "eval" / "message_confirmatory_candidates_v0.2.jsonl"
REVIEWS = ROOT / "data" / "eval" / "message_confirmatory_review_results_v0.2.json"
OUTPUT = ROOT / "data" / "eval" / "message_sanity_test_v0.2.jsonl"


def main() -> None:
    candidates = {
        record["id"]: record
        for record in (
            json.loads(line)
            for line in CANDIDATES.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    review_payload = json.loads(REVIEWS.read_text(encoding="utf-8"))
    reviews = {record["id"]: record for record in review_payload["records"]}
    if set(candidates) != set(reviews):
        raise ValueError("Candidate and review IDs do not match")

    promoted = []
    for record_id, candidate in candidates.items():
        review = reviews[record_id]
        if str(review["student_decision"]).strip().lower() != "accept":
            raise ValueError(f"Unexpected non-accept decision for {record_id}")
        item = dict(candidate)
        item["split"] = "test"
        item["review_status"] = "reviewed"
        item["reviewer"] = "AI-assisted content audit"
        item["notes"] = (
            "Accepted before model scoring. AI assisted with authoring and review; "
            "use only as a sanity-check benchmark, not independent human-reviewed evidence."
        )
        promoted.append(item)

    OUTPUT.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in promoted),
        encoding="utf-8",
    )
    print(json.dumps({"records": len(promoted), "output": str(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
