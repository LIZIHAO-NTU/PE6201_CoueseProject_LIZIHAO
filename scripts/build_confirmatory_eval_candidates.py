from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JSONL_PATH = ROOT / "data" / "eval" / "message_confirmatory_candidates_v0.2.jsonl"
CSV_PATH = ROOT / "data" / "eval" / "message_confirmatory_review_v0.2.csv"

SOURCES = {
    "government": (
        "Singapore Police Force — government official impersonation advisory",
        "https://www.police.gov.sg/media-hub/news/2025/03/20250313_police_advisory_on_impersonation_scams_involving_ministry_of_home_affairs_officers",
    ),
    "investment": (
        "Singapore Police Force — investment scam advisory",
        "https://www.police.gov.sg/media-hub/news/2025/02/20250211_police_advisory_on_investment_scams",
    ),
    "job": (
        "Singapore Police Force — job scam advisory",
        "https://www.police.gov.sg/Media-Hub/News/2026/05/20260515_joint_advisory_on_job_scams_involving_the_impersonation",
    ),
    "e_commerce": (
        "Singapore Police Force — e-commerce scam advisory",
        "https://www.police.gov.sg/media-hub/news/2025/01/20250124_police_advisory_on_ecommerce_scams_through_sale_of_products",
    ),
}


def record(
    record_id: str,
    message: str,
    risk_label: str,
    primary_type: str,
    mechanisms: list[str],
    campaign_group: str,
    rationale: str,
    channel: str = "whatsapp",
    source_key: str | None = None,
) -> dict:
    if source_key:
        source_name, source_url = SOURCES[source_key]
        source_type = "synthetic_from_advisory"
    else:
        source_name = "ScamLens SG authored confirmatory hard case"
        source_url = None
        source_type = "authored_hard_negative"
    return {
        "id": record_id,
        "message": message,
        "channel": channel,
        "language": "en",
        "risk_label": risk_label,
        "primary_type": primary_type,
        "mechanisms": mechanisms,
        "urls": [value.rstrip(".,;:!?)\"]") for value in re.findall(r"https?://\S+", message)],
        "source_type": source_type,
        "source_name": source_name,
        "source_url": source_url,
        "is_synthetic": True,
        "campaign_group": campaign_group,
        "split": "unassigned",
        "pii_removed": True,
        "review_status": "candidate",
        "annotation_confidence": "high" if risk_label != "ambiguous" else "medium",
        "label_rationale": rationale,
        "annotator": "Codex confirmatory draft — requires student review",
        "reviewer": None,
        "notes": "New confirmatory candidate. Do not run the model until student review is complete.",
    }


