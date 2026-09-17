import asyncio
import asyncpg
import os

async def main():
    db_url = os.getenv("ASYNC_DATABASE_URL", "postgresql://aiuser:aipassword@localhost:5432/ailearning")
    try:
        conn = await asyncpg.connect(db_url)
        rows = await conn.fetch("SELECT * FROM agent_approval_audit")
        print(f"Approvals: {len(rows)}")
        for r in rows:
            print(dict(r))
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
