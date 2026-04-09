# backend/database.py
import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from config import DB_PATH

# 全局数据库连接
_db_connection: aiosqlite.Connection | None = None


CREATE_TASKS_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    account_id  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    result_url  TEXT,
    error_msg   TEXT,
    prompt      TEXT,
    params      TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    submit_id   TEXT
);
"""

CREATE_PROJECTS_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    deleted_at  TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""

CREATE_MATERIALS_SQL = """
CREATE TABLE IF NOT EXISTS materials (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL,
    file_path   TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
"""

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

MIGRATE_ADD_SUBMIT_ID_SQL = """
ALTER TABLE tasks ADD COLUMN submit_id TEXT;
"""

MIGRATE_ADD_PROJECT_ID_SQL = """
ALTER TABLE tasks ADD COLUMN project_id TEXT;
"""

MIGRATE_ADD_LABEL_SQL = """
ALTER TABLE tasks ADD COLUMN label TEXT;
"""

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

async def get_db() -> aiosqlite.Connection:
    """获取数据库连接（用于 FastAPI 依赖注入）"""
    global _db_connection
    if _db_connection is None:
        _db_connection = await aiosqlite.connect(str(DB_PATH))
        _db_connection.row_factory = aiosqlite.Row
    return _db_connection


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[aiosqlite.Connection, None]:
    """数据库连接上下文管理器（用于非请求场景如 poller）"""
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def close_db():
    """关闭数据库连接"""
    global _db_connection
    if _db_connection is not None:
        await _db_connection.close()
        _db_connection = None


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