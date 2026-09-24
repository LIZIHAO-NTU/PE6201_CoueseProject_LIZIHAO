from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse


URL_PATTERN = re.compile(r"(?:(?:https?://)|(?:www\.))[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+", re.IGNORECASE)
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "rebrand.ly", "shorturl.at"}
OFFICIAL_DOMAINS = {"gov.sg", "police.gov.sg", "scamshield.gov.sg", "mas.gov.sg", "cpf.gov.sg", "singpass.gov.sg"}
BRANDS = {
    "singpass": {"singpass.gov.sg"},
    "cpf": {"cpf.gov.sg"},
    "iras": {"iras.gov.sg"},
    "scamshield": {"scamshield.gov.sg"},
    "dbs": {"dbs.com.sg"},
    "posb": {"posb.com.sg"},
    "ocbc": {"ocbc.com"},
    "uob": {"uob.com.sg"},
    "paynow": set(),
}


def extract_urls(message: str) -> list[str]:
    return [match.rstrip(".,;:!?)]}'\"") for match in URL_PATTERN.findall(message)]


def _registered_domain(host: str) -> str:
    host = host.strip(".").lower()
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    if host.endswith(".com.sg") or host.endswith(".org.sg") or host.endswith(".net.sg"):
        return ".".join(parts[-3:])
    if host.endswith(".gov.sg"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _is_official_government(host: str) -> bool:
    return host == "gov.sg" or host.endswith(".gov.sg")


def analyse_url(raw_url: str) -> dict:
    normalised = raw_url if re.match(r"^[a-z]+://", raw_url, re.IGNORECASE) else f"https://{raw_url}"
    parsed = urlparse(normalised)
    host = (parsed.hostname or "").lower().strip(".")
    registered_domain = _registered_domain(host)
    signals = []
    score = 0.04

    if not host:
        return {"url": raw_url, "host": "", "registered_domain": "", "score": 0.7, "risk_level": "high", "signals": ["The URL could not be parsed safely."]}

    if _is_ip(host):
        signals.append("Uses an IP address instead of a normal domain name")
        score += 0.30
    if "@" in parsed.netloc:
        signals.append("Contains an @ sign that can obscure the true destination")
        score += 0.28
    if host.startswith("xn--") or ".xn--" in host:
        signals.append("Uses Punycode, which can be used for look-alike domains")
        score += 0.24
    if registered_domain in SHORTENERS:
        signals.append("Uses a URL shortener that hides the final destination")
        score += 0.20
    if len(raw_url) > 100:
        signals.append("The URL is unusually long")
        score += 0.10
    if host.count(".") >= 4:
        signals.append("Uses many subdomain levels")
        score += 0.10
    if host.count("-") >= 2:
        signals.append("Uses multiple hyphens in the domain")
        score += 0.08

    for brand, approved_domains in BRANDS.items():
        if brand in host and registered_domain not in approved_domains:
            signals.append(f"Contains the brand term '{brand}' outside its recognised official domain")
            score += 0.35
            break

    if "gov.sg" in host and not _is_official_government(host):
        signals.append("Contains 'gov.sg' but is not actually under the gov.sg domain")
        score += 0.42

    path_text = f"{parsed.path} {parsed.query}".lower()
    if re.search(r"login|verify|secure|account|otp|password|wallet|payment", path_text):
        signals.append("Uses a credential- or payment-related path")
        score += 0.12

    if _is_official_government(host) or registered_domain in OFFICIAL_DOMAINS:
        score = min(score, 0.08)
        signals = ["The host is under a recognised Singapore Government domain"]

    score = round(min(score, 0.98), 3)
    risk_level = "high" if score >= 0.50 else "medium" if score >= 0.30 else "low"
    return {
        "url": raw_url,
        "host": host,
        "registered_domain": registered_domain,
        "score": score,
        "risk_level": risk_level,
        "signals": signals or ["No strong lexical warning signal was detected"],
    }


def analyse_urls(message: str) -> list[dict]:
    return [analyse_url(url) for url in extract_urls(message)]
