from mcp.server.fastmcp import FastMCP
import asyncio

mcp = FastMCP("EnterpriseServices")

@mcp.tool()
async def process_refund(order_id: str, amount: float) -> str:
    """
    Execute a refund for a specific order.
    WARNING: This is a high-risk side effect action that requires human approval.
    """
    await asyncio.sleep(1) # Simulate API delay
    return f"✅ 退款成功：订单 {order_id}，已成功退回原支付账户 {amount} 元"

@mcp.tool()
async def check_order_status(order_id: str) -> str:
    """
    Check the current status of an order.
    This is a safe read-only operation.
    """
    await asyncio.sleep(0.5)
    return f"订单 {order_id} 状态为：已收货，目前支持退款。"

if __name__ == "__main__":
    mcp.run(transport="stdio")
