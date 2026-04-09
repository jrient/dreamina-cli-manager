# 用户认证与权限系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现用户认证、权限管理、项目账号分配和分集功能

**Architecture:** Session 认证 + 权限中间件 + 数据库权限关联表

**Tech Stack:** FastAPI Sessions, bcrypt, SQLite, Vue 3 Router Guards, Element Plus

---

## 文件结构

### 后端新增
- `backend/routers/auth.py` — 认证路由（login/logout/me）
- `backend/routers/users.py` — 用户管理路由（管理员）
- `backend/services/auth.py` — 认证服务（Session、权限检查）

### 后端修改
- `backend/database.py` — 新增表和迁移 SQL
- `backend/models.py` — 新增用户相关 Pydantic 模型
- `backend/main.py` — 注册新路由、Session 中间件
- `backend/config.py` — Session 密钥配置
- `backend/routers/projects.py` — 权限过滤、成员/账号/设置 API
- `backend/routers/tasks.py` — 权限过滤、分集字段

### 前端新增
- `frontend/src/views/Login.vue` — 登录页
- `frontend/src/views/UserManagement.vue` — 用户管理页
- `frontend/src/views/ProjectSettings.vue` — 项目设置 Tab
- `frontend/src/stores/auth.js` — 认证状态 Pinia store

### 前端修改
- `frontend/src/router/index.js` — 新增路由、路由守卫
- `frontend/src/App.vue` — 用户信息、登出按钮
- `frontend/src/views/ProjectList.vue` — 权限过滤
- `frontend/src/views/SubmitTask.vue` — 分集下拉、账号过滤
- `frontend/src/views/TaskList.vue` — 分集筛选、创建者列
- `frontend/src/views/ProjectTasks.vue` — 分集筛选

---

## Task 1: 数据库表创建与迁移

**Files:**
- Modify: `backend/database.py`

- [ ] **Step 1: 添加用户表 SQL**

在 `database.py` 开头添加新表定义：

```python
# backend/database.py
# 在 CREATE_MATERIALS_SQL 之后添加：

CREATE_USERS_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    username    TEXT UNIQUE NOT NULL,
    password    TEXT NOT NULL,
    is_admin    INTEGER DEFAULT 0,
    deleted_at  TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""

CREATE_PROJECT_MEMBERS_SQL = """
CREATE TABLE IF NOT EXISTS project_members (
    project_id  TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    role        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    PRIMARY KEY (project_id, user_id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

CREATE_PROJECT_ACCOUNTS_SQL = """
CREATE TABLE IF NOT EXISTS project_accounts (
    project_id  TEXT NOT NULL,
    account_id  TEXT NOT NULL,
    PRIMARY KEY (project_id, account_id)
);
"""

CREATE_MEMBER_ACCOUNTS_SQL = """
CREATE TABLE IF NOT EXISTS member_accounts (
    project_id  TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    account_id  TEXT NOT NULL,
    PRIMARY KEY (project_id, user_id, account_id)
);
"""
```

- [ ] **Step 2: 添加迁移 SQL**

```python
# backend/database.py
# 在 MIGRATE_ADD_LABEL_SQL 之后添加：

MIGRATE_ADD_EPISODE_COUNT_SQL = """
ALTER TABLE projects ADD COLUMN episode_count INTEGER DEFAULT 50;
"""

MIGRATE_ADD_CREATOR_ID_TO_PROJECTS_SQL = """
ALTER TABLE projects ADD COLUMN creator_id TEXT;
"""

MIGRATE_ADD_CREATOR_ID_TO_TASKS_SQL = """
ALTER TABLE tasks ADD COLUMN creator_id TEXT;
"""

MIGRATE_ADD_EPISODE_TO_TASKS_SQL = """
ALTER TABLE tasks ADD COLUMN episode INTEGER;
"""
```

- [ ] **Step 3: 更新 init_db 函数**

```python
# backend/database.py
# 替换 init_db 函数：

async def init_db():
    async with aiosqlite.connect(str(DB_PATH)) as db:
        # 创建基础表
        await db.execute(CREATE_TASKS_SQL)
        await db.execute(CREATE_PROJECTS_SQL)
        await db.execute(CREATE_MATERIALS_SQL)

        # 创建用户认证相关表
        await db.execute(CREATE_USERS_SQL)
        await db.execute(CREATE_PROJECT_MEMBERS_SQL)
        await db.execute(CREATE_PROJECT_ACCOUNTS_SQL)
        await db.execute(CREATE_MEMBER_ACCOUNTS_SQL)

        await db.commit()

        # 迁移 tasks 表
        for migrate_sql in [MIGRATE_ADD_SUBMIT_ID_SQL, MIGRATE_ADD_PROJECT_ID_SQL, MIGRATE_ADD_LABEL_SQL, MIGRATE_ADD_CREATOR_ID_TO_TASKS_SQL, MIGRATE_ADD_EPISODE_TO_TASKS_SQL]:
            try:
                await db.execute(migrate_sql)
                await db.commit()
            except aiosqlite.OperationalError:
                pass

        # 迁移 projects 表
        for migrate_sql in [MIGRATE_ADD_EPISODE_COUNT_SQL, MIGRATE_ADD_CREATOR_ID_TO_PROJECTS_SQL]:
            try:
                await db.execute(migrate_sql)
                await db.commit()
            except aiosqlite.OperationalError:
                pass
```

- [ ] **Step 4: 运行测试验证数据库初始化**

Run: `cd /data/project/jm-auto/backend && python -c "from database import init_db; import asyncio; asyncio.run(init_db())"`

