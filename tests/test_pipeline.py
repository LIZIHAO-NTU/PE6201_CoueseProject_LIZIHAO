import json

from app.services.context_builder import build_llm_context
from app.services.ml_analyser import resolve_context_type
from app.services.pipeline import analyse_message
from app.services.retriever import RETRIEVER_VERSION, corpus_summary, retrieve_evidence
from app.services.telemetry import telemetry_store
from app.services.url_analyser import analyse_url, extract_urls


def _llm_settings(api_key="test-key"):
    return {
        "api_key": api_key,
        "model": "google/gemini-2.5-flash",
        "max_output_tokens": 400,
        "timeout_seconds": 15,
        "budget_usd": 8.0,
        "input_cost_per_million": 0.30,
        "output_cost_per_million": 2.50,
    }


def _fake_llm(assessment="likely_scam", scam_type="job"):
    def transport(**_kwargs):
        content = {
            "assessment": assessment,
            "scam_type": scam_type,
            "red_flags": ["Requests an unusual payment"],
            "missing_context": ["Sender identity is not independently verified"],
            "evidence_ids_used": ["scamshield-general-check"],
            "plain_language_explanation": "The message contains a pattern that should be verified independently.",
            "independent_verification_needed": True,
        }
        return {
            "model": "google/gemini-2.5-flash",
            "choices": [{"message": {"content": json.dumps(content)}}],
            "usage": {"prompt_tokens": 250, "completion_tokens": 80, "cost": 0.000275},
        }, 321.5

    return transport


def test_high_risk_government_impersonation_with_fake_url():
    result = analyse_message(
        message="Your Singpass account will be suspended immediately. Verify at https://singpass-gov-sg.example.com/login",
    )
    assert result["risk_level"] == "high"
    assert result["primary_type"] == "government_impersonation"
    assert result["urls"][0]["risk_level"] == "high"
    assert any("brand term" in signal for signal in result["urls"][0]["signals"])


def test_job_scam_without_url_is_detected():
    result = analyse_message(
        message="Part-time job: earn S$500 daily for simple tasks. Pay a S$50 deposit via PayNow to unlock commissions."
    )
    assert result["primary_type"] == "job"
    assert result["risk_level"] in {"medium", "high"}


def test_official_government_domain_is_not_penalised():
    item = analyse_url("https://www.scamshield.gov.sg/check-for-scams/")
    assert item["risk_level"] == "low"
    assert item["score"] <= 0.08


def test_gov_sg_in_attacker_domain_is_flagged():
    item = analyse_url("https://singpass.gov.sg.attacker-example.com/verify")
    assert item["risk_level"] == "high"
    assert item["registered_domain"] == "attacker-example.com"


def test_user_harm_state_escalates_actions():
    result = analyse_message(message="Hello", transferred_money=True)
    assert result["risk_level"] == "high"
    assert result["recommended_actions"][0]["priority"] == "urgent"
    assert "bank immediately" in result["recommended_actions"][0]["text"]


def test_url_extraction_strips_sentence_punctuation():
    assert extract_urls("Visit https://example.com/login, then reply.") == ["https://example.com/login"]


def test_trained_model_metadata_and_probabilities_are_returned():
    result = analyse_message(message="Your Singpass will be suspended. Verify your account now.")
    assert result["model_version"] == "tfidf-logreg-fusion-0.1"
    assert set(result["risk_probabilities"]) == {"ambiguous", "legitimate", "scam"}
    assert abs(sum(result["risk_probabilities"].values()) - 1.0) < 0.001


def test_medium_risk_explains_the_abstention():
    result = analyse_message(
        message="Your trading account shows S$18,400 profit. To withdraw it, pay the final S$1,200 tax and verification fee to the account provided."
    )
    assert result["risk_level"] == "medium"
    assert result["abstention_reasons"]


def test_off_platform_payment_guardrail_prevents_low_risk_reassurance():
    result = analyse_message(
        message=(
            "The marketplace checkout is unavailable. Send a S$120 deposit by PayNow; "
            "payment must be outside the platform."
        )
    )
    assert result["risk_level"] in {"medium", "high"}
    assert result["primary_type"] == "e_commerce"
    assert "off_platform_payment" in {item["id"] for item in result["mechanisms"]}
    assert result["guardrail_reasons"]
    assert result["safety_policy_version"] == "behaviour-guardrails-0.1"


def test_safe_in_platform_payment_warning_does_not_trigger_guardrail():
    result = analyse_message(
        message=(
            "Your marketplace order was paid through escrow inside the app. "
            "Do not transfer money directly to the seller."
        )
    )
    assert result["guardrail_reasons"] == []
    assert "off_platform_payment" not in {item["id"] for item in result["mechanisms"]}


def test_context_type_resolution_handles_cross_category_terms():
    assert resolve_context_type("Recruitment screening requires Singpass verification") == "job"
    assert resolve_context_type("CPF account verification is required") == "government_impersonation"
    assert resolve_context_type("Move the crypto to a new wallet") == "investment"
    assert resolve_context_type("Your parcel has an unpaid delivery fee") == "e_commerce"


