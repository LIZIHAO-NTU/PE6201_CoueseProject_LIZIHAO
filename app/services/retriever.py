from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "advisories.json"
TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]", re.IGNORECASE)
RETRIEVER_VERSION = "weighted-lexical-0.3"
REQUIRED_FIELDS = {
    "id",
    "document_id",
    "source",
    "source_domain",
    "title",
    "chunk_type",
    "action_stages",
    "audiences",
    "source_updated_date",
    "last_verified_date",
    "summary",
    "evidence",
    "actions",
    "url",
    "scam_types",
    "keywords",
    "phrases",
}
CHUNK_TYPES = {"recognition", "verification", "prevention", "response"}
ACTION_STAGES = {"pre_action", "clicked_link", "shared_credentials", "transferred_money"}
TYPE_LABELS = {
    "government_impersonation": "government impersonation",
    "investment": "investment",
    "job": "job",
    "e_commerce": "e-commerce",
    "uncertain": "uncertain or cross-cutting",
}


def _token_list(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_RE.findall(text)
        if len(token) > 1 or "\u4e00" <= token <= "\u9fff"
    ]


def _tokens(text: str) -> set[str]:
    return set(_token_list(text))


def _document_text(document: dict) -> str:
    return " ".join(
        [
            document["title"],
            document["summary"],
            document["evidence"],
            " ".join(document.get("actions", [])),
            " ".join(document.get("keywords", [])),
            " ".join(document.get("phrases", [])),
            document.get("chunk_type", ""),
            " ".join(document.get("action_stages", [])),
            " ".join(document.get("audiences", [])),
        ]
    )


@lru_cache(maxsize=1)
def _documents() -> list[dict]:
    documents = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    ids = [document.get("id") for document in documents]
    if len(ids) != len(set(ids)):
        raise ValueError("Evidence chunk IDs must be unique")
    for document in documents:
        missing = REQUIRED_FIELDS - set(document)
        if missing:
            raise ValueError(
                f"Evidence chunk is missing required fields: {document.get('id', '<unknown>')} "
                f"({', '.join(sorted(missing))})"
            )
        if document["chunk_type"] not in CHUNK_TYPES:
            raise ValueError(f"Unsupported evidence chunk type: {document['id']}")
        if not document["action_stages"] or not set(document["action_stages"]) <= ACTION_STAGES:
            raise ValueError(f"Unsupported evidence action stage: {document['id']}")
        parsed = urlparse(document["url"])
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError(f"Evidence source must use an absolute HTTPS URL: {document['id']}")
        hostname = parsed.hostname.lower()
        source_domain = document["source_domain"].lower()
        if hostname != source_domain and not hostname.endswith(f".{source_domain}"):
            raise ValueError(f"Evidence source domain mismatch: {document['id']}")
    return documents


def corpus_summary() -> dict:
    documents = _documents()
    return {
        "chunks": len(documents),
        "source_pages": len({document["document_id"] for document in documents}),
        "official_domains": sorted({document["source_domain"] for document in documents}),
        "chunk_types": dict(Counter(document["chunk_type"] for document in documents)),
        "last_verified_date": max(document["last_verified_date"] for document in documents),
        "retriever_version": RETRIEVER_VERSION,
    }


def _active_action_stages(user_state: dict | None) -> set[str]:
    if not user_state:
        return {"pre_action"}
    active = {
        stage
        for stage in ("clicked_link", "shared_credentials", "transferred_money")
        if user_state.get(stage)
    }
    return active or {"pre_action"}


@lru_cache(maxsize=1)
def _index() -> tuple[dict[str, float], dict[str, set[str]]]:
    documents = _documents()
    document_tokens = {document["id"]: _tokens(_document_text(document)) for document in documents}
    document_frequency: Counter[str] = Counter()
    for tokens in document_tokens.values():
        document_frequency.update(tokens)
    count = len(documents)
    idf = {
        token: math.log((count + 1) / (frequency + 1)) + 1
        for token, frequency in document_frequency.items()
    }
    return idf, document_tokens


