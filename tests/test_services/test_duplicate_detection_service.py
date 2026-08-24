from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from src.database import AsyncSessionLocal
from src.models.ticket import Ticket, TicketStatus
from src.models.user import User
from src.services.duplicate_detection_service import (
    DuplicateClass,
    _score_candidate,
    check_duplicate_tickets,
    classify_duplicate,
    normalize_ticket_text,
    ticket_fingerprint,
)


def make_ticket(title: str, description: str, status: TicketStatus = TicketStatus.RESOLVED) -> Ticket:
    return Ticket(
        id=100, ticket_number="INC-0100", title=title, description=description,
        submitter_id=1, status=status, created_at=datetime.now(UTC),
        suggested_solution="Reset VPN profile.", resolution_summary="Reset VPN profile.",
    )


def test_normalized_payload_detects_exact_duplicate():
    original = make_ticket("[VPN] Không kết nối được VPN", "Lỗi VPN mã lỗi 809 khi làm việc từ xa")
    score, method, title_score = _score_candidate(
        "[VPN] KHONG ket noi duoc VPN", "Loi VPN ma loi 809 khi lam viec tu xa", original, 0.99
    )

    assert score == 1.0
    assert method == "exact_normalized_payload"
    assert title_score == 1.0
    assert classify_duplicate(score, exact=True) == DuplicateClass.EXACT


def test_semantic_hybrid_uses_error_code_and_service_context():
    existing = make_ticket("[VPN Network] SSL VPN FortiClient failed", "Error code 809 from remote WFH")
    score, method, _ = _score_candidate(
        "[VPN Network] Cannot connect SSL VPN", "FortiClient error code 809 while remote", existing, 0.91
    )

    assert method == "semantic_vector_hybrid"
    assert score >= 0.62
    assert classify_duplicate(score) in {DuplicateClass.SEMANTIC, DuplicateClass.POSSIBLE}


def test_low_similarity_is_not_duplicate():
    existing = make_ticket("[Email] Outlook cannot send", "Mail profile error")
    score, _, _ = _score_candidate("[Hardware] Broken monitor", "Display cable has no signal", existing, 0.05)

    assert classify_duplicate(score) == DuplicateClass.NOT
    assert ticket_fingerprint("A", "B") != ticket_fingerprint("A", "C")
    assert normalize_ticket_text("VPN  —  LỖI!") == "vpn loi"


def test_shared_form_metadata_does_not_override_different_symptoms():
    existing = make_ticket(
        "[VPN] Ứng dụng bị treo",
        "[Hệ Thống / Dịch Vụ: SSL VPN FortiClient]\n--- MÔ TẢ CHI TIẾT SỰ CỐ ---\nFortiClient treo khi kết nối VPN.",
        status=TicketStatus.IN_PROGRESS,
    )
    score, method, _ = _score_candidate(
        "[VPN] Màn hình đen",
        "[Hệ Thống / Dịch Vụ: SSL VPN FortiClient]\n--- MÔ TẢ CHI TIẾT SỰ CỐ ---\nBật máy có tiếng nổ rồi màn hình chuyển đen.",
        existing,
        0.98,
    )

    assert score == 0.0
    assert method == "insufficient_symptom_overlap"


class FakeCollection:
    def query(self, **_: object) -> dict:
        return {
            "metadatas": [[
                {"ticket_id": 501, "company_unit": "real_estate", "department": "Sales", "fingerprint": "not-exact"},
                {"ticket_id": 999, "company_unit": "healthcare", "department": "ICU", "fingerprint": "not-exact"},
            ]],
            "distances": [[0.08, 0.01]],
        }


@pytest.mark.asyncio
async def test_duplicate_lookup_enforces_company_and_department_isolation():
    async with AsyncSessionLocal() as db:
        user = await db.get(User, 1)
        assert user is not None
        ticket = Ticket(
            id=501, ticket_number="INC-0501", title="[VPN] Cannot connect", description="SSL VPN error 809",
            submitter_id=user.id, status=TicketStatus.IN_PROGRESS, created_at=datetime.now(UTC),
        )
        db.add(ticket)
        await db.commit()
        with (
            patch("src.services.duplicate_detection_service.get_ticket_duplicate_collection", return_value=FakeCollection()),
            patch("src.services.duplicate_detection_service.embed_query", return_value=[0.0] * 384),
        ):
            check = await check_duplicate_tickets(db, "[VPN] Cannot connect", "SSL VPN error 809", user)

    assert len(check.matches) == 1
    assert check.matches[0].ticket.id == 501
    assert check.matches[0].is_active is True
