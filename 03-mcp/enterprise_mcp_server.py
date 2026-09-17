from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field
from typing import Optional, Dict

# ==========================================
# 1. 统一错误码与返回体规范
# ==========================================
class ErrorCode:
    SUCCESS = 0
    PARAM_ERROR = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    SYSTEM_ERROR = 500

class StandardResponse(BaseModel):
    code: int
    message: str
    data: Optional[Dict] = None

# ==========================================
# 2. 定义严格的参数校验模型 (Pydantic)
# ==========================================
# 💡 意义：大模型有时会“幻觉”出不存在的参数，或者拼错参数名。
# Pydantic 模型会自动转换为 MCP 协议要求的严格 JSON Schema 发给大模型。
# 只要大模型参数填错，底层直接拦截报错，不会把脏数据打到后端业务系统。
class QueryOrderSchema(BaseModel):
    order_id: str = Field(..., description="业务系统订单号，必须以 'ORD-' 开头", min_length=5)
    employee_id: str = Field(..., description="发起查询的内部员工 ID")
    auth_token: str = Field(..., description="安全凭证，用于鉴权")

class CancelOrderSchema(BaseModel):
    order_id: str = Field(..., description="要取消的订单号")
    reason: str = Field(default="用户要求退款", description="取消原因")

# ==========================================
# 3. 初始化企业统一 MCP Server
# ==========================================
mcp = FastMCP("EnterpriseUnifiedBizServer")

# ==========================================
# 4. 模拟底层业务系统（如 ERP、CRM）及权限中心
# ==========================================
def check_permission(employee_id: str, token: str, required_role: str) -> bool:
    """企业实际场景中，这里可能是调用内部 Oauth 或 JWT 解析"""
    if token != "corp-super-token-2026":
        return False
    if required_role == "admin" and not employee_id.startswith("ADMIN-"):
        return False
    return True

def mock_erp_query(order_id: str):
    if order_id == "ORD-10086":
        return {"status": "已发货", "amount": 999.0}
    return None

# ==========================================
# 5. MCP Tool 封装 (挂载到 Server)
# ==========================================
@mcp.tool()
def query_enterprise_order(params: QueryOrderSchema, ctx: Context) -> StandardResponse:
    """
    【核心业务工具】用于统一查询企业 ERP 的订单状态。
    注意：遇到权限被拒绝时，请如实告知用户，不要反复尝试。
    """
    # 记录审计日志
    ctx.info(f"[Audit Log] 员工 {params.employee_id} 正在尝试查询订单 {params.order_id}")
    
    # A. 统一权限拦截 (鉴权)
    if not check_permission(params.employee_id, params.auth_token, required_role="staff"):
        return StandardResponse(
            code=ErrorCode.FORBIDDEN, 
            message="【权限拒绝】提供的 Token 无效或员工身份不合法，无法查询机密订单。"
        )
    
    # B. 业务参数二次拦截 (校验)
    if not params.order_id.startswith("ORD-"):
        return StandardResponse(
            code=ErrorCode.PARAM_ERROR,
            message="【参数错误】订单号格式异常，请要求用户提供 ORD- 开头的单号。"
        )
        
    # C. 业务系统调用及容错兜底
    try:
        order_data = mock_erp_query(params.order_id)
        if not order_data:
            return StandardResponse(code=404, message="未找到该订单记录")
            
        return StandardResponse(
            code=ErrorCode.SUCCESS,
            message="查询成功",
            data=order_data
        )
    except Exception as e:
        # 向外抛出可控的错误信息，而不是堆栈跟踪
        ctx.error(f"[System Crash] 业务系统异常: {str(e)}")
        return StandardResponse(
            code=ErrorCode.SYSTEM_ERROR, 
            message="【系统异常】底层 ERP 系统超时或维护中，请稍后再试。"
        )

if __name__ == "__main__":
    print("🚀 企业级 MCP 服务已启动，正在等待大模型 Client 连接...")
    # 实际在生产环境中，通常使用 stdio（标准输入输出流）或 sse（Server-Sent Events）供大模型 Agent 调度
    # mcp.run(transport='stdio')
