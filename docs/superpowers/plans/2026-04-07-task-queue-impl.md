# 任务队列实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现任务队列，当即梦 API 返回并发限制错误时，任务进入排队状态，等待自动提交。

**Architecture:** 新增 `queued` 状态和 `submit_id` 列，poller 中添加队列调度器，每账号最多 10 个并发任务。

**Tech Stack:** Python, FastAPI, SQLite, pytest-asyncio

---

## 文件结构

| 文件 | 职责 | 改动类型 |
|------|------|----------|
| `backend/database.py` | 数据库 schema，新增 submit_id 列 | 修改 |
| `backend/services/dreamina.py` | 新增 ConcurrencyLimitError | 修改 |
| `backend/routers/tasks.py` | 创建任务时用 UUID，处理限流 | 修改 |
| `backend/services/poller.py` | 新增 dispatch_queued_tasks | 修改 |
| `backend/main.py` | 调度器加入 lifespan | 修改 |
| `backend/models.py` | TaskResponse 新增 submit_id | 修改 |
| `backend/tests/test_tasks.py` | 测试队列功能 | 修改 |
| `frontend/src/views/TaskList.vue` | 显示 queued 状态 | 修改 |

---

### Task 1: 数据库 Schema 变更

**Files:**
- Modify: `backend/database.py`
- Test: `backend/tests/test_tasks.py`

- [ ] **Step 1: 修改 database.py 添加 submit_id 列**

```python
# backend/database.py
import aiosqlite
from config import DB_PATH

CREATE_TASKS_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    account_id  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    submit_id   TEXT,  -- 提交成功后填入，queued 时为 NULL
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
```

- [ ] **Step 2: 修改 models.py 添加 submit_id 字段**

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
    submit_id: Optional[str] = None  # 新增
    result_url: Optional[str] = None
    error_msg: Optional[str] = None
    prompt: Optional[str] = None
    params: Optional[str] = None
    created_at: str
    updated_at: str
```

- [ ] **Step 3: 运行现有测试确认 schema 变更不影响**

Run: `cd /data/project/jm-auto/backend && pytest tests/test_tasks.py -v`
Expected: PASS（测试需要调整 insert 语句适配新列）

- [ ] **Step 4: 修改 test_tasks.py 适配新 schema**

```python
# backend/tests/test_tasks.py 第 68-70 行
await db.execute(
    "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?)",
    ("task1", "alice", "success", "submit1", "http://example.com/v.mp4", None, "p", "{}", now, now)
)
```

- [ ] **Step 5: 再次运行测试**

Run: `cd /data/project/jm-auto/backend && pytest tests/test_tasks.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/database.py backend/models.py backend/tests/test_tasks.py
git commit -m "feat(db): add submit_id column for task queue"
```

---

### Task 2: 新增 ConcurrencyLimitError

**Files:**
- Modify: `backend/services/dreamina.py`

- [ ] **Step 1: 在 dreamina.py 开头添加异常类**

```python
# backend/services/dreamina.py 第 10 行后添加
class ConcurrencyLimitError(Exception):
    """即梦并发限制，任务需排队等待"""
    pass
```

- [ ] **Step 2: 修改 submit_multimodal2video 识别限流错误**

在 `submit_multimodal2video` 函数中，找到抛出 RuntimeError 的位置（约第 143 行），改为：

```python
# backend/services/dreamina.py 第 141-143 行
if gen_status == "fail":
    fail_reason = data.get("fail_reason", "Unknown error")
    # 检查是否为并发限制错误
    if "ExceedConcurrencyLimit" in fail_reason or "ret=1310" in fail_reason:
        raise ConcurrencyLimitError(fail_reason)
    raise RuntimeError(f"任务提交失败: {fail_reason}")
