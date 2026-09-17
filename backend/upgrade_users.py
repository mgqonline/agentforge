import asyncio
import asyncpg
import os
import json

async def main():
    db_url = os.getenv("ASYNC_DATABASE_URL", "postgresql://aiuser:aipassword@localhost:5432/ailearning")
    try:
        conn = await asyncpg.connect(db_url)
        roles = json.dumps(["admin", "operator", "approver"])
        await conn.execute("UPDATE agent_users SET roles = $1::jsonb", roles)
        print("Successfully upgraded all users to admin.")
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
