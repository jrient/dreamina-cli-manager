# backend/routers/projects.py
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite
from fastapi import APIRouter, Cookie, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel

from config import DB_PATH, MATERIALS_DIR
from models import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectStats,
    MaterialCreate, MaterialUpdate, MaterialResponse,
    MemberAdd, MemberResponse, AccountAssignment, ProjectSettingsUpdate
)
from services.auth import get_session, get_user_by_id

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
        episode_count=row["episode_count"] if "episode_count" in row.keys() else 50,
        creator_id=row["creator_id"] if "creator_id" in row.keys() else None,
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


async def get_current_user_or_admin(session_id: str = None):
    """获取当前用户，验证登录状态"""
    if not session_id:
        raise HTTPException(401, "未登录")

    session = get_session(session_id)
    if not session:
        raise HTTPException(401, "登录已过期")

    user = await get_user_by_id(session["user_id"])
    if not user:
        raise HTTPException(401, "用户不存在")

    return {
        "id": user["id"],
        "username": user["username"],
        "is_admin": bool(user["is_admin"])
    }


async def check_project_access(project_id: str, user: dict, require_owner: bool = False):
    """检查项目访问权限"""
    if user["is_admin"]:
        return True

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT role FROM project_members WHERE project_id=? AND user_id=?",
            (project_id, user["id"])
        )
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(403, "无权限访问此项目")

        if require_owner and row["role"] != "owner":
            raise HTTPException(403, "需要项目拥有者权限")

        return True


# ==================== 项目 API ====================

@router.get("", response_model=list[ProjectResponse])
async def list_projects(include_deleted: bool = False, session_id: str = Cookie(None)):
    """获取项目列表（根据用户权限过滤）"""
    user = await get_current_user_or_admin(session_id)

    query = "SELECT p.* FROM projects p"
    params = []

    if not user["is_admin"]:
        # 非管理员只看参与的项目
        query += " JOIN project_members pm ON p.id = pm.project_id WHERE pm.user_id=?"
        params.append(user["id"])

        if not include_deleted:
            query += " AND p.deleted_at IS NULL"
    else:
        if not include_deleted:
            query += " WHERE p.deleted_at IS NULL"

    query += " ORDER BY p.updated_at DESC"

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            p = _row_to_project(r)
            if user["is_admin"]:
                p.my_role = "owner"
            else:
                rc = await db.execute(
                    "SELECT role FROM project_members WHERE project_id=? AND user_id=?",
                    (r["id"], user["id"])
                )
                mr = await rc.fetchone()
                p.my_role = mr["role"] if mr else None
            # 查询 owner 用户名
            oc = await db.execute(
                """SELECT u.username FROM project_members pm
                   JOIN users u ON pm.user_id = u.id
                   WHERE pm.project_id=? AND pm.role='owner' LIMIT 1""",
                (r["id"],)
            )
            owner = await oc.fetchone()
            p.creator_name = owner["username"] if owner else None
            result.append(p)

    return result


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProjectResponse)
async def create_project(data: ProjectCreate, session_id: str = Cookie(None)):
    """创建项目"""
    user = await get_current_user_or_admin(session_id)

    project_id = uuid.uuid4().hex[:12]
    now = _now()

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        # 创建项目
        await db.execute(
            "INSERT INTO projects (id, name, deleted_at, created_at, updated_at, episode_count, creator_id) VALUES (?, ?, NULL, ?, ?, 50, ?)",
            (project_id, data.name, now, now, user["id"]),
        )
        # 创建者成为项目拥有者
        await db.execute(
            "INSERT INTO project_members (project_id, user_id, role, created_at) VALUES (?, ?, 'owner', ?)",
            (project_id, user["id"], now),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM projects WHERE id=?", (project_id,))
        row = await cursor.fetchone()

    return _row_to_project(row)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, session_id: str = Cookie(None)):
    """获取单个项目"""
    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user)

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM projects WHERE id=?", (project_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, "项目不存在")

        if user["is_admin"]:
            my_role = "owner"
        else:
            rc = await db.execute(
                "SELECT role FROM project_members WHERE project_id=? AND user_id=?",
                (project_id, user["id"])
            )
            mr = await rc.fetchone()
            my_role = mr["role"] if mr else None

    p = _row_to_project(row)
    p.my_role = my_role
    return p


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, data: ProjectUpdate, session_id: str = Cookie(None)):
    """更新项目名称"""
    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user, require_owner=True)

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
async def delete_project(project_id: str, permanent: bool = False, session_id: str = Cookie(None)):
    """软删除或永久删除项目"""
    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user, require_owner=True)

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
async def restore_project(project_id: str, session_id: str = Cookie(None)):
    """恢复已删除的项目"""
    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user, require_owner=True)

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
async def get_project_stats(project_id: str, session_id: str = Cookie(None)):
    """获取项目统计"""
    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user)

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


