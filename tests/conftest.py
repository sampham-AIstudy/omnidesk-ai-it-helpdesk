"""Shared test fixtures cho toàn bộ test suite."""
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src._test_environment import TEST_RUN_ID
from src.data.knowledge_base import get_all_kb_entries
from src.database import AsyncSessionLocal, Base, engine
from src.main import _seed_demo_users, _seed_knowledge_base, app

TEST_DATASTORE_RUN_ID = TEST_RUN_ID


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    """Tự động init DB và seed users/KB trước khi chạy test suite."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    from src.services.rag_service import get_chroma_client
    chroma_client = get_chroma_client()
    for collection_name in ("helpdesk_ticket_duplicates_v1", "helpdesk_episodic_memory_v1"):
        try:
            chroma_client.delete_collection(collection_name)
        except Exception:
            pass

    async with AsyncSessionLocal() as db:
        await _seed_demo_users(db)
        indexed_ids = {entry["id"] for entry in get_all_kb_entries()}
        with patch(
            "src.services.rag_service.get_indexed_document_ids",
            return_value=indexed_ids,
        ):
            await _seed_knowledge_base(db)


@pytest_asyncio.fixture
async def client():
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_employee(client):
    """Fixture: đăng nhập employee, trả về token."""
    resp = await client.post("/api/v1/auth/login", json={"username": "employee1", "password": "demo123"})
    if resp.status_code != 200:
        return None
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def auth_technician(client):
    """Login the operational Technician fixture."""
    resp = await client.post("/api/v1/auth/login", json={"username": "tech1", "password": "demo123"})
    return resp.json()["access_token"] if resp.status_code == 200 else None


@pytest_asyncio.fixture
async def auth_admin(client):
    """Fixture: login admin and return JWT token."""
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    if resp.status_code != 200:
        return None
    return resp.json()["access_token"]


@pytest.fixture
def mock_llm():
    """Mock LLM để tránh gọi API thật trong tests."""
    mock = AsyncMock()
    mock.ainvoke.return_value = AsyncMock(
        content='{"category":"software","priority":"medium","urgency":"medium","confidence":0.88,"reasoning":"Mock test","is_production_impact":false,"suggested_routing_team":"IT Support"}'
    )
    mock.model = "mistral-mock"
    return mock
