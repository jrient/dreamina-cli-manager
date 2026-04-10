# backend/main.py
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import DB_PATH, POLL_INTERVAL, RESULTS_DIR, UPLOAD_DIR
from database import init_db, close_db
from routers.accounts import router as accounts_router
from routers.tasks import router as tasks_router
from routers.projects import router as projects_router
from routers.auth import router as auth_router
from routers.users import router as users_router
from services.poller import poll_tasks

logging.basicConfig(level=logging.INFO)
scheduler = AsyncIOScheduler()


async def _cleanup_orphan_materials():
    """删除 DB 中 file_path 指向不存在文件的素材记录，防止前端显示 FAILED。"""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id, file_path FROM materials")
        rows = await cursor.fetchall()
        orphans = [r["id"] for r in rows if not Path(r["file_path"]).exists()]
        if orphans:
            await db.executemany("DELETE FROM materials WHERE id=?", [(i,) for i in orphans])
            await db.commit()
            logging.warning("启动清理：删除 %d 条孤立素材记录（文件不存在）", len(orphans))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # 确保结果目录存在
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    await _cleanup_orphan_materials()
    scheduler.add_job(poll_tasks, "interval", seconds=POLL_INTERVAL, id="poller")
    scheduler.start()
    yield
    scheduler.shutdown()
    await close_db()


app = FastAPI(title="Dreamina Web UI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(accounts_router)
app.include_router(tasks_router)
app.include_router(projects_router)

# 挂载结果文件目录为静态文件服务
app.mount("/results", StaticFiles(directory=str(RESULTS_DIR)), name="results")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/api/health")
async def health():
    return {"status": "ok"}