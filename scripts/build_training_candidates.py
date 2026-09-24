from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSONL = ROOT / "data" / "training" / "message_training_candidates_v0.1.jsonl"
OUTPUT_CSV = ROOT / "data" / "training" / "message_training_review_v0.1.csv"
URL_RE = re.compile(r"https?://[^\s,]+")

SOURCES = {
    "gov": (
        "SPF/CPFB Joint Advisory on Government Official Impersonation Scam",
        "https://www.police.gov.sg/media-hub/news/2024/20240201_joint_advisory_on_government_official_impersonation_scam",
    ),
    "singpass": (
        "SPF/GovTech Advisory on Phishing Scams Involving Singpass",
        "https://www.police.gov.sg/media-hub/news/2022/20221002_advisory_on_phishing_scams_involving_singpass",
    ),
    "investment": (
        "SPF Police Advisory on Investment Scams",
        "https://www.police.gov.sg/media-hub/news/2025/02/20250211_police_advisory_on_investment_scams",
    ),
    "investment_group": (
        "SPF Advisory on Investment Scams Involving Chat Groups",
        "https://www.police.gov.sg/Media-Hub/News/2026/06/20260604_police_advisory_on_investment_scams_involving_chat_groups",
    ),
    "job": (
        "SPF/GovTech Joint Advisory on Job Scams and Singpass Misuse",
        "https://www.police.gov.sg/Media-Hub/News/2026/05/20260515_joint_advisory_on_job_scams_involving_the_impersonation",
    ),
    "job_singpass": (
        "SPF Police Advisory on Job Scams Involving Singpass Credentials",
        "https://www.police.gov.sg/media-hub/news/2024/20240309_police_advisory_on_job_scams",
    ),
    "ecommerce": (
        "SPF Police Advisory on E-Commerce Scams Through Shopee",
        "https://www.police.gov.sg/media-hub/news/2025/01/20250124_police_advisory_on_ecommerce_scams_through_sale_of_products",
    ),
}


def urls_in(message: str) -> list[str]:
    return [match.rstrip(".,;:!?)]}'\"") for match in URL_RE.findall(message)]


def scam(
    record_id: str,
    message: str,
    channel: str,
    primary_type: str,
    mechanisms: list[str],
    source_key: str,
    scenario: str,
    rationale: str,
) -> dict:
    source_name, source_url = SOURCES[source_key]
    return {
        "id": record_id,
        "message": message,
        "channel": channel,
        "language": "en",
        "risk_label": "scam",
        "primary_type": primary_type,
        "mechanisms": mechanisms,
        "urls": urls_in(message),
        "source_type": "synthetic_from_advisory",
        "source_name": source_name,
        "source_url": source_url,
        "is_synthetic": True,
        "campaign_group": scenario,
        "split": "unassigned",
        "pii_removed": True,
        "review_status": "candidate",
        "annotation_confidence": "high",
        "label_rationale": rationale,
        "annotator": "Codex training draft - requires student review",
        "reviewer": None,
        "notes": "Safe synthetic training candidate based on the cited modus operandi. Any URL uses a reserved example domain.",
    }


def non_scam(
    record_id: str,
    message: str,
    channel: str,
    risk_label: str,
    mechanisms: list[str],
    scenario: str,
    rationale: str,
) -> dict:
    return {
        "id": record_id,
        "message": message,
        "channel": channel,
        "language": "en",
        "risk_label": risk_label,
        "primary_type": "not_applicable" if risk_label == "legitimate" else "uncertain",
        "mechanisms": mechanisms,
        "urls": urls_in(message),
        "source_type": "authored_hard_negative",
        "source_name": "ScamLens SG authored training hard negative" if risk_label == "legitimate" else "ScamLens SG authored ambiguous training case",
        "source_url": None,
        "is_synthetic": True,
        "campaign_group": scenario,
        "split": "unassigned",
        "pii_removed": True,
        "review_status": "candidate",
        "annotation_confidence": "high" if risk_label == "legitimate" else "low",
        "label_rationale": rationale,
        "annotator": "Codex training draft - requires student review",
        "reviewer": None,
        "notes": "Authored offline for training review; confirm naturalness and label before use.",
    }


