import asyncio
import os
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server

# 1. 初始化 MCP Server
server = Server("learning-mcp-server")

# 2. 定义资源 (Resources)
# 资源就像是模型可以读取的“文件”或“数据块”
@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri="memo://learning-notes",
            name="MCP 学习笔记",
            description="关于 MCP 核心概念的简单说明",
            mimeType="text/plain",
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    if str(uri) == "memo://learning-notes":
        return "MCP 有三个核心概念：\n1. Resources: 模型可以读取的数据。\n2. Tools: 模型可以执行的操作。\n3. Prompts: 预定义的提示词模板。"
    raise ValueError(f"Unknown resource: {uri}")

# 3. 定义工具 (Tools)
# 工具是模型可以调用的函数，类似于 OpenAI 的 Function Calling
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_weather",
            description="获取指定城市的实时天气",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"},
                },
                "required": ["city"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "get_weather":
        city = arguments.get("city", "未知城市")
        # 这里仅作演示，实际应用中可以调用天气 API
        weather_info = f"{city} 的天气是：晴朗，气温 25°C。"
        return [
            types.TextContent(
                type="text",
                text=weather_info,
            )
        ]
    raise ValueError(f"Unknown tool: {name}")

# 4. 定义提示词模板 (Prompts)
# 提示词模板可以帮助用户更好地与模型交互
@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="weather-report",
            description="生成一份天气报告",
            arguments=[
                types.PromptArgument(
                    name="city",
                    description="城市名称",
                    required=True,
                )
            ],
        )
    ]

@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    if name == "weather-report":
        city = arguments.get("city", "未知城市")
        return types.GetPromptResult(
            description=f"关于 {city} 的天气报告",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"请帮我查一下 {city} 的天气，并写一份简单的简报。",
                    ),
                )
            ],
        )
    raise ValueError(f"Unknown prompt: {name}")

# 5. 启动 Server（使用标准输入输出 stdio）
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="learning-mcp-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
