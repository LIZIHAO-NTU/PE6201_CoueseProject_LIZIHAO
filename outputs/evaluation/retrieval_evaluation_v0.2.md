# Retrieval evaluation v0.2

Retriever: `weighted-lexical-0.3`

Designer-authored regression benchmark with the assessed scam type supplied to the retriever.

| Metric | Result |
|---|---:|
| Cases | 32 |
| Acceptable top-1 accuracy | 100.0% |
| Expected document in top 3 | 100.0% |
| Required category in top 3 | 100.0% |
| Required action stage in top 3 | 100.0% |
| Mean reciprocal rank | 1.000 |
| Provenance completeness | 100.0% |

## Assessed-type sensitivity

| Retrieval condition | Top-1 | Top-3 |
|---|---:|---:|
| Assessed type omitted | 100.0% | 100.0% |
| Counterfactual wrong type supplied | 100.0% | 100.0% |

This benchmark is for deterministic regression testing. Because its cases and acceptance rules were authored during development, it is not independent evidence of real-world retrieval quality.

## Top-1 failures

None.
