# backend/main.py
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import POLL_INTERVAL
from database import init_db
from routers.accounts import router as accounts_router
from routers.tasks import router as tasks_router
from services.poller import poll_tasks

logging.basicConfig(level=logging.INFO)
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler.add_job(poll_tasks, "interval", seconds=POLL_INTERVAL, id="poller")
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Dreamina Web UI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts_router)
app.include_router(tasks_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}