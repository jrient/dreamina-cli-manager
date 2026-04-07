# Dreamina Web UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Docker-based web application that lets users submit `dreamina multimodal2video` tasks via browser, select from admin-provided accounts, track async results, and download generated videos.

**Architecture:** FastAPI backend wraps the `dreamina` CLI using per-account XDG_CONFIG_HOME isolation; APScheduler polls task status every 10 seconds and updates SQLite; Vue 3 + Element Plus frontend polls the API and displays task cards with video links.

**Tech Stack:** Python 3.11 / FastAPI / aiosqlite / APScheduler / Vue 3 / Vite / Element Plus / Nginx / Docker Compose

---

## File Map

```
project/                          ← working directory
├── docker-compose.yml
├── accounts/                     ← admin drops *.json credential files here
├── db/                           ← SQLite volume mount (auto-created)
├── uploads/                      ← temp upload volume (auto-created)
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config.py                 ← env-driven settings (paths, intervals)
│   ├── database.py               ← aiosqlite pool, init_db()
│   ├── models.py                 ← Pydantic request/response schemas
│   ├── main.py                   ← FastAPI app, lifespan, router mount
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── accounts.py           ← GET /api/accounts, /api/accounts/{id}/credit
│   │   └── tasks.py              ← POST/GET/DELETE /api/tasks
│   ├── services/
│   │   ├── __init__.py
│   │   ├── dreamina.py           ← subprocess wrappers (submit, query, credit, init)
│   │   └── poller.py             ← APScheduler job definition
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py           ← test DB fixture, mock_dreamina fixture
│       ├── test_accounts.py
│       └── test_tasks.py
│
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── main.js
        ├── App.vue
        ├── router/
        │   └── index.js
        ├── api/
        │   └── index.js          ← fetch wrappers for all backend endpoints
        ├── components/
        │   └── AccountSelector.vue
        └── views/
            ├── SubmitTask.vue
            └── TaskList.vue
```

---

## Task 1: Root Scaffolding & Docker Compose

**Files:**
- Create: `docker-compose.yml`
- Create: `accounts/.gitkeep`
- Create: `db/.gitkeep`
- Create: `uploads/.gitkeep`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p accounts db uploads backend/routers backend/services backend/tests frontend/src/router frontend/src/api frontend/src/components frontend/src/views
touch accounts/.gitkeep db/.gitkeep uploads/.gitkeep
```

- [ ] **Step 2: Write docker-compose.yml**

```yaml
# docker-compose.yml
networks:
  dreamina-net:
    driver: bridge

services:
  backend:
    build: ./backend
    container_name: dreamina-backend
    environment:
      - ACCOUNTS_DIR=/app/accounts
      - CONFIG_BASE=/app/configs
      - DB_PATH=/app/db/tasks.db
      - UPLOAD_DIR=/app/uploads
      - POLL_INTERVAL=10
    volumes:
      - ./accounts:/app/accounts:ro
      - ./db:/app/db
      - ./uploads:/app/uploads
    networks:
      - dreamina-net
    restart: unless-stopped

  frontend:
    build: ./frontend
    container_name: dreamina-frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    networks:
      - dreamina-net
    restart: unless-stopped
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml accounts/.gitkeep db/.gitkeep uploads/.gitkeep
git commit -m "feat: root scaffolding and docker-compose"
```

---

## Task 2: Backend — Config & Database

**Files:**
- Create: `backend/config.py`
- Create: `backend/database.py`
- Create: `backend/requirements.txt`

- [ ] **Step 1: Write requirements.txt**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
aiosqlite==0.20.0
python-multipart==0.0.9
apscheduler==3.10.4
aiofiles==23.2.1
```

- [ ] **Step 2: Write config.py**

```python
# backend/config.py
import os
from pathlib import Path

ACCOUNTS_DIR = Path(os.getenv("ACCOUNTS_DIR", "/app/accounts"))
CONFIG_BASE = Path(os.getenv("CONFIG_BASE", "/app/configs"))
DB_PATH = Path(os.getenv("DB_PATH", "/app/db/tasks.db"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "10"))

# Ensure runtime directories exist
CONFIG_BASE.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 3: Write database.py**

```python
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
```

- [ ] **Step 4: Write tests/conftest.py**

```python
# backend/tests/conftest.py
import pytest
import pytest_asyncio
import aiosqlite
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock


@pytest_asyncio.fixture
async def test_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("database.DB_PATH", db_path)
    monkeypatch.setattr("config.DB_PATH", db_path)
    import database
    database.DB_PATH = db_path
    await database.init_db()
    return db_path


@pytest.fixture
def mock_dreamina():
    """Mock subprocess calls to dreamina CLI."""
    with patch("services.dreamina.run_cli") as mock:
        yield mock


@pytest_asyncio.fixture
async def client(test_db):
    from main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
