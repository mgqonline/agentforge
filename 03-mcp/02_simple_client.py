import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_client():
    # 1. 配置服务器参数 (指向我们刚创建的 server 文件)
    # 使用当前虚拟环境的 python 解释器运行
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[os.path.join(os.path.dirname(__file__), "01_simple_server.py")],
        env=os.environ.copy()
    )

    print("正在连接到 MCP Server...")
    print("(请稍等，正在建立握手连接...)")
    
    # 2. 建立连接
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化
            await session.initialize()
            print("连接成功！\n")

            # 3. 测试：列出并读取资源
            print("--- 测试 Resources ---")
            resources = await session.list_resources()
            print(f"可用资源: {[r.name for r in resources.resources]}")
            
            content = await session.read_resource("memo://learning-notes")
            print(f"读取资源内容 (memo://learning-notes):\n{content.contents[0].text}\n")

            # 4. 测试：列出并调用工具
            print("--- 测试 Tools ---")
            tools = await session.list_tools()
            print(f"可用工具: {[t.name for t in tools.tools]}")
            
            result = await session.call_tool("get_weather", arguments={"city": "上海"})
            print(f"调用 get_weather('上海'):\n{result.content[0].text}\n")

            # 5. 测试：列出并获取提示词
            print("--- 测试 Prompts ---")
            prompts = await session.list_prompts()
            print(f"可用提示词模板: {[p.name for p in prompts.prompts]}")
            
            prompt_result = await session.get_prompt("weather-report", arguments={"city": "北京"})
            print(f"获取提示词 'weather-report':\n{prompt_result.messages[0].content.text}")

if __name__ == "__main__":
    asyncio.run(run_client())