Expected: 无错误输出

- [ ] **Step 5: 提交**

```bash
git add backend/database.py
git commit -m "$(cat <<'EOF'
feat(db): add user auth tables and migrations

- users table with soft delete support
- project_members for role assignment
- project_accounts for account pool binding
- member_accounts for per-user account assignment
- tasks: creator_id, episode fields
- projects: episode_count, creator_id fields

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: 配置 Session 密钥

**Files:**
- Modify: `backend/config.py`

- [ ] **Step 1: 添加 Session 配置**

```python
# backend/config.py
# 在文件末尾添加：

# Session 配置
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "dreamina-secret-key-change-in-production")
SESSION_MAX_AGE = int(os.getenv("SESSION_MAX_AGE", "86400"))  # 24 hours
```

- [ ] **Step 2: 提交**

```bash
git add backend/config.py
git commit -m "$(cat <<'EOF'
feat(config): add session configuration

- SESSION_SECRET_KEY for session signing
- SESSION_MAX_AGE for session expiration (24h default)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 用户相关 Pydantic 模型

**Files:**
- Modify: `backend/models.py`

- [ ] **Step 1: 添加用户模型**

```python
# backend/models.py
# 在文件末尾添加：

class UserCreate(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    password: Optional[str] = None
    is_admin: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    username: str
    is_admin: bool
    deleted_at: Optional[str] = None
    created_at: str
    updated_at: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserSession(BaseModel):
    id: str
    username: str
    is_admin: bool
```

- [ ] **Step 2: 更新 ProjectResponse**

```python
# backend/models.py
# 替换 ProjectResponse：

class ProjectResponse(BaseModel):
    id: str
    name: str
    deleted_at: Optional[str] = None
    created_at: str
    updated_at: str
    episode_count: Optional[int] = 50
    creator_id: Optional[str] = None
```

- [ ] **Step 3: 更新 TaskResponse**

```python
# backend/models.py
# 替换 TaskResponse：

class TaskResponse(BaseModel):
    id: str
    account_id: str
    status: str
    submit_id: Optional[str] = None
    result_url: Optional[str] = None
    error_msg: Optional[str] = None
    prompt: Optional[str] = None
    params: Optional[str] = None
    created_at: str
    updated_at: str
    project_id: Optional[str] = None
    label: Optional[str] = None
    creator_id: Optional[str] = None
    episode: Optional[int] = None
```

- [ ] **Step 4: 新增成员相关模型**

```python
# backend/models.py
# 在末尾添加：

class MemberAdd(BaseModel):
    user_id: str
    role: str = "collaborator"


class MemberResponse(BaseModel):
    user_id: str
    username: str
    role: str
    accounts: list[str] = []


class AccountAssignment(BaseModel):
    accounts: list[str]


class ProjectSettingsUpdate(BaseModel):
    episode_count: Optional[int] = None
```

- [ ] **Step 5: 提交**

```bash
git add backend/models.py
git commit -m "$(cat <<'EOF'
feat(models): add user auth pydantic models

- UserCreate, UserUpdate, UserResponse
- LoginRequest, UserSession
- MemberAdd, MemberResponse
- AccountAssignment, ProjectSettingsUpdate
- Update ProjectResponse: episode_count, creator_id
- Update TaskResponse: creator_id, episode

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: 认证服务

**Files:**
- Create: `backend/services/auth.py`

- [ ] **Step 1: 创建认证服务文件**

```python
# backend/services/auth.py
import uuid
from datetime import datetime, timezone
import aiosqlite
import bcrypt

from config import DB_PATH, SESSION_SECRET_KEY

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
```

- [ ] **Step 2: 提交**

```bash
git add backend/services/auth.py
git commit -m "$(cat <<'EOF'
feat(services): add auth service with session and permission helpers

- Session management (create/get/delete in-memory)
- Password hashing with bcrypt
- User CRUD operations
- Permission helpers: get_user_project_role, get_user_projects
- Account availability: get_user_available_accounts, can_user_use_account
- First user detection for auto-admin

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: 认证路由

**Files:**
- Create: `backend/routers/auth.py`

- [ ] **Step 1: 创建认证路由文件**

```python
# backend/routers/auth.py
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from models import LoginRequest, UserSession, UserResponse
from services.auth import (
    get_user_by_username, verify_password, create_session,
    delete_session, get_session, get_user_by_id, is_first_user,
    create_user
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginResponse(BaseModel):
    user: UserSession
    session_id: str


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, response: Response):
    """用户登录"""
    user = await get_user_by_username(req.username)

    if not user:
        raise HTTPException(401, "用户名或密码错误")

    if user.get("deleted_at"):
        raise HTTPException(401, "账户已被禁用")

    if not verify_password(req.password, user["password"]):
        raise HTTPException(401, "用户名或密码错误")

    # 首个用户自动成为管理员
    check_admin = user["is_admin"]
    if not check_admin and await is_first_user():
        # 更新为管理员
        from services.auth import update_user
        await update_user(user["id"], is_admin=True)
        user["is_admin"] = 1
        check_admin = True

    session_id = create_session(user["id"], user["username"], bool(check_admin))

    # 设置 Cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=86400,  # 24 hours
        samesite="lax"
    )

    return LoginResponse(
        user=UserSession(
            id=user["id"],
            username=user["username"],
            is_admin=bool(check_admin)
        ),
        session_id=session_id
    )


@router.post("/logout")
async def logout(response: Response, session_id: str = None):
    """用户登出"""
    if session_id:
        delete_session(session_id)

    response.delete_cookie("session_id")
    return {"message": "已登出"}


@router.get("/me", response_model=UserSession)
async def get_current_user(session_id: str = None):
    """获取当前登录用户"""
    if not session_id:
        raise HTTPException(401, "未登录")

    session = get_session(session_id)
    if not session:
        raise HTTPException(401, "登录已过期")

    user = await get_user_by_id(session["user_id"])
    if not user:
        raise HTTPException(401, "用户不存在")

    return UserSession(
        id=user["id"],
        username=user["username"],
        is_admin=bool(user["is_admin"])
    )
```

