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
    # 确保结果目录存在
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

# 挂载结果文件目录为静态文件服务
app.mount("/results", StaticFiles(directory=str(RESULTS_DIR)), name="results")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/api/health")
async def health():
    return {"status": "ok"}