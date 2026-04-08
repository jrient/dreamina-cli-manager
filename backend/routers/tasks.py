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
        project_id=row["project_id"] if "project_id" in row.keys() else None,
        label=row["label"] if "label" in row.keys() else None,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TaskResponse)
async def create_task(
    account_id: str = Form(...),
    prompt: str = Form(""),
    duration: int = Form(5),
    ratio: str = Form("16:9"),
    model_version: str = Form("seedance2.0fast"),
    project_id: Optional[str] = Form(None),
    label: Optional[str] = Form(None),
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
            "INSERT INTO tasks (id, account_id, status, submit_id, result_url, error_msg, prompt, params, created_at, updated_at, project_id, label) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (task_id, account_id, task_status, submit_id, None, None, prompt, params, now, now, project_id, label),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
        row = await cursor.fetchone()

    return _row_to_task(row)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(status: Optional[str] = None, account_id: Optional[str] = None, project_id: Optional[str] = None):
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


@router.post("/{task_id}/copy", status_code=status.HTTP_201_CREATED, response_model=TaskResponse)
async def copy_task(task_id: str):
    """复制任务：包括项目关联、媒体文件、提示词、标签等"""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, "Task not found")

        # 获取原任务数据
        original = _row_to_task(row)
        params_data = json.loads(original.params or "{}")

    # 生成新任务ID
    new_task_id = uuid.uuid4().hex[:12]
    new_task_dir = UPLOAD_DIR / new_task_id
    new_task_dir.mkdir(parents=True, exist_ok=True)

    # 复制媒体文件
    original_task_dir = UPLOAD_DIR / task_id
    new_image_paths = []
    new_video_paths = []
    new_audio_paths = []

    for path in params_data.get("image_paths", []):
        original_path = Path(path)
        if original_path.exists():
            new_path = new_task_dir / original_path.name
            shutil.copy2(original_path, new_path)
            new_image_paths.append(str(new_path))

    for path in params_data.get("video_paths", []):
        original_path = Path(path)
        if original_path.exists():
            new_path = new_task_dir / original_path.name
            shutil.copy2(original_path, new_path)
            new_video_paths.append(str(new_path))

    for path in params_data.get("audio_paths", []):
        original_path = Path(path)
        if original_path.exists():
            new_path = new_task_dir / original_path.name
            shutil.copy2(original_path, new_path)
            new_audio_paths.append(str(new_path))

    # 更新 params
    new_params = json.dumps({
        "duration": params_data.get("duration", 5),
        "ratio": params_data.get("ratio", "16:9"),
        "model_version": params_data.get("model_version", "seedance2.0fast"),
        "image_paths": new_image_paths,
        "video_paths": new_video_paths,
        "audio_paths": new_audio_paths,
    })

    now = _now()

    # 创建新任务（状态为 queued，等待提交）
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "INSERT INTO tasks (id, account_id, status, submit_id, result_url, error_msg, prompt, params, created_at, updated_at, project_id, label) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (new_task_id, original.account_id, "queued", None, None, None, original.prompt, new_params, now, now, original.project_id, original.label),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM tasks WHERE id=?", (new_task_id,))
        row = await cursor.fetchone()

    return _row_to_task(row)