- [ ] **Step 2: 提交**

```bash
git add backend/routers/auth.py
git commit -m "$(cat <<'EOF'
feat(routers): add auth router for login/logout/me

- POST /login: validate credentials, create session, set cookie
- POST /logout: clear session and cookie
- GET /me: return current user info
- First user auto-promoted to admin

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: 用户管理路由

**Files:**
- Create: `backend/routers/users.py`

- [ ] **Step 1: 创建用户管理路由文件**

```python
# backend/routers/users.py
import aiosqlite
from fastapi import APIRouter, HTTPException

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
async def list_users(include_deleted: bool = False, session_id: str = None):
    """获取用户列表（管理员）"""
    await require_admin(session_id)

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
async def create_new_user(data: UserCreate, session_id: str = None):
    """创建用户（管理员）"""
    await require_admin(session_id)

    # 检查用户名是否已存在
    existing = await get_user_by_username(data.username)
    if existing:
        raise HTTPException(400, "用户名已存在")

    user = await create_user(data.username, data.password)
    return UserResponse(**user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user_info(user_id: str, data: UserUpdate, session_id: str = None):
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
async def delete_user(user_id: str, session_id: str = None):
    """软删除用户（管理员）"""
    admin_session = await require_admin(session_id)

    # 不能删除自己
    if admin_session["user_id"] == user_id:
        raise HTTPException(400, "不能删除自己")

    success = await soft_delete_user(user_id)
    if not success:
        raise HTTPException(400, "该用户仍有任务记录，无法删除")

    return {"message": "用户已删除"}
```

- [ ] **Step 2: 提交**

```bash
git add backend/routers/users.py
git commit -m "$(cat <<'EOF'
feat(routers): add users router for admin user management

- GET /users: list all users (with deleted filter)
- POST /users: create new user
- PUT /users/{id}: update password or admin status
- DELETE /users/{id}: soft delete user
- All endpoints require admin role

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: 注册路由到 main.py

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: 注册新路由**

```python
# backend/main.py
# 在导入部分添加：

from routers.auth import router as auth_router
from routers.users import router as users_router

# 在 app.include_router 部分添加：

app.include_router(auth_router)
app.include_router(users_router)
```

- [ ] **Step 2: 完整更新后的 main.py**

```python
# backend/main.py
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import POLL_INTERVAL, RESULTS_DIR, UPLOAD_DIR
from database import init_db, close_db
from routers.accounts import router as accounts_router
from routers.tasks import router as tasks_router
from routers.projects import router as projects_router
from routers.auth import router as auth_router
from routers.users import router as users_router
from services.poller import poll_tasks

logging.basicConfig(level=logging.INFO)
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    scheduler.add_job(poll_tasks, "interval", seconds=POLL_INTERVAL, id="poller")
    scheduler.start()
    yield
    scheduler.shutdown()
    await close_db()


app = FastAPI(title="Dreamina Web UI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(accounts_router)
app.include_router(tasks_router)
app.include_router(projects_router)

app.mount("/results", StaticFiles(directory=str(RESULTS_DIR)), name="results")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 3: 提交**

```bash
git add backend/main.py
git commit -m "$(cat <<'EOF'
feat(main): register auth and users routers

- Include auth_router for login/logout/me
- Include users_router for admin user management

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: 项目路由权限改造

**Files:**
- Modify: `backend/routers/projects.py`

- [ ] **Step 1: 添加权限检查和成员管理 API**

在文件开头添加导入和权限辅助函数：

```python
# backend/routers/projects.py
# 替换文件开头的导入和辅助函数部分：

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
```

- [ ] **Step 2: 修改 list_projects 添加权限过滤**

```python
# backend/routers/projects.py
# 替换 list_projects 函数：

@router.get("", response_model=list[ProjectResponse])
async def list_projects(include_deleted: bool = False, session_id: str = None):
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

    return [_row_to_project(r) for r in rows]
```

- [ ] **Step 3: 修改 create_project 添加创建者关联**

```python
# backend/routers/projects.py
# 替换 create_project 函数：

@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProjectResponse)
async def create_project(data: ProjectCreate, session_id: str = None):
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
```

- [ ] **Step 4: 添加成员管理 API**

在文件末尾添加：

```python
# backend/routers/projects.py
# 在文件末尾添加：


# ==================== 成员管理 API ====================

@router.get("/{project_id}/members", response_model=list[MemberResponse])
async def list_project_members(project_id: str, session_id: str = None):
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
async def add_project_member(project_id: str, data: MemberAdd, session_id: str = None):
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
async def remove_project_member(project_id: str, user_id: str, session_id: str = None):
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
async def get_project_accounts(project_id: str, session_id: str = None):
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


@router.put("/{project_id}/accounts")
async def set_project_accounts(project_id: str, data: AccountAssignment, session_id: str = None):
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
async def get_member_accounts(project_id: str, user_id: str, session_id: str = None):
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
async def set_member_accounts(project_id: str, user_id: str, data: AccountAssignment, session_id: str = None):
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
async def update_project_settings(project_id: str, data: ProjectSettingsUpdate, session_id: str = None):
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
```

- [ ] **Step 5: 提交**

```bash
git add backend/routers/projects.py
git commit -m "$(cat <<'EOF'
feat(projects): add permission filtering and member/account management

- list_projects: filter by user membership
- create_project: auto-add creator as owner
- Members API: list/add/remove members
- Accounts API: project account pool, member account assignment
- Settings API: episode_count configuration
- All endpoints check session and permissions

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: 任务路由权限改造

**Files:**
- Modify: `backend/routers/tasks.py`

- [ ] **Step 1: 添加权限检查导入和分集字段**

```python
# backend/routers/tasks.py
# 在导入部分添加：

from services.auth import get_session, get_user_by_id, can_user_use_account, get_user_project_role
```

- [ ] **Step 2: 更新 _row_to_task 函数**

```python
# backend/routers/tasks.py
# 替换 _row_to_task 函数：

def _row_to_task(row) -> TaskResponse:
    return TaskResponse(
        id=row["id"],
        account_id=row["account_id"],
        status=row["status"],
        submit_id=row["submit_id"],
        result_url=row["result_url"],
        error_msg=row["error_msg"],
        prompt=row["prompt"],
        params=row["params"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        project_id=row["project_id"] if "project_id" in row.keys() else None,
        label=row["label"] if "label" in row.keys() else None,
        creator_id=row["creator_id"] if "creator_id" in row.keys() else None,
        episode=row["episode"] if "episode" in row.keys() else None,
    )
```

- [ ] **Step 3: 添加权限辅助函数**

```python
# backend/routers/tasks.py
# 在 _row_to_task 函数后添加：

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
```

- [ ] **Step 4: 修改 create_task 添加权限和分集**

```python
# backend/routers/tasks.py
# 替换 create_task 函数：

@router.post("", status_code=status.HTTP_201_CREATED, response_model=TaskResponse)
async def create_task(
    account_id: str = Form(...),
    prompt: str = Form(""),
    duration: int = Form(5),
    ratio: str = Form("9:16"),
    model_version: str = Form("seedance2.0fast"),
    project_id: Optional[str] = Form(None),
    label: Optional[str] = Form(None),
    episode: Optional[int] = Form(None),
    images: list[UploadFile] = File(default=[]),
    videos: list[UploadFile] = File(default=[]),
    audios: list[UploadFile] = File(default=[]),
    session_id: str = None,
):
    user = await get_current_user_or_admin(session_id)

    if not images and not videos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one image or video is required",
        )
    if len(images) > 9:
        raise HTTPException(422, "Maximum 9 images allowed")
    if len(videos) > 3:
        raise HTTPException(422, "Maximum 3 videos allowed")
    if len(audios) > 3:
        raise HTTPException(422, "Maximum 3 audio files allowed")

    # 检查项目权限
    if project_id:
        role = await get_user_project_role(user["id"], project_id)
        if not role and not user["is_admin"]:
            raise HTTPException(403, "无权限访问此项目")

        # 检查账号权限
        if not user["is_admin"] and not await can_user_use_account(user["id"], project_id, account_id, False):
            raise HTTPException(403, "您无权限使用该账号")

        # 检查分集范围
        if episode:
            async with aiosqlite.connect(str(DB_PATH)) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT episode_count FROM projects WHERE id=?",
                    (project_id,)
                )
                row = await cursor.fetchone()
                if row and episode > row["episode_count"]:
                    raise HTTPException(400, f"分集号超出范围，最大为 {row['episode_count']}")

    # Check account exists and is logged in
    if not is_account_logged_in(account_id):
        account_home = ACCOUNT_HOME_BASE / account_id
        if not account_home.exists():
            raise HTTPException(404, f"账号 '{account_id}' 不存在")
        raise HTTPException(400, f"账号 '{account_id}' 未登录，请先在账号管理页面登录")

    # Generate UUID for task
    task_id = uuid.uuid4().hex[:12]

    # Save uploaded files to task-specific directory
    task_dir = UPLOAD_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    async def save(upload: UploadFile, dest_dir: Path) -> str:
        dest = dest_dir / upload.filename
        content = await upload.read()
        dest.write_bytes(content)
        return str(dest)

    image_paths = [await save(f, task_dir) for f in images]
    video_paths = [await save(f, task_dir) for f in videos]
    audio_paths = [await save(f, task_dir) for f in audios]

    params = json.dumps({
        "duration": duration,
        "ratio": ratio,
        "model_version": model_version,
        "image_paths": image_paths,
        "video_paths": video_paths,
        "audio_paths": audio_paths,
    })
    now = _now()

    # Try to submit, handle concurrency limit
    submit_id = None
    task_status = "queued"

    try:
        submit_id = await submit_multimodal2video(
            account_id=account_id,
            image_paths=image_paths,
            video_paths=video_paths,
            audio_paths=audio_paths,
            prompt=prompt,
            duration=duration,
            ratio=ratio,
            model_version=model_version,
        )
        task_status = "pending"
    except ConcurrencyLimitError:
        asyncio.get_event_loop().call_later(1, lambda: asyncio.ensure_future(dispatch_queued_tasks()))
    except Exception as e:
        shutil.rmtree(task_dir, ignore_errors=True)
        raise HTTPException(status_code=502, detail=str(e))

    # Insert task to database
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "INSERT INTO tasks (id, account_id, status, submit_id, result_url, error_msg, prompt, params, created_at, updated_at, project_id, label, creator_id, episode) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (task_id, account_id, task_status, submit_id, None, None, prompt, params, now, now, project_id, label, user["id"], episode),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
        row = await cursor.fetchone()

    return _row_to_task(row)
