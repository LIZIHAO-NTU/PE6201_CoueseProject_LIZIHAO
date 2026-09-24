from __future__ import annotations


def recommend_actions(
    *,
    risk_level: str,
    primary_type: str,
    clicked_link: bool,
    shared_credentials: bool,
    transferred_money: bool,
) -> list[dict]:
    actions: list[dict] = []

    if transferred_money:
        actions.extend([
            {"priority": "urgent", "text": "Contact your bank immediately and ask it to stop or block the transaction."},
            {"priority": "urgent", "text": "Make a Police report and keep the message, transaction details and screenshots as evidence."},
            {"priority": "urgent", "text": "Call the 24/7 ScamShield Helpline at 1799 for scam-related assistance."},
        ])
    elif shared_credentials:
        actions.extend([
            {"priority": "urgent", "text": "Change the affected password through the official app or website, not through the message link."},
            {"priority": "urgent", "text": "Contact the relevant bank or organisation and review recent account activity and linked devices."},
            {"priority": "high", "text": "Call ScamShield at 1799 if you are unsure what information may have been exposed."},
        ])
    elif clicked_link:
        actions.extend([
            {"priority": "high", "text": "Close the page and do not enter information, approve payments or download files."},
            {"priority": "high", "text": "If anything was downloaded, disconnect the device from the network and run a trusted security scan."},
            {"priority": "normal", "text": "Open the organisation's official app or type its official address manually to verify the claim."},
        ])
    else:
        actions.extend([
            {"priority": "high" if risk_level == "high" else "normal", "text": "Do not click the link, reply, transfer money or disclose credentials."},
            {"priority": "normal", "text": "Verify the request through an independently found official channel or the organisation's official app."},
            {"priority": "normal", "text": "Call the 24/7 ScamShield Helpline at 1799 if you remain uncertain."},
        ])

    type_specific = {
        "government_impersonation": "Government officials will not ask you to transfer money or disclose bank login details over a phone call. Verify through the agency's official gov.sg channel.",
        "investment": "Check the entity and representative using official MAS registers; do not pay additional withdrawal or verification fees.",
        "job": "Do not pay to secure a job or share Singpass credentials. Verify the recruiter through the organisation's independently sourced contact details.",
        "e_commerce": "Keep communication and payment on the authorised platform and report suspicious sellers to the platform.",
    }
    if primary_type in type_specific:
        actions.append({"priority": "normal", "text": type_specific[primary_type]})
    return actions

