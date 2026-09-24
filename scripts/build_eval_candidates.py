from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSONL = ROOT / "data" / "eval" / "message_eval_candidates_v0.1.jsonl"
OUTPUT_CSV = ROOT / "data" / "eval" / "message_eval_review_v0.1.csv"

SOURCES = {
    "gov_cpf": {
        "name": "SPF/CPFB Joint Advisory on Government Official Impersonation Scam",
        "url": "https://www.police.gov.sg/media-hub/news/2024/20240201_joint_advisory_on_government_official_impersonation_scam",
    },
    "gov_singpass": {
        "name": "SPF/GovTech Advisory on Phishing Scams Involving Singpass",
        "url": "https://www.police.gov.sg/media-hub/news/2022/20221002_advisory_on_phishing_scams_involving_singpass",
    },
    "investment": {
        "name": "SPF Police Advisory on Investment Scams",
        "url": "https://www.police.gov.sg/media-hub/news/2025/02/20250211_police_advisory_on_investment_scams",
    },
    "investment_group": {
        "name": "SPF Advisory on Investment Scams Involving Chat Groups",
        "url": "https://www.police.gov.sg/Media-Hub/News/2026/06/20260604_police_advisory_on_investment_scams_involving_chat_groups",
    },
    "job_recruiter": {
        "name": "SPF/GovTech Joint Advisory on Job Scams and Singpass Misuse",
        "url": "https://www.police.gov.sg/Media-Hub/News/2026/05/20260515_joint_advisory_on_job_scams_involving_the_impersonation",
    },
    "job_singpass": {
        "name": "SPF Police Advisory on Job Scams Involving Singpass Credentials",
        "url": "https://www.police.gov.sg/media-hub/news/2024/20240309_police_advisory_on_job_scams",
    },
    "ecommerce": {
        "name": "SPF Police Advisory on E-Commerce Scams Through Shopee",
        "url": "https://www.police.gov.sg/media-hub/news/2025/01/20250124_police_advisory_on_ecommerce_scams_through_sale_of_products",
    },
}


def scam_record(
    record_id: str,
    message: str,
    channel: str,
    primary_type: str,
    mechanisms: list[str],
    urls: list[str],
    source_key: str,
    campaign_group: str,
    rationale: str,
) -> dict:
    source = SOURCES[source_key]
    return {
        "id": record_id,
        "message": message,
        "channel": channel,
        "language": "en",
        "risk_label": "scam",
        "primary_type": primary_type,
        "mechanisms": mechanisms,
        "urls": urls,
        "source_type": "synthetic_from_advisory",
        "source_name": source["name"],
        "source_url": source["url"],
        "is_synthetic": True,
        "campaign_group": campaign_group,
        "split": "unassigned",
        "pii_removed": True,
        "review_status": "candidate",
        "annotation_confidence": "high",
        "label_rationale": rationale,
        "annotator": "Codex draft - requires student review",
        "reviewer": None,
        "notes": "Safe synthetic evaluation candidate derived from the cited official modus operandi; URL uses a reserved example domain.",
    }


def non_scam_record(
    record_id: str,
    message: str,
    channel: str,
    risk_label: str,
    mechanisms: list[str],
    urls: list[str],
    campaign_group: str,
    rationale: str,
    source_name: str,
    confidence: str = "high",
) -> dict:
    return {
        "id": record_id,
        "message": message,
        "channel": channel,
        "language": "en",
        "risk_label": risk_label,
        "primary_type": "not_applicable" if risk_label == "legitimate" else "uncertain",
        "mechanisms": mechanisms,
        "urls": urls,
        "source_type": "authored_hard_negative",
        "source_name": source_name,
        "source_url": None,
        "is_synthetic": True,
        "campaign_group": campaign_group,
        "split": "unassigned",
        "pii_removed": True,
        "review_status": "candidate",
        "annotation_confidence": confidence,
        "label_rationale": rationale,
        "annotator": "Codex draft - requires student review",
        "reviewer": None,
        "notes": "Authored offline evaluation candidate. Confirm naturalness and label before promotion to gold.",
    }