```

- [ ] **Step 5: Add pytest-asyncio to requirements**

Append to `backend/requirements.txt`:
```
pytest==8.2.0
pytest-asyncio==0.23.6
httpx==0.27.0
```

- [ ] **Step 6: Commit**

```bash
git add backend/config.py backend/database.py backend/requirements.txt backend/tests/conftest.py
git commit -m "feat(backend): config, database schema, test fixtures"
```

---

## Task 3: Backend — Dreamina CLI Service

**Files:**
- Create: `backend/services/__init__.py`
- Create: `backend/services/dreamina.py`

> **Note:** The exact stdout format of `dreamina` CLI is not documented. The parser below uses regex patterns that match common CLI output styles. Adjust `SUBMIT_ID_RE` and `RESULT_URL_RE` if the actual output differs.

- [ ] **Step 1: Write services/dreamina.py**

```python
# backend/services/dreamina.py
import asyncio
import json
import os
import re
import shutil
from pathlib import Path
from typing import Optional

from config import ACCOUNTS_DIR, CONFIG_BASE

# Regex patterns for parsing dreamina CLI output
SUBMIT_ID_RE = re.compile(r'(?:submit[_\s]id|task[_\s]id)[:\s]+([a-f0-9]{8,})', re.I)
RESULT_URL_RE = re.compile(r'https?://\S+\.(?:mp4|mov|webm)\S*', re.I)
STATUS_RE = re.compile(r'status[:\s]+(\w+)', re.I)
CREDIT_RE = re.compile(r'(?:credit|balance)[:\s]+([\d.]+)', re.I)


def get_account_env(account_id: str) -> dict:
    """Return environment with XDG_CONFIG_HOME set for the given account."""
    config_dir = CONFIG_BASE / account_id
    config_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["XDG_CONFIG_HOME"] = str(config_dir)
    return env


