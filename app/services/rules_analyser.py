from __future__ import annotations

from .text_analyser import analyse_text
from .url_analyser import analyse_urls


def analyse_with_rules(message: str) -> dict:
    text_result = analyse_text(message)
    url_results = analyse_urls(message)
    max_url_score = max((item["score"] for item in url_results), default=0.0)
    if url_results:
        score = 0.58 * text_result["score"] + 0.42 * max_url_score
        if text_result["score"] >= 0.5 and max_url_score >= 0.5:
            score += 0.12
        elif text_result["score"] >= 0.35 and max_url_score >= 0.5:
            score += 0.22
    else:
        score = text_result["score"]
    score = round(min(score, 0.98), 3)
    risk_level = "high" if score >= 0.64 else "medium" if score >= 0.34 else "low"
    return {
        "risk_level": risk_level,
        "risk_score": score,
        "primary_type": text_result["primary_type"],
        "primary_type_label": text_result["primary_type_label"],
        "mechanisms": text_result["mechanisms"],
        "urls": url_results,
        "model_version": "mvp-rules-0.1",
    }
