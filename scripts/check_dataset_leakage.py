from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left or right else 1.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check train/test campaign and message leakage.")
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--threshold", type=float, default=0.72)
    args = parser.parse_args()

    left = load_jsonl(args.left)
    right = load_jsonl(args.right)
    exact_messages = {record["message"].strip().lower() for record in left} & {
        record["message"].strip().lower() for record in right
    }
    campaign_overlap = {record["campaign_group"] for record in left} & {
        record["campaign_group"] for record in right
    }

    near_matches = []
    highest = (0.0, "", "")
    for left_record in left:
        left_tokens = tokens(left_record["message"])
        for right_record in right:
            score = jaccard(left_tokens, tokens(right_record["message"]))
            if score > highest[0]:
                highest = (score, left_record["id"], right_record["id"])
            if score >= args.threshold:
                near_matches.append((score, left_record["id"], right_record["id"]))

    print(f"Exact-message overlap: {len(exact_messages)}")
    print(f"Campaign-group overlap: {len(campaign_overlap)}")
    print(f"Near matches at threshold {args.threshold:.2f}: {len(near_matches)}")
    print(f"Highest token Jaccard: {highest[0]:.3f} ({highest[1]} vs {highest[2]})")
    if exact_messages or campaign_overlap or near_matches:
        for score, left_id, right_id in sorted(near_matches, reverse=True)[:10]:
            print(f"- {score:.3f}: {left_id} vs {right_id}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

