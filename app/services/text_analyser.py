from __future__ import annotations

import re
from collections import defaultdict


TYPE_PATTERNS = {
    "government_impersonation": {
        "label": "Government official impersonation",
        "patterns": [
            r"\bsingpass\b", r"\bcpf\b", r"\biras\b", r"\bministry\b",
            r"\bpolice\b", r"\bgovernment\b", r"gov(?:ernment)? officer",
            r"官方", r"政府", r"警察", r"新加坡政府",
        ],
    },
    "investment": {
        "label": "Investment scam",
        "patterns": [
            r"\binvest(?:ment|ing)?\b", r"\bcrypto\b", r"\btrading\b",
            r"guaranteed returns?", r"risk[- ]free", r"profit", r"withdrawal fee",
            r"投资", r"稳赚", r"高回报", r"交易平台", r"导师",
        ],
    },
    "job": {
        "label": "Job scam",
        "patterns": [
            r"\bjob\b", r"recruit(?:er|ment)", r"part[- ]time", r"work from home",
            r"commission", r"simple tasks?", r"daily income", r"职位", r"招聘",
            r"兼职", r"佣金", r"刷单", r"在家工作",
        ],
    },
    "e_commerce": {
        "label": "E-commerce scam",
        "patterns": [
            r"\bcarousell\b", r"\bshopee\b", r"\blazada\b", r"parcel",
            r"delivery fee", r"buyer protection", r"outside (?:the )?platform",
            r"商品", r"包裹", r"快递", r"平台外", r"卖家", r"买家",
        ],
    },
}

MECHANISM_PATTERNS = {
    "urgency_or_threat": {
        "label": "Creates urgency or threatens consequences",
        "patterns": [r"urgent", r"immediately", r"within \d+ hours?", r"suspend", r"blocked?", r"final warning", r"立即", r"马上", r"紧急", r"暂停", r"冻结", r"最后通知"],
        "weight": 0.16,
    },
    "credential_request": {
        "label": "Requests credentials, OTP or sensitive information",
        "patterns": [r"\botp\b", r"password", r"login details?", r"banking credentials?", r"singpass details?", r"\bnric\b", r"验证码", r"密码", r"登录资料", r"身份证"],
        "weight": 0.25,
    },
    "payment_request": {
        "label": "Requests money, a transfer or an upfront fee",
        "patterns": [r"transfer (?:money|funds?)", r"pay(?:ment)? fee", r"deposit", r"paynow", r"bank account", r"upfront", r"转账", r"付款", r"保证金", r"手续费", r"银行账户"],
        "weight": 0.22,
    },
    "off_platform_payment": {
        "label": "Requests payment outside a marketplace's protected checkout",
        "patterns": [
            r"payment (?:must|needs? to) be (?:made )?outside (?:the )?(?:platform|marketplace|carousell|shopee|lazada)",
            r"(?:outside|off)[ -]?platform payment",
            r"orders? (?:are|is) not accepted through (?:the )?(?:marketplace|platform) checkout",
            r"(?:cancel|leave|avoid|bypass).{0,45}(?:order|checkout|platform).{0,65}(?:paynow|bank transfer|transfer|pay me|pay directly)",
            r"(?:cannot|can't|unable to|do not) use (?:the )?(?:platform|app) payment",
        ],
        "weight": 0.24,
    },
    "unrealistic_reward": {
        "label": "Promises unusually easy or guaranteed returns",
        "patterns": [r"guaranteed", r"double your", r"easy money", r"high returns?", r"earn s?\$?\d+.*day", r"稳赚", r"翻倍", r"轻松赚钱", r"高回报", r"日赚"],
        "weight": 0.20,
    },
    "secrecy_or_isolation": {
        "label": "Asks the recipient to keep the matter secret",
        "patterns": [r"do not tell", r"keep (?:this|it) secret", r"confidential investigation", r"不要告诉", r"保密", r"秘密调查"],
        "weight": 0.18,
    },
    "external_link": {
        "label": "Directs the recipient to an external link",
        "patterns": [r"https?://", r"www\.", r"click (?:here|the link)", r"tap (?:here|the link)", r"点击链接", r"点此"],
        "weight": 0.10,
    },
    "app_installation": {
        "label": "Requests installation of an app or remote-access software",
        "patterns": [r"install (?:this|the|our) app", r"download.*apk", r"remote access", r"anydesk", r"teamviewer", r"安装.*(?:应用|软件)", r"下载.*apk", r"远程控制"],
        "weight": 0.27,
    },
}


def _matches(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def analyse_text(message: str) -> dict:
    type_scores: dict[str, int] = defaultdict(int)
    for type_id, config in TYPE_PATTERNS.items():
        type_scores[type_id] = sum(
            bool(re.search(pattern, message, re.IGNORECASE))
            for pattern in config["patterns"]
        )

    ranked_types = sorted(type_scores.items(), key=lambda item: item[1], reverse=True)
    if ranked_types and ranked_types[0][1] > 0:
        primary_type = ranked_types[0][0]
        primary_label = TYPE_PATTERNS[primary_type]["label"]
    else:
        primary_type = "uncertain"
        primary_label = "Uncertain / other"

    mechanisms = []
    raw_score = 0.05
    for mechanism_id, config in MECHANISM_PATTERNS.items():
        if _matches(message, config["patterns"]):
            mechanisms.append({"id": mechanism_id, "label": config["label"]})
            raw_score += config["weight"]

    if ranked_types and ranked_types[0][1] >= 2:
        raw_score += 0.12
    elif ranked_types and ranked_types[0][1] == 1:
        raw_score += 0.06

    return {
        "score": round(min(raw_score, 0.95), 3),
        "primary_type": primary_type,
        "primary_type_label": primary_label,
        "mechanisms": mechanisms,
        "type_scores": dict(type_scores),
    }