# ==================== 成员管理 API ====================

@router.get("/{project_id}/members", response_model=list[MemberResponse])
async def list_project_members(project_id: str, session_id: str = Cookie(None)):
    """获取项目成员列表"""
    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user)

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        # 获取成员列表
        cursor = await db.execute(
            """SELECT pm.user_id, pm.role, u.username, u.deleted_at
               FROM project_members pm
               JOIN users u ON pm.user_id = u.id
               WHERE pm.project_id=?""",
            (project_id,)
        )
        members = await cursor.fetchall()

        result = []
        for m in members:
            # 获取成员可用账号
            cursor = await db.execute(
                "SELECT account_id FROM member_accounts WHERE project_id=? AND user_id=?",
                (project_id, m["user_id"])
            )
            accounts = [r["account_id"] for r in await cursor.fetchall()]

            username = m["username"]
            if m["deleted_at"]:
                username = f"{username} (已删除)"

            result.append(MemberResponse(
                user_id=m["user_id"],
                username=username,
                role=m["role"],
                accounts=accounts
            ))

    return result


@router.post("/{project_id}/members", status_code=status.HTTP_201_CREATED)
async def add_project_member(project_id: str, data: MemberAdd, session_id: str = Cookie(None)):
    """添加项目成员"""
    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user, require_owner=True)

    # 检查用户是否存在
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id FROM users WHERE id=? AND deleted_at IS NULL",
            (data.user_id,)
        )
        if not await cursor.fetchone():
            raise HTTPException(404, "用户不存在")

        # 检查是否已是成员
        cursor = await db.execute(
            "SELECT 1 FROM project_members WHERE project_id=? AND user_id=?",
            (project_id, data.user_id)
        )
        if await cursor.fetchone():
            raise HTTPException(400, "该用户已是项目成员")

        now = _now()
        await db.execute(
            "INSERT INTO project_members (project_id, user_id, role, created_at) VALUES (?, ?, ?, ?)",
            (project_id, data.user_id, data.role, now)
        )
        await db.commit()

    return {"message": "成员已添加"}


@router.delete("/{project_id}/members/{user_id}")
async def remove_project_member(project_id: str, user_id: str, session_id: str = Cookie(None)):
    """移除项目成员"""
    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user, require_owner=True)

    async with aiosqlite.connect(str(DB_PATH)) as db:
        # 删除成员账号分配
        await db.execute(
            "DELETE FROM member_accounts WHERE project_id=? AND user_id=?",
            (project_id, user_id)
        )
        # 删除成员关系
        await db.execute(
            "DELETE FROM project_members WHERE project_id=? AND user_id=?",
            (project_id, user_id)
        )
        await db.commit()

    return {"message": "成员已移除"}


# ==================== 账号管理 API ====================

@router.get("/{project_id}/accounts", response_model=list[str])
async def get_project_accounts(project_id: str, session_id: str = Cookie(None)):
    """获取项目账号池"""
    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user)

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT account_id FROM project_accounts WHERE project_id=?",
            (project_id,)
        )
        rows = await cursor.fetchall()

    return [r["account_id"] for r in rows]


class UsableAccount(BaseModel):
    id: str
    credit: Optional[str] = None
    running: int = 0   # 执行中任务数
    queued: int = 0    # 排队中任务数


@router.get("/{project_id}/usable-accounts", response_model=list[UsableAccount])
async def get_usable_accounts(project_id: str, session_id: str = Cookie(None)):
    """获取当前用户在项目中可用的账号列表（含余额和队列状态）"""
    from services.dreamina import get_credit, is_account_logged_in

    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user)

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row

        # 获取项目账号池
        cursor = await db.execute(
            "SELECT account_id FROM project_accounts WHERE project_id=?",
            (project_id,)
        )
        project_accounts = {r["account_id"] for r in await cursor.fetchall()}

        # admin 或 owner 可用全部项目账号
        is_owner = user["is_admin"]
        if not is_owner:
            cursor = await db.execute(
                "SELECT role FROM project_members WHERE project_id=? AND user_id=?",
                (project_id, user["id"])
            )
            row = await cursor.fetchone()
            is_owner = row and row["role"] == "owner"

        if is_owner:
            usable = list(project_accounts)
        else:
            # 协作者只能用分配给自己的账号
            cursor = await db.execute(
                "SELECT account_id FROM member_accounts WHERE project_id=? AND user_id=?",
                (project_id, user["id"])
            )
            usable = [r["account_id"] for r in await cursor.fetchall() if r["account_id"] in project_accounts]

        # 统计各账号任务数
        cursor = await db.execute(
            """SELECT account_id,
                      SUM(CASE WHEN status IN ('pending','processing') THEN 1 ELSE 0 END) as running,
                      SUM(CASE WHEN status = 'queued' THEN 1 ELSE 0 END) as queued
               FROM tasks WHERE project_id=? GROUP BY account_id""",
            (project_id,)
        )
        task_counts = {r["account_id"]: {"running": r["running"], "queued": r["queued"]} for r in await cursor.fetchall()}

    result = []
    for acc_id in usable:
        credit = None
        if is_account_logged_in(acc_id):
            try:
                credit = await get_credit(acc_id)
            except Exception:
                pass
        counts = task_counts.get(acc_id, {"running": 0, "queued": 0})
        result.append(UsableAccount(
            id=acc_id,
            credit=credit,
            running=counts["running"],
            queued=counts["queued"]
        ))

    return result


