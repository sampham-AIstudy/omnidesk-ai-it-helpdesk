"""Shared test fixtures cho toàn bộ test suite."""
import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient

# Set test DB before importing app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test.db"

from src.main import app, _seed_demo_users, _seed_knowledge_base
from src.database import engine, Base, AsyncSessionLocal


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    """Tự động init DB và seed users/KB trước khi chạy test suite."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        await _seed_demo_users(db)
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
async def auth_manager(client):
    """Fixture: đăng nhập manager, trả về token."""
    resp = await client.post("/api/v1/auth/login", json={"username": "manager1", "password": "demo123"})
    if resp.status_code != 200:
        return None
    return resp.json()["access_token"]


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
