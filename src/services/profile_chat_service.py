"""Deterministic, session-scoped answers for a user's own profile and privacy boundaries."""
from __future__ import annotations

import re
import unicodedata

from src.models.user import User


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value).casefold()
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").replace("đ", "d")


_EMAIL_PATTERN = re.compile(r"(?i)(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w-])")
_PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?84|0)(?:[\s().-]*\d){8,10}(?!\w)")


def _mask_profile_contact_details(value: str) -> str:
    """Mask contact PII because profile replies may be persisted or shared."""
    return _PHONE_PATTERN.sub("***", _EMAIL_PATTERN.sub("***", value))


_PASSWORD_PROBE_PATTERNS = (
    r"\b(?:password|mat khau|pass)\s+(?:cua\s+)?(?:admin|manager|giam doc|director|truong phong|user|tai khoan|root|he thong|nguoi khac)\b",
    r"\b(?:password|mat khau)\s+admin\b",
    r"\bcho\s+toi\s+(?:password|mat khau)\b",
    r"\b(?:password|mat khau)\b.{0,24}\bla\s+gi\b",
)

_THIRD_PARTY_PERSON_PATTERNS = (
    r"\b(?:thong tin|tai khoan|ho so|profile|email|sdt|so dien thoai|dien thoai|phone|lien he|danh ba)\s+(?:ve\s+)?(?:tai khoan\s+)?(?:cua\s+)?(?:manager|giam doc|director|truong phong|pho phong|leader|sep|admin|administrator|quan tri vien|ky thuat vien|technician|tech|nhan vien\s+(?:khac|[a-z])|nguoi\s+khac|user\s+khac|tai khoan\s+khac|dong nghiep|ai\s+do)\b",
    r"\b(?:thong tin|tai khoan|ho so|profile|email|sdt|so dien thoai|dien thoai|phone)\s+(?:ve\s+)?(?:tai khoan\s+)?(?:manager|giam doc|director|truong phong|pho phong|leader|sep|admin|administrator|quan tri vien|ky thuat vien|technician|nhan vien\s+\w+)\b",
    r"\b(?:thong tin|email|sdt|so dien thoai)\s+(?:nguyen|tran|le|pham|hoang|huynh|phan|vu|vo|dang|bui|do|ho|ngo|duong|ly)\s+[a-z]+\b",
    r"\b(?:tai khoan|thong tin|email|sdt|so dien thoai|ho so|profile)\s+cua\s+(?!toi\b|minh\b|ban than\b|em\b)\w+",
    r"\bcho\s+toi\s+(?:tai khoan|thong tin|email|sdt|so dien thoai|ho so)\s+(?:cua\s+)?(?:manager|giam doc|director|truong phong|pho phong|leader|sep|admin|technician|ky thuat vien|nhan vien\s+\w+|nguoi\s+khac)\b",
    r"\b(?:gia vo|gia dinh|dong vai).{0,30}\b(?:admin|manager|giam doc).{0,40}\b(?:thong tin|email|tai khoan|mat khau|password)\b",
    r"\btai khoan\s+(?:manager|giam doc|director|truong phong|admin|technician)\b",
)

_SELF_PROFILE_PATTERNS = (
    r"\b(?:thong tin|ho so|profile|tai khoan)\s+(?:ca nhan\s+)?(?:cua\s+)?(?:toi|minh|ban than)\b",
    r"\b(?:thong tin|ho so|profile|tai khoan)\s+(?:cua\s+)?(?:toi|minh)\b",
    r"\b(?:email|sdt|so dien thoai|dien thoai|phone)\s+(?:cua\s+)?(?:toi|minh)\b",
    r"\b(?:toi|minh)\s+la\s+ai\b",
    r"\b(?:toi|minh)\s+ten\s+la\s+gi\b",
    r"\bten\s+(?:cua\s+)?(?:toi|minh)\b",
    r"\btai khoan\s+dang\s+dang\s+nhap\b",
    r"\b(?:so dien thoai|sdt|email)\s+(?:cua\s+)?toi\s+(?:da\s+cap\s+nhat\s+chua|la\s+gi)\b",
    r"\bthong tin\s+cua\s+toi\b",
    r"\bthong tin\s+(?:ve\s+)?tai khoan\s+cua\s+toi\b",
)


def self_profile_reply(message: str, user: User) -> str | None:
    """Answer only explicit self-profile questions, and reject third-party/credential probing.

    Returning a reply bypasses RAG/LLM entirely. This prevents prompt injection
    from turning a profile question into a query over other people or credentials.
    """
    text = _fold(message)

    # Benign policy / guidelines inquiries are handled by knowledge RAG, not profile guard
    is_policy_query = any(term in text for term in ("quy dinh", "chinh sach", "huong dan", "tieu chuan", "dieu khoan"))
    if is_policy_query and not any(term in text for term in ("cua toi", "cua minh", "ban than", "ca nhan")):
        return None

    # 1. Credential & secret probing protection
    if any(re.search(pat, text) for pat in _PASSWORD_PROBE_PATTERNS):
        return (
            "Vì lý do an ninh, hệ thống không bao giờ tiết lộ mật khẩu, mã xác thực "
            "hoặc thông tin bảo mật của bất kỳ tài khoản nào."
        )

    # 2. Third-party person / role profile probing protection
    if any(re.search(pat, text) for pat in _THIRD_PARTY_PERSON_PATTERNS):
        return (
            "Vì bảo mật và quyền riêng tư, tôi chỉ có thể xem thông tin hồ sơ của tài khoản đang đăng nhập. "
            "Tôi không thể tìm hoặc tiết lộ dữ liệu cá nhân hay tài khoản của người dùng khác (quản lý, giám đốc, kỹ thuật viên hoặc đồng nghiệp). "
            "Nếu cần liên hệ công việc, bạn vui lòng sử dụng danh bạ nội bộ được cấp quyền hoặc liên hệ phòng IT/Nhân sự."
        )

    # 3. Explicit self-profile inquiry
    is_self_profile = any(re.search(pat, text) for pat in _SELF_PROFILE_PATTERNS)
    if not is_self_profile:
        return None

    wants_name = "ten" in text or "toi la ai" in text
    wants_email = "email" in text or "e-mail" in text
    wants_phone = any(term in text for term in ("so dien thoai", "sdt", "dien thoai", "phone"))
    wants_profile = any(term in text for term in ("thong tin ca nhan", "ho so", "profile", "tai khoan", "thong tin"))

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
