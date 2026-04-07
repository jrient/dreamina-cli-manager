# backend/tests/test_accounts.py
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_list_accounts_empty(client, tmp_path, monkeypatch):
    monkeypatch.setattr("config.ACCOUNTS_DIR", tmp_path)
    import routers.accounts as acc_router
    monkeypatch.setattr(acc_router, "ACCOUNTS_DIR", tmp_path)
    resp = await client.get("/api/accounts")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_accounts_with_files(client, tmp_path, monkeypatch):
    (tmp_path / "alice.json").write_text("{}")
    (tmp_path / "bob.json").write_text("{}")
    import routers.accounts as acc_router
    monkeypatch.setattr(acc_router, "ACCOUNTS_DIR", tmp_path)
    resp = await client.get("/api/accounts")
    assert resp.status_code == 200
    ids = {a["id"] for a in resp.json()}
    assert ids == {"alice", "bob"}