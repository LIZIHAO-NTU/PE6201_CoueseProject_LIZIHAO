# ScamLens SG data annotation guide

Version: 1.0  
Scope: English-language message assessment MVP  
Unit of annotation: one received SMS, WhatsApp message or email excerpt

## 1. Why this guide exists

The dataset must support three different tasks without mixing their labels:

1. **Risk classification:** Is the message a scam, legitimate, or too ambiguous to judge?
2. **Scam categorisation:** If it is a scam, what is its primary social-engineering scenario?
3. **Mechanism detection:** Which observable attack techniques appear in the message?

The label must be based on the message plus reliable provenance, not on whether its wording merely feels suspicious. Evaluation labels require human review; an LLM may suggest a label but must not be the final authority.

## 2. Dataset boundaries

### Included

- SMS, WhatsApp, Telegram or email-style text received by a Singapore resident.
- English messages and common Singapore entities or services such as Singpass, CPF, PayNow, local banks and e-commerce platforms.
- Messages with or without URLs.
- Legitimate messages that contain payments, links, deadlines or security alerts.
- Ambiguous messages where the available text is insufficient for a safe conclusion.

### Excluded from the current MVP

- Phone-call audio or transcripts that require speaker or acoustic analysis.
- Website screenshots, webpage HTML and image-only advertisements.
- Malay, Tamil, Chinese or mixed-language samples intended as evaluated support.
- Messages containing real unredacted personal, banking or authentication data.
- URL samples whose only label comes from actively opening a potentially malicious site on the development machine.

## 3. Required labels

### 3.1 `risk_label`

Choose exactly one:

| Label | Use when | Do not use when |
|---|---|---|
| `scam` | Reliable provenance or the full scenario establishes fraudulent intent. | The message is only unusual or marketing-like. |
| `legitimate` | The message is verified genuine, comes from a controlled legitimate template, or is a deliberately authored hard negative. | A plausible-looking domain or sender name is the only evidence. |
| `ambiguous` | The text alone cannot support either conclusion safely. | There is clear provenance establishing scam or legitimate status. |

`ambiguous` is a real target class for abstention evaluation, not an annotation failure.

### 3.2 `primary_type`

Choose exactly one:

| Label | Definition |
|---|---|
| `government_impersonation` | Impersonates a government agency, public officer or government-linked service. |
| `investment` | Promotes a fraudulent investment, trading scheme or fake returns/withdrawal process. |
| `job` | Offers fake employment, paid tasks, recruitment or commission work. |
| `e_commerce` | Fraudulent buying, selling, delivery or off-platform payment scenario. |
| `other_scam` | Confirmed scam outside the four evaluated categories. |
| `uncertain` | Risk is ambiguous or scam type cannot be determined. |
| `not_applicable` | Verified legitimate message. |

Consistency rules:

- `risk_label=scam` must not use `not_applicable`.
- `risk_label=legitimate` must use `not_applicable`.
- `risk_label=ambiguous` normally uses `uncertain`.
- Phishing is not a primary type. Record it as an attack mechanism because phishing can occur in all four categories.

### 3.3 `mechanisms`

Choose zero or more observable mechanisms:

- `urgency_or_threat`
- `credential_request`
- `payment_request`
- `unrealistic_reward`
- `secrecy_or_isolation`
- `external_link`
- `brand_impersonation`
- `suspicious_url`
- `off_platform_payment`
- `app_installation`
- `remote_access_request`
- `social_proof_manipulation`

Mechanisms describe message content, not the annotator's conclusion. A legitimate bank alert may contain `external_link` or `urgency_or_threat`; that alone does not make it a scam.

## 4. Source and provenance labels

### `source_type`

- `official_public_example`: message or screenshot published by ScamShield, SPF, CSA or another official source.
- `licensed_public_dataset`: record from a dataset whose reuse terms have been reviewed.
- `synthetic_from_advisory`: generated from an official modus operandi, then human-reviewed.
- `authored_hard_negative`: deliberately written legitimate-looking message used to test false positives.
- `consented_anonymised`: voluntarily contributed message with consent and completed anonymisation.

Every record must include a human-readable `source_name`. Records derived from an external source must include `source_url`. Synthetic records must identify the advisory or scenario on which they were based.

## 5. Split and leakage control

Use `campaign_group` to keep related records together. It identifies the underlying campaign, source advisory, generation template or legitimate notification family.

Examples:

- All variations derived from one SPF job-scam advisory share one `campaign_group`.
- All messages using the same synthetic template share one `campaign_group`.
- Multiple URLs from the same registered domain share one URL-domain group during URL-model splitting.

Rules:

1. A `campaign_group` must appear in only one of `train`, `validation` or `test`.
2. Gold evaluation records use `split=test` and `review_status=gold`.
3. Do not tune prompts, thresholds or rules after reading test-set errors. Use validation data for iteration.
4. Near-duplicate messages must not be distributed across splits.
5. Synthetic variants from the same prompt/template must not be distributed across splits.

## 6. Privacy and safe handling

Before saving a record:

- Replace real names with neutral placeholders such as `[PERSON]`.
- Replace NRIC/FIN, phone numbers, email addresses, account/card numbers and transaction references.
- Replace live suspicious domains with safe reserved domains when the exact domain is not essential. Use `example.com`, `example.org` or `example.net` for authored examples.
- Never retain OTPs, passwords, Singpass credentials or banking credentials.
- Set `pii_removed=true` only after a human privacy check.
- Do not actively open suspicious URLs during annotation.

## 7. Annotation workflow

### Pass 1: independent annotation

The annotator reads the message and source metadata, then assigns:

- `risk_label`
- `primary_type`
- `mechanisms`
- `label_rationale`
- `confidence`

The rationale should cite observable evidence or source provenance in one or two sentences. It must not simply repeat the label.

### Pass 2: quality review

For validation and test records, a second review checks:

- label consistency;
- source link and provenance;
- privacy removal;
- campaign grouping;
- whether a legitimate hard negative is genuinely plausible;
- whether an ambiguous case should remain ambiguous rather than being forced into a class.

Set `review_status=gold` only after this pass. Training candidates may use `candidate` or `reviewed`.

## 8. Confidence scale

- `high`: reliable provenance or clear complete scenario.
- `medium`: label is supportable but depends on contextual interpretation.
- `low`: insufficient evidence; usually pair with `risk_label=ambiguous`.

Confidence is annotation confidence, not the model's predicted probability.

## 9. Hard-negative requirements

At least 25% of the final evaluation set should be legitimate hard negatives, including:

- real-looking bank transaction alerts;
- school or tuition payment reminders;
- parcel and delivery notifications;
- legitimate job or recruitment messages;
- government service reminders;
- messages containing an official URL;
- urgent but legitimate security alerts.

The aim is to prevent a model from learning shortcuts such as “any payment request or URL equals scam.”

## 10. Evaluation-set acceptance checklist

Before freezing the gold test set:

- [ ] Every ID is unique.
- [ ] Every message has been privacy-reviewed.
- [ ] Every label follows the consistency rules.
- [ ] All scam records have defensible provenance.
- [ ] At least 25% are legitimate hard negatives.
- [ ] Ambiguous cases are represented.
- [ ] All four primary scam categories are represented.
- [ ] Campaign/template groups do not cross data splits.
- [ ] URL domains do not leak across URL-model train and test groups.
- [ ] No gold label was accepted solely from an LLM judgement.