@router.put("/{project_id}/accounts")
async def set_project_accounts(project_id: str, data: AccountAssignment, session_id: str = Cookie(None)):
    """设置项目账号池"""
    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user, require_owner=True)

    async with aiosqlite.connect(str(DB_PATH)) as db:
        # 删除旧的
        await db.execute("DELETE FROM project_accounts WHERE project_id=?", (project_id,))
        # 删除受影响的成员账号分配
        await db.execute("DELETE FROM member_accounts WHERE project_id=?", (project_id,))

        # 添加新的
        for account_id in data.accounts:
            await db.execute(
                "INSERT INTO project_accounts (project_id, account_id) VALUES (?, ?)",
                (project_id, account_id)
            )
        await db.commit()

    return {"message": "账号池已更新"}


@router.get("/{project_id}/member-accounts/{user_id}", response_model=list[str])
async def get_member_accounts(project_id: str, user_id: str, session_id: str = Cookie(None)):
    """获取成员可用账号"""
    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user)

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT account_id FROM member_accounts WHERE project_id=? AND user_id=?",
            (project_id, user_id)
        )
        rows = await cursor.fetchall()

    return [r["account_id"] for r in rows]


@router.put("/{project_id}/member-accounts/{user_id}")
async def set_member_accounts(project_id: str, user_id: str, data: AccountAssignment, session_id: str = Cookie(None)):
    """设置成员可用账号"""
    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user, require_owner=True)

    # 验证账号都在项目账号池中
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT account_id FROM project_accounts WHERE project_id=?",
            (project_id,)
        )
        project_accounts = {r["account_id"] for r in await cursor.fetchall()}

        for account_id in data.accounts:
            if account_id not in project_accounts:
                raise HTTPException(400, f"账号 {account_id} 不在项目账号池中")

        # 删除旧的
        await db.execute(
            "DELETE FROM member_accounts WHERE project_id=? AND user_id=?",
            (project_id, user_id)
        )

        # 添加新的
        for account_id in data.accounts:
            await db.execute(
                "INSERT INTO member_accounts (project_id, user_id, account_id) VALUES (?, ?, ?)",
                (project_id, user_id, account_id)
            )
        await db.commit()

    return {"message": "成员账号已更新"}


# ==================== 项目设置 API ====================

@router.put("/{project_id}/settings")
async def update_project_settings(project_id: str, data: ProjectSettingsUpdate, session_id: str = Cookie(None)):
    """更新项目设置"""
    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user, require_owner=True)

    now = _now()

    async with aiosqlite.connect(str(DB_PATH)) as db:
        updates = ["updated_at=?"]
        params = [now]

        if data.episode_count is not None:
            if data.episode_count < 1:
                raise HTTPException(400, "集数必须大于0")
            updates.append("episode_count=?")
            params.append(data.episode_count)

        params.append(project_id)

        await db.execute(
            f"UPDATE projects SET {', '.join(updates)} WHERE id=?",
            params
        )
        await db.commit()

    return {"message": "设置已更新"}


# ==================== 素材 API ====================

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac"}


@router.get("/{project_id}/materials", response_model=list[MaterialResponse])
async def list_materials(project_id: str, type: Optional[str] = None, session_id: str = Cookie(None)):
    """获取项目素材列表"""
    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user)

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
    session_id: str = Cookie(None),
):
    """上传素材"""
    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user)

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
async def update_material(project_id: str, material_id: str, data: MaterialUpdate, session_id: str = Cookie(None)):
    """更新素材名称"""
    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user)

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
async def delete_material(project_id: str, material_id: str, session_id: str = Cookie(None)):
    """删除素材"""
    user = await get_current_user_or_admin(session_id)
    await check_project_access(project_id, user)

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