RECORDS = [
    record("msg_confirm_gov_001", "MOM investigation unit: your work pass is linked to an illegal employer. Join the video call now and share your screen while you sign in to Singpass.", "scam", "government_impersonation", ["urgency_or_threat", "credential_request", "brand_impersonation"], "confirm_gov_mom_screen_share_01", "An unsolicited government investigation pretext asks the recipient to expose a Singpass session through screen sharing.", source_key="government"),
    record("msg_confirm_gov_002", "ICA refund team: S$214 in overpaid immigration fees is ready. Enter your bank card details at https://ica-refund.example.com/claim by 6 pm.", "scam", "government_impersonation", ["urgency_or_threat", "credential_request", "external_link", "brand_impersonation", "suspicious_url"], "confirm_gov_ica_refund_01", "It impersonates a public agency and requests financial details through a non-official domain.", channel="sms", source_key="government"),
    record("msg_confirm_gov_003", "Police case file 4471 requires device verification. Install the case-review app from https://spf-case.example.net/update.apk and keep the investigation confidential.", "scam", "government_impersonation", ["secrecy_or_isolation", "external_link", "app_installation", "brand_impersonation", "suspicious_url"], "confirm_gov_police_case_app_01", "A police impersonation pretext requests installation of an APK and secrecy.", channel="sms", source_key="government"),
    record("msg_confirm_inv_001", "Your copy-trading dashboard shows S$9,870 profit. A refundable S$680 security deposit is required before the withdrawal can be released.", "scam", "investment", ["payment_request", "unrealistic_reward"], "confirm_inv_copytrade_release_01", "Displayed profits are used to justify an additional fee before withdrawal.", source_key="investment"),
    record("msg_confirm_inv_002", "Private pre-IPO allocation closes tonight. Transfer S$2,500 to the analyst's personal account and your shares will appear in the portal tomorrow.", "scam", "investment", ["urgency_or_threat", "payment_request", "unrealistic_reward"], "confirm_inv_preipo_personal_account_01", "An urgent investment offer requests payment to a personal account with an unverifiable promise of shares.", channel="telegram", source_key="investment"),
    record("msg_confirm_inv_003", "Crypto recovery specialist here. I can restore your frozen wallet today; send the 12-word recovery phrase so I can reconnect it to the exchange.", "scam", "investment", ["urgency_or_threat", "credential_request"], "confirm_inv_wallet_seed_recovery_01", "A recovery pretext asks for a wallet seed phrase, which grants control of the assets.", channel="telegram", source_key="investment"),
    record("msg_confirm_job_001", "Hotel rating role: complete three reviews to earn S$60. Your task balance is now negative, so top up S$240 to unlock the commission.", "scam", "job", ["payment_request", "unrealistic_reward"], "confirm_job_hotel_rating_topup_01", "A task job creates a negative balance and demands a top-up to release earnings.", channel="telegram", source_key="job"),
    record("msg_confirm_job_002", "Accounts trainee selected. Let customers pay into your personal bank account, then forward the funds daily and keep 6% as commission.", "scam", "job", ["payment_request", "unrealistic_reward"], "confirm_job_money_mule_01", "A job offer recruits the recipient to receive and forward third-party funds through a personal account.", source_key="job"),
    record("msg_confirm_job_003", "Delivery driver vacancy confirmed without interview. PayNow S$95 to the coordinator for the uniform and access card before tomorrow's shift.", "scam", "job", ["urgency_or_threat", "payment_request"], "confirm_job_uniform_fee_01", "An unsolicited job confirmation demands an upfront fee through a personal payment channel.", source_key="job"),
    record("msg_confirm_ecom_001", "Your buyer has paid for the camera. To release the money, enter your card number and OTP at https://marketplace-payout.example.org/receive.", "scam", "e_commerce", ["credential_request", "external_link", "suspicious_url"], "confirm_ecom_fake_payout_01", "A fake marketplace payout flow requests card credentials and an OTP on an unrelated domain.", source_key="e_commerce"),
    record("msg_confirm_ecom_002", "The gaming console is S$320. Marketplace checkout is unavailable, so send a S$100 PayNow deposit to reserve it before another buyer arrives.", "scam", "e_commerce", ["urgency_or_threat", "payment_request", "off_platform_payment"], "confirm_ecom_console_deposit_01", "The seller moves payment outside protected checkout and requests an urgent reservation deposit.", source_key="e_commerce"),
    record("msg_confirm_ecom_003", "Redelivery required for parcel SG482. Pay the S$2.35 handling charge at https://sg-redelivery.example.com before 10 pm.", "scam", "e_commerce", ["urgency_or_threat", "payment_request", "external_link", "suspicious_url"], "confirm_ecom_redelivery_fee_01", "A low-value parcel fee and deadline direct the recipient to a non-official payment domain.", channel="sms", source_key="e_commerce"),
    record("msg_confirm_legit_001", "Singpass notice: a login was approved at 11:42 am. If this was not you, open the Singpass app yourself and review recent activity.", "legitimate", "not_applicable", [], "confirm_legit_singpass_open_app_01", "It directs the user to an already installed official app and requests no credentials, payment or supplied link.", channel="sms"),
    record("msg_confirm_legit_002", "Your CDP e-statement is ready. Use your existing SGX bookmark to sign in; this email does not contain a login or payment link.", "legitimate", "not_applicable", [], "confirm_legit_cdp_statement_01", "It provides a normal account notification and tells the recipient to use an existing trusted route.", channel="email"),
    record("msg_confirm_legit_003", "Your interview for the clinic administrator position is at 3 pm on Thursday. No applicant fee is required; call the public switchboard if you need to reschedule.", "legitimate", "not_applicable", [], "confirm_legit_interview_no_fee_01", "A normal interview notice explicitly rejects fees and offers an independently verifiable contact route.", channel="email"),
    record("msg_confirm_legit_004", "Your marketplace order was paid through the in-app checkout. No further transfer is needed, and the seller will not ask for an OTP.", "legitimate", "not_applicable", [], "confirm_legit_platform_checkout_01", "It confirms protected in-platform payment and warns against additional transfers or OTP disclosure.", channel="sms"),
    record("msg_confirm_legit_005", "PayNow received: S$48.00 from M LIM. This is a receipt only. No reply or action is required.", "legitimate", "not_applicable", [], "confirm_legit_paynow_receipt_01", "It is a completed payment receipt with no request for action or information.", channel="sms"),
    record("msg_confirm_amb_001", "Can you make the payment for the booking? I will send the account details after my appointment.", "ambiguous", "uncertain", [], "confirm_amb_booking_payment_01", "The request lacks provenance, amount, recipient and context, so intent cannot be established.", source_key=None),
    record("msg_confirm_amb_002", "There is an issue with your package. Contact support when you are free so we can explain the next step.", "ambiguous", "uncertain", [], "confirm_amb_package_support_01", "It provides too little detail to distinguish a legitimate service message from a scam opening.", channel="sms"),
    record("msg_confirm_amb_003", "We reviewed your application and need one more verification step. HR will call you later today.", "ambiguous", "uncertain", [], "confirm_amb_application_verification_01", "No sensitive information, money or link is requested yet, but the sender and application are not identifiable.", channel="sms"),
]


def main() -> None:
    ids = [item["id"] for item in RECORDS]
    campaigns = [item["campaign_group"] for item in RECORDS]
    if len(RECORDS) != 20 or len(set(ids)) != 20 or len(set(campaigns)) != 20:
        raise ValueError("Confirmatory candidate IDs and campaign groups must be unique across 20 records")

    JSONL_PATH.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in RECORDS),
        encoding="utf-8",
    )
    fields = [
        "id", "message", "proposed_risk_label", "proposed_primary_type", "proposed_mechanisms",
        "source_name", "source_url", "campaign_group", "student_decision", "corrected_risk_label",
        "corrected_primary_type", "corrected_mechanisms", "review_notes",
    ]
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for item in RECORDS:
            writer.writerow({
                "id": item["id"],
                "message": item["message"],
                "proposed_risk_label": item["risk_label"],
                "proposed_primary_type": item["primary_type"],
                "proposed_mechanisms": "|".join(item["mechanisms"]),
                "source_name": item["source_name"],
                "source_url": item["source_url"] or "",
                "campaign_group": item["campaign_group"],
                "student_decision": "",
                "corrected_risk_label": "",
                "corrected_primary_type": "",
                "corrected_mechanisms": "",
                "review_notes": "",
            })
    print(json.dumps({"records": len(RECORDS), "jsonl": str(JSONL_PATH), "csv": str(CSV_PATH)}, indent=2))


if __name__ == "__main__":
    main()
