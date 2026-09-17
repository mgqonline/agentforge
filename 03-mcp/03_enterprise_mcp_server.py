import os
import json
from typing import Optional
from pydantic import BaseModel, Field, ValidationError

# ---------------------------------------------------------
# 1. 统一错误码与响应规范
# 大模型也是程序的调用者，向它返回规范的错误码和人类可读的 msg，
# 能极大帮助大模型触发 "自我反思(Reflection)" 进行重试。
# ---------------------------------------------------------
class ErrorCode:
    SUCCESS = 0
    UNAUTHORIZED = 401
    INVALID_PARAM = 400
    BUSINESS_ERROR = 4001
    SYSTEM_ERROR = 500

def api_response(code: int, msg: str, data: dict = None) -> str:
    """统一企业级接口返回格式"""
    # ensure_ascii=False 保证中文字符不被转码，这能帮大模型省下大量 Token
    return json.dumps({
        "code": code,
        "msg": msg,
        "data": data or {}
    }, ensure_ascii=False)

# ---------------------------------------------------------
# 2. 权限校验桩 (Auth & RBAC)
# 永远不要信任大模型的行为，所有高危操作必须在工具层进行鉴权！
# ---------------------------------------------------------
def check_permission(token: str, required_role: str) -> bool:
    """模拟微服务架构中的鉴权中心"""
    # 生产环境中，这里会解析 JWT 或请求 IAM(鉴权系统)
    mock_token_roles = {
        "token_guest_123": ["order.read"],
        "token_admin_999": ["order.read", "order.refund"]
    }
    roles = mock_token_roles.get(token, [])
    return required_role in roles

# ---------------------------------------------------------
# 3. 严格的参数校验模型 (基于 Pydantic)
# 大模型容易“幻觉”出错误的参数格式，通过正则表达式和边界约束，
# 在数据进入后端真实业务系统前将其拦截。
# ---------------------------------------------------------
class OrderQuerySchema(BaseModel):
    user_token: str = Field(..., description="用户的鉴权Token，必须由上下文中获取并透传")
    order_id: str = Field(..., pattern=r"^ORD-\d{6}$", description="订单号，必须是 'ORD-' 开头加上6位纯数字")

class OrderRefundSchema(BaseModel):
    user_token: str = Field(...)
    order_id: str = Field(..., pattern=r"^ORD-\d{6}$")
    amount: float = Field(..., gt=0, le=10000, description="退款金额必须大于0，且受风控限制单次不能超过10000")
    reason: str = Field(..., min_length=5, description="退款理由至少需要5个字符的描述")

# ---------------------------------------------------------
# 4. MCP 工具集封装 (模拟 FastMCP 或原生工具注册)
# ---------------------------------------------------------
class EnterpriseMCPServer:
    """
    企业统一 MCP 工具集网关
    将散落在公司各个系统（ERP、CRM、支付）的接口统一封装并暴露给 Agent
    """
    
    def tool_query_order(self, raw_json_params: str) -> str:
        """【工具1】统一订单查询入口"""
        # A. 参数校验防线
        try:
            req = OrderQuerySchema.model_validate_json(raw_json_params)
        except ValidationError as e:
            return api_response(ErrorCode.INVALID_PARAM, "参数格式错误，请检查大写前缀及数字长度", data=e.errors())
            
        # B. 权限防线
        if not check_permission(req.user_token, "order.read"):
            return api_response(ErrorCode.UNAUTHORIZED, "鉴权失败：您的 Token 无权查询订单系统")
            
        # C. 业务执行 (Mock 调下游真实系统)
        mock_db = {
            "ORD-123456": {"status": "PAID", "amount": 99.0, "item": "AI 算力包"},
            "ORD-999999": {"status": "REFUNDED", "amount": 500.0, "item": "企业版会员"}
        }
        order = mock_db.get(req.order_id)
        if not order:
            return api_response(ErrorCode.SUCCESS, "未查询到对应订单", data={"found": False})
            
        return api_response(ErrorCode.SUCCESS, "查询成功", data={"found": True, "order": order})

    def tool_refund_order(self, raw_json_params: str) -> str:
        """【工具2】订单退款高危操作入口"""
        # A. 参数校验
        try:
            req = OrderRefundSchema.model_validate_json(raw_json_params)
        except ValidationError as e:
            return api_response(ErrorCode.INVALID_PARAM, "退款参数非法，请严格检查金额和理由长度", data=e.errors())
            
        # B. 权限防线 (拦截越权操作)
        if not check_permission(req.user_token, "order.refund"):
            return api_response(ErrorCode.UNAUTHORIZED, "【严重拦截】越权操作：该账户没有财务退款权限！")
            
        # C. 模拟真实退款业务逻辑
        return api_response(ErrorCode.SUCCESS, f"退款流水已生成。订单 {req.order_id} 成功退款 {req.amount} 元", data={"tx_id": "TX987654321"})

# ==========================================
# 本地测试桩代码
# ==========================================
if __name__ == "__main__":
    server = EnterpriseMCPServer()
    
    print("=== 测试 1: 格式错误的参数拦截 ===")
    bad_param = '{"user_token": "token_admin_999", "order_id": "123456"}' # 缺失 ORD- 前缀
    print("返回:", server.tool_query_order(bad_param))
    
    print("\n=== 测试 2: 越权的高危操作拦截 ===")
    guest_param = '{"user_token": "token_guest_123", "order_id": "ORD-123456", "amount": 50.0, "reason": "产品不好用"}'
    print("返回:", server.tool_refund_order(guest_param))
    
    print("\n=== 测试 3: 正常的标准全链路调用 ===")
    good_param = '{"user_token": "token_admin_999", "order_id": "ORD-123456", "amount": 50.0, "reason": "客户重复购买协商退款"}'
    print("返回:", server.tool_refund_order(good_param))
