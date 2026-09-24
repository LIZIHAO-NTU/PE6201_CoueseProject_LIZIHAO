from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse


RISK_LABELS = {"scam", "legitimate", "ambiguous"}
PRIMARY_TYPES = {
    "government_impersonation", "investment", "job", "e_commerce",
    "other_scam", "uncertain", "not_applicable",
}
MECHANISMS = {
    "urgency_or_threat", "credential_request", "payment_request",
    "unrealistic_reward", "secrecy_or_isolation", "external_link",
    "brand_impersonation", "suspicious_url", "off_platform_payment",
    "app_installation", "remote_access_request", "social_proof_manipulation",
}
SOURCE_TYPES = {
    "official_public_example", "licensed_public_dataset",
    "synthetic_from_advisory", "authored_hard_negative", "consented_anonymised",
}
SPLITS = {"unassigned", "train", "validation", "test"}
REVIEW_STATUSES = {"candidate", "reviewed", "gold", "rejected"}
CONFIDENCE_LEVELS = {"low", "medium", "high"}
REQUIRED = {
    "id", "message", "channel", "language", "risk_label", "primary_type",
    "mechanisms", "urls", "source_type", "source_name", "source_url",
    "is_synthetic", "campaign_group", "split", "pii_removed",
    "review_status", "annotation_confidence", "label_rationale",
}
ID_PATTERN = re.compile(r"^msg_[a-z0-9_]{4,64}$")


def is_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_record(record: object, line_number: int) -> list[str]:
    prefix = f"line {line_number}"
    if not isinstance(record, dict):
        return [f"{prefix}: record must be a JSON object"]
    errors = []
    missing = sorted(REQUIRED - set(record))
    if missing:
        errors.append(f"{prefix}: missing fields: {', '.join(missing)}")
        return errors

    if not isinstance(record["id"], str) or not ID_PATTERN.match(record["id"]):
        errors.append(f"{prefix}: invalid id format")
    if not isinstance(record["message"], str) or not record["message"].strip():
        errors.append(f"{prefix}: message must be non-empty")
    if record["language"] != "en":
        errors.append(f"{prefix}: MVP language must be 'en'")
    if record["risk_label"] not in RISK_LABELS:
        errors.append(f"{prefix}: unknown risk_label")
    if record["primary_type"] not in PRIMARY_TYPES:
        errors.append(f"{prefix}: unknown primary_type")
    if record["source_type"] not in SOURCE_TYPES:
        errors.append(f"{prefix}: unknown source_type")
    if record["split"] not in SPLITS:
        errors.append(f"{prefix}: unknown split")
    if record["review_status"] not in REVIEW_STATUSES:
        errors.append(f"{prefix}: unknown review_status")
    if record["annotation_confidence"] not in CONFIDENCE_LEVELS:
        errors.append(f"{prefix}: unknown annotation_confidence")
    if not isinstance(record["mechanisms"], list) or len(record["mechanisms"]) != len(set(record["mechanisms"])):
        errors.append(f"{prefix}: mechanisms must be a unique list")
    elif set(record["mechanisms"]) - MECHANISMS:
        errors.append(f"{prefix}: unknown mechanisms: {sorted(set(record['mechanisms']) - MECHANISMS)}")
    if not isinstance(record["urls"], list) or any(not is_url(url) for url in record["urls"]):
        errors.append(f"{prefix}: urls must contain only absolute HTTP(S) URLs")
    if record["source_url"] is not None and not is_url(record["source_url"]):
        errors.append(f"{prefix}: source_url must be null or an absolute HTTP(S) URL")
    if not isinstance(record["pii_removed"], bool) or not isinstance(record["is_synthetic"], bool):
        errors.append(f"{prefix}: pii_removed and is_synthetic must be booleans")
    if not isinstance(record["label_rationale"], str) or len(record["label_rationale"].strip()) < 10:
        errors.append(f"{prefix}: label_rationale is too short")

    if record["risk_label"] == "legitimate" and record["primary_type"] != "not_applicable":
        errors.append(f"{prefix}: legitimate records must use primary_type=not_applicable")
    if record["risk_label"] == "ambiguous" and record["primary_type"] != "uncertain":
        errors.append(f"{prefix}: ambiguous records must use primary_type=uncertain")
    if record["risk_label"] == "scam" and record["primary_type"] == "not_applicable":
        errors.append(f"{prefix}: scam records cannot use primary_type=not_applicable")
    if record["source_type"] == "synthetic_from_advisory":
        if not record["is_synthetic"] or record["source_url"] is None:
            errors.append(f"{prefix}: synthetic_from_advisory requires is_synthetic=true and source_url")
    if record["review_status"] == "gold":
        if record["split"] != "test" or record["pii_removed"] is not True:
            errors.append(f"{prefix}: gold records require split=test and pii_removed=true")
    return errors


def validate_file(path: Path) -> list[str]:
    errors = []
    records = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: invalid JSON: {exc.msg}")
            continue
        errors.extend(validate_record(record, line_number))
        if isinstance(record, dict):
            records.append((line_number, record))

    seen_ids = {}
    group_splits: dict[str, set[str]] = defaultdict(set)
    for line_number, record in records:
        record_id = record.get("id")
        if record_id in seen_ids:
            errors.append(f"line {line_number}: duplicate id {record_id!r}; first seen on line {seen_ids[record_id]}")
        else:
            seen_ids[record_id] = line_number
        group = record.get("campaign_group")
        split = record.get("split")
        if isinstance(group, str) and split in {"train", "validation", "test"}:
            group_splits[group].add(split)

    for group, splits in sorted(group_splits.items()):
        if len(splits) > 1:
            errors.append(f"campaign_group {group!r} crosses splits: {sorted(splits)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ScamLens SG JSONL message data.")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    errors = validate_file(args.path)
    if errors:
        print("Dataset validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    record_count = sum(bool(line.strip()) for line in args.path.read_text(encoding="utf-8").splitlines())
    print(f"Dataset valid: {record_count} records in {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