def _weighted_coverage(query_tokens: set[str], document_tokens: set[str], idf: dict[str, float]) -> float:
    if not query_tokens:
        return 0.0
    denominator = sum(idf.get(token, 1.0) for token in query_tokens)
    numerator = sum(idf.get(token, 1.0) for token in query_tokens & document_tokens)
    return numerator / max(denominator, 1.0)


def _matched_phrases(message: str, document: dict) -> list[str]:
    lowered = message.lower()
    return [phrase for phrase in document.get("phrases", []) if phrase.lower() in lowered]


def _score_document(
    *,
    message: str,
    query_tokens: set[str],
    primary_type: str,
    document: dict,
    idf: dict[str, float],
    document_tokens: set[str],
    active_action_stages: set[str],
) -> tuple[float, list[str], list[str]]:
    coverage = _weighted_coverage(query_tokens, document_tokens, idf)
    keyword_matches = sorted(query_tokens & _tokens(" ".join(document.get("keywords", []))))
    phrase_matches = _matched_phrases(message, document)
    type_match = primary_type in document["scam_types"]
    action_stage_matches = sorted(active_action_stages & set(document["action_stages"]))

    score = 0.58 * coverage
    score += min(len(keyword_matches), 4) * 0.055
    score += min(len(phrase_matches), 2) * 0.12
    score += 0.08 if type_match else 0.0
    if active_action_stages != {"pre_action"}:
        score += 0.16 if action_stage_matches else 0.0
        if document["chunk_type"] == "response" and not action_stage_matches:
            score -= 0.06
    elif document["chunk_type"] == "response" and "pre_action" not in document["action_stages"]:
        score -= 0.06
    if primary_type and not type_match and document["id"] != "scamshield-general-check":
        score -= 0.08
    if document["id"] == "scamshield-general-check":
        score += 0.06

    reasons = []
    if type_match:
        reasons.append(f"Matches assessed type: {TYPE_LABELS.get(primary_type, primary_type)}")
    if keyword_matches:
        reasons.append(f"Matched cues: {', '.join(keyword_matches[:5])}")
    if phrase_matches:
        reasons.append(f"Matched phrase: {phrase_matches[0]}")
    if action_stage_matches and active_action_stages != {"pre_action"}:
        reasons.append(
            "Matches intervention stage: "
            + ", ".join(stage.replace("_", " ") for stage in action_stage_matches)
        )
    if document["id"] == "scamshield-general-check" and len(reasons) == 1:
        reasons.append("General Singapore verification and helpline guidance")

    return score, reasons, keyword_matches


def retrieve_evidence(
    message: str,
    primary_type: str,
    limit: int = 3,
    user_state: dict | None = None,
) -> list[dict]:
    """Return auditable evidence without changing the model's risk decision.

    Ranking combines IDF-weighted query coverage, curated cue/phrase matches and
    an assessed-type boost. Every returned item includes provenance and match
    reasons so retrieval quality can be evaluated independently.
    """

    clean_message = message.replace("_", " ").strip()
    query_tokens = _tokens(clean_message)
    active_action_stages = _active_action_stages(user_state)
    idf, indexed_tokens = _index()
    ranked = []
    for position, document in enumerate(_documents()):
        score, reasons, keyword_matches = _score_document(
            message=clean_message,
            query_tokens=query_tokens,
            primary_type=primary_type,
            document=document,
            idf=idf,
            document_tokens=indexed_tokens[document["id"]],
            active_action_stages=active_action_stages,
        )
        ranked.append((score, -position, document, reasons, keyword_matches))

    results = []
    for rank, (score, _, document, reasons, keyword_matches) in enumerate(
        sorted(ranked, key=lambda item: (item[0], item[1]), reverse=True)[: max(1, limit)],
        start=1,
    ):
        results.append(
            {
                **document,
                "rank": rank,
                "retrieval_score": round(score, 3),
                "retriever_version": RETRIEVER_VERSION,
                "match_reasons": reasons or ["Fallback official guidance"],
                "matched_keywords": keyword_matches[:5],
                "matched_action_stages": (
                    sorted(active_action_stages & set(document["action_stages"]))
                    if active_action_stages != {"pre_action"}
                    else []
                ),
            }
        )
    return results