def test_retriever_returns_category_specific_evidence_with_provenance():
    cases = [
        ("government_impersonation", "CPF officer says transfer funds to a safe account", "gov-safe-account-transfer"),
        ("investment", "Pay a withdrawal tax fee to release crypto profits", "investment-fake-profit-withdrawal"),
        ("job", "Part-time job requires a deposit to unlock task commissions", "job-task-advance-payment"),
        ("e_commerce", "Pay the Shopee seller directly outside the platform", "ecommerce-off-platform-payment"),
        ("uncertain", "Microsoft pop-up displays a support number for a virus warning", "tech-support-popup"),
    ]
    for primary_type, message, expected_id in cases:
        evidence = retrieve_evidence(message, primary_type)
        assert evidence[0]["id"] == expected_id
        assert evidence[0]["match_reasons"]
        assert evidence[0]["last_verified_date"] == "2026-08-15"
        assert evidence[0]["url"].startswith("https://")
        assert evidence[0]["retriever_version"] == RETRIEVER_VERSION


def test_rag_corpus_is_chunked_and_source_verified():
    summary = corpus_summary()
    assert summary["chunks"] == 24
    assert summary["source_pages"] == 12
    assert summary["last_verified_date"] == "2026-08-15"
    assert summary["chunk_types"]["recognition"] > 0
    assert summary["chunk_types"]["verification"] > 0
    assert summary["chunk_types"]["response"] > 0


def test_retriever_uses_user_harm_stage_for_response_evidence():
    evidence = retrieve_evidence(
        "I already transferred money to the account in the suspicious message.",
        "uncertain",
        user_state={"transferred_money": True},
    )
    assert evidence[0]["id"] == "scamshield-response-money"
    assert "transferred_money" in evidence[0]["matched_action_stages"]
    assert any("intervention stage" in reason for reason in evidence[0]["match_reasons"])


def test_evidence_retrieval_does_not_change_risk_decision():
    message = "Part-time job: earn commissions for simple tasks after paying a deposit."
    result = analyse_message(message=message)
    evidence = retrieve_evidence(message, result["primary_type"])
    assert result["risk_level"] in {"medium", "high"}
    assert result["risk_score"] == result["text_score"]
    assert evidence == result["evidence"]
    assert result["retriever_version"] == RETRIEVER_VERSION


def test_llm_is_off_by_default_and_does_not_call_transport():
    def fail_if_called(**_kwargs):
        raise AssertionError("LLM transport must not run in default local mode")

    result = analyse_message(message="Hello, are you free now?", llm_transport=fail_if_called)
    assert result["analysis_mode"]["requested"] == "local"
    assert result["analysis_mode"]["used"] == "local"
    assert result["llm_analysis"] is None


def test_llm_concern_can_only_conservatively_upgrade_a_low_local_result():
    telemetry_store.reset()
    result = analyse_message(
        message="Hello, are you free now?",
        use_llm=True,
        llm_settings=_llm_settings(),
        llm_transport=_fake_llm(assessment="likely_scam", scam_type="job"),
        developer_mode=True,
    )
    assert result["analysis_mode"]["used"] == "llm_enhanced"
    assert result["risk_level"] in {"medium", "high"}
    assert result["llm_analysis"]["status"] == "success"
    assert result["developer_diagnostics"]["llm_run"]["context_sent"]
    assert telemetry_store.snapshot()["calls"] == 1
    assert telemetry_store.snapshot()["by_model"][0]["model"] == "google/gemini-2.5-flash"
    assert telemetry_store.snapshot()["by_model"][0]["average_latency_ms"] == 321.5


def test_llm_cannot_downgrade_a_local_high_risk_result():
    result = analyse_message(
        message="Your Singpass is suspended. Enter your OTP at https://singpass-login.example.com now.",
        use_llm=True,
        llm_settings=_llm_settings(),
        llm_transport=_fake_llm(assessment="likely_legitimate", scam_type="uncertain"),
    )
    assert result["risk_level"] == "high"
    assert "preserved" in " ".join(result["fusion_reasons"])


def test_missing_key_falls_back_to_local_without_failure():
    telemetry_store.reset()
    result = analyse_message(
        message="Hello",
        use_llm=True,
        llm_settings=_llm_settings(api_key=""),
    )
    assert result["analysis_mode"]["used"] == "local"
    assert result["analysis_mode"]["fell_back"] is True
    assert "not configured" in result["llm_analysis"]["fallback_reason"]


def test_llm_context_redacts_common_personal_identifiers():
    local = analyse_message(message="Hello")
    context = build_llm_context(
        message="Email alex@example.com, call +65 9123 4567, NRIC S1234567D.",
        local_result={
            **local,
            "guardrail_reasons": local["guardrail_reasons"],
        },
        evidence=local["evidence"],
        user_state=local["user_state"],
    )
    assert "alex@example.com" not in context["untrusted_message"]
    assert "9123 4567" not in context["untrusted_message"]
    assert "S1234567D" not in context["untrusted_message"]
    assert len(context["retrieved_official_evidence"]) == 2
    assert context["retrieved_official_evidence"][0]["chunk_type"]
    assert context["retrieved_official_evidence"][0]["source_url"].startswith("https://")
    assert context["retrieved_official_evidence"][0]["last_verified_date"] == "2026-08-15"
