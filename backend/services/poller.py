# backend/services/poller.py
import asyncio
import json
import logging
import aiohttp
import aiosqlite
from datetime import datetime, timezone
from pathlib import Path

from config import DB_PATH, POLL_INTERVAL, RESULTS_DIR
from services.dreamina import query_result, submit_multimodal2video, ConcurrencyLimitError

logger = logging.getLogger(__name__)


async def download_result(task_id: str, result_url: str) -> str | None:
    """下载任务结果文件到本地，返回本地路径"""
    if not result_url:
        return None

    # 确定文件扩展名
    ext = ".mp4"
    if ".mov" in result_url.lower():
        ext = ".mov"
    elif ".webm" in result_url.lower():
        ext = ".webm"
    elif ".mp4" in result_url.lower():
        ext = ".mp4"

    # 创建结果目录
    task_result_dir = RESULTS_DIR / task_id
    task_result_dir.mkdir(parents=True, exist_ok=True)

    local_path = task_result_dir / f"result{ext}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(result_url, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    local_path.write_bytes(content)
                    logger.info(f"Downloaded result for task {task_id} to {local_path}")
                    return str(local_path)
                else:
                    logger.warning(f"Failed to download {result_url}: HTTP {resp.status}")
                    return None
    except Exception as e:
        logger.error(f"Download error for task {task_id}: {e}")
        return None


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

                # 如果任务成功且有结果URL，下载到本地
                local_path = None
                if result["status"] == "success" and result["result_url"]:
                    local_path = await download_result(task_id, result["result_url"])

                # 更新数据库：优先使用本地路径
                final_url = local_path if local_path else result["result_url"]
                async with aiosqlite.connect(str(DB_PATH)) as db:
                    await db.execute(
                        "UPDATE tasks SET status=?, result_url=?, error_msg=?, updated_at=? WHERE id=?",
                        (result["status"], final_url, result["error_msg"], now, task_id),
                    )
                    await db.commit()
                logger.info(f"Task {task_id}: {result['status']}" + (f" (downloaded)" if local_path else ""))
            except Exception as e:
                logger.warning(f"Poll failed for task {task_id}: {e}")

        # 调度 queued 任务
        await dispatch_queued_tasks()
    except Exception as e:
        logger.error(f"Poller cycle error: {e}")


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