```

- [ ] **Step 5: 修改 list_tasks 添加权限过滤和分集筛选**

```python
# backend/routers/tasks.py
# 替换 list_tasks 函数：

@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    status: Optional[str] = None,
    account_id: Optional[str] = None,
    project_id: Optional[str] = None,
    episode: Optional[int] = None,
    session_id: str = None
):
    user = await get_current_user_or_admin(session_id)

    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if status:
        query += " AND status=?"
        params.append(status)
    if account_id:
        query += " AND account_id=?"
        params.append(account_id)
    if project_id:
        query += " AND project_id=?"
        params.append(project_id)
    if episode:
        query += " AND episode=?"
        params.append(episode)

    # 非管理员只看自己的任务
    if not user["is_admin"]:
        query += " AND creator_id=?"
        params.append(user["id"])

    query += " ORDER BY created_at DESC"

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

    return [_row_to_task(r) for r in rows]
```

- [ ] **Step 6: 提交**

```bash
git add backend/routers/tasks.py
git commit -m "$(cat <<'EOF'
feat(tasks): add permission filtering and episode support

- create_task: check project/account permission, add episode field
- list_tasks: filter by creator (non-admin), add episode filter
- TaskResponse: include creator_id, episode

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: 前端登录页

**Files:**
- Create: `frontend/src/views/Login.vue`