```

- [ ] **Step 3: Commit**

```bash
git add backend/services/dreamina.py
git commit -m "feat(dreamina): add ConcurrencyLimitError for queue handling"
```

---

### Task 3: 任务创建逻辑变更

**Files:**
- Modify: `backend/routers/tasks.py`

- [ ] **Step 1: 在 tasks.py 开头导入 uuid 和异常类**

```python
# backend/routers/tasks.py 第 1-14 行改为
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from config import ACCOUNTS_DIR, UPLOAD_DIR, DB_PATH
from models import TaskResponse
from services.dreamina import submit_multimodal2video, ConcurrencyLimitError, ACCOUNT_HOME_BASE, is_account_logged_in
```

- [ ] **Step 2: 修改 _row_to_task 函数适配 submit_id**

```python
# backend/routers/tasks.py 第 23-34 行
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
    )
```

- [ ] **Step 3: 修改 create_task 函数使用 UUID 和处理限流**

```python
# backend/routers/tasks.py 第 37-113 行完整替换
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
    except ConcurrencyLimitError as e:
        # Task queued, will be submitted later
        pass
    except Exception as e:
        # Real error, clean up and fail
        shutil.rmtree(task_dir, ignore_errors=True)
        raise HTTPException(status_code=502, detail=str(e))

    # Insert task to database
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?)",
            (task_id, account_id, task_status, submit_id, None, None, prompt, params, now, now),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
        row = await cursor.fetchone()

    return _row_to_task(row)
```

- [ ] **Step 4: Commit**

```bash
git add backend/routers/tasks.py
git commit -m "feat(tasks): use UUID and handle ConcurrencyLimitError for queue"
```

---

### Task 4: 队列调度器

**Files:**
- Modify: `backend/services/poller.py`

- [ ] **Step 1: 在 poller.py 添加 dispatch_queued_tasks 函数**

```python
# backend/services/poller.py 在文件末尾添加
import uuid
from services.dreamina import ConcurrencyLimitError

MAX_CONCURRENT_PER_ACCOUNT = 10

async def dispatch_queued_tasks():
    """检查并提交 queued 任务"""
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            db.row_factory = aiosqlite.Row
            # 获取所有 queued 任务
            cursor = await db.execute(
                "SELECT id, account_id, prompt, params FROM tasks WHERE status='queued' ORDER BY created_at"
            )
            queued_tasks = await cursor.fetchall()

        for task in queued_tasks:
            task_id = task["id"]
            account_id = task["account_id"]
            params = json.loads(task["params"]) if task["params"] else {}

            # 检查该账号当前活跃任务数
            async with aiosqlite.connect(str(DB_PATH)) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT COUNT(*) as cnt FROM tasks WHERE account_id=? AND status IN ('pending', 'processing')",
                    (account_id,)
                )
                row = await cursor.fetchone()
                active_count = row["cnt"]

            if active_count >= MAX_CONCURRENT_PER_ACCOUNT:
                continue  # 该账号已满，跳过

            # 尝试提交
            try:
                submit_id = await submit_multimodal2video(
                    account_id=account_id,
                    image_paths=params.get("image_paths", []),
                    video_paths=params.get("video_paths", []),
                    audio_paths=params.get("audio_paths", []),
                    prompt=task["prompt"] or "",
                    duration=params.get("duration", 5),
                    ratio=params.get("ratio", "16:9"),
                    model_version=params.get("model_version", "seedance2.0fast"),
                )
                now = datetime.now(timezone.utc).isoformat()
                async with aiosqlite.connect(str(DB_PATH)) as db:
                    await db.execute(
                        "UPDATE tasks SET status='pending', submit_id=?, updated_at=? WHERE id=?",
                        (submit_id, now, task_id),
                    )
                    await db.commit()
                logger.info(f"Queued task {task_id} submitted as {submit_id}")
            except ConcurrencyLimitError:
                # 仍然限流，下次再试
                logger.debug(f"Task {task_id} still queued (concurrency limit)")
                break  # 其他账号可能也满了，停止本轮
            except Exception as e:
                # 真实错误，标记失败
                now = datetime.now(timezone.utc).isoformat()
                async with aiosqlite.connect(str(DB_PATH)) as db:
                    await db.execute(
                        "UPDATE tasks SET status='failed', error_msg=?, updated_at=? WHERE id=?",
                        (str(e), now, task_id),
                    )
                    await db.commit()
                logger.warning(f"Queued task {task_id} failed: {e}")
    except Exception as e:
        logger.error(f"Queue dispatcher error: {e}")
