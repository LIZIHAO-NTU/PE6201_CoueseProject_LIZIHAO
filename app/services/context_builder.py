from __future__ import annotations

import hashlib
import json
import re


EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
SG_PHONE_RE = re.compile(r"(?<!\d)(?:\+?65[\s-]?)?[689]\d{3}[\s-]?\d{4}(?!\d)")
NRIC_RE = re.compile(r"(?<![A-Za-z0-9])[STFGM]\d{7}[A-Za-z](?![A-Za-z0-9])", re.IGNORECASE)


def redact_message(message: str) -> str:
    redacted = EMAIL_RE.sub("[EMAIL REDACTED]", message)
    redacted = SG_PHONE_RE.sub("[PHONE REDACTED]", redacted)
    redacted = NRIC_RE.sub("[ID REDACTED]", redacted)
    return redacted[:4000]


def build_llm_context(
    *,
    message: str,
    local_result: dict,
    evidence: list[dict],
    user_state: dict,
) -> dict:
    urls = [
        {
            "host": item.get("host"),
            "registered_domain": item.get("registered_domain"),
            "risk_level": item.get("risk_level"),
            "score": item.get("score"),
            "signals": item.get("signals", [])[:5],
        }
        for item in local_result.get("urls", [])[:3]
    ]
    compact_evidence = [
        {
            "id": item.get("id"),
            "source": item.get("source"),
            "title": item.get("title"),
            "chunk_type": item.get("chunk_type"),
            "action_stages": item.get("action_stages", []),
            "evidence": item.get("evidence"),
            "match_reasons": item.get("match_reasons", [])[:3],
            "source_url": item.get("url"),
            "last_verified_date": item.get("last_verified_date"),
        }
        for item in evidence[:2]
    ]
    return {
        "untrusted_message": redact_message(message),
        "local_assessment": {
            "risk_level": local_result["risk_level"],
            "risk_score": local_result["risk_score"],
            "primary_type": local_result["primary_type"],
            "risk_probabilities": local_result.get("risk_probabilities", {}),
            "signals": [item.get("label") for item in local_result.get("mechanisms", [])[:8]],
            "guardrails": local_result.get("guardrail_reasons", []),
        },
        "url_analysis": urls,
        "user_state": user_state,
        "retrieved_official_evidence": compact_evidence,
    }


def context_hash(context: dict) -> str:
    serialised = json.dumps(context, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(serialised).hexdigest()[:16]
