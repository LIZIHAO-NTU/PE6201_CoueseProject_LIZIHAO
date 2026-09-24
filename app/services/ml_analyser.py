from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import joblib

from .text_analyser import TYPE_PATTERNS, analyse_text
from .url_analyser import analyse_urls


MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
CONFIG_PATH = MODEL_DIR / "model_config_v0.1.json"
SAFETY_POLICY_VERSION = "behaviour-guardrails-0.1"

TYPE_CONTEXT_PATTERNS = [
    (
        "job",
        re.compile(
            r"\b(?:job|recruit(?:er|ment)?|employment|position|vacan(?:cy|cies)|career|commission|hr|data[- ]entry)\b"
            r"|\bapplication (?:is )?(?:shortlisted|approved)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "government_impersonation",
        re.compile(r"\b(?:singpass|cpf|iras|mom|moh|ministry|police|government)\b", re.IGNORECASE),
    ),
    (
        "investment",
        re.compile(
            r"\b(?:invest(?:ment|ing)?|crypto|trading|forex|profit|wallet|shares?|withdraw(?:al)?)\b"
            r"|\b(?:guaranteed|high|\d+(?:\.\d+)?%) returns?\b|\bfund (?:your|the) account\b",
            re.IGNORECASE,
        ),
    ),
    (
        "e_commerce",
        re.compile(
            r"\b(?:carousell|shopee|lazada|marketplace|parcel|buyer|seller|order)\b"
            r"|\b(?:delivery fee|transport insurance|reservation deposit|customs charge)\b",
            re.IGNORECASE,
        ),
    ),
]


@lru_cache(maxsize=1)
def _artifacts() -> tuple[dict, object, object]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    risk_model = joblib.load(MODEL_DIR / config["risk_model_file"])
    type_model = joblib.load(MODEL_DIR / config["type_model_file"])
    return config, risk_model, type_model


def _probability_map(model: object, message: str) -> dict[str, float]:
    values = model.predict_proba([message])[0]
    return {
        str(label): round(float(probability), 6)
        for label, probability in zip(model.classes_, values, strict=True)
    }


def resolve_context_type(message: str) -> str | None:
    """Return an auditable high-signal type, with job context outranking identity tools."""
    for type_id, pattern in TYPE_CONTEXT_PATTERNS:
        if pattern.search(message):
            return type_id
    return None


def analyse_with_model(message: str) -> dict:
    config, risk_model, type_model = _artifacts()
    risk_probabilities = _probability_map(risk_model, message)
    type_probabilities = _probability_map(type_model, message)
    url_results = analyse_urls(message)
    max_url_score = max((item["score"] for item in url_results), default=0.0)
    text_scam_probability = risk_probabilities.get("scam", 0.0)

    if url_results:
        text_weight = config["text_weight"]
        fused_score = text_weight * text_scam_probability + (1 - text_weight) * max_url_score
    else:
        fused_score = text_scam_probability
    fused_score = round(min(max(fused_score, 0.0), 1.0), 3)

    max_probability = max(risk_probabilities.values())
    abstention_reasons = []
    if fused_score >= config["high_threshold"]:
        risk_level = "high"
    else:
        if fused_score >= config["medium_threshold"]:
            abstention_reasons.append("scam probability is above the verification threshold")
        if risk_probabilities.get("ambiguous", 0.0) >= config["ambiguous_threshold"]:
            abstention_reasons.append("the message resembles insufficient-information cases")
        if max_probability < config["confidence_threshold"]:
            abstention_reasons.append("the classifier confidence is low")
        risk_level = "medium" if abstention_reasons else "low"

    rule_result = analyse_text(message)
    mechanism_ids = {item["id"] for item in rule_result["mechanisms"]}
    guardrail_reasons = []
    if {"off_platform_payment", "payment_request"}.issubset(mechanism_ids):
        guardrail_reasons.append(
            "the message requests payment outside a marketplace's protected checkout"
        )
        if risk_level == "low":
            risk_level = "medium"
            fused_score = round(max(fused_score, config["medium_threshold"]), 3)
            abstention_reasons.append(guardrail_reasons[0])

    if risk_level == "low":
        primary_type = "uncertain"
        primary_type_label = "Uncertain / other"
        type_resolution_source = "suppressed_for_low_risk"
    else:
        context_type = resolve_context_type(message)
        primary_type = context_type or max(type_probabilities, key=type_probabilities.get)
        primary_type_label = TYPE_PATTERNS[primary_type]["label"]
        type_resolution_source = "context_rule" if context_type else "type_classifier"

    return {
        "risk_level": risk_level,
        "risk_score": fused_score,
        "primary_type": primary_type,
        "primary_type_label": primary_type_label,
        "mechanisms": rule_result["mechanisms"],
        "text_score": round(text_scam_probability, 3),
        "rules_text_score": rule_result["score"],
        "risk_probabilities": risk_probabilities,
        "type_probabilities": type_probabilities,
        "type_resolution_source": type_resolution_source,
        "urls": url_results,
        "max_url_score": max_url_score,
        "text_weight": config["text_weight"],
        "abstention_reasons": abstention_reasons,
        "guardrail_reasons": guardrail_reasons,
        "model_version": config["model_version"],
        "safety_policy_version": SAFETY_POLICY_VERSION,
    }
