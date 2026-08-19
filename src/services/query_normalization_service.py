"""Deterministic Help Desk query normalization and technical token extraction.

Provides conservative Vietnamese informal abbreviation expansion and exact
technical token extraction while strictly preserving technical terms, product
names, error codes, and URLs.
"""
from __future__ import annotations

import re
import unicodedata

# Protected technical tokens that should never be modified or split
PROTECTED_TECHNICAL_TERMS: set[str] = {
    # Products & Platforms
    "forticlient", "cisco", "anyconnect", "bitlocker", "outlook", "exchange",
    "sap", "teams", "zoom", "autocad", "adobe", "workday", "hris", "gitlab",
    "github", "windows", "office", "word", "excel", "powerpoint", "azure",
    "entra", "okta", "pacs", "dicom", "his", "wms", "erp", "crm", "salesforce",
    # Protocols & Acronyms
    "vpn", "mfa", "2fa", "sspr", "bsod", "dns", "dhcp", "lan", "wan", "wifi",
    "wi-fi", "wireless", "ost", "pst", "ntfs", "pos", "mri", "x-quang", "dlp",
    "cpu", "ram", "gpu", "ssd", "hdd", "usb", "ip", "tcp", "udp", "ssl", "tls",
    # Error phrases & Technical tokens
    "stop code", "blue screen", "recovery key", "authentication failed",
    "maximum sessions exceeded", "session timeout", "outbox", "disconnected",
    "phishing", "malware", "ransomware", "403", "401", "404", "500", "502",
}

# Conservative Help Desk informal abbreviations -> canonical Vietnamese
INFORMAL_VI_MAP: dict[str, str] = {
    # Negations & Conditionals
    "ko": "không",
    "k": "không",
    "khong": "không",
    "khg": "không",
    "hok": "không",
    "hem": "không",
    "dc": "được",
    "đc": "được",
    "duoc": "được",
    "dx": "được",
    # Entities & Locations
    "cty": "công ty",
    "cong ty": "công ty",
    "mk": "mật khẩu",
    "mat khau": "mật khẩu",
    "pass": "mật khẩu",
    "pwd": "mật khẩu",
    "password": "mật khẩu",
    "sdt": "số điện thoại",
    "sđt": "số điện thoại",
    "acc": "tài khoản",
    "tai khoan": "tài khoản",
    "tk": "tài khoản",
    "may tinh": "máy tính",
    "laptop": "laptop",
    # Actions & States
    "auth": "authentication",
    "login": "đăng nhập",
    "dang nhap": "đăng nhập",
    "sync": "đồng bộ",
    "dong bo": "đồng bộ",
    "err": "lỗi",
    "loi": "lỗi",
    "cham": "chậm",
    "lag": "lag",
    "qua troi": "nhiều",
    "nho": "nhớ",
    "vao": "vào",
    "ket noi": "kết nối",
    "mat": "mất",
    "khau": "khẩu",
    "ket": "kẹt",
    "noi": "nối",
    "reset": "reset",
}


def _strip_combining_accents(text: str) -> str:
    """Normalize Unicode to NFKD and remove combining accent characters."""
    normalized = unicodedata.normalize("NFKD", text).casefold()
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_informal_query(query: str) -> str:
    """Normalize informal Vietnamese tokens while preserving technical tokens.

    Idempotent: normalize_informal_query(normalize_informal_query(q)) == normalize_informal_query(q).
    """
    if not query or not query.strip():
        return query

    text = query.strip()
    words = text.split()
    normalized_tokens: list[str] = []
    i = 0

    while i < len(words):
        # 1. Check two-word technical term / informal phrase
        if i + 1 < len(words):
            two_word_raw = f"{words[i]} {words[i+1]}"
            two_word_lower = two_word_raw.lower()

            # Protected exact technical term
            if two_word_lower in PROTECTED_TECHNICAL_TERMS:
                normalized_tokens.append(two_word_raw)
                i += 2
                continue

            # Two-word informal mapping
            if two_word_lower in INFORMAL_VI_MAP:
                normalized_tokens.append(INFORMAL_VI_MAP[two_word_lower])
                i += 2
                continue

        # 2. Check single word
        word_raw = words[i]
        word_lower = word_raw.lower()

        # Check if protected technical term
        if word_lower in PROTECTED_TECHNICAL_TERMS:
            normalized_tokens.append(word_raw)
            i += 1
            continue

        # Check single-word informal mapping (case-insensitive)
        clean_word = re.sub(r"^[^\w]+|[^\w]+$", "", word_lower)
        if clean_word in INFORMAL_VI_MAP:
            replacement = INFORMAL_VI_MAP[clean_word]
            # Preserve surrounding punctuation
            prefix = word_raw[:len(word_raw) - len(word_raw.lstrip("^()[]{},;:!?."))]
            suffix = word_raw[len(word_raw.rstrip("^()[]{},;:!?.")):]
            normalized_tokens.append(f"{prefix}{replacement}{suffix}")
        else:
            normalized_tokens.append(word_raw)
        i += 1

    return " ".join(normalized_tokens)


def extract_exact_technical_tokens(text: str) -> set[str]:
    """Extract exact technical terms and identifiers present in the text."""
    if not text:
        return set()

    text_lower = text.lower()
    found: set[str] = set()

    for term in PROTECTED_TECHNICAL_TERMS:
        # Match whole word / phrase with word boundary
        pattern = r"(?:\b|^)" + re.escape(term) + r"(?:\b|$)"
        if re.search(pattern, text_lower):
            found.add(term)

    # Match HTTP error codes (e.g., "HTTP 403", "403")
    for code_match in re.finditer(r"\b(?:http\s*)?(401|403|404|500|502)\b", text_lower):
        found.add(code_match.group(0))

    return found
