# Review instructions for evaluation candidates v0.1

The 30 records in `data/eval/message_eval_candidates_v0.1.jsonl` are **candidates**, not a gold test set. Scam cases are safe synthetic variants derived from cited Singapore Police Force advisories. Legitimate and ambiguous cases are deliberately authored offline examples.

Use `data/eval/message_eval_review_v0.1.csv` for review. For each row:

1. Read the message without looking at the current model's output.
2. Open and check the official source when a source URL is provided.
3. Enter one decision in `student_decision`:
   - `accept`
   - `edit`
   - `reject`
4. If editing, complete the corrected label/mechanism columns.
5. Note unnatural wording, overly obvious clues or duplicated scenarios in `review_notes`.

Do not run the current classifier against individual records while deciding their gold labels. The aim is to establish an evaluation target independently of the model.

## Target distribution in this batch

| Group | Count |
|---|---:|
| Government official impersonation | 5 |
| Investment scams | 5 |
| Job scams | 5 |
| E-commerce scams | 5 |
| Legitimate hard negatives | 7 |
| Ambiguous / abstention cases | 3 |
| **Total** | **30** |

After review, accepted and corrected cases can be promoted to `review_status=gold`, `split=test`. Rejected cases should remain outside the gold set and be replaced with newly authored candidates from different campaign groups.

