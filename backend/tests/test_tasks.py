# backend/tests/test_tasks.py
import pytest
import pytest_asyncio
import json
import aiosqlite
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from io import BytesIO


@pytest_asyncio.fixture
async def test_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("database.DB_PATH", db_path)
    monkeypatch.setattr("config.DB_PATH", db_path)
    import database
    database.DB_PATH = db_path
    await database.init_db()
    return db_path


@pytest_asyncio.fixture
async def client(test_db):
    from main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def sample_project(client):
    """创建一个测试项目"""
    resp = await client.post("/api/projects", json={"name": "测试项目"})
    return resp.json()["id"]


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
async def test_submit_task_with_project_and_label(client, tmp_path, monkeypatch, sample_project):
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
                "project_id": sample_project,
                "label": "测试标签",
            },
            files={"images": ("test.png", BytesIO(img_bytes), "image/png")},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == "abc123def456"
    assert body["status"] == "pending"
    assert body["account_id"] == "alice"
    assert body["project_id"] == sample_project
    assert body["label"] == "测试标签"


@pytest.mark.asyncio
async def test_list_tasks_empty(client):
    resp = await client.get("/api/tasks")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_tasks_by_project(client, sample_project):
    import database
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    # 插入两个任务，一个关联项目
    async with aiosqlite.connect(str(database.DB_PATH)) as db:
        await db.execute(
            "INSERT INTO tasks (id, account_id, status, prompt, params, created_at, updated_at, project_id, label) VALUES (?,?,?,?,?,?,?,?,?)",
            ("task1", "alice", "success", "p1", "{}", now, now, sample_project, "标签1")
        )
        await db.execute(
            "INSERT INTO tasks (id, account_id, status, prompt, params, created_at, updated_at, project_id, label) VALUES (?,?,?,?,?,?,?,?,?)",
            ("task2", "bob", "success", "p2", "{}", now, now, None, None)
        )
        await db.commit()

    # 按项目筛选
    resp = await client.get(f"/api/tasks?project_id={sample_project}")
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == 1
    assert tasks[0]["id"] == "task1"
    assert tasks[0]["project_id"] == sample_project
    assert tasks[0]["label"] == "标签1"


@pytest.mark.asyncio
async def test_copy_task(client, tmp_path, monkeypatch):
    import database
    from datetime import datetime, timezone
    import shutil

    now = datetime.now(timezone.utc).isoformat()
    monkeypatch.setattr("config.UPLOAD_DIR", tmp_path / "uploads")
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()

    # 创建原任务的文件目录
    original_task_dir = uploads_dir / "task1"
    original_task_dir.mkdir()
    (original_task_dir / "image1.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    # 插入原任务
    params = json.dumps({
        "duration": 5,
        "ratio": "16:9",
        "model_version": "seedance2.0fast",
        "image_paths": [str(original_task_dir / "image1.jpg")],
        "video_paths": [],
        "audio_paths": [],
    })

    async with aiosqlite.connect(str(database.DB_PATH)) as db:
        await db.execute(
            "INSERT INTO tasks (id, account_id, status, prompt, params, created_at, updated_at, project_id, label) VALUES (?,?,?,?,?,?,?,?,?)",
            ("task1", "alice", "success", "原始提示词", params, now, now, None, "原始标签")
        )
        await db.commit()

    # 复制任务
    resp = await client.post("/api/tasks/task1/copy")
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] != "task1"  # 新 ID
    assert body["account_id"] == "alice"
    assert body["prompt"] == "原始提示词"
    assert body["label"] == "原始标签"
    assert body["status"] == "queued"

    # 验证新任务的文件已复制
    new_task_dir = uploads_dir / body["id"]
    assert new_task_dir.exists()
    assert (new_task_dir / "image1.jpg").exists()


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
            "INSERT INTO tasks (id, account_id, status, submit_id, result_url, error_msg, prompt, params, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("task1", "alice", "success", "submit1", "http://example.com/v.mp4", None, "p", "{}", now, now)
        )
        await db.commit()

    resp = await client.delete("/api/tasks/task1")
    assert resp.status_code == 204

    resp2 = await client.get("/api/tasks/task1")
    assert resp2.status_code == 404