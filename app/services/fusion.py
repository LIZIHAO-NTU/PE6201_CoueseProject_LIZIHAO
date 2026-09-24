from __future__ import annotations


TYPE_LABELS = {
    "government_impersonation": "Government impersonation",
    "investment": "Investment scam",
    "job": "Job scam",
    "e_commerce": "E-commerce scam",
    "uncertain": "Uncertain / other",
}


def fuse_assessments(*, local_result: dict, llm_result: dict | None, harm_escalation: bool) -> dict:
    local_level = local_result["risk_level"]
    final_level = local_level
    final_score = float(local_result["risk_score"])
    final_type = local_result["primary_type"]
    reasons: list[str] = []

    if harm_escalation:
        final_level = "high"
        final_score = max(final_score, 0.72)
        reasons.append("User-reported harm state forced a high-risk intervention")

    if llm_result and llm_result.get("status") == "success":
        assessment = llm_result["output"]["assessment"]
        if not harm_escalation:
            if local_level == "high":
                reasons.append("Local high-risk decision was preserved")
            elif local_level == "medium" and assessment == "likely_scam":
                final_level = "high"
                final_score = max(final_score, 0.72)
                reasons.append("LLM second opinion reinforced a suspicious local result")
            elif local_level == "low" and assessment in {"likely_scam", "uncertain"}:
                final_level = "medium"
                final_score = max(final_score, 0.40)
                reasons.append("LLM concern prevented low-risk reassurance")
            else:
                reasons.append("LLM second opinion did not change the local risk band")

        llm_type = llm_result["output"]["scam_type"]
        if final_type == "uncertain" and final_level != "low" and llm_type != "uncertain":
            final_type = llm_type
            reasons.append("LLM supplied a type only where the local model abstained")
    elif llm_result:
        reasons.append("LLM was unavailable; the verified local pipeline was used")

    return {
        "risk_level": final_level,
        "risk_score": round(min(final_score, 0.98), 3),
        "primary_type": final_type,
        "primary_type_label": TYPE_LABELS[final_type],
        "fusion_reasons": reasons,
    }
