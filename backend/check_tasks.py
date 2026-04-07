import asyncio
import aiosqlite

async def main():
    async with aiosqlite.connect('/app/db/tasks.db') as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id, account_id, submit_id, status, created_at, updated_at, error_msg FROM tasks")
        rows = await cursor.fetchall()
        for row in rows:
            print(f"{row['id']} | {row['status']} | submit={row['submit_id']} | created={row['created_at']} | updated={row['updated_at']}")

asyncio.run(main())
