# backend/tests/test_projects.py
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


@pytest_asyncio.fixture
async def client(test_db):
    from main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ==================== 项目 API 测试 ====================

@pytest.mark.asyncio
async def test_list_projects_empty(client):
    resp = await client.get("/api/projects")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_project(client):
    resp = await client.post("/api/projects", json={"name": "测试项目"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "测试项目"
    assert body["id"]
    assert body["deleted_at"] is None


@pytest.mark.asyncio
async def test_get_project(client):
    # 先创建项目
    create_resp = await client.post("/api/projects", json={"name": "获取测试"})
    project_id = create_resp.json()["id"]

    # 获取项目
    resp = await client.get(f"/api/projects/{project_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "获取测试"


@pytest.mark.asyncio
async def test_update_project(client):
    # 先创建项目
    create_resp = await client.post("/api/projects", json={"name": "更新测试"})
    project_id = create_resp.json()["id"]

    # 更新项目
    resp = await client.put(f"/api/projects/{project_id}", json={"name": "更新后名称"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "更新后名称"


@pytest.mark.asyncio
async def test_delete_project_soft(client):
    # 先创建项目
    create_resp = await client.post("/api/projects", json={"name": "删除测试"})
    project_id = create_resp.json()["id"]

    # 软删除项目
    resp = await client.delete(f"/api/projects/{project_id}")
    assert resp.status_code == 204

    # 验证不在活跃列表
    list_resp = await client.get("/api/projects")
    active_projects = [p for p in list_resp.json() if p["id"] == project_id]
    assert len(active_projects) == 0

    # 验证在已删除列表
    deleted_resp = await client.get("/api/projects?include_deleted=true")
    deleted_projects = [p for p in deleted_resp.json() if p["id"] == project_id]
    assert len(deleted_projects) == 1
    assert deleted_projects[0]["deleted_at"] is not None


@pytest.mark.asyncio
async def test_restore_project(client):
    # 先创建并删除项目
    create_resp = await client.post("/api/projects", json={"name": "恢复测试"})
    project_id = create_resp.json()["id"]
    await client.delete(f"/api/projects/{project_id}")

    # 恢复项目
    resp = await client.post(f"/api/projects/{project_id}/restore")
    assert resp.status_code == 200
    assert resp.json()["deleted_at"] is None


@pytest.mark.asyncio
async def test_delete_project_permanent(client):
    # 先创建并软删除项目
    create_resp = await client.post("/api/projects", json={"name": "永久删除测试"})
    project_id = create_resp.json()["id"]
    await client.delete(f"/api/projects/{project_id}")

    # 永久删除
    resp = await client.delete(f"/api/projects/{project_id}?permanent=true")
    assert resp.status_code == 204

    # 验证完全不存在
    deleted_resp = await client.get("/api/projects?include_deleted=true")
    projects = [p for p in deleted_resp.json() if p["id"] == project_id]
    assert len(projects) == 0


@pytest.mark.asyncio
async def test_get_project_stats(client):
    # 先创建项目
    create_resp = await client.post("/api/projects", json={"name": "统计测试"})
    project_id = create_resp.json()["id"]

    resp = await client.get(f"/api/projects/{project_id}/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["task_count"] == 0
    assert body["material_count"] == 0


@pytest.mark.asyncio
async def test_project_not_found(client):
    resp = await client.get("/api/projects/nonexistent")
    assert resp.status_code == 404


# ==================== 素材 API 测试 ====================

@pytest.mark.asyncio
async def test_list_materials_empty(client):
    # 先创建项目
    create_resp = await client.post("/api/projects", json={"name": "素材测试"})
    project_id = create_resp.json()["id"]

    resp = await client.get(f"/api/projects/{project_id}/materials")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_image_material(client):
    # 先创建项目
    create_resp = await client.post("/api/projects", json={"name": "图片素材"})
    project_id = create_resp.json()["id"]

    # 创建图片素材
    from io import BytesIO
    img_bytes = b"\x89PNG\r\n" + b"\x00" * 100  # fake PNG header

    resp = await client.post(
        f"/api/projects/{project_id}/materials",
        data={"name": "测试图片", "type": "image"},
        files={"file": ("test.png", BytesIO(img_bytes), "image/png")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "测试图片"
    assert body["type"] == "image"
    assert body["file_path"]


@pytest.mark.asyncio
async def test_create_audio_material(client):
    # 先创建项目
    create_resp = await client.post("/api/projects", json={"name": "音频素材"})
    project_id = create_resp.json()["id"]

    # 创建音频素材
    from io import BytesIO
    audio_bytes = b"\x00" * 100  # fake audio

    resp = await client.post(
        f"/api/projects/{project_id}/materials",
        data={"name": "测试音频", "type": "audio"},
        files={"file": ("test.mp3", BytesIO(audio_bytes), "audio/mpeg")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "测试音频"
    assert body["type"] == "audio"


@pytest.mark.asyncio
async def test_list_materials_by_type(client):
    # 先创建项目
    create_resp = await client.post("/api/projects", json={"name": "分类素材"})
    project_id = create_resp.json()["id"]

    # 创建图片和音频
    from io import BytesIO
    await client.post(
        f"/api/projects/{project_id}/materials",
        data={"name": "图片1", "type": "image"},
        files={"file": ("img.png", BytesIO(b"\x89PNG"), "image/png")},
    )
    await client.post(
        f"/api/projects/{project_id}/materials",
        data={"name": "音频1", "type": "audio"},
        files={"file": ("aud.mp3", BytesIO(b"\x00"), "audio/mpeg")},
    )

    # 按类型筛选
    img_resp = await client.get(f"/api/projects/{project_id}/materials?type=image")
    assert len(img_resp.json()) == 1

    aud_resp = await client.get(f"/api/projects/{project_id}/materials?type=audio")
    assert len(aud_resp.json()) == 1


@pytest.mark.asyncio
async def test_update_material(client):
    # 先创建项目和素材
    create_resp = await client.post("/api/projects", json={"name": "更新素材"})
    project_id = create_resp.json()["id"]
    from io import BytesIO
    mat_resp = await client.post(
        f"/api/projects/{project_id}/materials",
        data={"name": "原名称", "type": "image"},
        files={"file": ("test.png", BytesIO(b"\x89PNG"), "image/png")},
    )
    material_id = mat_resp.json()["id"]

    # 更新素材
    resp = await client.put(
        f"/api/projects/{project_id}/materials/{material_id}",
        json={"name": "新名称"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "新名称"


@pytest.mark.asyncio
async def test_delete_material(client):
    # 先创建项目和素材
    create_resp = await client.post("/api/projects", json={"name": "删除素材"})
    project_id = create_resp.json()["id"]
    from io import BytesIO
    mat_resp = await client.post(
        f"/api/projects/{project_id}/materials",
        data={"name": "待删除", "type": "image"},
        files={"file": ("test.png", BytesIO(b"\x89PNG"), "image/png")},
    )
    material_id = mat_resp.json()["id"]

    # 删除素材
    resp = await client.delete(f"/api/projects/{project_id}/materials/{material_id}")
    assert resp.status_code == 204

    # 验证已删除
    list_resp = await client.get(f"/api/projects/{project_id}/materials")
    materials = [m for m in list_resp.json() if m["id"] == material_id]
    assert len(materials) == 0


@pytest.mark.asyncio
async def test_material_invalid_type(client):
    # 先创建项目
    create_resp = await client.post("/api/projects", json={"name": "无效类型"})
    project_id = create_resp.json()["id"]

    from io import BytesIO
    resp = await client.post(
        f"/api/projects/{project_id}/materials",
        data={"name": "无效", "type": "video"},
        files={"file": ("test.mp4", BytesIO(b"\x00"), "video/mp4")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_material_project_not_found(client):
    from io import BytesIO
    resp = await client.post(
        "/api/projects/nonexistent/materials",
        data={"name": "测试", "type": "image"},
        files={"file": ("test.png", BytesIO(b"\x89PNG"), "image/png")},
    )
    assert resp.status_code == 404