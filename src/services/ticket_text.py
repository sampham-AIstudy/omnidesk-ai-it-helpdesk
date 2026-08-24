"""Normalize ticket form content before it reaches AI decision nodes.

The employee form adds a product label and several structured fields for the
technician.  Those labels are useful context, but they must not outweigh the
user's own report: selecting the wrong product must not turn a generic
software-install request into a SAP ticket.
"""
from __future__ import annotations

import re

_FORM_PRODUCT_PREFIX = re.compile(
    r"^\s*\[(?:Mạng Nội Bộ & VPN|Email & Office|SAP ERP|Phần Cứng & Laptop|"
    r"Tài Khoản & Quyền|Máy Chủ & Hạ Tầng|Yêu Cầu Khác)\]\s*",
    re.IGNORECASE,
)
_DETAIL_MARKER = re.compile(r"---\s*MÔ TẢ CHI TIẾT SỰ CỐ\s*---", re.IGNORECASE)


def user_report(title: str, description: str) -> tuple[str, str]:
    """Return only the free-text report, excluding UI-added form framing.

    No user content is discarded beyond the known leading product tag and the
    structured form header before the detail marker.
    """
    clean_title = _FORM_PRODUCT_PREFIX.sub("", title or "").strip()
    raw_description = description or ""
    marker = _DETAIL_MARKER.search(raw_description)
    clean_description = raw_description[marker.end():].strip() if marker else raw_description.strip()
    return clean_title or (title or "").strip(), clean_description