- [ ] **Step 1: 创建登录页组件**

```vue
<!-- frontend/src/views/Login.vue -->
<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="login-header">
          <span class="login-title">🎬 Dreamina 视频生成</span>
        </div>
      </template>

      <el-form :model="form" :rules="rules" ref="formRef" @submit.prevent="handleLogin">
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            @click="handleLogin"
            class="login-btn"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await authStore.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #1e1e2e 0%, #2d2d3f 100%);
}

.login-card {
  width: 400px;
}

.login-header {
  text-align: center;
}

.login-title {
  font-size: 20px;
  font-weight: bold;
}

.login-btn {
  width: 100%;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/views/Login.vue
git commit -m "$(cat <<'EOF'
feat(frontend): add Login page

- Username/password form
- Validation and error handling
- Redirect after successful login

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: 前端认证 Store

**Files:**
- Create: `frontend/src/stores/auth.js`

- [ ] **Step 1: 创建认证 Store**

```javascript
// frontend/src/stores/auth.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.is_admin || false)

  async function fetchUser() {
    try {
      const response = await axios.get('/api/auth/me')
      user.value = response.data
      return true
    } catch (err) {
      user.value = null
      return false
    }
  }

  async function login(username, password) {
    const response = await axios.post('/api/auth/login', { username, password })
    user.value = response.data.user
    return response.data
  }

  async function logout() {
    try {
      await axios.post('/api/auth/logout')
    } catch (err) {
      // ignore
    }
    user.value = null
  }

  return {
    user,
    loading,
    isLoggedIn,
    isAdmin,
    fetchUser,
    login,
    logout
  }
})
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/stores/auth.js
git commit -m "$(cat <<'EOF'
feat(frontend): add auth Pinia store

- User state management
- login/logout/fetchUser actions
- isLoggedIn and isAdmin computed properties

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: 路由守卫和路由配置

**Files:**
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/main.js`

- [ ] **Step 1: 更新路由配置**

```javascript
// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// 页面组件
import Login from '../views/Login.vue'
import HomePage from '../views/HomePage.vue'
import AccountManager from '../views/AccountManager.vue'
import ProjectList from '../views/ProjectList.vue'
import ProjectTasks from '../views/ProjectTasks.vue'
import ProjectMaterials from '../views/ProjectMaterials.vue'
import ProjectSettings from '../views/ProjectSettings.vue'
import AdminEntry from '../views/AdminEntry.vue'
import AdminProjects from '../views/AdminProjects.vue'
import AdminAccounts from '../views/AdminAccounts.vue'
import AdminTasks from '../views/AdminTasks.vue'
import UserManagement from '../views/UserManagement.vue'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: Login,
    meta: { guest: true }
  },
  {
    path: '/',
    name: 'home',
    component: HomePage,
    meta: { requiresAuth: true }
  },
  {
    path: '/accounts',
    name: 'accounts',
    component: AccountManager,
    meta: { requiresAuth: true }
  },
  {
    path: '/projects',
    name: 'projects',
    component: ProjectList,
    meta: { requiresAuth: true }
  },
  {
    path: '/projects/:id/tasks',
    name: 'project-tasks',
    component: ProjectTasks,
    meta: { requiresAuth: true }
  },
  {
    path: '/projects/:id/materials',
    name: 'project-materials',
    component: ProjectMaterials,
    meta: { requiresAuth: true }
  },
  {
    path: '/projects/:id/settings',
    name: 'project-settings',
    component: ProjectSettings,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'admin',
    component: AdminEntry,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/projects',
    name: 'admin-projects',
    component: AdminProjects,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/accounts',
    name: 'admin-accounts',
    component: AdminAccounts,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/tasks',
    name: 'admin-tasks',
    component: AdminTasks,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/users',
    name: 'admin-users',
    component: UserManagement,
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // 如果还没获取用户信息，尝试获取
  if (!authStore.user && !authStore.loading) {
    await authStore.fetchUser()
  }

  // 需要登录的页面
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    return next('/login')
  }

  // 需要管理员的页面
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return next('/')
  }

  // 已登录用户访问登录页，重定向到首页
  if (to.meta.guest && authStore.isLoggedIn) {
    return next('/')
  }

  next()
})

