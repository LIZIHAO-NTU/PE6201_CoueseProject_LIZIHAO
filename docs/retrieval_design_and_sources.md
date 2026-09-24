# Evidence retrieval design and source register

## Role in the system

ScamLens SG uses retrieval in both operating modes. The local mode retrieves and displays official evidence after the classifier and safety policy make their decision. When the optional LLM is enabled, the top two retrieved chunks are added to the redacted model context, making that branch a complete retrieval-augmented generation pipeline. Retrieved text never directly changes the local numerical risk score; any LLM contribution still passes through conservative fusion.

This separation makes three claims testable:

1. classification performance can be measured without the retriever;
2. retrieval relevance can be measured without retraining the classifier;
3. every user-facing evidence item can be traced to an official HTTPS source.

## Retrieval method

`weighted-lexical-0.3` ranks evidence chunks using:

- IDF-weighted coverage of query tokens;
- matches against curated scam cues and multi-word phrases;
- a boost when the document covers the assessed scam type;
- a boost for response chunks that match a reported clicked-link, credential-sharing or money-transfer stage;
- a small fallback boost for general ScamShield verification guidance.

The response exposes `rank`, `retrieval_score`, `matched_keywords`, `matched_action_stages`, `match_reasons`, `chunk_type`, `action_stages`, `source_domain`, `source_updated_date`, `last_verified_date` and `retriever_version`. Scores are ranking values, not calibrated probabilities.

## Curated official sources

The corpus contains 24 evidence chunks from the 12 source pages below. All links were manually verified on 15 August 2026.

| Corpus entry | Coverage | Official source |
|---|---|---|
| ScamShield portal | General checking and 1799 helpline | https://www.scamshield.gov.sg/ |
| I've been scammed | Immediate bank, police and account-security response | https://www.scamshield.gov.sg/i-have-been-scammed/ |
| Government Officials Impersonation Scams | Government impersonation | https://www.scamshield.gov.sg/i-want-protection-from-scams/learn-to-recognise-scams/government-officials-impersonation-scams/ |
| SPF MOM malware-enabled scam advisory | Fake government email, website and compressed-file malware | https://www.police.gov.sg/Media-Hub/News/2026/05/20260519_advisory_on_malware_enabled_scams_involving_emails_and_websites_that_impersonate |
| Investment Scams | Investment and withdrawal-fee patterns | https://www.scamshield.gov.sg/i-want-protection-from-scams/learn-to-recognise-scams/investment-scams/ |
| MAS Financial Institutions Directory | Independent licence verification | https://eservices.mas.gov.sg/fid/institution |
| Job Scams | Task, commission, deposit and recruitment patterns | https://www.scamshield.gov.sg/i-want-protection-from-scams/learn-to-recognise-scams/job-scams/ |
| Singpass contact and scam support | Credential compromise and official support | https://portal.singpass.gov.sg/home/ui/contact-us |
| E-Commerce Scams | Off-platform payment, delivery and customs fees | https://www.scamshield.gov.sg/i-want-protection-from-scams/learn-to-recognise-scams/e-commerce-scams/ |
| Phishing Scams | Suspicious links, credentials, card details and OTPs | https://www.scamshield.gov.sg/i-want-protection-from-scams/learn-to-recognise-scams/phishing-scams/ |
| SPF/CSA Microsoft technical-support advisory | Pop-up and false support-number recognition | https://www.police.gov.sg/Media-Hub/News/2026/06/20260609_joint_advisory_on_technical_support_scams_involving_the_impersonation_of_microsoft |
| SPF/CSA technical-support advisory | Remote-access compromise and response steps | https://www.police.gov.sg/media-hub/news/2025/01/20250121_advisory_on_technical_support_scams |

The machine-readable corpus is `app/data/advisories.json`. Source text is paraphrased into short evidence statements and actions; the original pages remain the authority.

## Evaluation

`data/eval/retrieval_eval_v0.2.jsonl` contains 32 English queries across government impersonation, investment, job, e-commerce, uncertain/cross-cutting and post-harm response cases. Each case specifies acceptable top-1 chunks, a required category and, where applicable, a required action stage. `scripts/evaluate_retriever.py` reports:

- acceptable top-1 accuracy;
- expected-document top-3 coverage;
- required-category top-3 coverage;
- required-action-stage top-3 coverage;
- mean reciprocal rank;
- provenance completeness.

The current benchmark scores 100% on all percentage metrics and 1.000 MRR. These cases and acceptance rules were authored during development and should be treated as regression tests. A stronger final evaluation would have a different reviewer write or approve the queries before the results are inspected.

As a sensitivity check, omitting the assessed scam type or supplying a deliberately wrong type retains 100% top-1 and top-3 performance on this authored benchmark. This indicates that the query cues dominate the small type prior in the current cases, but it should not be interpreted as independent evidence of robustness.

## Known limitations

- The corpus is still small, curated and English-only.
- Ranking is lexical; it does not use embeddings or semantic reranking.
- The assessed scam type is supplied to the retriever, so a classification error can bias evidence selection.
- Official pages can change after the recorded verification date.
- The current component does not generate a free-form answer, so it should be described as evidence retrieval or retrieval-augmented evidence, not as a full generative RAG pipeline.