def build_records() -> list[dict]:
    records = [
        # Government official impersonation (5)
        scam_record(
            "msg_eval_gov_001",
            "SINGPASS ALERT: Your account will be suspended in 2 hours. Confirm your identity at https://singpass-check.example.com/login.",
            "sms", "government_impersonation",
            ["urgency_or_threat", "credential_request", "external_link", "brand_impersonation", "suspicious_url"],
            ["https://singpass-check.example.com/login"], "gov_singpass", "eval_gov_singpass_suspend_01",
            "It impersonates Singpass, threatens immediate suspension and directs the recipient to a non-gov.sg credential page.",
        ),
        scam_record(
            "msg_eval_gov_002",
            "This is Officer Lim from the Singapore Police. Your bank account is linked to a money-laundering case. Keep this investigation confidential and transfer S$2,000 to the safety account today.",
            "whatsapp", "government_impersonation",
            ["urgency_or_threat", "payment_request", "secrecy_or_isolation", "brand_impersonation"],
            [], "gov_cpf", "eval_gov_police_safety_account_01",
            "The sender claims to be Police, alleges an investigation, demands secrecy and requests a transfer to a supposed safety account.",
        ),
        scam_record(
            "msg_eval_gov_003",
            "CPF withdrawal review required. Submit your banking user ID, password and OTP at https://cpf-secure.example.net/verify to prevent your funds from being locked.",
            "email", "government_impersonation",
            ["urgency_or_threat", "credential_request", "external_link", "brand_impersonation", "suspicious_url"],
            ["https://cpf-secure.example.net/verify"], "gov_cpf", "eval_gov_cpf_lock_01",
            "It impersonates CPF, requests banking credentials and OTP, and uses a brand-bearing domain outside cpf.gov.sg.",
        ),
        scam_record(
            "msg_eval_gov_004",
            "IRAS tax refund of S$386 is waiting. Verify your card now at https://iras-refund.example.org/payment before the claim expires tonight.",
            "sms", "government_impersonation",
            ["urgency_or_threat", "credential_request", "external_link", "brand_impersonation", "suspicious_url"],
            ["https://iras-refund.example.org/payment"], "gov_singpass", "eval_gov_iras_refund_01",
            "The message uses a tax-refund pretext, an expiring deadline and a non-official domain to solicit card details.",
        ),
        scam_record(
            "msg_eval_gov_005",
            "Ministry verification team: install the SecureGov mobile app from https://gov-sg-support.example.com/app.apk so we can complete the investigation on your identity.",
            "whatsapp", "government_impersonation",
            ["app_installation", "external_link", "brand_impersonation", "suspicious_url"],
            ["https://gov-sg-support.example.com/app.apk"], "gov_cpf", "eval_gov_fake_app_01",
            "It impersonates a ministry and requests installation of an APK from a domain that is not under gov.sg.",
        ),

        # Investment scam (5)
        scam_record(
            "msg_eval_inv_001",
            "Join our private crypto group. Our AI strategy guarantees 20% returns every week. Start with S$500 today and I will guide your first trade.",
            "telegram", "investment",
            ["payment_request", "unrealistic_reward"], [], "investment", "eval_inv_guaranteed_crypto_01",
            "It promises guaranteed extraordinary weekly returns and asks for an immediate initial investment.",
        ),
        scam_record(
            "msg_eval_inv_002",
            "Your trading account shows S$18,400 profit. To withdraw it, pay the final S$1,200 tax and verification fee to the account provided.",
            "whatsapp", "investment",
            ["payment_request", "urgency_or_threat"], [], "investment", "eval_inv_withdrawal_fee_01",
            "The message requests an additional fee before releasing supposed investment profits, matching a known withdrawal-fee pattern.",
        ),
        scam_record(
            "msg_eval_inv_003",
            "Free investment lesson tonight. Our mentor has helped 300 members profit. Register at https://sg-wealth-club.example.com and join the WhatsApp VIP group.",
            "sms", "investment",
            ["external_link", "social_proof_manipulation", "suspicious_url"],
            ["https://sg-wealth-club.example.com"], "investment_group", "eval_inv_learning_group_01",
            "It uses free lessons, a mentor and unverifiable member profits to funnel the recipient into an external investment group.",
        ),
        scam_record(
            "msg_eval_inv_004",
            "I saw your profile and think you would like this low-risk forex opportunity. Deposit S$300 through the wallet link and I will add a 100% welcome bonus.",
            "whatsapp", "investment",
            ["payment_request", "unrealistic_reward"], [], "investment", "eval_inv_unsolicited_forex_01",
            "An unsolicited investment approach promises a 100% bonus and asks for a wallet deposit.",
        ),
        scam_record(
            "msg_eval_inv_005",
            "The platform is upgrading tonight. Move your crypto to https://secure-exchange-upgrade.example.net/wallet within 30 minutes or your balance may be lost.",
            "email", "investment",
            ["urgency_or_threat", "payment_request", "external_link", "suspicious_url"],
            ["https://secure-exchange-upgrade.example.net/wallet"], "investment", "eval_inv_wallet_migration_01",
            "It creates a short deadline and loss threat to induce transfer of crypto to an unverified external wallet site.",
        ),

        # Job scam (5)
        scam_record(
            "msg_eval_job_001",
            "Part-time product reviewer needed. Earn S$450 daily from home. Pay a refundable S$80 deposit to activate your task account.",
            "whatsapp", "job",
            ["payment_request", "unrealistic_reward"], [], "job_recruiter", "eval_job_task_deposit_01",
            "The message offers implausibly high pay for simple remote tasks and requires an upfront activation deposit.",
        ),
        scam_record(
            "msg_eval_job_002",
            "Your concert crew application is shortlisted. Send your NRIC image and Singpass password so HR can complete the mandatory background check.",
            "telegram", "job",
            ["credential_request", "brand_impersonation"], [], "job_recruiter", "eval_job_concert_singpass_01",
            "A recruitment pretext is used to request NRIC and Singpass credentials, which legitimate recruiters should not require.",
        ),
        scam_record(
            "msg_eval_job_003",
            "Recruitment screening: change the mobile number in your Singpass profile to [PHONE] and send us the login OTP when it arrives.",
            "whatsapp", "job",
            ["credential_request", "brand_impersonation"], [], "job_singpass", "eval_job_change_singpass_01",
            "The purported screening process asks the applicant to change Singpass details and provide an OTP.",
        ),
        scam_record(
            "msg_eval_job_004",
            "Remote data-entry role, no interview required. Download the company work app at https://recruitment-tools.example.com/jobs.apk and log in with Singpass.",
            "sms", "job",
            ["app_installation", "credential_request", "external_link", "suspicious_url"],
            ["https://recruitment-tools.example.com/jobs.apk"], "job_singpass", "eval_job_apk_singpass_01",
            "It combines an unusually frictionless job offer with APK installation and a Singpass login request.",
        ),
        scam_record(
            "msg_eval_job_005",
            "You have earned S$72 commission. Complete one final S$300 order using your own funds to release all earnings immediately.",
            "telegram", "job",
            ["payment_request", "urgency_or_threat"], [], "job_recruiter", "eval_job_commission_unlock_01",
            "The task-job scenario requires the worker to fund another order before withdrawing purported commission.",
        ),

        # E-commerce scam (5)
        scam_record(
            "msg_eval_ecom_001",
            "I can give you 35% off if you cancel the Shopee order and PayNow me directly. The deal is only available for the next hour.",
            "whatsapp", "e_commerce",
            ["off_platform_payment", "payment_request", "urgency_or_threat"], [], "ecommerce", "eval_ecom_offplatform_discount_01",
            "It offers a large time-limited discount in exchange for leaving the authorised platform and paying directly.",
        ),
        scam_record(
            "msg_eval_ecom_002",
            "Your parcel is held due to an unpaid S$1.80 delivery fee. Pay now at https://parcel-fee.example.com/sg to avoid return to sender.",
            "sms", "e_commerce",
            ["payment_request", "urgency_or_threat", "external_link", "suspicious_url"],
            ["https://parcel-fee.example.com/sg"], "ecommerce", "eval_ecom_parcel_fee_01",
            "A small delivery fee and return threat are used to direct the recipient to an unverified payment site.",
        ),
        scam_record(
            "msg_eval_ecom_003",
            "Buyer payment received. Enter your card number and OTP at https://carousell-release.example.net to receive the funds.",
            "email", "e_commerce",
            ["credential_request", "external_link", "brand_impersonation", "suspicious_url"],
            ["https://carousell-release.example.net"], "ecommerce", "eval_ecom_fake_buyer_payment_01",
            "It impersonates an e-commerce payment flow and asks the seller for card details and OTP on a look-alike domain.",
        ),
        scam_record(
            "msg_eval_ecom_004",
            "The laptop is yours for S$600. Transfer a S$200 reservation deposit now; I cannot use the platform payment because my seller account is being reviewed.",
            "whatsapp", "e_commerce",
            ["off_platform_payment", "payment_request", "urgency_or_threat"], [], "ecommerce", "eval_ecom_reservation_deposit_01",
            "The seller uses an account-review excuse to request an urgent reservation deposit outside the platform.",
        ),
        scam_record(
            "msg_eval_ecom_005",
            "Customs charge pending for order [ORDER]. Confirm your address and bank login at https://delivery-customs.example.org/confirm before midnight.",
            "sms", "e_commerce",
            ["credential_request", "urgency_or_threat", "external_link", "suspicious_url"],
            ["https://delivery-customs.example.org/confirm"], "ecommerce", "eval_ecom_customs_login_01",
            "The message uses a customs-fee pretext and deadline to solicit address and banking credentials at an unverified domain.",
        ),

        # Legitimate hard negatives (7)
        non_scam_record(
            "msg_eval_legit_001",
            "Your card purchase of S$18.40 was approved. If this was not you, call the number printed on the back of your card.",
            "sms", "legitimate", [], [], "eval_legit_bank_alert_01",
            "This controlled bank-alert template contains no link and directs the customer to an independently available official contact channel.",
            "ScamLens SG authored legitimate bank-alert hard negative",
        ),
        non_scam_record(
            "msg_eval_legit_002",
            "Reminder: School fees are due on 28 August. Please log in to the existing parent portal using your saved bookmark to view the invoice.",
            "email", "legitimate", ["urgency_or_threat", "payment_request"], [], "eval_legit_school_fee_01",
            "This controlled school reminder provides a normal deadline and tells the recipient to use an existing saved portal rather than a supplied link.",
            "ScamLens SG authored school-payment hard negative",
        ),
        non_scam_record(
            "msg_eval_legit_003",
            "Your parcel will arrive tomorrow between 2 pm and 5 pm. No payment or action is required.",
            "sms", "legitimate", [], [], "eval_legit_delivery_01",
            "This controlled delivery notification asks for no payment, credentials, link visit or reply.",
            "ScamLens SG authored delivery hard negative",
        ),
        non_scam_record(
            "msg_eval_legit_004",
            "Your interview for the Operations Assistant role is confirmed for Monday at 10 am. Reply YES to confirm or call the main office number listed on our public website.",
            "sms", "legitimate", [], [], "eval_legit_interview_01",
            "This controlled recruitment message requests only confirmation and directs verification to a public official contact channel.",
            "ScamLens SG authored recruitment hard negative",
        ),
        non_scam_record(
            "msg_eval_legit_005",
            "ScamShield reminder: if you are unsure about a suspicious message, visit https://www.scamshield.gov.sg/ or call 1799.",
            "sms", "legitimate", ["external_link"], ["https://www.scamshield.gov.sg/"], "eval_legit_scamshield_01",
            "The message links to the recognised official ScamShield gov.sg domain and provides the published helpline number.",
            "ScamLens SG authored official-domain hard negative",
        ),
        non_scam_record(
            "msg_eval_legit_006",
            "Security notice: a new device signed in to your account. Open the official app directly to review the activity. We will never ask for your password or OTP.",
            "email", "legitimate", ["urgency_or_threat"], [], "eval_legit_security_alert_01",
            "This controlled security alert contains urgency but no link or credential request and directs the user to the official app.",
            "ScamLens SG authored security-alert hard negative",
        ),
        non_scam_record(
            "msg_eval_legit_007",
            "The buyer has paid through the platform. Keep all messages and delivery updates inside the app; no direct transfer is needed.",
            "whatsapp", "legitimate", [], [], "eval_legit_platform_sale_01",
            "This controlled e-commerce notification explicitly keeps communication and payment within the platform.",
            "ScamLens SG authored e-commerce hard negative",
        ),

        # Ambiguous / abstention cases (3)
        non_scam_record(
            "msg_eval_amb_001",
            "Hi, are you free to talk? I need your help with something urgent.",
            "whatsapp", "ambiguous", ["urgency_or_threat"], [], "eval_amb_help_01",
            "The message expresses urgency but provides no request or provenance sufficient to determine whether it is fraudulent.",
            "ScamLens SG authored ambiguous case", "low",
        ),
        non_scam_record(
            "msg_eval_amb_002",
            "Your application requires one more verification step. Please contact the office when convenient.",
            "sms", "ambiguous", [], [], "eval_amb_application_01",
            "The sender, application and verification method are unspecified, and no risky action is requested in the available text.",
            "ScamLens SG authored ambiguous case", "low",
        ),
        non_scam_record(
            "msg_eval_amb_003",
            "The price is S$120. I can reserve it until this evening if you are still interested.",
            "whatsapp", "ambiguous", ["urgency_or_threat"], [], "eval_amb_reservation_01",
            "A price and time limit are present, but the excerpt lacks payment instructions, platform context and provenance needed for a safe judgement.",
            "ScamLens SG authored ambiguous case", "low",
        ),
    ]
    assert len(records) == 30
    return records


