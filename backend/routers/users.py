# backend/routers/users.py
import aiosqlite
from fastapi import APIRouter, Cookie, HTTPException

from config import DB_PATH
from models import UserCreate, UserUpdate, UserResponse
from services.auth import (
    create_user, update_user, soft_delete_user,
    get_user_by_username, get_session
)

router = APIRouter(prefix="/api/users", tags=["users"])


def _row_to_user(row) -> UserResponse:
    return UserResponse(
        id=row["id"],
        username=row["username"],
        is_admin=bool(row["is_admin"]),
        deleted_at=row["deleted_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def require_admin(session_id: str):
    """验证管理员权限"""
    if not session_id:
        raise HTTPException(401, "未登录")

    session = get_session(session_id)
    if not session:
        raise HTTPException(401, "登录已过期")

    if not session.get("is_admin"):
        raise HTTPException(403, "需要管理员权限")

    return session


@router.get("", response_model=list[UserResponse])
async def list_users(include_deleted: bool = False, session_id: str = Cookie(None)):
    """获取用户列表（登录用户可读，增删改仍需管理员）"""
    if not session_id or not get_session(session_id):
        raise HTTPException(401, "未登录")

    query = "SELECT * FROM users"
    if not include_deleted:
        query += " WHERE deleted_at IS NULL"
    query += " ORDER BY created_at DESC"

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query)
        rows = await cursor.fetchall()

    return [_row_to_user(r) for r in rows]


@router.post("", response_model=UserResponse)
async def create_new_user(data: UserCreate, session_id: str = Cookie(None)):
    """创建用户（管理员）"""
    await require_admin(session_id)

    # 检查用户名是否已存在
    existing = await get_user_by_username(data.username)
    if existing:
        raise HTTPException(400, "用户名已存在")

    user = await create_user(data.username, data.password)
    return UserResponse(**user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user_info(user_id: str, data: UserUpdate, session_id: str = Cookie(None)):
    """更新用户（管理员）"""
    await require_admin(session_id)

    user = await update_user(
        user_id,
        password=data.password,
        is_admin=data.is_admin
    )
    if not user:
        raise HTTPException(404, "用户不存在")

    return _row_to_user(user)


@router.delete("/{user_id}")
async def delete_user(user_id: str, session_id: str = Cookie(None)):
    """软删除用户（管理员）"""
    admin_session = await require_admin(session_id)

    # 不能删除自己
    if admin_session["user_id"] == user_id:
        raise HTTPException(400, "不能删除自己")

    success = await soft_delete_user(user_id)
    if not success:
        raise HTTPException(400, "该用户仍有任务记录，无法删除")

    return {"message": "用户已删除"}