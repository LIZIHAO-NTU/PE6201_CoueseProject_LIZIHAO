# ScamLens SG trained-model evaluation v0.1

The configuration was selected using the 12-record validation set. The 30-record gold test set was accessed only after the configuration was frozen.

## Gold-test comparison

| Metric | Rules baseline | TF-IDF + Logistic Regression with validated fusion configuration |
|---|---:|---:|
| Exact three-way accuracy | 30.0% | 63.3% |
| Operational scam recall | 20.0% | 95.0% |
| High-risk scam recall | 10.0% | 55.0% |
| Legitimate false-positive rate | 0.0% | 14.3% |
| Abstention rate | 6.7% | 36.7% |
| Ambiguous-case abstention recall | 0.0% | 66.7% |
| Deployed scam-type accuracy | 70.0% | 50.0% |

The underlying type classifier scored 55.0% when evaluated independently. The deployed pipeline scored 50.0% because it suppresses category predictions to `uncertain` when the overall risk result is low.

## Frozen configuration

- Logistic regression C: 0.5
- Text weight when a URL is present: 1.0
- Medium threshold: 0.4
- High threshold: 0.5
- Ambiguous probability threshold: 0.25
- Low-confidence abstention threshold: 0.4

Validation selected a text weight of 1.0, so URL inspection did not change the numerical risk score in this frozen configuration. URL warnings remain visible to users as a separate signal.

## Limitations

The training, validation and test sets are small and mostly synthetic. The results demonstrate the project pipeline and a controlled comparison, not real-world deployment performance. More independently sourced and naturalistic messages are required before any safety claim.
