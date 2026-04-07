# backend/database.py
import aiosqlite
from config import DB_PATH

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
    updated_at  TEXT NOT NULL
);
"""

async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    return db

async def init_db():
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(CREATE_TASKS_SQL)
        await db.commit()