async def run_cli(args: list[str], account_id: str, stdin: Optional[str] = None) -> tuple[int, str, str]:
    """Run dreamina CLI with account isolation. Returns (returncode, stdout, stderr)."""
    env = get_account_env(account_id)
    proc = await asyncio.create_subprocess_exec(
        "dreamina", *args,
        stdin=asyncio.subprocess.PIPE if stdin else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdin_bytes = stdin.encode() if stdin else None
    stdout, stderr = await proc.communicate(input=stdin_bytes)
    return proc.returncode, stdout.decode(), stderr.decode()


async def ensure_account_initialized(account_id: str) -> None:
    """Import JSON credentials into account-specific config dir (idempotent)."""
    marker = CONFIG_BASE / account_id / ".initialized"
    if marker.exists():
        return

    json_path = ACCOUNTS_DIR / f"{account_id}.json"
    if not json_path.exists():
        raise FileNotFoundError(f"Account JSON not found: {json_path}")

    credentials = json_path.read_text()
    returncode, stdout, stderr = await run_cli(
        ["import_login_response"], account_id=account_id, stdin=credentials
    )
    if returncode != 0:
        raise RuntimeError(f"Account init failed: {stderr or stdout}")

    marker.touch()


async def get_credit(account_id: str) -> str:
    """Return credit balance string for account."""
    await ensure_account_initialized(account_id)
    returncode, stdout, stderr = await run_cli(["user_credit"], account_id=account_id)
    if returncode != 0:
        raise RuntimeError(f"user_credit failed: {stderr or stdout}")
    m = CREDIT_RE.search(stdout)
    return m.group(1) if m else stdout.strip()


async def submit_multimodal2video(
    account_id: str,
    image_paths: list[str],
    video_paths: list[str],
    audio_paths: list[str],
    prompt: str,
    duration: int,
    ratio: str,
    model_version: str,
) -> str:
    """Submit a multimodal2video task. Returns submit_id."""
    await ensure_account_initialized(account_id)

    args = ["multimodal2video"]
    for p in image_paths:
        args += ["--image", p]
    for p in video_paths:
        args += ["--video", p]
    for p in audio_paths:
        args += ["--audio", p]
    if prompt:
        args += ["--prompt", prompt]
    args += ["--duration", str(duration)]
    if ratio:
        args += ["--ratio", ratio]
    if model_version:
        args += ["--model_version", model_version]

    returncode, stdout, stderr = await run_cli(args, account_id=account_id)
    combined = stdout + "\n" + stderr

    if returncode != 0:
        raise RuntimeError(f"multimodal2video failed: {combined.strip()}")

    m = SUBMIT_ID_RE.search(combined)
    if not m:
        # Try to find any hex-looking ID if regex misses
        fallback = re.search(r'\b([a-f0-9]{12,})\b', combined)
        if fallback:
            return fallback.group(1)
        raise RuntimeError(f"Could not parse submit_id from output: {combined.strip()}")

    return m.group(1)


async def query_result(account_id: str, submit_id: str) -> dict:
    """Query task status. Returns dict with keys: status, result_url, error_msg."""
    await ensure_account_initialized(account_id)
    returncode, stdout, stderr = await run_cli(
        ["query_result", f"--submit_id={submit_id}"], account_id=account_id
    )
    combined = stdout + "\n" + stderr

    # Try JSON parse first
    try:
        data = json.loads(stdout.strip())
        if isinstance(data, dict):
            status = data.get("status", "processing")
            result_url = data.get("result_url") or data.get("url") or data.get("video_url")
            error_msg = data.get("error") or data.get("message") if status == "failed" else None
            return {"status": status, "result_url": result_url, "error_msg": error_msg}
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: regex parse
    status_match = STATUS_RE.search(combined)
    raw_status = status_match.group(1).lower() if status_match else "processing"

    # Normalize status to our four states
    if raw_status in ("success", "succeeded", "completed", "done"):
        status = "success"
    elif raw_status in ("fail", "failed", "error"):
        status = "failed"
    elif raw_status in ("pending", "queued", "waiting"):
        status = "pending"
    else:
        status = "processing"

    url_match = RESULT_URL_RE.search(combined)
    result_url = url_match.group(0) if url_match else None

    error_msg = None
    if status == "failed":
        error_msg = combined.strip()

    return {"status": status, "result_url": result_url, "error_msg": error_msg}
```

- [ ] **Step 2: Write tests/test_accounts.py (accounts-only, CLI-mocked)**

```python
# backend/tests/test_accounts.py
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_list_accounts_empty(client, tmp_path, monkeypatch):
    monkeypatch.setattr("config.ACCOUNTS_DIR", tmp_path)
    import routers.accounts as acc_router
    monkeypatch.setattr(acc_router, "ACCOUNTS_DIR", tmp_path)
    resp = await client.get("/api/accounts")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_accounts_with_files(client, tmp_path, monkeypatch):
    (tmp_path / "alice.json").write_text("{}")
    (tmp_path / "bob.json").write_text("{}")
    import routers.accounts as acc_router
    monkeypatch.setattr(acc_router, "ACCOUNTS_DIR", tmp_path)
    resp = await client.get("/api/accounts")
    assert resp.status_code == 200
    ids = {a["id"] for a in resp.json()}
    assert ids == {"alice", "bob"}
```

- [ ] **Step 3: Run tests (expect failures since routers not written yet)**

```bash
cd backend && python -m pytest tests/test_accounts.py -v 2>&1 | head -20
```

Expected: Import error or test collection error — confirms tests are wired up.

- [ ] **Step 4: Commit**

```bash
git add backend/services/__init__.py backend/services/dreamina.py backend/tests/test_accounts.py
git commit -m "feat(backend): dreamina CLI service wrapper with account isolation"
```

---

## Task 4: Backend — Models & Accounts Router

**Files:**
- Create: `backend/models.py`
- Create: `backend/routers/__init__.py`
- Create: `backend/routers/accounts.py`

- [ ] **Step 1: Write models.py**

```python
# backend/models.py
from pydantic import BaseModel
from typing import Optional


class AccountInfo(BaseModel):
    id: str
    filename: str


class CreditResponse(BaseModel):
    account_id: str
    credit: str


class TaskCreate(BaseModel):
    account_id: str
    prompt: Optional[str] = ""
    duration: int = 5
    ratio: str = "16:9"
    model_version: str = "seedance2.0fast"


class TaskResponse(BaseModel):
    id: str
    account_id: str
    status: str
    result_url: Optional[str] = None
    error_msg: Optional[str] = None
    prompt: Optional[str] = None
    params: Optional[str] = None
    created_at: str
    updated_at: str
```

- [ ] **Step 2: Write routers/accounts.py**

```python
# backend/routers/accounts.py
from fastapi import APIRouter, HTTPException
from models import AccountInfo, CreditResponse
from services.dreamina import get_credit
from config import ACCOUNTS_DIR

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountInfo])
async def list_accounts():
    accounts = []
    for f in sorted(ACCOUNTS_DIR.glob("*.json")):
        accounts.append(AccountInfo(id=f.stem, filename=f.name))
    return accounts


