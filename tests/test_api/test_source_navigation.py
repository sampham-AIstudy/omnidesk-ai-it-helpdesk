from unittest.mock import patch

import pytest

from tests.test_api.test_employee_security import _create_employee_ticket


@pytest.mark.asyncio
async def test_source_reader_opens_exact_acl_checked_provenance(client, auth_employee):
    document = {
        "doc_id": "historical-2047",
        "content": "Resolved VPN lesson content.",
        "metadata": {
            "title": "KB bài học từ Ticket #INC-20260810-2047",
            "category": "network",
            "solution": "Use the approved VPN reset procedure.",
        },
    }
    with patch("src.api.chat.get_document_by_id", return_value=document) as get_source:
        response = await client.get(
            "/api/v1/chat/sources/historical-2047",
            headers={"Authorization": f"Bearer {auth_employee}"},
        )

    assert response.status_code == 200
    assert response.json()["source_id"] == "historical-2047"
    assert response.json()["title"] == "KB bài học từ Ticket #INC-20260810-2047"
    get_source.assert_called_once()


@pytest.mark.asyncio
async def test_legacy_source_label_resolves_to_real_rag_document(client, auth_employee):
    document = {
        "doc_id": "historical-2047",
        "content": "Resolved VPN lesson content.",
        "metadata": {"title": "KB bài học từ Ticket #INC-20260810-2047"},
    }
    with patch("src.api.chat.get_document_by_title", return_value=document):
        response = await client.get(
            "/api/v1/chat/sources",
            params={"label": "KB bài học từ Ticket #INC-20260810-2047"},
            headers={"Authorization": f"Bearer {auth_employee}"},
        )

    assert response.status_code == 200
    assert response.json()["source_id"] == "historical-2047"


@pytest.mark.asyncio
async def test_ticket_reference_resolves_to_exact_authorized_ticket(client, auth_employee):
    ticket_id = await _create_employee_ticket()
    ticket = await client.get(
        f"/api/v1/tickets/{ticket_id}", headers={"Authorization": f"Bearer {auth_employee}"}
    )
    response = await client.get(
        f"/api/v1/tickets/resolve/{ticket.json()['ticket_number']}",
        headers={"Authorization": f"Bearer {auth_employee}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == ticket_id
