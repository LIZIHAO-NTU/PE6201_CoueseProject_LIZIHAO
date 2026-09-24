from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "eval" / "message_untouched_confirmatory_candidates_v0.3.jsonl"
REPORT = ROOT / "data" / "eval" / "message_untouched_confirmatory_audit_v0.3.json"
THRESHOLD = 0.72
SAFE_MESSAGE_HOSTS = {"example.com", "example.org", "example.net"}


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left or right else 1.0


def main() -> None:
    records = [
        json.loads(line)
        for line in DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    near_duplicates: list[dict] = []
    highest = {"score": 0.0, "left_id": "", "right_id": ""}
    for index, left in enumerate(records):
        left_tokens = tokens(left["message"])
        for right in records[index + 1 :]:
            score = jaccard(left_tokens, tokens(right["message"]))
            if score > highest["score"]:
                highest = {
                    "score": round(score, 3),
                    "left_id": left["id"],
                    "right_id": right["id"],
                }
            if score >= THRESHOLD:
                near_duplicates.append(
                    {
                        "score": round(score, 3),
                        "left_id": left["id"],
                        "right_id": right["id"],
                    }
                )

    unsafe_message_urls: list[dict] = []
    for record in records:
        for url in record.get("urls", []):
            hostname = (urlparse(url).hostname or "").lower()
            if hostname not in SAFE_MESSAGE_HOSTS and not any(
                hostname.endswith(f".{safe_host}") for safe_host in SAFE_MESSAGE_HOSTS
            ):
                unsafe_message_urls.append({"id": record["id"], "url": url})

    report = {
        "dataset": str(DATASET.relative_to(ROOT)),
        "record_count": len(records),
        "risk_distribution": dict(Counter(record["risk_label"] for record in records)),
        "scam_type_distribution": dict(
            Counter(
                record["primary_type"]
                for record in records
                if record["risk_label"] == "scam"
            )
        ),
        "channel_distribution": dict(Counter(record["channel"] for record in records)),
        "message_url_distribution": {
            "with_url": sum(bool(record.get("urls")) for record in records),
            "without_url": sum(not record.get("urls") for record in records),
        },
        "unique_ids": len({record["id"] for record in records}) == len(records),
        "unique_campaign_groups": len({record["campaign_group"] for record in records})
        == len(records),
        "internal_near_duplicate_threshold": THRESHOLD,
        "internal_near_duplicates": near_duplicates,
        "highest_internal_token_jaccard": highest,
        "unsafe_message_urls": unsafe_message_urls,
        "passed": not near_duplicates and not unsafe_message_urls,
        "note": (
            "Message URLs use reserved example domains. Official advisory source URLs are metadata "
            "and are not opened by the application during message analysis."
        ),
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