def main() -> None:
    records = build_records()
    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSONL.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )

    review_fields = [
        "id", "message", "proposed_risk_label", "proposed_primary_type",
        "proposed_mechanisms", "source_name", "source_url", "campaign_group",
        "student_decision", "corrected_risk_label", "corrected_primary_type",
        "corrected_mechanisms", "review_notes",
    ]
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=review_fields)
        writer.writeheader()
        for record in records:
            writer.writerow({
                "id": record["id"],
                "message": record["message"],
                "proposed_risk_label": record["risk_label"],
                "proposed_primary_type": record["primary_type"],
                "proposed_mechanisms": "|".join(record["mechanisms"]),
                "source_name": record["source_name"],
                "source_url": record["source_url"] or "",
                "campaign_group": record["campaign_group"],
                "student_decision": "",
                "corrected_risk_label": "",
                "corrected_primary_type": "",
                "corrected_mechanisms": "",
                "review_notes": "",
            })

    risk_counts = Counter(record["risk_label"] for record in records)
    type_counts = Counter(record["primary_type"] for record in records)
    print(f"Created {OUTPUT_JSONL}")
    print(f"Created {OUTPUT_CSV}")
    print(f"Risk labels: {dict(sorted(risk_counts.items()))}")
    print(f"Primary types: {dict(sorted(type_counts.items()))}")


if __name__ == "__main__":
    main()

