# backend/routers/tasks.py
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

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        # 写入文件
        dest.write_bytes(content)
        # fsync 确保数据写入磁盘
        import os
        fd = os.open(str(dest), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        # 验证文件存在
        if not dest.exists():
            raise RuntimeError(f"文件保存失败: {dest}")
        import datetime
        print(f"[DEBUG {datetime.datetime.utcnow().isoformat()}] 文件已保存: {dest}, 大小: {dest.stat().st_size} bytes, 存在: {dest.is_file()}")
        return str(dest)

    print(f"[DEBUG] 开始保存文件...")
    image_paths = [await save(f, task_dir) for f in images]
    print(f"[DEBUG] 文件保存完成, image_paths: {image_paths}")
    video_paths = [await save(f, task_dir) for f in videos]
    audio_paths = [await save(f, task_dir) for f in audios]

    # 在调用 CLI 前再次验证文件
    for p in image_paths:
        path = Path(p)
        if not path.exists():
            raise RuntimeError(f"文件不存在: {p}")
        print(f"[DEBUG] CLI调用前验证文件存在: {p}, 大小: {path.stat().st_size}")

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
            "INSERT INTO tasks (id, account_id, status, submit_id, result_url, error_msg, prompt, params, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (task_id, account_id, task_status, submit_id, None, None, prompt, params, now, now),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
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