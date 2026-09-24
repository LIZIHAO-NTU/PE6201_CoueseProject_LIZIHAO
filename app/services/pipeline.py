from __future__ import annotations

from time import perf_counter

from .context_builder import build_llm_context
from .fusion import fuse_assessments
from .intervention import recommend_actions
from .llm_analyser import PROMPT_VERSION, analyse_with_llm
from .ml_analyser import analyse_with_model
from .retriever import RETRIEVER_VERSION, retrieve_evidence
from .telemetry import telemetry_store


def analyse_message(
    *,
    message: str,
    clicked_link: bool = False,
    shared_credentials: bool = False,
    transferred_money: bool = False,
    use_llm: bool = False,
    developer_mode: bool = False,
    llm_settings: dict | None = None,
    llm_transport=None,
) -> dict:
    started = perf_counter()
    model_result = analyse_with_model(message)
    user_state = {
        "clicked_link": clicked_link,
        "shared_credentials": shared_credentials,
        "transferred_money": transferred_money,
    }
    evidence = retrieve_evidence(
        message,
        model_result["primary_type"],
        user_state=user_state,
    )

    llm_result = None
    if use_llm:
        settings = llm_settings or {
            "api_key": "",
            "model": "google/gemini-2.5-flash",
            "max_output_tokens": 400,
            "timeout_seconds": 15,
            "budget_usd": 8.0,
            "input_cost_per_million": 0.30,
            "output_cost_per_million": 2.50,
        }
        llm_context = build_llm_context(
            message=message,
            local_result=model_result,
            evidence=evidence,
            user_state=user_state,
        )
        llm_result = analyse_with_llm(
            context=llm_context,
            settings=settings,
            transport=llm_transport,
        )

    fused = fuse_assessments(
        local_result=model_result,
        llm_result=llm_result,
        harm_escalation=shared_credentials or transferred_money,
    )
    risk_level = fused["risk_level"]
    fused_score = fused["risk_score"]
    primary_type = fused["primary_type"]
    if primary_type != model_result["primary_type"]:
        evidence = retrieve_evidence(message, primary_type, user_state=user_state)

    actions = recommend_actions(
        risk_level=risk_level,
        primary_type=primary_type,
        clicked_link=clicked_link,
        shared_credentials=shared_credentials,
        transferred_money=transferred_money,
    )

    llm_succeeded = bool(llm_result and llm_result.get("status") == "success")
    public_llm = None
    if llm_result:
        public_llm = {
            "status": llm_result["status"],
            "model": llm_result["model"],
            "fallback_reason": llm_result.get("fallback_reason"),
            "output": llm_result.get("output"),
            "latency_ms": llm_result.get("latency_ms"),
            "prompt_tokens": llm_result.get("prompt_tokens", 0),
            "completion_tokens": llm_result.get("completion_tokens", 0),
            "estimated_cost_usd": llm_result.get("estimated_cost_usd", 0.0),
        }

    result = {
        "risk_level": risk_level,
        "risk_score": fused_score,
        "assessment_label": {
            "high": "High risk - likely scam",
            "medium": "Suspicious - verify independently",
            "low": "Low detected risk - not a guarantee of safety",
        }[risk_level],
        "primary_type": primary_type,
        "primary_type_label": fused["primary_type_label"],
        "mechanisms": model_result["mechanisms"],
        "text_score": model_result["text_score"],
        "rules_text_score": model_result["rules_text_score"],
        "risk_probabilities": model_result["risk_probabilities"],
        "type_probabilities": model_result["type_probabilities"],
        "type_resolution_source": model_result["type_resolution_source"],
        "urls": model_result["urls"],
        "abstention_reasons": model_result["abstention_reasons"],
        "guardrail_reasons": model_result["guardrail_reasons"],
        "fusion_reasons": fused["fusion_reasons"],
        "evidence": evidence,
        "recommended_actions": actions,
        "user_state": user_state,
        "analysis_mode": {
            "requested": "llm_enhanced" if use_llm else "local",
            "used": "llm_enhanced" if llm_succeeded else "local",
            "label": "Local + LLM second opinion" if llm_succeeded else "Local analysis",
            "fell_back": bool(use_llm and not llm_succeeded),
        },
        "llm_analysis": public_llm,
        "disclaimer": "This student prototype provides a risk assessment, not a definitive determination. When in doubt, verify through official channels or call ScamShield at 1799.",
        "model_version": model_result["model_version"],
        "safety_policy_version": model_result["safety_policy_version"],
        "retriever_version": RETRIEVER_VERSION,
        "prompt_version": PROMPT_VERSION if use_llm else None,
        "performance": {
            "total_latency_ms": round((perf_counter() - started) * 1000, 1),
        },
    }
    if developer_mode:
        result["developer_diagnostics"] = {
            "local_decision": {
                "risk_level": model_result["risk_level"],
                "risk_score": model_result["risk_score"],
                "primary_type": model_result["primary_type"],
                "type_resolution_source": model_result["type_resolution_source"],
                "risk_probabilities": model_result["risk_probabilities"],
                "type_probabilities": model_result["type_probabilities"],
                "guardrails": model_result["guardrail_reasons"],
            },
            "llm_run": llm_result,
            "fusion": fused,
            "retrieval": [
                {
                    "rank": item["rank"],
                    "id": item["id"],
                    "retrieval_score": item["retrieval_score"],
                    "match_reasons": item["match_reasons"],
                    "chunk_type": item["chunk_type"],
                    "action_stages": item["action_stages"],
                    "matched_action_stages": item["matched_action_stages"],
                }
                for item in evidence
            ],
            "url_analysis": model_result["urls"],
            "session_telemetry": telemetry_store.snapshot(),
        }
    return result
