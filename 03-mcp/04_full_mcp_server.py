import os
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# 创建一个名为 IT_Ops_Bot 的 MCP Server
mcp = FastMCP("IT_Ops_Bot")

# ==========================================================
# 能力一：Resources (资源)
# 场景：暴露只读的静态/动态数据，供大模型作为上下文“阅读”。
# 资源以 URI 的形式存在，模型可以请求读取它们。
# ==========================================================

@mcp.resource("docs://architecture/overview")
def get_architecture_doc() -> str:
    """暴露系统的核心架构文档（静态资源）"""
    return "内部系统采用微服务架构，包含 Order(订单) 和 Payment(支付) 两个核心服务。主要数据库是 PostgreSQL。"

@mcp.resource("log://{service_name}/latest")
def get_service_logs(service_name: str) -> str:
    """动态资源：大模型可以通过传入服务名，读取该服务的最新日志"""
    logs = {
        "order": "[WARN] 10:05 AM - Order creation latency > 2s\n[ERROR] 10:06 AM - PostgreSQL Connection Timeout",
        "payment": "[INFO] 10:05 AM - Transaction TX-999 successful\n[INFO] 10:06 AM - Payment gateway healthy"
    }
    return logs.get(service_name, f"未找到服务 {service_name} 的相关日志。")

# ==========================================================
# 能力二：Tools (工具)
# 场景：允许大模型采取具有“副作用”的物理行动（增删改查、调外部API）。
# ==========================================================

@mcp.tool()
def restart_service(
    service_name: str = Field(description="需要重启的服务名称，如 order 或 payment"), 
    force: bool = Field(default=False, description="是否强制重启（可能导致丢数据），默认 False")
) -> str:
    """IT 运维工具：重启指定的微服务"""
    # 真实的业务逻辑会去调用 Kubernetes 或 Docker 的 API
    action_type = "强制重启 (SIGKILL)" if force else "平滑重启 (SIGTERM)"
    return f"🛠️ [行动执行完成] 已对微服务 '{service_name}' 下发了 {action_type} 指令。服务当前状态：重启中..."

# ==========================================================
# 能力三：Prompts (提示词模板)
# 场景：提供预定义的 Prompt 模板，帮助人类用户快速生成高质量的问题。
# 当用户在客户端（如 Claude Desktop）调用此 Prompt 时，它会自动注入系统上下文。
# ==========================================================

@mcp.prompt()
def troubleshoot_service(service: str) -> str:
    """排障模板：生成一个指导大模型排查特定服务报错的 Prompt"""
    # 这里的精妙之处在于：Prompt 模板里提示大模型去读取我们刚才定义的 Resource，并使用 Tool！
    return f"""你现在是公司的首席 SRE（网站可靠性工程师）。
线上系统告警，微服务 `{service}` 出现了异常。

请你按照以下步骤执行：
1. 请先读取系统日志资源 `log://{service}/latest` 以了解当前的报错详情。
2. 结合整体架构文档 `docs://architecture/overview` 分析该报错可能会影响哪些上下游。
3. 如果日志显示是致命的连接超时等故障，请果断使用 `restart_service` 工具将其重启。
4. 最后向我汇报你的排查和处理结果。"""

if __name__ == "__main__":
    print("🚀 完整能力 MCP Server (IT_Ops_Bot) 启动就绪！")
    print("已挂载能力：")
    print("  - Resources: 架构文档, 动态日志")
    print("  - Tools: 服务重启工具")
    print("  - Prompts: SRE 排障向导")
    print("\n你可以通过 stdio 将此脚本作为 MCP Server 接入到 Claude 等客户端中运行。")
    print("正在监听标准输入输出流 (stdio)...")
    
    # 启动 MCP 服务器，监听 stdio。在真实使用中，客户端（如 Claude Desktop）会通过执行这个 Python 脚本与它通信。
    mcp.run()
