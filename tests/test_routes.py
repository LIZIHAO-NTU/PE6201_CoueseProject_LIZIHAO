import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "OPENROUTER_API_KEY": "",
            "SCAMLENS_EVALUATION_DB": str(tmp_path / "evaluation.sqlite3"),
            "SCAMLENS_EVALUATION_EXPORT_DIR": str(tmp_path / "exports"),
            "SCAMLENS_BENCHMARK_SYNC": True,
        }
    )
    return app.test_client()


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"ScamLens" in response.data
    assert b"Use LLM" in response.data
    assert b"Gemini" not in response.data
    assert b'name="use_llm"' in response.data
    assert b'name="use_llm" checked' not in response.data
    assert b"LI ZIHAO" in response.data
    assert b"G2606399B" in response.data
    assert b"PE6201" in response.data
    assert b"End-of-Course Project" in response.data


def test_api_rejects_missing_message(client):
    response = client.post("/api/v1/analyse", json={})
    assert response.status_code == 400


def test_api_returns_structured_assessment(client):
    response = client.post(
        "/api/v1/analyse",
        json={"message": "Your Singpass will be suspended. Verify at https://singpass-secure.example.com/login"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["risk_level"] == "high"
    assert payload["evidence"]
    assert payload["recommended_actions"]
    assert payload["safety_policy_version"] == "behaviour-guardrails-0.1"
    assert payload["retriever_version"] == "weighted-lexical-0.3"
    assert payload["evidence"][0]["match_reasons"]
    assert payload["evidence"][0]["last_verified_date"]
    assert payload["type_resolution_source"] in {"context_rule", "type_classifier"}


def test_evaluation_page_shows_frozen_model_results(client):
    response = client.get("/evaluation")
    assert response.status_code == 200
    assert b"95.0%" in response.data
    assert b"48 / 12 / 30" in response.data
    assert b"AI-assisted sanity check" in response.data
    assert b"0 / 12" in response.data
    assert b"Current dual-mode system" in response.data
    assert b"Cross-model experiment" in response.data
    assert b"Benchmark pending" in response.data


def test_about_page_describes_the_current_dual_mode_architecture(client):
    response = client.get("/about")
    assert response.status_code == 200
    assert b"Optional LLM" in response.data
    assert b"Conservative fusion" in response.data
    assert b"Developer mode" in response.data
    assert b"OpenRouter" in response.data


def test_developer_mode_is_a_one_click_session_toggle(client):
    client.application.config["SCAMLENS_LLM_MODEL"] = "google/gemini-2.5-flash"
    response = client.post("/developer/toggle", follow_redirects=True)
    assert response.status_code == 200
    assert b"Developer mode is on" in response.data
    assert b"Runtime configuration" in response.data
    assert b"google/gemini-2.5-flash" in response.data
    assert b"anthropic/claude-haiku-4.5" in response.data
    assert b"anthropic/claude-sonnet-4.6" in response.data
    assert b"24 chunks" in response.data

    response = client.post("/developer/toggle", follow_redirects=True)
    assert response.status_code == 200
    assert b"Developer mode is on" not in response.data


def test_developer_can_switch_the_active_llm_model(client):
    client.post("/developer/toggle")
    response = client.post(
        "/developer/model",
        data={"llm_model": "anthropic/claude-sonnet-4.6"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b'<option value="anthropic/claude-sonnet-4.6" selected>' in response.data
    assert b"US$3.00 input / US$15.00 output" in response.data


def test_developer_model_switch_rejects_unapproved_model_ids(client):
    client.post("/developer/toggle")
    response = client.post("/developer/model", data={"llm_model": "unknown/model"})
    assert response.status_code == 400


def test_llm_api_request_without_key_returns_safe_local_fallback(client):
    response = client.post(
        "/api/v1/analyse",
        json={"message": "Hello, are you free now?", "use_llm": True},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["analysis_mode"]["requested"] == "llm_enhanced"
    assert payload["analysis_mode"]["used"] == "local"
    assert payload["analysis_mode"]["fell_back"] is True


def test_assessments_are_persisted_without_raw_message(client):
    message = "Private test phrase that must never appear in SQLite"
    response = client.post("/api/v1/analyse", json={"message": message})
    assert response.status_code == 200

    store = client.application.extensions["scamlens_evaluation_store"]
    overview = store.persistent_overview()
    assert overview["assessments"] == 1
    assert message.encode("utf-8") not in store.database_path.read_bytes()


def test_developer_can_run_export_and_freeze_a_local_benchmark(client):
    client.post("/developer/toggle")
    response = client.post(
        "/developer/benchmark",
        data={
            "dataset_id": "sanity-v0.2",
            "case_limit": "3",
            "budget_cap_usd": "0",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Latest automatic performance summary" in response.data

    store = client.application.extensions["scamlens_evaluation_store"]
    run = store.list_benchmarks()[0]
    assert run["status"] == "completed"
    assert run["progress_completed"] == 3
    assert run["summary"]["variants"][0]["variant"] == "local"
    assert run["summary"]["retrieval"]["mean_reciprocal_rank"] == 1.0
    assert (store.export_dir / f"benchmark_{run['run_id']}.json").exists()
    assert (store.export_dir / f"benchmark_{run['run_id']}.csv").exists()

    csv_response = client.get(f"/developer/benchmark/{run['run_id']}/export.csv")
    assert csv_response.status_code == 200
    assert b"message_hash" in csv_response.data
    assert b"MOM investigation unit" not in csv_response.data

    json_response = client.get(f"/developer/benchmark/{run['run_id']}/export.json")
    assert json_response.status_code == 200
    assert b'"results"' in json_response.data
    assert b"MOM investigation unit" not in json_response.data

    freeze_response = client.post(
        f"/developer/benchmark/{run['run_id']}/freeze", follow_redirects=True
    )
    assert freeze_response.status_code == 200
    assert store.get_benchmark(run["run_id"])["is_frozen"] is True
    assert (store.export_dir / "frozen_benchmark.json").exists()
    assert (store.export_dir / "frozen_benchmark.csv").exists()

    evaluation_response = client.get("/evaluation")
    assert b"Frozen benchmark" in evaluation_response.data
