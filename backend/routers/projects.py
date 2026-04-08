# backend/routers/projects.py
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from config import DB_PATH, MATERIALS_DIR
from models import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectStats,
    MaterialCreate, MaterialUpdate, MaterialResponse
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_project(row) -> ProjectResponse:
    return ProjectResponse(
        id=row["id"],
        name=row["name"],
        deleted_at=row["deleted_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_material(row) -> MaterialResponse:
    return MaterialResponse(
        id=row["id"],
        project_id=row["project_id"],
        name=row["name"],
        type=row["type"],
        file_path=row["file_path"],
        created_at=row["created_at"],
    )


# ==================== 项目 API ====================

@router.get("", response_model=list[ProjectResponse])
async def list_projects(include_deleted: bool = False):
    """获取活跃项目列表"""
    query = "SELECT * FROM projects"
    if not include_deleted:
        query += " WHERE deleted_at IS NULL"
    query += " ORDER BY updated_at DESC"

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query)
        rows = await cursor.fetchall()

    return [_row_to_project(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProjectResponse)
async def create_project(data: ProjectCreate):
    """创建项目"""
    project_id = uuid.uuid4().hex[:12]
    now = _now()

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "INSERT INTO projects (id, name, deleted_at, created_at, updated_at) VALUES (?, ?, NULL, ?, ?)",
            (project_id, data.name, now, now),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM projects WHERE id=?", (project_id,))
        row = await cursor.fetchone()

    return _row_to_project(row)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """获取单个项目"""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM projects WHERE id=?", (project_id,))
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(404, "项目不存在")
    return _row_to_project(row)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, data: ProjectUpdate):
    """更新项目名称"""
    now = _now()

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM projects WHERE id=?", (project_id,))
        if not await cursor.fetchone():
            raise HTTPException(404, "项目不存在")
        await db.execute(
            "UPDATE projects SET name=?, updated_at=? WHERE id=?",
            (data.name, now, project_id),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM projects WHERE id=?", (project_id,))
        row = await cursor.fetchone()

    return _row_to_project(row)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str, permanent: bool = False):
    """软删除或永久删除项目"""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM projects WHERE id=?", (project_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, "项目不存在")

        if permanent:
            # 永久删除：先删除素材，再删除项目
            cursor = await db.execute("SELECT file_path FROM materials WHERE project_id=?", (project_id,))
            materials = await cursor.fetchall()
            for m in materials:
                file_path = Path(m["file_path"])
                if file_path.exists():
                    file_path.unlink()
            await db.execute("DELETE FROM materials WHERE project_id=?", (project_id,))
            await db.execute("DELETE FROM projects WHERE id=?", (project_id,))
        else:
            # 软删除
            now = _now()
            await db.execute(
                "UPDATE projects SET deleted_at=?, updated_at=? WHERE id=?",
                (now, now, project_id),
            )
        await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{project_id}/restore", response_model=ProjectResponse)
async def restore_project(project_id: str):
    """恢复已删除的项目"""
    now = _now()

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM projects WHERE id=?", (project_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, "项目不存在")
        if row["deleted_at"] is None:
            raise HTTPException(400, "项目未被删除")

        await db.execute(
            "UPDATE projects SET deleted_at=NULL, updated_at=? WHERE id=?",
            (now, project_id),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM projects WHERE id=?", (project_id,))
        row = await cursor.fetchone()

    return _row_to_project(row)


@router.get("/{project_id}/stats", response_model=ProjectStats)
async def get_project_stats(project_id: str):
    """获取项目统计"""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        # 检查项目存在
        cursor = await db.execute("SELECT id FROM projects WHERE id=?", (project_id,))
        if not await cursor.fetchone():
            raise HTTPException(404, "项目不存在")

        # 统计任务数
        cursor = await db.execute("SELECT COUNT(*) as count FROM tasks WHERE project_id=?", (project_id,))
        task_row = await cursor.fetchone()
        task_count = task_row["count"]

        # 统计素材数
        cursor = await db.execute("SELECT COUNT(*) as count FROM materials WHERE project_id=?", (project_id,))
        material_row = await cursor.fetchone()
        material_count = material_row["count"]

    return ProjectStats(task_count=task_count, material_count=material_count)


# ==================== 素材 API ====================

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac"}


@router.get("/{project_id}/materials", response_model=list[MaterialResponse])
async def list_materials(project_id: str, type: Optional[str] = None):
    """获取项目素材列表"""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        # 检查项目存在
        cursor = await db.execute("SELECT id FROM projects WHERE id=?", (project_id,))
        if not await cursor.fetchone():
            raise HTTPException(404, "项目不存在")

        query = "SELECT * FROM materials WHERE project_id=?"
        params = [project_id]
        if type:
            query += " AND type=?"
            params.append(type)
        query += " ORDER BY created_at DESC"

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

    return [_row_to_material(r) for r in rows]


@router.post("/{project_id}/materials", status_code=status.HTTP_201_CREATED, response_model=MaterialResponse)
async def create_material(
    project_id: str,
    name: str = Form(...),
    type: str = Form(...),
    file: UploadFile = File(...),
):
    """上传素材"""
    if type not in ("image", "audio"):
        raise HTTPException(400, "素材类型必须是 image 或 audio")

    # 检查文件扩展名
    ext = Path(file.filename).suffix.lower()
    if type == "image" and ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(400, f"图片格式不支持，允许: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}")
    if type == "audio" and ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(400, f"音频格式不支持，允许: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}")

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        # 检查项目存在且未删除
        cursor = await db.execute(
            "SELECT id FROM projects WHERE id=? AND deleted_at IS NULL",
            (project_id,)
        )
        if not await cursor.fetchone():
            raise HTTPException(404, "项目不存在或已被删除")

    # 保存文件
    material_id = uuid.uuid4().hex[:12]
    file_path = MATERIALS_DIR / f"{material_id}{ext}"
    content = await file.read()
    file_path.write_bytes(content)

    now = _now()

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "INSERT INTO materials (id, project_id, name, type, file_path, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (material_id, project_id, name, type, str(file_path), now),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM materials WHERE id=?", (material_id,))
        row = await cursor.fetchone()

    return _row_to_material(row)


@router.put("/{project_id}/materials/{material_id}", response_model=MaterialResponse)
async def update_material(project_id: str, material_id: str, data: MaterialUpdate):
    """更新素材名称"""
    now = _now()

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM materials WHERE id=? AND project_id=?",
            (material_id, project_id)
        )
        if not await cursor.fetchone():
            raise HTTPException(404, "素材不存在")

        await db.execute(
            "UPDATE materials SET name=? WHERE id=?",
            (data.name, material_id),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM materials WHERE id=?", (material_id,))
        row = await cursor.fetchone()

    return _row_to_material(row)


@router.delete("/{project_id}/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(project_id: str, material_id: str):
    """删除素材"""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM materials WHERE id=? AND project_id=?",
            (material_id, project_id)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, "素材不存在")

        # 删除文件
        file_path = Path(row["file_path"])
        if file_path.exists():
            file_path.unlink()

        await db.execute("DELETE FROM materials WHERE id=?", (material_id,))
        await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)