@router.get("/{account_id}/credit", response_model=CreditResponse)
async def get_account_credit(account_id: str):
    json_path = ACCOUNTS_DIR / f"{account_id}.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found")
    try:
        credit = await get_credit(account_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return CreditResponse(account_id=account_id, credit=credit)
```

- [ ] **Step 3: Write routers/__init__.py**

```python
# backend/routers/__init__.py
```

- [ ] **Step 4: Run account tests (they should now pass)**

```bash
cd backend && python -m pytest tests/test_accounts.py -v
```

Expected: Both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/models.py backend/routers/__init__.py backend/routers/accounts.py
git commit -m "feat(backend): models and accounts router"
```

---

## Task 5: Backend — Tasks Router

**Files:**
- Create: `backend/routers/tasks.py`
- Create: `backend/tests/test_tasks.py`

- [ ] **Step 1: Write failing tests for task submission**

```python
# backend/tests/test_tasks.py
import pytest
import json
from unittest.mock import patch, AsyncMock
from io import BytesIO


@pytest.mark.asyncio
async def test_submit_task_no_files(client):
    resp = await client.post("/api/tasks", data={
        "account_id": "alice",
        "duration": "5",
        "ratio": "16:9",
        "model_version": "seedance2.0fast",
    })
    assert resp.status_code == 422  # must have at least one image or video


@pytest.mark.asyncio
async def test_submit_task_success(client, tmp_path, monkeypatch):
    import routers.tasks as task_router
    monkeypatch.setattr("config.ACCOUNTS_DIR", tmp_path)
    monkeypatch.setattr("config.UPLOAD_DIR", tmp_path / "uploads")
    (tmp_path / "uploads").mkdir()
    (tmp_path / "alice.json").write_text("{}")

    with patch("routers.tasks.submit_multimodal2video", new_callable=AsyncMock) as mock_submit:
        mock_submit.return_value = "abc123def456"
        img_bytes = b"\x89PNG\r\n" + b"\x00" * 20  # fake PNG header

        resp = await client.post(
            "/api/tasks",
            data={
                "account_id": "alice",
                "duration": "5",
                "ratio": "16:9",
                "model_version": "seedance2.0fast",
                "prompt": "test prompt",
            },
            files={"images": ("test.png", BytesIO(img_bytes), "image/png")},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == "abc123def456"
    assert body["status"] == "pending"
    assert body["account_id"] == "alice"


@pytest.mark.asyncio
async def test_list_tasks_empty(client):
    resp = await client.get("/api/tasks")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_delete_task(client, tmp_path, monkeypatch):
    import aiosqlite
    from database import get_db
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(monkeypatch._config_db if hasattr(monkeypatch, '_config_db') else tmp_path / 'test.db')) as db:
        pass  # use the test_db fixture via client

    # Insert a task directly
    import database
    async with aiosqlite.connect(str(database.DB_PATH)) as db:
        await db.execute(
            "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?)",
            ("task1", "alice", "success", "http://example.com/v.mp4", None, "p", "{}", now, now)
        )
        await db.commit()

    resp = await client.delete("/api/tasks/task1")
    assert resp.status_code == 204

    resp2 = await client.get("/api/tasks/task1")
    assert resp2.status_code == 404
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest tests/test_tasks.py -v 2>&1 | head -30
```

Expected: ImportError or 404 (router not mounted yet).

- [ ] **Step 3: Write routers/tasks.py**

```python
# backend/routers/tasks.py
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from config import ACCOUNTS_DIR, UPLOAD_DIR, DB_PATH
from models import TaskResponse
from services.dreamina import submit_multimodal2video

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_task(row) -> TaskResponse:
    return TaskResponse(
        id=row["id"],
        account_id=row["account_id"],
        status=row["status"],
        result_url=row["result_url"],
        error_msg=row["error_msg"],
        prompt=row["prompt"],
        params=row["params"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TaskResponse)
async def create_task(
    account_id: str = Form(...),
    prompt: str = Form(""),
    duration: int = Form(5),
    ratio: str = Form("16:9"),
    model_version: str = Form("seedance2.0fast"),
    images: list[UploadFile] = File(default=[]),
    videos: list[UploadFile] = File(default=[]),
    audios: list[UploadFile] = File(default=[]),
):
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

    account_json = ACCOUNTS_DIR / f"{account_id}.json"
    if not account_json.exists():
        raise HTTPException(404, f"Account '{account_id}' not found")

    # Save uploaded files to temp directory (named after a placeholder; rename after submit)
    tmp_dir = UPLOAD_DIR / "_tmp_new"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    async def save(upload: UploadFile, dest_dir: Path) -> str:
        dest = dest_dir / upload.filename
        content = await upload.read()
        dest.write_bytes(content)
        return str(dest)

    image_paths = [await save(f, tmp_dir) for f in images]
    video_paths = [await save(f, tmp_dir) for f in videos]
    audio_paths = [await save(f, tmp_dir) for f in audios]

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
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=502, detail=str(e))

    # Rename temp dir to submit_id
    final_dir = UPLOAD_DIR / submit_id
    shutil.move(str(tmp_dir), str(final_dir))

    params = json.dumps({"duration": duration, "ratio": ratio, "model_version": model_version})
    now = _now()

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?)",
            (submit_id, account_id, "pending", None, None, prompt, params, now, now),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM tasks WHERE id=?", (submit_id,))
        row = await cursor.fetchone()

    return _row_to_task(row)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(status: Optional[str] = None, account_id: Optional[str] = None):
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"
        params.append(status)
    if account_id:
        query += " AND account_id=?"
        params.append(account_id)
    query += " ORDER BY created_at DESC"

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

    return [_row_to_task(r) for r in rows]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(404, "Task not found")
    return _row_to_task(row)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        cursor = await db.execute("SELECT id FROM tasks WHERE id=?", (task_id,))
        if not await cursor.fetchone():
            raise HTTPException(404, "Task not found")
        await db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        await db.commit()

    task_dir = UPLOAD_DIR / task_id
    if task_dir.exists():
        shutil.rmtree(task_dir, ignore_errors=True)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 4: Run task tests**

```bash
cd backend && python -m pytest tests/test_tasks.py -v
```

Expected: Most pass. Fix any failures before continuing.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/tasks.py backend/tests/test_tasks.py
git commit -m "feat(backend): tasks router with file upload and CRUD"
```

---

## Task 6: Backend — APScheduler Poller

**Files:**
- Create: `backend/services/poller.py`

- [ ] **Step 1: Write services/poller.py**

```python
# backend/services/poller.py
import asyncio
import logging
import aiosqlite
from datetime import datetime, timezone

from config import DB_PATH, POLL_INTERVAL
from services.dreamina import query_result

logger = logging.getLogger(__name__)


async def poll_tasks():
    """Check all pending/processing tasks and update their status."""
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, account_id FROM tasks WHERE status IN ('pending', 'processing')"
            )
            rows = await cursor.fetchall()

        for row in rows:
            task_id = row["id"]
            account_id = row["account_id"]
            try:
                result = await query_result(account_id=account_id, submit_id=task_id)
                now = datetime.now(timezone.utc).isoformat()
                async with aiosqlite.connect(str(DB_PATH)) as db:
                    await db.execute(
                        "UPDATE tasks SET status=?, result_url=?, error_msg=?, updated_at=? WHERE id=?",
                        (result["status"], result["result_url"], result["error_msg"], now, task_id),
                    )
                    await db.commit()
                logger.info(f"Task {task_id}: {result['status']}")
            except Exception as e:
                logger.warning(f"Poll failed for task {task_id}: {e}")
    except Exception as e:
        logger.error(f"Poller cycle error: {e}")
```

- [ ] **Step 2: Commit**

```bash
git add backend/services/poller.py
git commit -m "feat(backend): APScheduler polling service"
```

---

## Task 7: Backend — Main App & Dockerfile

**Files:**
- Create: `backend/main.py`
- Create: `backend/Dockerfile`

- [ ] **Step 1: Write main.py**

```python
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
```

- [ ] **Step 2: Run all tests**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 3: Write backend Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dreamina binary
# Option A: copy pre-downloaded binary (recommended for air-gapped envs)
# COPY dreamina /usr/local/bin/dreamina
# RUN chmod +x /usr/local/bin/dreamina

# Option B: download at build time (replace URL with actual release URL)
# RUN curl -L https://github.com/<org>/dreamina/releases/latest/download/dreamina-linux-amd64 \
#     -o /usr/local/bin/dreamina && chmod +x /usr/local/bin/dreamina

# For development: assume dreamina is already on PATH via volume or host install
# Remove this line and uncomment one of the above for production
RUN echo "Ensure dreamina binary is available" && which dreamina || echo "WARNING: dreamina not found, add it before production use"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

> **Note on dreamina binary:** The Dockerfile above has three options. For initial deployment, copy the `dreamina` binary into `backend/` and uncomment Option A. The binary path on your current system can be found with `which dreamina`.

- [ ] **Step 4: Copy dreamina binary into backend build context**

```bash
cp $(which dreamina) backend/dreamina
```

Then uncomment Option A in the Dockerfile.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/Dockerfile
git commit -m "feat(backend): FastAPI app wiring, APScheduler, Dockerfile"
```

---

## Task 8: Frontend — Project Setup

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/src/main.js`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.js`

- [ ] **Step 1: Initialize Vue 3 project**

```bash
cd frontend && npm create vite@latest . -- --template vue --yes
npm install element-plus @element-plus/icons-vue vue-router@4
```

- [ ] **Step 2: Write vite.config.js**

```javascript
// frontend/vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
```

- [ ] **Step 3: Write src/router/index.js**

```javascript
// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import SubmitTask from '../views/SubmitTask.vue'
import TaskList from '../views/TaskList.vue'

const routes = [
  { path: '/', component: SubmitTask },
  { path: '/tasks', component: TaskList },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
```

- [ ] **Step 4: Write src/main.js**

```javascript
// frontend/src/main.js
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as Icons from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(ElementPlus)
app.use(router)
Object.entries(Icons).forEach(([name, icon]) => app.component(name, icon))
app.mount('#app')
```

- [ ] **Step 5: Write src/App.vue**

```vue
<!-- frontend/src/App.vue -->
<template>
  <el-container class="app-container">
    <el-header height="60px" class="app-header">
      <div class="header-left">
        <span class="app-title">Dreamina 视频生成</span>
      </div>
      <div class="header-center">
        <AccountSelector />
      </div>
      <div class="header-right">
        <el-menu mode="horizontal" :router="true" :default-active="$route.path">
          <el-menu-item index="/">提交任务</el-menu-item>
          <el-menu-item index="/tasks">任务列表</el-menu-item>
        </el-menu>
      </div>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import AccountSelector from './components/AccountSelector.vue'
</script>

<style>
.app-container { min-height: 100vh; }
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
}
.app-title { font-size: 18px; font-weight: bold; color: #303133; }
</style>
```

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): Vue 3 + Element Plus project setup with router"
```

---

## Task 9: Frontend — API Client

**Files:**
- Create: `frontend/src/api/index.js`

- [ ] **Step 1: Write src/api/index.js**

```javascript
// frontend/src/api/index.js
const BASE = '/api'

async function request(method, path, { body, params } = {}) {
  let url = BASE + path
  if (params) {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v != null))
    if (qs.toString()) url += '?' + qs
  }
  const resp = await fetch(url, {
    method,
    body,
    // Don't set Content-Type for FormData (browser sets it with boundary)
    ...(body instanceof FormData ? {} : { headers: { 'Content-Type': 'application/json' } }),
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || resp.statusText)
  }
  if (resp.status === 204) return null
  return resp.json()
}

export const api = {
  // Accounts
  listAccounts: () => request('GET', '/accounts'),
  getCredit: (id) => request('GET', `/accounts/${id}/credit`),

  // Tasks
  submitTask: (formData) => request('POST', '/tasks', { body: formData }),
  listTasks: (filters = {}) => request('GET', '/tasks', { params: filters }),
  getTask: (id) => request('GET', `/tasks/${id}`),
  deleteTask: (id) => request('DELETE', `/tasks/${id}`),
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/index.js
git commit -m "feat(frontend): API client module"
```

---

## Task 10: Frontend — AccountSelector Component

**Files:**
- Create: `frontend/src/components/AccountSelector.vue`

- [ ] **Step 1: Write AccountSelector.vue**

```vue
<!-- frontend/src/components/AccountSelector.vue -->
<template>
  <div class="account-selector">
    <el-select
      v-model="selectedId"
      placeholder="选择账号"
      style="width: 160px"
      @change="onAccountChange"
    >
      <el-option
        v-for="acc in accounts"
        :key="acc.id"
        :label="acc.id"
        :value="acc.id"
      />
    </el-select>
    <el-button
      :loading="loadingCredit"
      :disabled="!selectedId"
      text
      type="primary"
      @click="fetchCredit"
    >
      {{ credit !== null ? `余额: ${credit}` : '查询余额' }}
    </el-button>
  </div>
</template>

<script setup>
import { ref, onMounted, provide } from 'vue'
import { api } from '../api/index.js'
import { ElMessage } from 'element-plus'

const accounts = ref([])
const selectedId = ref('')
const credit = ref(null)
const loadingCredit = ref(false)

// Provide selected account to child views
provide('selectedAccountId', selectedId)

onMounted(async () => {
  try {
    accounts.value = await api.listAccounts()
    if (accounts.value.length > 0) selectedId.value = accounts.value[0].id
  } catch (e) {
    ElMessage.error('加载账号失败: ' + e.message)
  }
})

function onAccountChange() {
  credit.value = null
}

async function fetchCredit() {
  if (!selectedId.value) return
  loadingCredit.value = true
  try {
    const res = await api.getCredit(selectedId.value)
    credit.value = res.credit
  } catch (e) {
    ElMessage.error('查询余额失败: ' + e.message)
  } finally {
    loadingCredit.value = false
  }
}
</script>

<style scoped>
.account-selector { display: flex; align-items: center; gap: 8px; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/AccountSelector.vue
git commit -m "feat(frontend): AccountSelector component with credit query"
```

---

## Task 11: Frontend — SubmitTask View

**Files:**
- Create: `frontend/src/views/SubmitTask.vue`

- [ ] **Step 1: Write SubmitTask.vue**

```vue
<!-- frontend/src/views/SubmitTask.vue -->
<template>
  <el-card class="submit-card">
    <template #header>提交 Multimodal2Video 任务</template>

    <el-form :model="form" label-width="100px" @submit.prevent="submit">

      <!-- Images -->
      <el-form-item label="图片">
        <el-upload
          v-model:file-list="form.images"
          list-type="picture-card"
          :auto-upload="false"
          :limit="9"
          accept="image/*"
          multiple
          :on-exceed="() => ElMessage.warning('最多 9 张图片')"
        >
          <el-icon><Plus /></el-icon>
          <template #tip>
            <div class="el-upload__tip">最多 9 张，至少 1 张图片或视频</div>
          </template>
        </el-upload>
      </el-form-item>

      <!-- Audio -->
      <el-form-item label="音频">
        <el-upload
          v-model:file-list="form.audios"
          :auto-upload="false"
          :limit="3"
          accept="audio/*"
          multiple
          :on-exceed="() => ElMessage.warning('最多 3 个音频')"
        >
          <el-button type="primary" plain>选择音频</el-button>
          <template #tip><div class="el-upload__tip">最多 3 个，时长需 2-15 秒</div></template>
        </el-upload>
      </el-form-item>

      <!-- Videos -->
      <el-form-item label="参考视频">
        <el-upload
          v-model:file-list="form.videos"
          :auto-upload="false"
          :limit="3"
          accept="video/*"
          multiple
          :on-exceed="() => ElMessage.warning('最多 3 个视频')"
        >
          <el-button type="primary" plain>选择视频</el-button>
          <template #tip><div class="el-upload__tip">最多 3 个</div></template>
        </el-upload>
      </el-form-item>

      <!-- Prompt -->
      <el-form-item label="提示词">
        <el-input v-model="form.prompt" type="textarea" :rows="3" placeholder="可选：描述生成内容" />
      </el-form-item>

      <!-- Duration -->
      <el-form-item label="时长 (秒)">
        <el-slider v-model="form.duration" :min="4" :max="15" :step="1" show-input style="width: 340px" />
      </el-form-item>

      <!-- Ratio -->
      <el-form-item label="比例">
        <el-radio-group v-model="form.ratio">
          <el-radio-button v-for="r in ratios" :key="r" :label="r">{{ r }}</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <!-- Model -->
      <el-form-item label="模型版本">
        <el-select v-model="form.model_version" style="width: 220px">
          <el-option v-for="m in models" :key="m.value" :label="m.label" :value="m.value" />
        </el-select>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" native-type="submit" :loading="submitting" :disabled="!accountId">
          提交任务
        </el-button>
        <el-text v-if="!accountId" type="warning" style="margin-left: 12px">请先选择账号</el-text>
      </el-form-item>

    </el-form>
  </el-card>
</template>

<script setup>
import { ref, inject } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api/index.js'

const router = useRouter()
const accountId = inject('selectedAccountId')

const ratios = ['1:1', '16:9', '9:16', '4:3', '3:4', '21:9']
const models = [
  { label: 'Seedance 2.0 Fast', value: 'seedance2.0fast' },
  { label: 'Seedance 2.0', value: 'seedance2.0' },
  { label: 'Seedance 2.0 VIP', value: 'seedance2.0_vip' },
  { label: 'Seedance 2.0 Fast VIP', value: 'seedance2.0fast_vip' },
]

const form = ref({
  images: [],
  audios: [],
  videos: [],
  prompt: '',
  duration: 5,
  ratio: '16:9',
  model_version: 'seedance2.0fast',
})
const submitting = ref(false)

async function submit() {
  if (!form.value.images.length && !form.value.videos.length) {
    ElMessage.error('至少需要 1 张图片或 1 个参考视频')
    return
  }

  const fd = new FormData()
  fd.append('account_id', accountId.value)
  fd.append('prompt', form.value.prompt)
  fd.append('duration', form.value.duration)
  fd.append('ratio', form.value.ratio)
  fd.append('model_version', form.value.model_version)

  form.value.images.forEach(f => fd.append('images', f.raw))
  form.value.audios.forEach(f => fd.append('audios', f.raw))
  form.value.videos.forEach(f => fd.append('videos', f.raw))

  submitting.value = true
  try {
    const task = await api.submitTask(fd)
    ElMessage.success(`任务已提交，ID: ${task.id}`)
    router.push('/tasks')
  } catch (e) {
    ElMessage.error('提交失败: ' + e.message)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.submit-card { max-width: 780px; margin: 24px auto; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/SubmitTask.vue
git commit -m "feat(frontend): SubmitTask view with file upload and params"
```

---

## Task 12: Frontend — TaskList View

**Files:**
- Create: `frontend/src/views/TaskList.vue`

- [ ] **Step 1: Write TaskList.vue**

```vue
<!-- frontend/src/views/TaskList.vue -->
<template>
  <div class="task-list">
    <div class="list-header">
      <el-text size="large">任务列表</el-text>
      <el-button :loading="loading" @click="fetchTasks">刷新</el-button>
    </div>

    <el-empty v-if="!tasks.length && !loading" description="暂无任务" />

    <el-card
      v-for="task in tasks"
      :key="task.id"
      class="task-card"
      shadow="hover"
    >
      <div class="task-header">
        <el-tag :type="statusType(task.status)">{{ statusLabel(task.status) }}</el-tag>
        <span class="task-meta">{{ task.account_id }} · {{ formatDate(task.created_at) }}</span>
        <el-button type="danger" text @click="deleteTask(task.id)">
          <el-icon><Delete /></el-icon>
        </el-button>
      </div>

      <div class="task-params" v-if="task.params">
        <el-text type="info" size="small">
          {{ formatParams(task.params) }}
        </el-text>
      </div>

      <div v-if="task.prompt" class="task-prompt">
        <el-text size="small">{{ task.prompt }}</el-text>
      </div>

      <div v-if="task.status === 'success' && task.result_url" class="task-result">
        <el-link :href="task.result_url" target="_blank" type="primary">
          <el-icon><VideoPlay /></el-icon> 下载/查看视频
        </el-link>
      </div>

      <div v-if="task.status === 'failed'" class="task-error">
        <el-text type="danger" size="small">{{ task.error_msg }}</el-text>
        <el-alert
          v-if="task.error_msg && task.error_msg.includes('ComplianceConfirmation')"
          title="请先在 Dreamina Web 端完成合规授权后重试"
          type="warning"
          show-icon
          :closable="false"
          style="margin-top: 8px"
        />
      </div>

      <div class="task-id">
        <el-text type="info" size="small">ID: {{ task.id }}</el-text>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/index.js'

const tasks = ref([])
const loading = ref(false)
let refreshTimer = null

onMounted(() => {
  fetchTasks()
  refreshTimer = setInterval(fetchTasks, 10000)
})

onUnmounted(() => {
  clearInterval(refreshTimer)
})

async function fetchTasks() {
  loading.value = true
  try {
    tasks.value = await api.listTasks()
  } catch (e) {
    ElMessage.error('加载任务失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function deleteTask(id) {
  await ElMessageBox.confirm('确认删除该任务记录？', '提示', { type: 'warning' })
  try {
    await api.deleteTask(id)
    tasks.value = tasks.value.filter(t => t.id !== id)
    ElMessage.success('已删除')
  } catch (e) {
    ElMessage.error('删除失败: ' + e.message)
  }
}

function statusType(s) {
  return { pending: 'info', processing: 'warning', success: 'success', failed: 'danger' }[s] || 'info'
}

function statusLabel(s) {
  return { pending: '等待中', processing: '生成中', success: '已完成', failed: '失败' }[s] || s
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

function formatParams(paramsStr) {
  try {
    const p = JSON.parse(paramsStr)
    return `${p.ratio} · ${p.duration}s · ${p.model_version}`
  } catch {
    return paramsStr
  }
}
</script>

<style scoped>
.task-list { max-width: 860px; margin: 24px auto; }
.list-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.task-card { margin-bottom: 12px; }
.task-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.task-meta { flex: 1; color: #909399; font-size: 13px; }
.task-params { margin-bottom: 4px; }
.task-prompt { margin: 6px 0; }
.task-result { margin-top: 10px; }
.task-error { margin-top: 8px; }
.task-id { margin-top: 8px; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/TaskList.vue
git commit -m "feat(frontend): TaskList view with auto-refresh and delete"
```

---

## Task 13: Frontend — Dockerfile & Nginx

**Files:**
- Create: `frontend/nginx.conf`
- Create: `frontend/Dockerfile`

- [ ] **Step 1: Write nginx.conf**

```nginx
# frontend/nginx.conf
server {
    listen 80;
    server_name _;
    client_max_body_size 500m;

    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        client_max_body_size 500m;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 2: Write frontend Dockerfile**

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

- [ ] **Step 3: Commit**

```bash
git add frontend/nginx.conf frontend/Dockerfile
git commit -m "feat(frontend): Nginx config and multi-stage Dockerfile"
```

---

## Task 14: Integration & First Boot

- [ ] **Step 1: Copy dreamina binary into backend build context**

```bash
cp $(which dreamina) backend/dreamina
chmod +x backend/dreamina
```

Update `backend/Dockerfile` to uncomment Option A:
```dockerfile
COPY dreamina /usr/local/bin/dreamina
RUN chmod +x /usr/local/bin/dreamina
```

- [ ] **Step 2: Add a test account JSON**

```bash
# Place your dreamina credential JSON in accounts/
cp /path/to/your/dreamina_session.json accounts/myaccount.json
```

- [ ] **Step 3: Build and start**

```bash
docker compose up --build -d
```

Expected: Both containers start without errors.

- [ ] **Step 4: Check backend health**

```bash
curl http://localhost/api/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 5: Check accounts endpoint**

```bash
curl http://localhost/api/accounts
```

Expected: `[{"id":"myaccount","filename":"myaccount.json"}]`

- [ ] **Step 6: Open browser**

Navigate to `http://localhost`. Verify:
- Account selector shows your account
- "提交任务" page loads with upload areas
- "任务列表" page shows empty list

- [ ] **Step 7: Submit a test task**

Select the account, upload an image, click "提交任务". Verify:
- Task appears in task list with status "等待中" (pending)
- After 10-30 seconds, status changes to "生成中" (processing)
- Eventually shows "已完成" with video link (or "失败" with error details)

- [ ] **Step 8: Commit final state**

```bash
git add backend/dreamina backend/Dockerfile
git commit -m "feat: add dreamina binary and complete integration"
```

---

## Self-Review Checklist

- [x] **Accounts API** — Task 4 covers list and credit endpoints
- [x] **Tasks submit** — Task 5 covers POST /api/tasks with multipart upload
- [x] **Tasks query/delete** — Task 5 covers GET/DELETE
- [x] **APScheduler poller** — Task 6
- [x] **XDG_CONFIG_HOME account isolation** — Task 3, `get_account_env()`
- [x] **File cleanup after submit** — Task 5, `shutil.rmtree` in delete and post-submit
- [x] **Compliance error handling** — TaskList.vue checks for `ComplianceConfirmation` in error_msg
- [x] **File count validation** — frontend + backend both enforce limits
- [x] **Nginx 500MB upload limit** — Task 13
- [x] **Docker network** — Task 1 docker-compose.yml
- [x] **Vue auto-refresh** — Task 12, `setInterval(fetchTasks, 10000)`
- [x] **dreamina binary in Docker** — Task 14 with clear instructions
