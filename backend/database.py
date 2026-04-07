# backend/database.py
import aiosqlite
from config import DB_PATH

CREATE_TASKS_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    account_id  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    submit_id   TEXT,
    result_url  TEXT,
    error_msg   TEXT,
    prompt      TEXT,
    params      TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""

MIGRATE_ADD_SUBMIT_ID_SQL = """
ALTER TABLE tasks ADD COLUMN submit_id TEXT;
"""

async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    return db

async def init_db():
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(CREATE_TASKS_SQL)
        await db.commit()
        # 尝试迁移：如果 submit_id 列不存在则添加
        try:
            await db.execute(MIGRATE_ADD_SUBMIT_ID_SQL)
            await db.commit()
        except aiosqlite.OperationalError:
            pass  # 列已存在，跳过