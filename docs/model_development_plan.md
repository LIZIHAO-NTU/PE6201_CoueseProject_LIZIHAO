# ScamLens SG model development plan

## Current fixed assets

- Gold test set: 30 student-reviewed records, locked to `split=test`.
- Current comparator: explainable weighted-rule model `mvp-rules-0.1`.
- Training review batch: 60 candidates, separate from the gold test messages and campaign groups.

The gold test set must not be used to select features, tune thresholds or rewrite rules. It is only used for final comparisons after choices are made on training and validation data.

## After the 60 candidates are reviewed

1. Apply accepted edits and exclude rejected records.
2. Split the reviewed pool by class and campaign group into approximately 80% training and 20% validation data.
3. Train an interpretable text classifier using word and character TF-IDF features with logistic regression.
4. Retain the static URL analyser as a separate signal and calibrate text/URL fusion weights only on validation data.
5. Choose two operating thresholds on validation data:
   - high risk: sufficient evidence to give strong protective intervention;
   - medium risk: abstain and ask the user to verify independently.
6. Freeze the model configuration, then evaluate once on the 30-record gold test set.

## Required comparisons

| Configuration | Purpose |
|---|---|
| Rules only | Honest MVP baseline |
| Trained text classifier only | Measures the value of supervised learning |
| URL analyser only | Measures URL-signal value |
| Text + URL fusion | Tests the multi-signal design |
| Text + URL + RAG explanation | Full user-facing system; RAG supplies evidence, not the risk label |

## Metrics

- Scam recall when medium and high both count as flagged.
- High-risk scam recall.
- Precision among flagged messages.
- False-positive rate on legitimate messages.
- Abstention rate and ambiguous-case abstention recall.
- Primary scam-type accuracy.
- Per-category and URL/non-URL breakdowns.

Because the current dataset is small and synthetic, results must be presented as prototype evidence rather than deployment performance. The report should include confidence intervals or repeated cross-validation on the reviewed training pool and clearly state that a larger naturalistic dataset is future work.
