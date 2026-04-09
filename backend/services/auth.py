# backend/services/auth.py
import uuid
from datetime import datetime, timezone
import aiosqlite
import bcrypt

from config import DB_PATH

# 内存 Session 存储（生产环境可替换为 Redis）
_sessions: dict[str, dict] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_session(user_id: str, username: str, is_admin: bool) -> str:
    """创建 Session，返回 session_id"""
    session_id = uuid.uuid4().hex
    _sessions[session_id] = {
        "user_id": user_id,
        "username": username,
        "is_admin": is_admin,
    }
    return session_id


def get_session(session_id: str) -> dict | None:
    """获取 Session"""
    return _sessions.get(session_id)


def delete_session(session_id: str) -> None:
    """删除 Session"""
    if session_id in _sessions:
        del _sessions[session_id]


async def get_user_by_id(user_id: str) -> dict | None:
    """根据 ID 获取用户"""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE id=? AND deleted_at IS NULL",
            (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
    return None


async def get_user_by_username(username: str) -> dict | None:
    """根据用户名获取用户（包括已删除的，用于检测重复）"""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
    return None


async def create_user(username: str, password: str, is_admin: bool = False) -> dict:
    """创建用户"""
    user_id = uuid.uuid4().hex[:12]
    hashed = hash_password(password)
    now = _now()

    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "INSERT INTO users (id, username, password, is_admin, deleted_at, created_at, updated_at) VALUES (?, ?, ?, ?, NULL, ?, ?)",
            (user_id, username, hashed, int(is_admin), now, now)
        )
        await db.commit()

    return {
        "id": user_id,
        "username": username,
        "is_admin": is_admin,
        "deleted_at": None,
        "created_at": now,
        "updated_at": now,
    }


async def update_user(user_id: str, password: str | None = None, is_admin: bool | None = None) -> dict | None:
    """更新用户"""
    now = _now()

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row

        # 检查用户存在
        cursor = await db.execute("SELECT * FROM users WHERE id=?", (user_id,))
        row = await cursor.fetchone()
        if not row:
            return None

        updates = ["updated_at=?"]
        params = [now]

        if password:
            updates.append("password=?")
            params.append(hash_password(password))

        if is_admin is not None:
            updates.append("is_admin=?")
            params.append(int(is_admin))

        params.append(user_id)

        await db.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id=?",
            params
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM users WHERE id=?", (user_id,))
        row = await cursor.fetchone()

    return dict(row)


async def soft_delete_user(user_id: str) -> bool:
    """软删除用户"""
    now = _now()

    async with aiosqlite.connect(str(DB_PATH)) as db:
        # 检查是否有任务
        cursor = await db.execute(
            "SELECT COUNT(*) as count FROM tasks WHERE creator_id=?",
            (user_id,)
        )
        row = await cursor.fetchone()
        if row["count"] > 0:
            return False

        await db.execute(
            "UPDATE users SET deleted_at=?, updated_at=? WHERE id=?",
            (now, now, user_id)
        )
        await db.commit()

    return True


async def get_user_project_role(user_id: str, project_id: str) -> str | None:
    """获取用户在项目中的角色"""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT role FROM project_members WHERE project_id=? AND user_id=?",
            (project_id, user_id)
        )
        row = await cursor.fetchone()
        if row:
            return row["role"]
    return None


async def get_user_projects(user_id: str, is_admin: bool) -> list[str]:
    """获取用户可见的项目 ID 列表"""
    if is_admin:
        # 管理员可见所有项目
        async with aiosqlite.connect(str(DB_PATH)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id FROM projects WHERE deleted_at IS NULL"
            )
            rows = await cursor.fetchall()
            return [r["id"] for r in rows]

    # 普通用户只看参与的
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT project_id FROM project_members WHERE user_id=?",
            (user_id,)
        )
        rows = await cursor.fetchall()

        # 过滤已删除的项目
        project_ids = [r["project_id"] for r in rows]
        if not project_ids:
            return []

        cursor = await db.execute(
            f"SELECT id FROM projects WHERE id IN ({','.join(['?']*len(project_ids))}) AND deleted_at IS NULL",
            project_ids
        )
        rows = await cursor.fetchall()
        return [r["id"] for r in rows]


async def get_user_available_accounts(user_id: str, project_id: str, is_admin: bool) -> list[str]:
    """获取用户在某项目中可用的账号列表"""
    if is_admin:
        # 管理员可用项目账号池中的所有账号
        async with aiosqlite.connect(str(DB_PATH)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT account_id FROM project_accounts WHERE project_id=?",
                (project_id,)
            )
            rows = await cursor.fetchall()
            return [r["account_id"] for r in rows]

    # 协作者只可用分配给他们的账号
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT account_id FROM member_accounts WHERE project_id=? AND user_id=?",
            (project_id, user_id)
        )
        rows = await cursor.fetchall()
        return [r["account_id"] for r in rows]


async def can_user_use_account(user_id: str, project_id: str, account_id: str, is_admin: bool) -> bool:
    """检查用户是否可以使用某账号"""
    available = await get_user_available_accounts(user_id, project_id, is_admin)
    return account_id in available


async def is_first_user() -> bool:
    """检查是否是第一个用户（用于自动设置管理员）"""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        cursor = await db.execute("SELECT COUNT(*) as count FROM users WHERE deleted_at IS NULL")
        row = await cursor.fetchone()
        return row["count"] == 0