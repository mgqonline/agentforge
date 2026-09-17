import asyncio
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

async def main():
    async with AsyncSqliteSaver.from_conn_string("memory.db") as memory_saver:
        print("AsyncSqliteSaver initialized successfully.")

asyncio.run(main())
