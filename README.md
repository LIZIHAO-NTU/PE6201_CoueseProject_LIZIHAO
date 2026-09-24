# ScamLens SG

[![Tests](https://github.com/LIZIHAO-NTU/PE6201_CoueseProject_LIZIHAO/actions/workflows/tests.yml/badge.svg)](https://github.com/LIZIHAO-NTU/PE6201_CoueseProject_LIZIHAO/actions/workflows/tests.yml)

**Release: v2.0**

An evidence-grounded, multi-signal scam risk assessment and intervention assistant for Singapore residents. This repository contains the final Flask course prototype for the PE6201 End-of-Course Project.

## What the prototype does

- Accepts pasted SMS, WhatsApp or email text.
- Detects four primary scam categories: government official impersonation, investment, job and e-commerce.
- Identifies cross-cutting mechanisms such as urgency, credential requests, payment requests and app installation.
- Extracts URLs and performs static lexical/domain analysis without visiting them.
- Fuses text and URL risk scores.
- Retrieves ranked evidence from a curated, source-verified set of Singapore official guidance, and explains why each item matched.
- Offers an explicitly enabled LLM second opinion through OpenRouter; it is off by default and fails safely back to local analysis.
- Includes a one-click developer mode for local/LLM/fusion traces, RAG ranks, URL diagnostics, token use, latency, estimated cost and fallback reasons.
- Persists privacy-minimised assessment telemetry and labelled benchmark results in local SQLite.
- Runs controlled local/cross-model benchmarks with automatic performance, RAG, latency, token and cost summaries.
- Exports every completed benchmark to CSV and JSON and can freeze one run for the Evaluation page.
- Changes intervention advice based on whether the user clicked, shared credentials or transferred money.
- Exposes both a web interface and `POST /api/v1/analyse` JSON endpoint.

## Run locally

Python 3.11 is recommended. Local analysis works without an API key.

```bat
conda create -n scamlens python=3.11 -y
conda activate scamlens
python -m pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:5000`.

## Architecture

`message → local ML and guardrails → static URL analysis → official-source retrieval → optional LLM second opinion → conservative fusion → deterministic intervention`

- `app/services/` contains the independently testable ML, URL, retrieval, LLM, fusion, intervention and evaluation modules.
- `app/templates/` and `app/static/` contain the Flask user interface.
- `data/` contains versioned schemas, reviewed datasets, model metadata and the curated evidence corpus.
- `scripts/` contains validation, training and evaluation entry points.
- `outputs/evaluation/` contains frozen and diagnostic results; `tests/` contains regression and safety tests.

## Optional OpenRouter integration

Do not paste the course API key into Python, HTML, JavaScript or Git. Copy `.env.example` to `.env`, place the key only in `OPENROUTER_API_KEY`, and keep `.env` uncommitted. The application loads only the `OPENROUTER_API_KEY` and `SCAMLENS_*` entries from this local file and uses `google/gemini-2.5-flash` by default.

The LLM is deliberately **off by default**. A user must turn on **Use LLM** for an individual assessment. Only a compact context is sent: a redacted message, local probabilities and signals, static URL findings, user harm state and the top two official evidence records. Email addresses, Singapore phone numbers and NRIC-like identifiers are masked first.

The deterministic fusion policy is safety-oriented: the LLM cannot downgrade a local high-risk result or a user-harm escalation. If the API key is missing, the local budget guard is reached, OpenRouter times out, or structured output validation fails, ScamLens returns the local result with a visible fallback notice.

The local server-session guard defaults to US$8.00, leaving headroom on a US$10 course allowance. Change `SCAMLENS_LLM_BUDGET_USD` if the key is shared or governed elsewhere. Cost in developer mode uses the provider-reported value when available and otherwise an estimate based on the configurable rates in `.env.example`.

## Developer mode

Use the **Developer off/on** control in the navigation bar. One click enters the diagnostics dashboard; one click exits it. While enabled, every assessment also displays its local decision, LLM request context, fusion explanation, RAG ranking and URL analysis. The dashboard never displays the API key, raw provider response or unredacted prompt message.

Developer mode also provides a session-scoped model switcher. The allowlist contains `google/gemini-2.5-flash` for routine runs, `anthropic/claude-haiku-4.5` for a fast cross-family comparison and `anthropic/claude-sonnet-4.6` for selective high-quality review. Each profile supplies its own fallback cost-estimation rates; OpenRouter-reported cost still takes precedence when present.

## Persistent evaluation automation

Every web/API assessment writes only operational metadata and a short message hash to `instance/scamlens_evaluation.sqlite3`; raw pasted messages are never stored. These unlabelled events support latency, fallback, token and cost observability, but are deliberately excluded from accuracy claims.

Developer mode can run a labelled benchmark in the background. The local baseline is always included and any allowlisted LLM variants receive the same cases and pipeline context. Before paid calls begin, ScamLens estimates a conservative maximum cost, checks it against the per-run cap and requires explicit confirmation. The benchmark automatically calculates:

- exact three-way accuracy, operational/high-risk scam recall and legitimate false-positive rate;
- ambiguous-case abstention, scam-type accuracy and critical false reassurance count;
- structured-output success, fallback rate, mean/P50/P95 latency, token use and cost;
- retrieval Top-1/Top-3 coverage, MRR, category coverage and provenance completeness.

Completed runs are written automatically to `outputs/evaluation/persistent/benchmark_<run_id>.json` and `.csv`. Freezing a completed run also updates `frozen_benchmark.json` and `.csv`; the public Evaluation page reads the same frozen SQLite summary. Exports contain case IDs, labels, hashes, predictions and diagnostics, but not message text.

## Run tests

```bat
python -m pytest -q
```

Every push and pull request runs the same test suite through GitHub Actions. Key offline evaluation steps can be reproduced with:

```bat
python scripts/check_dataset_leakage.py data\training\message_training_candidates_v0.1.jsonl data\eval\message_gold_test_v0.1.jsonl
python scripts/evaluate_baseline.py
python scripts/evaluate_deployed_model.py
python scripts/evaluate_retriever.py
```

## JSON API

Send a JSON object to `POST /api/v1/analyse`. The message is required; state flags must be JSON booleans.

```json
{
  "message": "Your account will be suspended. Verify at https://example.com",
  "clicked_link": false,
  "shared_credentials": false,
  "transferred_money": false,
  "use_llm": false
}
```

## Current model

The final prototype uses word and character TF-IDF features with Logistic Regression for risk classification. Operating thresholds were selected only on the validation split. A small auditable safety-policy layer prevents low-risk reassurance for explicit off-platform marketplace payment requests, and a context resolver improves scam-type explanations before falling back to the trained type classifier. Static URL inspection, rule-based mechanism extraction, lexical evidence retrieval and intervention logic remain separate and auditable modules. The original weighted-rule detector is retained as an evaluation baseline.

The reviewed datasets are small and mostly synthetic. Reported results demonstrate the engineering and evaluation workflow; they are not evidence of deployment readiness.

## Frozen evaluation result

On the 30-record gold test set, the trained deployment achieved 95.0% operational scam recall and 63.3% exact three-way accuracy, compared with 30.0% and 30.0% for the rules baseline. The trained model's legitimate false-positive rate was 14.3%, and one scam received a low-risk result. The complete student review is available in [`outputs/evaluation/deployed_predictions_review_v0.2.csv`](outputs/evaluation/deployed_predictions_review_v0.2.csv), with its structured summary in [`outputs/evaluation/model_error_review_results_v0.1.json`](outputs/evaluation/model_error_review_results_v0.1.json).

Validation selected a text weight of 1.0. URL inspection therefore remains a separately displayed safety signal but does not change the frozen numerical risk score in this small-data configuration.

## Human error review and mitigation

The 17 non-correct gold-test outputs were reviewed using three impact levels. The review found one critical low-risk false reassurance, ten issues needing mitigation and six acceptable safety trade-offs. The resulting behaviour guardrail and type-context resolver were checked on the unchanged validation split before regression testing.

The original gold-test result remains the independent frozen result. The post-review run is documented separately as a diagnostic because the gold error review informed the mitigation priorities; it must not be presented as a fresh independent test estimate. In that diagnostic, no gold scam remained low risk and the type explanations were correct for all 20 gold scams. A new untouched evaluation set is required to confirm generalisation.

An additional 20-case AI-assisted sanity-check benchmark was reviewed before model scoring. It achieved 100.0% operational scam recall, 0.0% legitimate false-positive rate, 100.0% ambiguous-case abstention recall and 100.0% deployed scam-type accuracy. Exact three-way accuracy was 70.0% because six scams received the intentionally conservative medium-risk outcome. No scam received low risk. Because AI assisted with both authoring and review, these are regression and demonstration results rather than independent evidence.

## Evidence retrieval

The `weighted-lexical-0.3` retriever ranks 24 purpose-specific evidence chunks from 12 official source pages. Ranking combines IDF-weighted query coverage, scam-type alignment, auditable cue/phrase matches and an intervention-stage boost when the user reports clicking, sharing credentials or transferring money. Each result includes chunk metadata, source provenance, rank and match reasons. Retrieval alone cannot change the local numerical risk score; when LLM mode is enabled, the top two chunks ground the second-stage review.

On the 32-case designer-authored retrieval regression benchmark, acceptable top-1 accuracy, expected-document top-3 coverage, required-category top-3 coverage, required-action-stage coverage and provenance completeness were all 100.0%. This is a deterministic engineering benchmark created during development, not independent evidence of real-world RAG quality. Reproduce it with:

```bat
python scripts/evaluate_retriever.py
```

The source register and methodology are documented in `docs/retrieval_design_and_sources.md`; detailed output is in `outputs/evaluation/retrieval_evaluation_v0.2.md`.

This is a student prototype and is not affiliated with or endorsed by the Singapore Government. It does not provide a definitive determination that a message or URL is safe.

## Data preparation

Before collecting training or evaluation data, follow the [data annotation guide](docs/data_annotation_guide.md). The machine-readable field contract is in `data/schemas/message_record.schema.json`, and illustrative records are in `data/templates/annotation_examples.jsonl`.

Validate any JSONL dataset with:

```bat
python scripts/validate_message_dataset.py path\to\dataset.jsonl
```

The first 30 evaluation candidates were student-reviewed and promoted to the fixed test set at `data/eval/message_gold_test_v0.1.jsonl`. Do not use this file for training or threshold tuning. The initial rule baseline results are recorded in `outputs/evaluation/baseline_evaluation_v0.1.md`.

The 60 training/validation candidates at `data/training/message_training_candidates_v0.1.jsonl` were reviewed before model training. The review table is in [`data/training/message_training_review_v0.1.csv`](data/training/message_training_review_v0.1.csv), with its structured summary in [`data/training/message_training_review_results_v0.1.json`](data/training/message_training_review_results_v0.1.json). The modelling and comparison sequence is documented in [`docs/model_development_plan.md`](docs/model_development_plan.md).

Check train/test leakage with:

```bat
python scripts/check_dataset_leakage.py data\training\message_training_candidates_v0.1.jsonl data\eval\message_gold_test_v0.1.jsonl
```

## Security, privacy and responsible-use boundaries

- Browser state-changing forms use CSRF protection; responses include a restrictive content security policy and standard browser security headers.
- The JSON API validates types and limits messages to 8,000 characters. Flask also enforces a request-size limit.
- URLs are inspected statically and are never opened. LLM output is schema-validated, and cited evidence IDs must match records retrieved for that request.
- Persistent telemetry stores message hashes and operational metadata, not raw messages. LLM mode is opt-in and redacts common personal identifiers before sending a compact context.
- `.env`, SQLite databases, logs and local environments are excluded from Git. Never commit an API key.

This is a local student prototype, not a production security service or a definitive determination that a message or URL is safe. The datasets are small and partly synthetic; a real deployment would require broader multilingual data, adversarial/red-team evaluation, accessibility and usability testing, live threat-intelligence governance, authenticated API access, rate limiting and formal privacy/security review.