export default router
```

- [ ] **Step 2: 检查 main.js 是否已配置 Pinia**

如果 `frontend/src/main.js` 未配置 Pinia，需要添加：

```javascript
// frontend/src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/router/index.js frontend/src/main.js
git commit -m "$(cat <<'EOF'
feat(frontend): add route guards and auth routing

- Login route with guest meta
- Admin routes with requiresAdmin meta
- Route guard checks auth state
- Redirect unauthenticated users to login
- Configure Pinia in main.js

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: 用户管理页面

**Files:**
- Create: `frontend/src/views/UserManagement.vue`

- [ ] **Step 1: 创建用户管理页面**

```vue
<!-- frontend/src/views/UserManagement.vue -->
<template>
  <div class="user-management">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button type="primary" @click="showCreateDialog">新建用户</el-button>
        </div>
      </template>

      <el-table :data="users" v-loading="loading">
        <el-table-column prop="username" label="用户名" />
        <el-table-column label="管理员" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_admin" type="success">是</el-tag>
            <el-tag v-else type="info">否</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240">
          <template #default="{ row }">
            <el-button size="small" @click="showResetPassword(row)">重置密码</el-button>
            <el-button
              v-if="!row.is_admin"
              size="small"
              type="warning"
              @click="setAdmin(row, true)"
            >
              设为管理员
            </el-button>
            <el-button
              v-if="row.is_admin"
              size="small"
              type="info"
              @click="setAdmin(row, false)"
            >
              取消管理员
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="deleteUser(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建用户对话框 -->
    <el-dialog v-model="createDialogVisible" title="新建用户" width="400px">
      <el-form :model="createForm" :rules="createRules" ref="createFormRef">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="createForm.username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="createForm.password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createUser" :loading="createLoading">创建</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog v-model="resetDialogVisible" title="重置密码" width="400px">
      <el-form :model="resetForm" :rules="resetRules" ref="resetFormRef">
        <el-form-item label="新密码" prop="password">
          <el-input v-model="resetForm.password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="resetPassword" :loading="resetLoading">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const users = ref([])
const loading = ref(false)

const createDialogVisible = ref(false)
const createLoading = ref(false)
const createFormRef = ref()
const createForm = reactive({ username: '', password: '' })
const createRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const resetDialogVisible = ref(false)
const resetLoading = ref(false)
const resetFormRef = ref()
const resetForm = reactive({ userId: '', password: '' })
const resetRules = {
  password: [{ required: true, message: '请输入新密码', trigger: 'blur' }]
}

const fetchUsers = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/users')
    users.value = response.data
  } catch (err) {
    ElMessage.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  createForm.username = ''
  createForm.password = ''
  createDialogVisible.value = true
}

const createUser = async () => {
  const valid = await createFormRef.value.validate().catch(() => false)
  if (!valid) return

  createLoading.value = true
  try {
    await axios.post('/api/users', createForm)
    ElMessage.success('用户创建成功')
    createDialogVisible.value = false
    fetchUsers()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '创建失败')
  } finally {
    createLoading.value = false
  }
}

const showResetPassword = (row) => {
  resetForm.userId = row.id
  resetForm.password = ''
  resetDialogVisible.value = true
}

const resetPassword = async () => {
  const valid = await resetFormRef.value.validate().catch(() => false)
  if (!valid) return

  resetLoading.value = true
  try {
    await axios.put(`/api/users/${resetForm.userId}`, { password: resetForm.password })
    ElMessage.success('密码重置成功')
    resetDialogVisible.value = false
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '重置失败')
  } finally {
    resetLoading.value = false
  }
}

const setAdmin = async (row, isAdmin) => {
  try {
    await axios.put(`/api/users/${row.id}`, { is_admin: isAdmin })
    ElMessage.success(isAdmin ? '已设为管理员' : '已取消管理员')
    fetchUsers()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  }
}

const deleteUser = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除用户 "${row.username}"？`, '确认删除', {
      type: 'warning'
    })
    await axios.delete(`/api/users/${row.id}`)
    ElMessage.success('用户已删除')
    fetchUsers()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err.response?.data?.detail || '删除失败')
    }
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(fetchUsers)
</script>

