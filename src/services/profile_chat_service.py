"""Deterministic, session-scoped answers for a user's own profile."""
from __future__ import annotations

import re
import unicodedata

from src.models.user import User


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value).casefold()
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").replace("đ", "d")


_PROFILE_TERMS = (
    "email", "e-mail", "so dien thoai", "sdt", "dien thoai",
    "phone", "thong tin ca nhan", "ho so", "profile", "tai khoan",
)
_SELF_TERMS = ("toi", "minh", "ban than", "cua toi", "tai khoan toi", "ho so toi")
_OTHER_TERMS = (
    "nguoi khac", "user khac", "nhan vien khac", "tai khoan khac",
    "nguoi dung khac", "cua nguoi", "cua user", "cua nhan vien",
)


_EMAIL_PATTERN = re.compile(r"(?i)(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w-])")
_PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?84|0)(?:[\s().-]*\d){8,10}(?!\w)")


def _mask_profile_contact_details(value: str) -> str:
    """Mask contact PII because profile replies may be persisted or shared."""
    return _PHONE_PATTERN.sub("***", _EMAIL_PATTERN.sub("***", value))


def self_profile_reply(message: str, user: User) -> str | None:
    """Answer only explicit self-profile questions, never perform a user lookup.

    Returning a reply bypasses RAG/LLM entirely.  This prevents prompt injection
    from turning a profile question into a query over other people or documents.
    """
    text = _fold(message)
    is_profile_question = (
        any(term in text for term in _PROFILE_TERMS)
        or "toi la ai" in text
        or bool(re.search(r"\b(?:toi|minh)\b.{0,24}\bten\b|\bten\s+cua\s+", text))
    )
    if not is_profile_question:
        return None

    asks_for_other = any(term in text for term in _OTHER_TERMS) or bool(
        re.search(r"\b(?:ten|email|sdt|so dien thoai|ho so)\s+cua\s+(?!toi\b|minh\b)", text)
    )
    if asks_for_other or not any(term in text for term in _SELF_TERMS):
        return (
            "Vì bảo mật, tôi chỉ có thể xem thông tin hồ sơ của tài khoản đang đăng nhập. "
            "Tôi không thể tìm hoặc tiết lộ dữ liệu cá nhân của người dùng khác."
        )

    wants_name = "ten" in text or "toi la ai" in text
    wants_email = "email" in text or "e-mail" in text
    wants_phone = any(term in text for term in ("so dien thoai", "sdt", "dien thoai", "phone"))
    wants_profile = any(term in text for term in ("thong tin ca nhan", "ho so", "profile", "tai khoan"))

    details: list[str] = []
    if wants_name or wants_profile:
        details.append(f"Họ và tên: {user.full_name}.")
    if wants_email or wants_profile:
        details.append(f"Email: {user.email}.")
    if wants_phone or wants_profile:
        details.append(
            f"Số điện thoại: {user.phone}." if user.phone else "Số điện thoại: bạn chưa cập nhật trong hồ sơ."
        )
    details = [_mask_profile_contact_details(detail) for detail in details]
    if not details:
        details.append(f"Bạn đang đăng nhập với họ và tên: {user.full_name}.")
    return " ".join(details) + " Bạn có thể cập nhật thông tin này trong Hồ sơ cá nhân."
