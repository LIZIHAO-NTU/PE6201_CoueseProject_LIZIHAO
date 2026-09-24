# Scope alignment review

## Course deliverable boundary

ScamLens SG is the individual End-of-Course Project, not A1 or A2. Its required final deliverables are a clear problem statement, business and technical trade-off analysis, code in a GitHub repository, a recorded demonstration and a self-appraisal cover document.

The A2-only requirements - an agent using an external tool, a cost-to-serve model and a responsible-deployment checklist with at least ten tests - are useful inspirations but are not mandatory for this individual project.

## Problem statement versus implemented MVP

| Area | Problem statement dated 12 Aug 2026 | Implemented MVP | Alignment action |
|---|---|---|---|
| Text analysis | Foundation model for structured analysis | Reviewed TF-IDF Logistic Regression plus optional structured LLM second opinion and conservative fusion | Make local analysis the default and present the LLM as an evaluated comparator |
| URL analysis | Narrow ML URL-risk model | Static lexical/domain analyser; validation selected zero numerical fusion weight | Describe as static analysis unless a labelled URL model is added |
| Retrieval | API embeddings and RAG | Nine-source, IDF-weighted lexical evidence retrieval with provenance | Revise "embedding API" claim or add an embedding ablation |
| Language | Multilingual rationale and English/Chinese evaluation | English-only MVP | Remove multilingual evaluation promise; retain it as future work |
| Evaluation size | Independent human-reviewed 120-150 cases | 30 human-reviewed gold cases, 20 AI-assisted sanity cases, 18 retrieval cases and a persistent controlled-benchmark harness | Replace the numeric promise with completed evidence, then add one untouched confirmatory set if time permits |
| Data handling | No retention and identifier removal | Raw messages are processed in memory; only hashes and operational metadata are persisted locally | Aligned for the local prototype |
| Supported scams | Government impersonation, investment, job and e-commerce | Same four categories plus cross-cutting mechanisms | Aligned |
| Intervention | Actions adapt to user harm state | Clicked/shared/transferred flags change recommended actions | Aligned |

## Recommended final scope

Keep the current deterministic hybrid architecture and revise the milestone wording to match it:

- supervised narrow ML for message risk and type;
- auditable static URL inspection as a separate signal;
- source-verified lexical evidence retrieval instead of embedding-based generative RAG;
- optional OpenRouter LLM comparison with structured output and conservative fusion;
- persistent SQLite observability, automatic cross-model metrics and frozen CSV/JSON exports;
- behaviour guardrails, uncertainty-aware abstention and stage-based intervention;
- English-only, Singapore-specific student prototype;
- transparent separation of independent gold results, post-review diagnostics and AI-assisted regression evidence.

This scope is technically coherent, reproducible and already has measurable ablations. The foundation-model API is an explicit comparator rather than the default authority. Embedding retrieval remains an optional ablation because it adds cost, latency and a new evaluation burden for a nine-document corpus.

## Final problem-statement direction

Align the unsubmitted problem statement to the implemented hybrid MVP. Describe English-only scope, supervised local ML, static URL inspection, auditable lexical retrieval, optional LLM comparison, conservative fusion, persistent evaluation and stage-based intervention. Keep multilingual support, embedding retrieval and a learned URL classifier as future work or explicit ablations rather than unfulfilled MVP promises.
