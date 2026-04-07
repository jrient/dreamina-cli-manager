# backend/tests/conftest.py
import pytest
import pytest_asyncio
import aiosqlite
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock


@pytest_asyncio.fixture
async def test_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("database.DB_PATH", db_path)
    monkeypatch.setattr("config.DB_PATH", db_path)
    import database
    database.DB_PATH = db_path
    await database.init_db()
    return db_path


@pytest.fixture
def mock_dreamina():
    """Mock subprocess calls to dreamina CLI."""
    with patch("services.dreamina.run_cli") as mock:
        yield mock


@pytest_asyncio.fixture
async def client(test_db):
    from main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac