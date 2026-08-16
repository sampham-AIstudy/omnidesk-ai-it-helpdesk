"""Tests for Chatbot Workspace new conversation flow and isolation.

Verifies:
- CHAT-NEW-01: Single POST /chat/conversations returns unique ID, active conversation metadata, empty messages.
- CHAT-NEW-02: Concurrent/rapid creation returns distinct IDs without cross-pollution.
- CHAT-NEW-03: Multiple conversation creations produce distinct isolated containers.
- CHAT-NEW-04: Conversation details fetch returns only messages belonging to that conversation.
- CHAT-NEW-05: New conversation starts with empty message history.
- CHAT-NEW-06: Listing conversations returns the newly created conversation in user history.
"""
from __future__ import annotations

import asyncio
import pytest
from httpx import AsyncClient


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_chat_new_01_single_creation_returns_active_conversation(
    client: AsyncClient, auth_employee: str
) -> None:
    """CHAT-NEW-01: Single call creates exactly one conversation and returns id immediately."""
    response = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Cuộc trò chuyện mới"},
        headers=_headers(auth_employee),
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "id" in data
    assert data["title"] == "Cuộc trò chuyện mới"
    assert data["messages"] == []


@pytest.mark.asyncio
async def test_chat_new_02_and_03_rapid_double_creation_creates_distinct_conversations(
    client: AsyncClient, auth_employee: str
) -> None:
    """CHAT-NEW-02 & CHAT-NEW-03: Rapid calls create distinct conversations without collision."""
    resp1, resp2 = await asyncio.gather(
        client.post("/api/v1/chat/conversations", json={"title": "Chat 1"}, headers=_headers(auth_employee)),
        client.post("/api/v1/chat/conversations", json={"title": "Chat 2"}, headers=_headers(auth_employee)),
    )
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    id1 = resp1.json()["id"]
    id2 = resp2.json()["id"]
    assert id1 != id2


@pytest.mark.asyncio
async def test_chat_new_04_and_05_new_conversation_has_clean_empty_history(
    client: AsyncClient, auth_employee: str
) -> None:
    """CHAT-NEW-04 & CHAT-NEW-05: New conversation does not leak messages from previous conversation."""
    # Create conversation 1
    resp1 = await client.post(
        "/api/v1/chat/conversations", json={"title": "First Conv"}, headers=_headers(auth_employee)
    )
    id1 = resp1.json()["id"]

    # Create conversation 2
    resp2 = await client.post(
        "/api/v1/chat/conversations", json={"title": "Second Conv"}, headers=_headers(auth_employee)
    )
    id2 = resp2.json()["id"]

    # Verify conversation 2 is completely empty
    detail2 = await client.get(f"/api/v1/chat/conversations/{id2}", headers=_headers(auth_employee))
    assert detail2.status_code == 200
    assert detail2.json()["messages"] == []


@pytest.mark.asyncio
async def test_chat_new_06_refetch_contains_new_conversation_without_overwriting(
    client: AsyncClient, auth_employee: str
) -> None:
    """CHAT-NEW-06: Refetched list contains newly created conversation."""
    created = await client.post(
        "/api/v1/chat/conversations", json={"title": "Persistent Check"}, headers=_headers(auth_employee)
    )
    new_id = created.json()["id"]

    list_resp = await client.get("/api/v1/chat/conversations", headers=_headers(auth_employee))
    assert list_resp.status_code == 200
    ids = [item["id"] for item in list_resp.json()]
    assert new_id in ids
