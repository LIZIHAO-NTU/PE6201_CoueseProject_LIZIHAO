# ScamLens SG baseline evaluation v0.1

- Model: `mvp-rules-0.1`
- Gold test records: 30
- Exact three-way accuracy: 30.0%
- Operational scam recall (medium or high): 20.0%
- High-risk scam recall: 10.0%
- Legitimate false-positive rate (medium or high): 0.0%
- Abstention rate (medium): 6.7%
- Scam type accuracy: 70.0%

## Interpretation

Medium is treated as an abstention requiring independent verification. For the operational scam-recall metric, both medium and high count as flagged; exact three-way accuracy requires the model to match scam, legitimate or ambiguous exactly.

## Per scam type

| Type | N | Flagged recall | High-risk recall | Type accuracy |
|---|---:|---:|---:|---:|
| e_commerce | 5 | 0.0% | 0.0% | 60.0% |
| government_impersonation | 5 | 40.0% | 40.0% | 100.0% |
| investment | 5 | 0.0% | 0.0% | 80.0% |
| job | 5 | 40.0% | 0.0% | 40.0% |

## Errors requiring analysis

| ID | Gold risk | Predicted risk | Gold type | Predicted type | Score |
|---|---|---|---|---|---:|
| msg_eval_gov_002 | scam | legitimate | government_impersonation | government_impersonation | 0.330 |
| msg_eval_gov_004 | scam | legitimate | government_impersonation | government_impersonation | 0.336 |
| msg_eval_gov_005 | scam | legitimate | government_impersonation | government_impersonation | 0.172 |
| msg_eval_inv_001 | scam | legitimate | investment | investment | 0.110 |
| msg_eval_inv_002 | scam | legitimate | investment | investment | 0.170 |
| msg_eval_inv_003 | scam | legitimate | investment | investment | 0.207 |
| msg_eval_inv_004 | scam | legitimate | investment | uncertain | 0.270 |
| msg_eval_inv_005 | scam | legitimate | investment | investment | 0.223 |
| msg_eval_job_001 | scam | legitimate | job | job | 0.330 |
| msg_eval_job_002 | scam | ambiguous | job | government_impersonation | 0.360 |
| msg_eval_job_003 | scam | ambiguous | job | government_impersonation | 0.360 |
| msg_eval_job_004 | scam | legitimate | job | government_impersonation | 0.295 |
| msg_eval_job_005 | scam | legitimate | job | job | 0.270 |
| msg_eval_ecom_001 | scam | legitimate | e_commerce | e_commerce | 0.330 |
| msg_eval_ecom_002 | scam | legitimate | e_commerce | e_commerce | 0.173 |
| msg_eval_ecom_003 | scam | legitimate | e_commerce | e_commerce | 0.284 |
| msg_eval_ecom_004 | scam | legitimate | e_commerce | uncertain | 0.270 |
| msg_eval_ecom_005 | scam | legitimate | e_commerce | uncertain | 0.104 |
| msg_eval_amb_001 | ambiguous | legitimate | uncertain | uncertain | 0.210 |
| msg_eval_amb_002 | ambiguous | legitimate | uncertain | uncertain | 0.050 |
| msg_eval_amb_003 | ambiguous | legitimate | uncertain | uncertain | 0.050 |

## Limitation

This is a deliberately small, mostly synthetic test set. Results establish an auditable baseline but are not a deployment claim. A larger set of naturalistic, independently sourced messages is still required.
