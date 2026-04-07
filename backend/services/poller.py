# backend/services/poller.py
import asyncio
import json
import logging
import aiosqlite
from datetime import datetime, timezone

from config import DB_PATH, POLL_INTERVAL
from services.dreamina import query_result, submit_multimodal2video, ConcurrencyLimitError

logger = logging.getLogger(__name__)


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