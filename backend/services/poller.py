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