```

需要在文件开头添加 json import：

```python
# backend/services/poller.py 第 1-5 行
import asyncio
import json
import logging
import aiosqlite
from datetime import datetime, timezone
```

- [ ] **Step 2: 修改 poll_tasks 在轮询后调用调度器**

```python
# backend/services/poller.py 第 13-38 行修改
async def poll_tasks():
    """Check all pending/processing tasks and update their status."""
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, account_id, submit_id FROM tasks WHERE status IN ('pending', 'processing')"
            )
            rows = await cursor.fetchall()

        for row in rows:
            task_id = row["id"]
            submit_id = row["submit_id"]
            account_id = row["account_id"]
            if not submit_id:
                continue  # pending 但无 submit_id，跳过
            try:
                result = await query_result(account_id=account_id, submit_id=submit_id)
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

        # 调度 queued 任务
        await dispatch_queued_tasks()
    except Exception as e:
        logger.error(f"Poller cycle error: {e}")
```

- [ ] **Step 3: Commit**

```bash
git add backend/services/poller.py
git commit -m "feat(poller): add queue dispatcher for queued tasks"
```

---

### Task 5: 前端显示 queued 状态

**Files:**
- Modify: `frontend/src/views/TaskList.vue`

- [ ] **Step 1: 查看当前 TaskList.vue 结构**

先读取文件了解现有状态显示逻辑。

- [ ] **Step 2: 在状态显示中添加 queued**

找到状态显示的部分，添加 queued 状态的显示逻辑：

```vue
<!-- 在状态显示组件中添加 -->
<span v-if="task.status === 'queued'" class="status queued">
  ⏳ 排队中
</span>
```

样式：

```css
.status.queued {
  color: #888;
  background: #f5f5f5;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/TaskList.vue
git commit -m "feat(frontend): show queued status in TaskList"
```

---

### Task 6: 集成测试

**Files:**
- Modify: `backend/tests/test_tasks.py`

- [ ] **Step 1: 添加队列测试**

```python
# backend/tests/test_tasks.py 添加新测试
@pytest.mark.asyncio
async def test_submit_task_queued_on_concurrency_limit(client, tmp_path, monkeypatch):
    import routers.tasks as task_router
    from services.dreamina import ConcurrencyLimitError

    monkeypatch.setattr("config.ACCOUNTS_DIR", tmp_path)
    monkeypatch.setattr("config.UPLOAD_DIR", tmp_path / "uploads")
    (tmp_path / "uploads").mkdir()
    (tmp_path / "alice.json").write_text("{}")

    with patch("routers.tasks.submit_multimodal2video", new_callable=AsyncMock) as mock_submit:
        mock_submit.side_effect = ConcurrencyLimitError("ExceedConcurrencyLimit")
        img_bytes = b"\x89PNG\r\n" + b"\x00" * 20

        resp = await client.post(
            "/api/tasks",
            data={
                "account_id": "alice",
                "duration": "5",
                "ratio": "16:9",
                "model_version": "seedance2.0fast",
            },
            files={"images": ("test.png", BytesIO(img_bytes), "image/png")},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "queued"
    assert body["submit_id"] is None
    assert body["account_id"] == "alice"
```

- [ ] **Step 2: 运行所有测试**

Run: `cd /data/project/jm-auto/backend && pytest tests/ -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_tasks.py
git commit -m "test: add queue functionality tests"
```

---

### Task 7: 最终验证

- [ ] **Step 1: 启动后端服务测试**

Run: `cd /data/project/jm-auto/backend && python main.py`

Expected: 服务启动，无错误

- [ ] **Step 2: 手动测试队列功能**

1. 创建任务触发 ConcurrencyLimitError
2. 检查任务状态为 queued
3. 等待 poller 调度
4. 任务状态变为 pending

- [ ] **Step 3: 最终 commit**

```bash
git add -A
git commit -m "feat: complete task queue implementation"
```