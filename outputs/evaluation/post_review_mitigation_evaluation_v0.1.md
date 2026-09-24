# ScamLens SG post-review mitigation evaluation v0.1

The reviewed error set contained one critical low-risk false reassurance, ten issues needing mitigation and six acceptable trade-offs. The frozen statistical model and its thresholds remain unchanged.

## Mitigations

- Added an auditable medium-risk floor when a message both requests payment and explicitly moves payment outside a marketplace's protected checkout.
- Added a context-based scam-type resolver with job context taking precedence over identity-tool terms such as Singpass, followed by explicit government, investment and e-commerce context. The trained type classifier remains the fallback.
- Added positive and safe-negative regression tests for the new guardrail.

## Validation result

On the unchanged 12-record validation split, operational scam recall is 100.0%, legitimate false-positive rate is 33.3%, and deployed scam-type accuracy is 100.0%.

## Gold-set post-hoc diagnostic

> These are not fresh independent test results. The gold error review informed mitigation priorities, so this table is a regression diagnostic only.

| Metric | Frozen pre-review result | Post-review diagnostic |
|---|---:|---:|
| Exact three-way accuracy | 63.3% | 63.3% |
| Operational scam recall | 95.0% | 100.0% |
| High-risk scam recall | 55.0% | 55.0% |
| Legitimate false-positive rate | 14.3% | 14.3% |
| Abstention rate | 36.7% | 40.0% |
| Ambiguous-case abstention recall | 66.7% | 66.7% |
| Deployed scam-type accuracy | 50.0% | 100.0% |
| Low-risk scams | 1 | 0 |

## Interpretation

The critical failure mode is no longer low risk: the affected behavioural pattern is routed to independent verification. Type explanations are more consistent, but the apparent gold-set gain must be confirmed on a new untouched evaluation set before it is treated as generalisation evidence.
