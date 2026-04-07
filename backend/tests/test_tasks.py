# backend/tests/test_tasks.py
import pytest
import json
from unittest.mock import patch, AsyncMock
from io import BytesIO


@pytest.mark.asyncio
async def test_submit_task_no_files(client):
    resp = await client.post("/api/tasks", data={
        "account_id": "alice",
        "duration": "5",
        "ratio": "16:9",
        "model_version": "seedance2.0fast",
    })
    assert resp.status_code == 422  # must have at least one image or video


@pytest.mark.asyncio
async def test_submit_task_success(client, tmp_path, monkeypatch):
    import routers.tasks as task_router
    monkeypatch.setattr("config.ACCOUNTS_DIR", tmp_path)
    monkeypatch.setattr("config.UPLOAD_DIR", tmp_path / "uploads")
    (tmp_path / "uploads").mkdir()
    (tmp_path / "alice.json").write_text("{}")

    with patch("routers.tasks.submit_multimodal2video", new_callable=AsyncMock) as mock_submit:
        mock_submit.return_value = "abc123def456"
        img_bytes = b"\x89PNG\r\n" + b"\x00" * 20  # fake PNG header

        resp = await client.post(
            "/api/tasks",
            data={
                "account_id": "alice",
                "duration": "5",
                "ratio": "16:9",
                "model_version": "seedance2.0fast",
                "prompt": "test prompt",
            },
            files={"images": ("test.png", BytesIO(img_bytes), "image/png")},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == "abc123def456"
    assert body["status"] == "pending"
    assert body["account_id"] == "alice"


@pytest.mark.asyncio
async def test_list_tasks_empty(client):
    resp = await client.get("/api/tasks")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_delete_task(client, tmp_path, monkeypatch):
    import aiosqlite
    from database import get_db
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()

    # Insert a task directly
    import database
    async with aiosqlite.connect(str(database.DB_PATH)) as db:
        await db.execute(
            "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("task1", "alice", "success", "submit1", "http://example.com/v.mp4", None, "p", "{}", now, now)
        )
        await db.commit()

    resp = await client.delete("/api/tasks/task1")
    assert resp.status_code == 204

    resp2 = await client.get("/api/tasks/task1")
    assert resp2.status_code == 404