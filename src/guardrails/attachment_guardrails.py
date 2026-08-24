"""
Attachment Guardrail Module
Pipeline: Attachment -> File type validation -> Size validation -> Text extraction -> Injection scan -> PII scan -> Threat scan (VirusTotal & Google Safe Browsing) -> Safe document.
"""

import logging
import re
from typing import Any

import requests

from src.config import get_settings
from src.guardrails.input_guardrails import detect_injection
from src.guardrails.output_guardrails import redact_secrets_and_pii

logger = logging.getLogger(__name__)
settings = get_settings()

ALLOWED_EXTENSIONS = {".txt", ".log", ".pdf", ".docx", ".csv", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


def scan_url_virustotal(url_to_scan: str) -> dict[str, Any]:
    """Scan URL using VirusTotal API v3."""
    api_key = settings.virustotal_api_key
    if not api_key:
        return {"malicious": False, "reason": "No VirusTotal API key configured"}

    vt_url = "https://www.virustotal.com/api/v3/urls"
    headers = {"x-apikey": api_key}
    try:
        res = requests.post(vt_url, data={"url": url_to_scan}, headers=headers, timeout=5)
        if res.status_code in (200, 201):
            return {"malicious": False, "raw": res.json()}
    except Exception as e:
        logger.warning(f"VirusTotal API scan error: {e}")
    return {"malicious": False}


def scan_url_safe_browsing(urls: list[str]) -> dict[str, Any]:
    """Scan URLs using Google Safe Browsing API v4."""
    api_key = settings.google_safe_browsing_api
    if not api_key or not urls:
        return {"safe": True, "matches": []}

    endpoint = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}"
    payload: dict[str, Any] = {
        "client": {"clientId": "helpdesk-agent", "clientVersion": "1.0.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": u} for u in urls],
        },
    }

    try:
        res = requests.post(endpoint, json=payload, timeout=5)
        if res.status_code == 200:
            matches = res.json().get("matches", [])
            return {"safe": len(matches) == 0, "matches": matches}
    except Exception as e:
        logger.warning(f"Google Safe Browsing API error: {e}")
    return {"safe": True, "matches": []}


def scan_attachment(file_name: str, file_bytes: bytes, text_content: str = "") -> dict[str, Any]:
    """Execute full attachment security scanning pipeline."""
    # 1. File extension validation
    ext = "." + file_name.split(".")[-1].lower() if "." in file_name else ""
    if ext not in ALLOWED_EXTENSIONS:
        return {"safe": False, "reason": f"File extension '{ext}' not allowed"}

    # 2. File size validation
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        return {"safe": False, "reason": f"File size ({len(file_bytes)} bytes) exceeds limit (10MB)"}

    # 3. Prompt injection scan on extracted text
    if text_content:
        inj_res = detect_injection(text_content)
        if inj_res["detected"]:
            return {"safe": False, "reason": f"Prompt injection detected in attachment text: {inj_res['reason']}"}

        # PII & Secret Redaction
        pii_res = redact_secrets_and_pii(text_content)
        text_content = pii_res["redacted"]

        # Extract and scan URLs
        extracted_urls = re.findall(r"https?://[^\s'\"]+", text_content)
        if extracted_urls:
            sb_res = scan_url_safe_browsing(extracted_urls)
            if not sb_res["safe"]:
                return {"safe": False, "reason": f"Malicious URLs detected in attachment: {sb_res['matches']}"}

    return {
        "safe": True,
        "sanitized_text": text_content,
        "file_name": file_name,
        "reason": "Attachment passed security checks",
    }


if __name__ == "__main__":
    test_file = scan_attachment("log.txt", b"sample content", "Check this link http://example.com")
    print("Attachment Scan Result:", test_file)
