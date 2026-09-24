from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / "outputs" / "evaluation" / "model_error_review_results_v0.1.json"
JSONL_PATH = ROOT / "outputs" / "evaluation" / "deployed_predictions_v0.1.jsonl"
CSV_PATH = ROOT / "outputs" / "evaluation" / "deployed_predictions_review_v0.1.csv"


def main() -> None:
    payload = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    records = payload["records"]
    if len(records) != 30:
        raise ValueError(f"Expected 30 frozen reviewed records, found {len(records)}")

    JSONL_PATH.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    print(json.dumps({"records": len(records), "jsonl": str(JSONL_PATH), "csv": str(CSV_PATH)}, indent=2))


if __name__ == "__main__":
    main()