def build_records() -> list[dict]:
    records: list[dict] = []

    government = [
        ("ICA: your passport is under investigation. Pay the S$120 clearance charge today to avoid travel restrictions.", "sms", ["urgency_or_threat", "payment_request", "brand_impersonation"], "gov", "ica_clearance_fee", "It impersonates ICA, threatens travel restrictions and demands a clearance payment."),
        ("MOM work pass notice: upload your Singpass login and OTP at https://mom-pass-review.example.com before 6 pm.", "sms", ["urgency_or_threat", "credential_request", "external_link", "brand_impersonation", "suspicious_url"], "singpass", "mom_pass_review", "It uses a government work-pass pretext to request Singpass credentials on a non-official domain."),
        ("Police warrant department here. Do not discuss this call. Move your savings to the protected account while we verify the case.", "whatsapp", ["payment_request", "secrecy_or_isolation", "brand_impersonation"], "gov", "police_protected_account", "A supposed Police unit requests secrecy and transfer of savings to a safety account."),
        ("HDB household rebate approved. Enter your card details at https://hdb-rebate.example.net/claim to receive S$480.", "email", ["credential_request", "external_link", "brand_impersonation", "suspicious_url"], "gov", "hdb_rebate_card", "It impersonates HDB and requests card details through an unverified rebate page."),
        ("CPF security team detected malware. Install cpf-protect.apk from https://cpf-helpdesk.example.org/app now.", "whatsapp", ["urgency_or_threat", "app_installation", "external_link", "brand_impersonation", "suspicious_url"], "gov", "cpf_malware_apk", "It impersonates CPF and pushes an APK from a domain outside cpf.gov.sg."),
        ("MOH enforcement notice: an unpaid vaccination fine is recorded under your NRIC. PayNow S$90 within one hour.", "sms", ["urgency_or_threat", "payment_request", "brand_impersonation"], "gov", "moh_vaccine_fine", "It impersonates MOH, references NRIC and demands an urgent PayNow payment."),
        ("Scan this QR and approve the Singpass request so the government officer can cancel the loan opened in your name.", "whatsapp", ["credential_request", "brand_impersonation"], "singpass", "singpass_qr_loan", "A supposed officer asks the recipient to approve a Singpass authentication for a fabricated loan case."),
        ("Singapore Customs: prohibited goods were found in a parcel addressed to you. Contact our investigator and keep the matter private.", "sms", ["urgency_or_threat", "secrecy_or_isolation", "brand_impersonation"], "gov", "customs_prohibited_parcel", "It impersonates Customs and uses a criminal allegation plus secrecy to induce engagement."),
        ("IRAS audit resolution: transfer the refundable S$600 bond today. The audit will close after verification.", "email", ["urgency_or_threat", "payment_request", "brand_impersonation"], "gov", "iras_audit_bond", "It presents a fake tax audit and requests an invented refundable bond."),
        ("I am an Anti-Scam Centre officer. Your account is being drained; send the balance to our temporary holding wallet immediately.", "whatsapp", ["urgency_or_threat", "payment_request", "brand_impersonation"], "gov", "asc_holding_wallet", "It impersonates an anti-scam officer and urges transfer to a holding wallet."),
    ]
    for index, item in enumerate(government, 1):
        message, channel, mechanisms, source, scenario, rationale = item
        records.append(scam(f"msg_train_gov_{index:03d}", message, channel, "government_impersonation", mechanisms, source, f"train_gov_{scenario}_01", rationale))

    investment = [
        ("Our gold trading bot has never lost a trade. Deposit S$800 before tonight's session for a guaranteed 15% gain.", "telegram", ["urgency_or_threat", "payment_request", "unrealistic_reward"], "investment", "gold_bot", "It guarantees an implausible return and requests a time-limited deposit."),
        ("I enjoyed chatting with you. Let me teach you the crypto method that helped me retire early; start by funding this wallet.", "whatsapp", ["payment_request", "unrealistic_reward"], "investment", "relationship_crypto", "A relationship-building approach transitions into a crypto funding request and exceptional wealth claim."),
        ("Pre-IPO allocation available only to our members. Pay the S$1,500 reservation amount now and double it after listing.", "telegram", ["urgency_or_threat", "payment_request", "unrealistic_reward"], "investment", "preipo_allocation", "It offers exclusive pre-IPO access, promises doubling and demands an advance payment."),
        ("Activate your cloud-mining package at https://mining-yield.example.com. The dashboard pays 3% daily with zero risk.", "email", ["external_link", "payment_request", "unrealistic_reward", "suspicious_url"], "investment", "mining_yield", "It advertises impossible risk-free daily returns through an unverified mining platform."),
        ("The professor's stock group has 1,200 winning students. Buy the recommended counter before 10 am and send a screenshot.", "telegram", ["urgency_or_threat", "social_proof_manipulation"], "investment_group", "professor_stock_group", "It uses fabricated authority and crowd success to push an urgent stock purchase."),
        ("Your frozen investment account can be recovered. Pay the compliance officer S$700 first to unlock the withdrawal.", "whatsapp", ["payment_request", "urgency_or_threat"], "investment", "recovery_unlock_fee", "It requests an advance fee to recover or unlock purported investment funds."),
        ("MAS-licensed opportunity: verify your investor account at https://mas-approved-fund.example.net/login and transfer the minimum S$2,000.", "sms", ["credential_request", "payment_request", "external_link", "brand_impersonation", "suspicious_url"], "investment", "mas_fake_fund", "It falsely invokes MAS, requests login details and solicits a transfer through a non-government domain."),
        ("Your exchange wallet must be revalidated. Send the 12-word recovery phrase to support or trading will be disabled.", "email", ["urgency_or_threat", "credential_request"], "investment", "wallet_seed_phrase", "It threatens account restriction and requests a crypto wallet recovery phrase."),
        ("Earn fixed 8% monthly from our commodity pool. Members receive instant bonuses for each friend they add.", "whatsapp", ["unrealistic_reward", "social_proof_manipulation"], "investment_group", "commodity_referral", "It promises fixed high returns and uses referral incentives and group growth as social proof."),
        ("A famous Singapore entrepreneur uses this AI share app. Install it from https://smart-share.example.org/app.apk and fund your account.", "sms", ["app_installation", "payment_request", "external_link", "social_proof_manipulation", "suspicious_url"], "investment", "celebrity_ai_app", "It uses celebrity-style endorsement, an external APK and a funding request."),
    ]
    for index, item in enumerate(investment, 1):
        message, channel, mechanisms, source, scenario, rationale = item
        records.append(scam(f"msg_train_inv_{index:03d}", message, channel, "investment", mechanisms, source, f"train_inv_{scenario}_01", rationale))

    jobs = [
        ("Online data optimisation assistant: complete 30 clicks daily. Top up S$100 to start and withdraw S$280 after the batch.", "whatsapp", ["payment_request", "unrealistic_reward"], "job", "optimisation_topup", "A simple-task job promises disproportionate earnings and requires an upfront top-up."),
        ("Hotel reviewer vacancy, S$25 per rating. Your account is negative after today's task; deposit S$350 to continue.", "telegram", ["payment_request", "unrealistic_reward"], "job", "hotel_review_negative", "A task job creates a negative balance and demands a deposit to continue."),
        ("You passed the interview for a remote admin role. Pay S$60 for the company laptop courier before we issue the contract.", "sms", ["payment_request"], "job", "laptop_courier_fee", "A supposed employer asks for an advance equipment-delivery payment before issuing a contract."),
        ("Recruiter: the overseas role is confirmed. Send the medical and work-permit fee by PayNow today.", "whatsapp", ["urgency_or_threat", "payment_request"], "job", "permit_medical_fee", "A recruiter pretext requests urgent work-permit and medical fees."),
        ("Home-based parcel forwarding staff needed. Receive packages, remove the labels and resend them for S$200 each.", "telegram", ["unrealistic_reward"], "job", "parcel_reshipping", "The role asks the recipient to reship goods for unusually high pay, a risky recruitment pattern."),
        ("Your crypto payroll account needs S$150 activation credit before salary can be released.", "whatsapp", ["payment_request"], "job", "crypto_salary_activation", "A fake payroll process requires the worker to pay before receiving salary."),
        ("Accounts assistant position: let customers transfer money into your personal bank account and forward it daily for 5% commission.", "whatsapp", ["payment_request", "unrealistic_reward"], "job", "personal_account_mule", "The alleged job recruits the recipient to receive and forward funds through a personal account."),
        ("Complete five surveys to earn S$90. The final survey requires a S$40 refundable verification payment.", "sms", ["payment_request", "unrealistic_reward"], "job", "survey_refund_fee", "It offers high survey earnings but requires a refundable verification payment."),
        ("IT support vacancy: install our remote-work client and allow full device access for the screening test.", "email", ["app_installation", "remote_access_request"], "job", "remote_access_screening", "A job screening process requests remote-access software and broad device control."),
        ("Sign this employment form using Singpass at https://career-sign.example.com and enter the OTP sent to your phone.", "sms", ["credential_request", "external_link", "brand_impersonation", "suspicious_url"], "job_singpass", "fake_singpass_contract", "It uses an employment contract pretext to capture Singpass authentication on a non-official domain."),
    ]
    for index, item in enumerate(jobs, 1):
        message, channel, mechanisms, source, scenario, rationale = item
        records.append(scam(f"msg_train_job_{index:03d}", message, channel, "job", mechanisms, source, f"train_job_{scenario}_01", rationale))

    ecommerce = [
        ("Two concert tickets available below cost. PayNow the full amount in 15 minutes or I will sell them to the next buyer.", "telegram", ["urgency_or_threat", "payment_request", "off_platform_payment"], "tickets_paynow", "It uses scarcity and an urgent direct payment request for unverifiable tickets."),
        ("Premium durians, same-day delivery. Transfer S$80 first; orders are not accepted through the marketplace checkout.", "whatsapp", ["payment_request", "off_platform_payment"], "durian_preorder", "It requires advance payment while explicitly avoiding platform checkout."),
        ("The sofa is reserved once you send a S$150 deposit. My mover can deliver tonight but payment must be outside Carousell.", "whatsapp", ["urgency_or_threat", "payment_request", "off_platform_payment", "brand_impersonation"], "sofa_deposit", "It requests an urgent reservation deposit and moves payment outside the marketplace."),
        ("Purebred puppy available. Pay the transport insurance at https://pet-delivery.example.com before viewing.", "email", ["payment_request", "external_link", "suspicious_url"], "pet_transport_fee", "It requests a pre-viewing transport fee through an unverified site."),
        ("Seller protection requires you to log in at https://shopee-escrow.example.net and confirm the OTP before funds are released.", "sms", ["credential_request", "external_link", "brand_impersonation", "suspicious_url"], "fake_escrow_otp", "It impersonates platform escrow and requests login plus OTP through a look-alike domain."),
        ("Your refund is ready. Complete the card verification form at https://refund-centre.example.org within 30 minutes.", "email", ["urgency_or_threat", "credential_request", "external_link", "suspicious_url"], "refund_card_form", "It uses a refund pretext and deadline to capture card details on an unverified domain."),
        ("Scan the attached payment QR to receive money from the buyer, then enter your banking PIN on the confirmation page.", "whatsapp", ["credential_request", "payment_request"], "buyer_qr_pin", "A fake buyer-payment flow asks the seller to scan a code and disclose a banking PIN."),
        ("Courier insurance of S$12 is required for your order. Pay at https://secure-courier.example.com or delivery will be cancelled.", "sms", ["urgency_or_threat", "payment_request", "external_link", "suspicious_url"], "courier_insurance", "It threatens cancellation to collect a fabricated courier fee through an unverified site."),
        ("Authentic luxury watch, 60% below retail. Transfer the deposit today because another buyer is waiting.", "whatsapp", ["urgency_or_threat", "payment_request", "unrealistic_reward"], "luxury_watch_deposit", "An implausible discount and competing-buyer pressure are used to obtain a deposit."),
        ("Platform customer service: your sale breached policy. Download the verification app from https://seller-check.example.net/app.apk to avoid suspension.", "email", ["urgency_or_threat", "app_installation", "external_link", "brand_impersonation", "suspicious_url"], "seller_verification_apk", "It impersonates platform support and threatens suspension to induce APK installation."),
    ]
    for index, item in enumerate(ecommerce, 1):
        message, channel, mechanisms, scenario, rationale = item
        records.append(scam(f"msg_train_ecom_{index:03d}", message, channel, "e_commerce", mechanisms, "ecommerce", f"train_ecom_{scenario}_01", rationale))

    legitimate = [
        ("DBS alert: S$52.10 was charged to your card. If unrecognised, open the DBS app directly and select Card Security.", "sms", [], "bank_open_app", "It asks the customer to use an already installed official app and requests no credentials or payment."),
        ("Your CPF statement for July is available. Access it by typing cpf.gov.sg in your browser or through the CPF mobile app.", "email", ["external_link", "brand_impersonation"], "cpf_statement", "It directs the recipient to a known official domain or app without requesting sensitive information."),
        ("Interview update: the hiring manager is delayed by 20 minutes. No documents or payment are needed; reply if you need to reschedule.", "sms", [], "interview_delay", "It is a routine scheduling update that explicitly requests no documents or money."),
        ("Your Shopee order has been paid in the app. Do not transfer money or share an OTP with the seller.", "sms", ["brand_impersonation"], "platform_paid_warning", "It confirms in-platform payment and warns against direct transfers or OTP disclosure."),
        ("Free public webinar: Understanding Investment Risk. Registration does not require a deposit, trading account or bank details.", "email", [], "investment_webinar", "It is an educational event that explicitly avoids deposits and sensitive-data collection."),
        ("Singpass notification: a login was approved at 3:14 pm. If this was not you, open the Singpass app directly to review access.", "sms", ["brand_impersonation"], "singpass_login_alert", "It directs the user to the official app and contains no link or request for credentials."),
        ("Your parcel is at the lobby collection point. Collection code: 4821. No fee is due.", "sms", [], "parcel_collection", "It gives delivery information and explicitly states that no fee is required."),
        ("PayNow received: S$35.00 from A TAN. This is a receipt only; no action is required.", "sms", [], "paynow_receipt", "It is a payment receipt that requests no response, transfer or credential."),
        ("OTP 731204 is for your purchase. Never share this code. If you did not initiate the purchase, call the number on your card.", "sms", ["credential_request"], "otp_warning", "Although it contains an OTP, it warns against sharing it and provides an independently verifiable contact method."),
        ("IRAS notice: your tax assessment is available in myTax Portal. Navigate to iras.gov.sg yourself; this email contains no payment link.", "email", ["external_link", "brand_impersonation"], "iras_portal_notice", "It names the official government domain and explicitly contains no payment link."),
        ("The recruiter has sent the job description from our company email. The next step is a video interview; there are no applicant fees.", "email", [], "recruiter_no_fee", "It follows a normal recruitment process and explicitly states there are no applicant fees."),
        ("Reminder: semester fees are due next Friday. Use the university portal bookmark you already have to view the bill.", "email", ["urgency_or_threat", "payment_request"], "university_fee", "It is a normal fee reminder that avoids supplied links and directs the user to an existing portal."),
        ("Hospital appointment confirmed for 9 September at 2 pm. Bring your identity card; payment, if any, is made at the clinic counter.", "sms", [], "hospital_appointment", "It is an appointment confirmation with payment handled in person and no external action."),
        ("Your marketplace buyer has paid through escrow. Ship only after the status changes to Paid inside the app.", "whatsapp", [], "escrow_safe_sale", "It reinforces checking payment inside the platform and does not request direct payment."),
        ("Mum, my train is delayed and my phone battery is low. I will call you when I reach home; no need to do anything.", "whatsapp", ["urgency_or_threat"], "family_delay", "It contains situational urgency but no request for money, credentials or action."),
    ]
    for index, item in enumerate(legitimate, 1):
        message, channel, mechanisms, scenario, rationale = item
        records.append(non_scam(f"msg_train_legit_{index:03d}", message, channel, "legitimate", mechanisms, f"train_legit_{scenario}_01", rationale))

    ambiguous = [
        ("Can you send the payment to the same account as last time? I will explain after my meeting.", "whatsapp", ["payment_request"], "same_account", "A payment request exists, but prior relationship and transaction context are unavailable."),
        ("Security verification pending. Please call us today regarding your account.", "sms", ["urgency_or_threat"], "security_call", "The sender and callback number are missing, but the excerpt requests no credentials or transfer."),
        ("The recruiter needs one more document before confirming your start date.", "whatsapp", [], "recruiter_document", "The requested document is unspecified, so sensitivity and legitimacy cannot be assessed."),
        ("Your order cannot be delivered until the outstanding item is resolved. Check your account for details.", "sms", ["urgency_or_threat"], "order_issue", "There is insufficient information about the sender, account access method or outstanding item."),
        ("This opportunity closes tonight. Let me know if you want the details.", "telegram", ["urgency_or_threat"], "opportunity_details", "Urgency is present, but the nature of the opportunity and any requested action are not yet known."),
    ]
    for index, item in enumerate(ambiguous, 1):
        message, channel, mechanisms, scenario, rationale = item
        records.append(non_scam(f"msg_train_amb_{index:03d}", message, channel, "ambiguous", mechanisms, f"train_amb_{scenario}_01", rationale))

    assert len(records) == 60
    return records


def main() -> None:
    records = build_records()
    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSONL.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )

    fields = [
        "id", "message", "proposed_risk_label", "proposed_primary_type",
        "proposed_mechanisms", "source_name", "source_url", "campaign_group",
        "student_decision", "corrected_risk_label", "corrected_primary_type",
        "corrected_mechanisms", "review_notes",
    ]
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
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

    print(f"Created {OUTPUT_JSONL}")
    print(f"Created {OUTPUT_CSV}")
    print(f"Risk labels: {dict(Counter(record['risk_label'] for record in records))}")
    print(f"Primary types: {dict(Counter(record['primary_type'] for record in records))}")


if __name__ == "__main__":
    main()

