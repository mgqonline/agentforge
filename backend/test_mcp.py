import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
import sys

async def main():
    config = {
        "transport": "stdio",
        "command": sys.executable,
        "args": ["mcp_server.py"]
    }
    client = MultiServerMCPClient(connections={"enterprise": config})
    async with client.session("enterprise") as session:
        from langchain_mcp_adapters.tools import load_mcp_tools
        tools = await load_mcp_tools(session)
        print([t.name for t in tools])

asyncio.run(main())