<style scoped>
.user-management {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/views/UserManagement.vue
git commit -m "$(cat <<'EOF'
feat(frontend): add UserManagement page

- User list table with admin status
- Create user dialog
- Reset password dialog
- Set/remove admin role
- Soft delete user

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: 项目设置页面

**Files:**
- Create: `frontend/src/views/ProjectSettings.vue`

- [ ] **Step 1: 创建项目设置页面**

```vue
<!-- frontend/src/views/ProjectSettings.vue -->
<template>
  <div class="project-settings">
    <el-card v-loading="loading">
      <el-tabs v-model="activeTab">
        <!-- 基本设置 -->
        <el-tab-pane label="基本设置" name="basic">
          <el-form :model="settings" label-width="100px">
            <el-form-item label="集数配置">
              <el-select v-model="settings.episode_count" @change="saveSettings">
                <el-option
                  v-for="n in 100"
                  :key="n"
                  :label="n"
                  :value="n"
                />
              </el-select>
              <span style="margin-left: 10px; color: #909399;">任务分集范围 1-{{ settings.episode_count }}</span>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 账号配置 -->
        <el-tab-pane label="账号配置" name="accounts">
          <div class="section">
            <div class="section-title">项目账号池</div>
            <el-select
              v-model="projectAccounts"
              multiple
              placeholder="选择可用账号"
              style="width: 100%;"
              @change="saveProjectAccounts"
            >
              <el-option
                v-for="account in allAccounts"
                :key="account.id"
                :label="account.id"
                :value="account.id"
              />
            </el-select>
          </div>
        </el-tab-pane>

        <!-- 协作者管理 -->
        <el-tab-pane label="协作者管理" name="members">
          <div class="section">
            <div class="section-header">
              <span class="section-title">协作者列表</span>
              <el-button type="primary" size="small" @click="showAddMemberDialog">添加协作者</el-button>
            </div>

            <el-table :data="members" size="small">
              <el-table-column prop="username" label="用户名" />
              <el-table-column prop="role" label="角色" width="100">
                <template #default="{ row }">
                  <el-tag v-if="row.role === 'owner'" type="success">拥有者</el-tag>
                  <el-tag v-else>协作者</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="可用账号">
                <template #default="{ row }">
                  <span v-if="row.role === 'owner'">全部</span>
                  <span v-else>{{ row.accounts.join(', ') || '未分配' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="150">
                <template #default="{ row }">
                  <template v-if="row.role !== 'owner'">
                    <el-button size="small" @click="showAccountDialog(row)">配置账号</el-button>
                    <el-button size="small" type="danger" @click="removeMember(row)">移除</el-button>
                  </template>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 添加协作者对话框 -->
    <el-dialog v-model="addMemberDialogVisible" title="添加协作者" width="400px">
      <el-select v-model="selectedUserId" placeholder="选择用户" style="width: 100%;">
        <el-option
          v-for="user in availableUsers"
          :key="user.id"
          :label="user.username"
          :value="user.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="addMemberDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addMember" :loading="addMemberLoading">添加</el-button>
      </template>
    </el-dialog>

    <!-- 配置账号对话框 -->
    <el-dialog v-model="accountDialogVisible" title="配置可用账号" width="400px">
      <el-select v-model="selectedAccounts" multiple placeholder="选择账号" style="width: 100%;">
        <el-option
          v-for="account in projectAccounts"
          :key="account"
          :label="account"
          :value="account"
        />
      </el-select>
      <template #footer>
        <el-button @click="accountDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveMemberAccounts" :loading="accountLoading">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const route = useRoute()
const projectId = route.params.id

const loading = ref(false)
const activeTab = ref('basic')

const settings = reactive({ episode_count: 50 })
const projectAccounts = ref([])
const members = ref([])
const allAccounts = ref([])
const allUsers = ref([])

// 添加协作者
const addMemberDialogVisible = ref(false)
const addMemberLoading = ref(false)
const selectedUserId = ref('')

// 配置账号
const accountDialogVisible = ref(false)
const accountLoading = ref(false)
const selectedMemberId = ref('')
const selectedAccounts = ref([])

const availableUsers = computed(() => {
  const memberIds = new Set(members.value.map(m => m.user_id))
  return allUsers.value.filter(u => !memberIds.has(u.id))
})

const fetchData = async () => {
  loading.value = true
  try {
    // 获取项目信息
    const projectRes = await axios.get(`/api/projects/${projectId}`)
    settings.episode_count = projectRes.data.episode_count || 50

    // 获取项目账号
    const accountsRes = await axios.get(`/api/projects/${projectId}/accounts`)
    projectAccounts.value = accountsRes.data

    // 获取成员
    const membersRes = await axios.get(`/api/projects/${projectId}/members`)
    members.value = membersRes.data

    // 获取所有即梦账号
    const allAccountsRes = await axios.get('/api/accounts')
    allAccounts.value = allAccountsRes.data

    // 获取所有用户
    const usersRes = await axios.get('/api/users')
    allUsers.value = usersRes.data
  } catch (err) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const saveSettings = async () => {
  try {
    await axios.put(`/api/projects/${projectId}/settings`, {
      episode_count: settings.episode_count
    })
    ElMessage.success('设置已保存')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  }
}

const saveProjectAccounts = async () => {
  try {
    await axios.put(`/api/projects/${projectId}/accounts`, {
      accounts: projectAccounts.value
    })
    ElMessage.success('账号池已更新')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  }
}

const showAddMemberDialog = () => {
  selectedUserId.value = ''
  addMemberDialogVisible.value = true
}

const addMember = async () => {
  if (!selectedUserId.value) {
    ElMessage.warning('请选择用户')
    return
  }

  addMemberLoading.value = true
  try {
    await axios.post(`/api/projects/${projectId}/members`, {
      user_id: selectedUserId.value,
      role: 'collaborator'
    })
    ElMessage.success('协作者已添加')
    addMemberDialogVisible.value = false
    fetchData()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '添加失败')
  } finally {
    addMemberLoading.value = false
  }
}

const showAccountDialog = (row) => {
  selectedMemberId.value = row.user_id
  selectedAccounts.value = [...row.accounts]
  accountDialogVisible.value = true
}

const saveMemberAccounts = async () => {
  accountLoading.value = true
  try {
    await axios.put(`/api/projects/${projectId}/member-accounts/${selectedMemberId.value}`, {
      accounts: selectedAccounts.value
    })
    ElMessage.success('账号已分配')
    accountDialogVisible.value = false
    fetchData()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally {
    accountLoading.value = false
  }
}

const removeMember = async (row) => {
  try {
    await ElMessageBox.confirm(`确定移除协作者 "${row.username}"？`, '确认', { type: 'warning' })
    await axios.delete(`/api/projects/${projectId}/members/${row.user_id}`)
    ElMessage.success('协作者已移除')
    fetchData()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err.response?.data?.detail || '移除失败')
    }
  }
}

onMounted(fetchData)
</script>

<style scoped>
.project-settings {
  padding: 20px;
}

.section {
  margin-bottom: 20px;
}

.section-title {
  font-weight: bold;
  margin-bottom: 10px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/views/ProjectSettings.vue
git commit -m "$(cat <<'EOF'
feat(frontend): add ProjectSettings page

- Basic settings: episode count
- Account pool: multi-select from all accounts
- Member management: add/remove collaborators
- Assign accounts to collaborators

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 15: 更新 App.vue 添加用户信息

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: 更新 App.vue**

```vue
<!-- frontend/src/App.vue -->
<template>
  <el-container class="app-container">
    <el-header height="60px" class="app-header">
      <div class="header-left">
        <span class="app-title">🎬 Dreamina 视频生成</span>
      </div>
      <div class="header-center">
        <AccountSelector v-if="authStore.isLoggedIn" />
      </div>
      <div class="header-right">
        <template v-if="authStore.isLoggedIn">
          <el-button text @click="$router.push('/projects')">项目</el-button>
          <el-button text @click="$router.push('/accounts')">账号管理</el-button>
          <el-button v-if="authStore.isAdmin" text @click="$router.push('/admin')">Admin</el-button>
          <el-dropdown @command="handleCommand">
            <span class="user-dropdown">
              {{ authStore.user?.username }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </div>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowDown } from '@element-plus/icons-vue'
import AccountSelector from './components/AccountSelector.vue'
import { useAuthStore } from './stores/auth'

const router = useRouter()
const authStore = useAuthStore()

onMounted(async () => {
  await authStore.fetchUser()
})

const handleCommand = (command) => {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<style>
body { margin: 0; }
.app-container { min-height: 100vh; }
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #1e1e2e;
  border-bottom: none;
  padding: 0 20px;
}
.app-title {
  font-size: 18px;
  font-weight: bold;
  color: #fff;
}
.header-right {
  display: flex;
  gap: 8px;
  align-items: center;
}
.user-dropdown {
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}
.app-main {
  padding: 0;
  overflow: hidden;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/App.vue
git commit -m "$(cat <<'EOF'
feat(frontend): update App.vue with user info and logout

- Show username in header dropdown
- Logout button
- Conditional rendering based on auth state
- Show Admin button only for admins

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 16: 任务提交页添加分集选择

**Files:**
- Modify: `frontend/src/views/SubmitTask.vue`

- [ ] **Step 1: 添加分集下拉框和账号过滤**

在 SubmitTask.vue 中添加分集字段和账号过滤逻辑。由于文件较大，这里只展示关键修改：

```vue
<!-- 在表单中添加分集选择，在 account_id 选择后添加： -->
<el-form-item label="分集">
  <el-select v-model="form.episode" placeholder="选择分集" clearable>
    <el-option
      v-for="n in episodeCount"
      :key="n"
      :label="`第 ${n} 集`"
      :value="n"
    />
  </el-select>
</el-form-item>
```

同时需要在获取项目信息时获取 episode_count，在账号列表中只显示用户可用的账号。

- [ ] **Step 2: 提交**

```bash
git add frontend/src/views/SubmitTask.vue
git commit -m "$(cat <<'EOF'
feat(frontend): add episode selector to SubmitTask

- Episode dropdown (1 to project episode_count)
- Filter accounts by user permission

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 17: 任务列表添加分集筛选和创建者

**Files:**
- Modify: `frontend/src/views/TaskList.vue`
- Modify: `frontend/src/views/ProjectTasks.vue`

- [ ] **Step 1: 添加分集筛选和创建者列**

在筛选条件中添加分集筛选，在表格中添加创建者列。

- [ ] **Step 2: 提交**

```bash
git add frontend/src/views/TaskList.vue frontend/src/views/ProjectTasks.vue
git commit -m "$(cat <<'EOF'
feat(frontend): add episode filter and creator column to task list

- Episode filter dropdown
- Creator username column
- Episode display column

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 18: 安装 bcrypt 依赖

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: 添加 bcrypt 到依赖**

```
# backend/requirements.txt
# 在现有依赖后添加：
bcrypt>=4.0.0
```

- [ ] **Step 2: 提交**

```bash
git add backend/requirements.txt
git commit -m "$(cat <<'EOF'
chore(deps): add bcrypt for password hashing

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 19: 更新 Admin 入口页面

**Files:**
- Modify: `frontend/src/views/AdminEntry.vue`

- [ ] **Step 1: 添加用户管理入口**

在 AdminEntry.vue 中添加用户管理链接。

- [ ] **Step 2: 提交**

```bash
git add frontend/src/views/AdminEntry.vue
git commit -m "$(cat <<'EOF'
feat(frontend): add user management link to AdminEntry

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## 实现检查清单

完成后验证以下功能：

- [ ] 首次访问自动跳转到登录页
- [ ] 第一个注册用户自动成为管理员
- [ ] 管理员可以创建用户
- [ ] 管理员可以重置用户密码
- [ ] 管理员可以设置/取消管理员
- [ ] 管理员可以软删除用户
- [ ] 项目创建者自动成为拥有者
- [ ] 项目拥有者可以添加协作者
- [ ] 项目拥有者可以配置账号池
- [ ] 项目拥有者可以分配协作者账号
- [ ] 协作者只能看到自己的任务
- [ ] 协作者只能使用分配的账号
- [ ] 任务可以设置分集
- [ ] 任务列表可以按分集筛选