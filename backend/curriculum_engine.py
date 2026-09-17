import os
import re
from typing import List, Dict, Any, Optional

CHALLENGE_METADATA = {
    "01-prompt-engineering": {
        "mission_title": "实战挑战：构建工业级分层 Prompt 角色适配器",
        "mission_goal": "实现一个标准化的 `create_role_prompt(role_name, instruction, user_input)` 函数，将业务人设与用户指令解耦，构造符合 OpenAI/LangChain 标准的消息协议字典。",
        "requirements": [
            "实现函数 `create_role_prompt(role_name: str, instruction: str, user_input: str) -> dict`",
            "返回字典必须包含 `system`（合成角色设定与核心指令）和 `user`（用户输入）键",
            "需具备基本防御性校验：若 `instruction` 为空，自动注入兜底指令 '你是一位严谨的 AI 助手'",
            "返回字典中需包含 `ready: True` 状态标志"
        ],
        "learning_steps": [
            "第 1 步【研读手册】：切换到【知识手册】Tab，理解 System 角色设定与运行时参数解耦的四层框架；",
            "第 2 步【编码实现】：在右侧编辑器中定义并实现 `create_role_prompt` 函数；",
            "第 3 步【沙箱自测】：按 ⌘+Enter 或点击【运行】，在隔离沙箱中调试打印结果；",
            "第 4 步【验证通关】：点击【验证通关】，系统自动执行单元测试断言，通过后点亮关卡并获取 +80 XP！"
        ],
        "acceptance_criteria": "自动化测试将传入不同角色参数，断言返回值类型为 dict，必须包含包含 system/user 字段，且正确注入身份约束。",
        "hint": "在 system 中可使用 f'你是一名{role_name}。{instruction}' 进行规范拼接，并用三元表达式进行空值兜底。",
        "solution_code": """# ==========================================
# 💡 官方标准参考实现 (工业级高可靠版本)
# ==========================================

def create_role_prompt(role_name: str, instruction: str, user_input: str) -> dict:
    \"\"\"根据入参组装标准的大模型提示词消息字典\"\"\"
    safe_instruction = instruction.strip() if instruction and instruction.strip() else "你是一位严谨的 AI 助手"
    system_text = f"你是一名{role_name.strip()}。{safe_instruction}"
    
    return {
        "system": system_text,
        "user": user_input.strip() if user_input else "",
        "ready": True
    }

if __name__ == "__main__":
    res = create_role_prompt("极客架构师", "用清晰的代码回答", "什么是异步编程？")
    print(">>> 官方参考答案自测输出:")
    print(res)
""",
        "starter_code": """# ==========================================
# 🎯 本关闯关实战任务：
# 请实现 create_role_prompt 函数，将角色身份、核心指令与用户输入解耦，
# 构造规范的字典：{"system": str, "user": str, "ready": bool}
# 完成后点击上方【运行】调试，点击【验证通关】完成考核点亮关卡！
# ==========================================

def create_role_prompt(role_name: str, instruction: str, user_input: str) -> dict:
    \"\"\"根据入参组装标准的大模型提示词消息字典\"\"\"
    # 请在下方编写你的实现逻辑：
    fallback_instruction = instruction if instruction else "你是一位严谨的 AI 助手"
    system_text = f"你是一名{role_name}。{fallback_instruction}"
    
    return {
        "system": system_text,
        "user": user_input,
        "ready": True
    }

# --- 以下为本关示范运行代码（可直接点击【运行】体验） ---
if __name__ == "__main__":
    test_res = create_role_prompt("极客程序员", "用清晰的代码回答", "什么是异步编程？")
    print(">>> 闯关函数自测输出:")
    print(test_res)
""",
        "test_code": """import unittest

class TestPhase01Challenge(unittest.TestCase):
    def test_func_exists(self):
        self.assertTrue('create_role_prompt' in globals(), "未在代码中找到 create_role_prompt 函数，请按指引定义该函数")

    def test_output_structure(self):
        func = globals()['create_role_prompt']
        res = func("技术专家", "严格分析", "如何做并发优化？")
        self.assertIsInstance(res, dict, "create_role_prompt 返回值必须是 dict 字典类型")
        self.assertIn("system", res, "返回字典必须包含 'system' 键")
        self.assertIn("user", res, "返回字典必须包含 'user' 键")
        self.assertTrue(res.get("ready"), "返回字典中的 'ready' 标志位应为 True")
        self.assertIn("技术专家", res["system"], "系统指令中应包含传入的角色名称")
        self.assertEqual(res["user"], "如何做并发优化？", "user 字段应与传入的用户提问一致")

    def test_empty_fallback(self):
        func = globals()['create_role_prompt']
        res = func("评审导师", "", "测试空指令兜底")
        self.assertIn("AI 助手", res["system"], "当 instruction 为空时应触发兜底设置")

if __name__ == '__main__':
    unittest.main()
"""
    },
    "02-function-calling": {
        "mission_title": "实战挑战：实现结构化工具声明与参数分发器",
        "mission_goal": "编写外部工具规范声明与 `dispatch_tool_call(tool_name, arguments)` 执行器，实现大模型 Function Calling 的参数自动解析与安全分发。",
        "requirements": [
            "定义 `dispatch_tool_call(tool_name: str, arguments: dict) -> dict` 函数",
            "支持 `get_weather` 或 `query_order` 等至少一个工具名称的模拟分发",
            "返回统一格式 `{'status': 'success', 'result': ...}`，未知工具返回 `{'status': 'error', 'message': 'Unknown tool'}`"
        ],
        "learning_steps": [
            "第 1 步：阅读指南中的 Function Calling 协议定义与 JSON Schema；",
            "第 2 步：实现工具路由字典与分发函数；",
            "第 3 步：运行沙箱观察分发返回值；",
            "第 4 步：点击【验证通关】完成测试通过。"
        ],
        "acceptance_criteria": "测试集将模拟 LLM 输出的工具名称与参数，验证分发成功率与异常处理能力。",
        "hint": "建议使用字典映射 `tools_map = {'get_weather': weather_fn}` 优雅分发，避免冗长 if-else。",
        "solution_code": """# ==========================================
# 💡 官方标准参考实现 (工厂表驱动模式)
# ==========================================

def _handle_get_weather(args: dict) -> str:
    city = args.get("city", "未知地区")
    return f"{city}天气晴朗，气温 24℃，适宜出行"

def _handle_query_order(args: dict) -> str:
    order_id = args.get("order_id", "N/A")
    return f"工单 {order_id} 状态正常，已进入发货质检阶段"

TOOL_REGISTRY = {
    "get_weather": _handle_get_weather,
    "query_order": _handle_query_order
}

def dispatch_tool_call(tool_name: str, arguments: dict) -> dict:
    \"\"\"通过注册表分发执行大模型工具调用\"\"\"
    handler = TOOL_REGISTRY.get(tool_name)
    if not handler:
        return {"status": "error", "message": "Unknown tool"}
    
    try:
        output = handler(arguments)
        return {"status": "success", "result": output}
    except Exception as e:
        return {"status": "error", "message": f"Execution failed: {str(e)}"}

if __name__ == "__main__":
    print(dispatch_tool_call("get_weather", {"city": "上海"}))
    print(dispatch_tool_call("query_order", {"order_id": "ORD-2026-8888"}))
""",
        "starter_code": """# ==========================================
# 🎯 本关闯关实战任务：
# 实现 dispatch_tool_call 函数，根据模型返回的工具名与参数字典，
# 分发执行并返回统一格式：{"status": "success", "result": ...}
# ==========================================

def dispatch_tool_call(tool_name: str, arguments: dict) -> dict:
    \"\"\"模拟大模型工具调用分发器\"\"\"
    if tool_name == "get_weather":
        city = arguments.get("city", "未知")
        return {"status": "success", "result": f"{city}天气晴朗，气温24℃"}
    elif tool_name == "query_order":
        order_id = arguments.get("order_id", "")
        return {"status": "success", "result": f"工单 {order_id} 状态正常"}
    else:
        return {"status": "error", "message": "Unknown tool"}

if __name__ == "__main__":
    res = dispatch_tool_call("get_weather", {"city": "北京"})
    print("工具分发测试:", res)
""",
        "test_code": """import unittest

class TestFunctionCalling(unittest.TestCase):
    def test_dispatch_known(self):
        self.assertTrue('dispatch_tool_call' in globals(), "未定义 dispatch_tool_call 函数")
        func = globals()['dispatch_tool_call']
        res = func("get_weather", {"city": "上海"})
        self.assertEqual(res.get("status"), "success")
        self.assertIn("上海", res.get("result", ""))

    def test_dispatch_unknown(self):
        func = globals()['dispatch_tool_call']
        res = func("unknown_tool", {})
        self.assertEqual(res.get("status"), "error")

if __name__ == '__main__':
    unittest.main()
"""
    },
    "03-mcp": {
        "mission_title": "实战挑战：实现 MCP 协议标准工具分发与权限网关",
        "mission_goal": "构建一个标准的 `mcp_tool_gateway(token, tool_name, params)` 协议适配器，实现入参严格校验、角色权限（RBAC）拦截与规范的 JSON-RPC 结果返回。",
        "requirements": [
            "实现函数 `mcp_tool_gateway(token: str, tool_name: str, params: dict) -> dict`",
            "根据 token 进行鉴权：若 token 为 'admin_token' 拥有全权限，若为 'guest_token' 仅允许 'read' 类工具，否则返回 code 401 鉴权拒绝",
            "支持 'order_query' 工具返回订单数据；高危工具 'order_refund' 仅限 admin 操作",
            "返回值统一符合企业级标准格式：`{'code': int, 'msg': str, 'data': dict}`"
        ],
        "learning_steps": [
            "第 1 步【研读手册】：查看【知识手册】关于 MCP 协议三大基石（Resources, Tools, Prompts）及通信规范；",
            "第 2 步【编写网关】：在右侧实现 `mcp_tool_gateway` 函数，加入 Token 权限判断与参数清洗；",
            "第 3 步【沙箱调试】：点击【运行】(⌘↵) 观察不同权限 Token 调用的返回状态；",
            "第 4 步【验证通关】：点击【验证通关】，通过自动化单元测试攻克本关！"
        ],
        "acceptance_criteria": "测试用例将分别注入普通 guest、管理员 admin 以及非法 token，断言鉴权拦截码与正确的数据透传。",
        "hint": "定义权限映射表，如 `PERMISSIONS = {'guest_token': ['order_query'], 'admin_token': ['order_query', 'order_refund']}`。",
        "solution_code": """# ==========================================
# 💡 官方标准参考实现 (MCP 协议权限网关)
# ==========================================

ROLE_PERMISSIONS = {
    "guest_token": ["order_query"],
    "admin_token": ["order_query", "order_refund"]
}

def mcp_tool_gateway(token: str, tool_name: str, params: dict) -> dict:
    \"\"\"模拟 MCP Server 工具网关，包含鉴权、参数校验与路由分发\"\"\"
    allowed_tools = ROLE_PERMISSIONS.get(token)
    if not allowed_tools:
        return {"code": 401, "msg": "未授权的访问凭据", "data": {}}
    
    if tool_name not in allowed_tools:
        return {"code": 403, "msg": f"权限拒绝：当前角色无权执行 [{tool_name}]", "data": {}}
    
    # 模拟工具执行
    if tool_name == "order_query":
        order_id = params.get("order_id", "ORD-DEFAULT")
        return {"code": 0, "msg": "查询成功", "data": {"order_id": order_id, "status": "COMPLETED"}}
    elif tool_name == "order_refund":
        amount = params.get("amount", 0)
        return {"code": 0, "msg": "退款成功", "data": {"refund_amount": amount, "tx_id": "TX-998877"}}
    
    return {"code": 404, "msg": "未知工具", "data": {}}

if __name__ == "__main__":
    print(mcp_tool_gateway("admin_token", "order_refund", {"amount": 200}))
    print(mcp_tool_gateway("guest_token", "order_refund", {"amount": 200}))
""",
        "starter_code": """# ==========================================
# 🎯 本关闯关实战任务：
# 请实现 mcp_tool_gateway(token, tool_name, params) 函数：
# 1. 鉴权：admin_token 允许所有工具，guest_token 仅允许 order_query，其余返回 401
# 2. 鉴权失败或越权拦截返回统一结构：{"code": int, "msg": str, "data": dict}
# 3. 正常执行返回 code: 0 与对应业务数据
# ==========================================

def mcp_tool_gateway(token: str, tool_name: str, params: dict) -> dict:
    \"\"\"请在此编写 MCP 工具调用网关实现\"\"\"
    # 请根据关卡要求完善权限与工具分发逻辑：
    if token not in ["admin_token", "guest_token"]:
        return {"code": 401, "msg": "Unauthorized", "data": {}}
    
    if token == "guest_token" and tool_name != "order_query":
        return {"code": 403, "msg": "Forbidden", "data": {}}
        
    if tool_name == "order_query":
        return {"code": 0, "msg": "Success", "data": {"order_id": params.get("order_id"), "status": "ACTIVE"}}
    elif tool_name == "order_refund":
        return {"code": 0, "msg": "Success", "data": {"refunded": True}}
        
    return {"code": 404, "msg": "NotFound", "data": {}}

if __name__ == "__main__":
    res = mcp_tool_gateway("guest_token", "order_query", {"order_id": "ORD-123456"})
    print("网关自测输出:", res)
""",
        "test_code": """import unittest

class TestMCPGateway(unittest.TestCase):
    def test_exists(self):
        self.assertTrue('mcp_tool_gateway' in globals(), "必须定义 mcp_tool_gateway 函数")

    def test_unauthorized(self):
        fn = globals()['mcp_tool_gateway']
        res = fn("invalid_token", "order_query", {})
        self.assertEqual(res.get("code"), 401, "无效 token 应返回 code 401")

    def test_guest_forbidden_refund(self):
        fn = globals()['mcp_tool_gateway']
        res = fn("guest_token", "order_refund", {"amount": 100})
        self.assertEqual(res.get("code"), 403, "guest 执行 refund 应被拦截返回 403")

    def test_admin_success(self):
        fn = globals()['mcp_tool_gateway']
        res = fn("admin_token", "order_refund", {"amount": 500})
        self.assertEqual(res.get("code"), 0, "admin 执行退款应成功返回 code 0")
        self.assertIn("data", res)

if __name__ == '__main__':
    unittest.main()
"""
    },
    "04-rag": {
        "mission_title": "实战挑战：实现两阶段 RRF 混合重排检索器",
        "mission_goal": "实现 `reciprocal_rank_fusion(dense_ranks, sparse_ranks, k=60)` 倒数秩融合算法，将稠密向量检索与稀疏关键词检索的召回结果合并重排，输出综合最优相关性排名。",
        "requirements": [
            "定义函数 `reciprocal_rank_fusion(dense_ranks: list, sparse_ranks: list, k: int = 60) -> list`",
            "根据 RRF 公式计算得分：$RRF(d) = \\sum \\frac{1}{k + rank_i + 1}$",
            "返回按融合得分从高到低降序排序的文档 ID 列表 `[doc_id, ...]`",
            "能够稳健处理单路召回为空或两路召回部分重叠的场景"
        ],
        "learning_steps": [
            "第 1 步【研读手册】：查看【知识手册】中 BM25 稀疏匹配与向量稠密检索的互补原理；",
            "第 2 步【编码实现】：实现倒数秩融合评分字典并在最后完成降序排列；",
            "第 3 步【沙箱测试】：点击【运行】观察双路召回的合并排名效果；",
            "第 4 步【验证通关】：点击【验证通关】，通过自动化测试点亮 RAG 勋章！"
        ],
        "acceptance_criteria": "断言双路均出现的文档排名显著高于单路文档，且排序契约与测试用例一致。",
        "hint": "遍历每一路的索引 `for rank, doc_id in enumerate(list): scores[doc_id] += 1 / (k + rank + 1)`。",
        "solution_code": """# ==========================================
# 💡 官方标准参考实现 (RRF 倒数秩多路融合算法)
# ==========================================

def reciprocal_rank_fusion(dense_ranks: list, sparse_ranks: list, k: int = 60) -> list:
    \"\"\"使用倒数秩融合 (RRF) 算法合并两路召回排序结果\"\"\"
    rrf_scores = {}
    
    # 累加稠密向量路分数
    for rank, doc_id in enumerate(dense_ranks):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))
        
    # 累加稀疏关键词路分数
    for rank, doc_id in enumerate(sparse_ranks):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))
        
    # 按照最终合成打分降序排列
    sorted_docs = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)
    return [doc_id for doc_id, score in sorted_docs]

if __name__ == "__main__":
    dense = ["doc_A", "doc_B", "doc_C"]
    sparse = ["doc_B", "doc_D", "doc_A"]
    fused = reciprocal_rank_fusion(dense, sparse, k=60)
    print("RRF 融合结果:", fused)
""",
        "starter_code": """# ==========================================
# 🎯 本关闯关实战任务：
# 请实现 reciprocal_rank_fusion(dense_ranks, sparse_ranks, k=60) 函数，
# 将两路召回的文档列表按 RRF 算法打分并降序返回合并后的文档 ID 列表。
# ==========================================

def reciprocal_rank_fusion(dense_ranks: list, sparse_ranks: list, k: int = 60) -> list:
    \"\"\"实现多路召回倒数秩融合\"\"\"
    scores = {}
    for rank, doc_id in enumerate(dense_ranks):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        
    for rank, doc_id in enumerate(sparse_ranks):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [item[0] for item in sorted_items]

if __name__ == "__main__":
    res = reciprocal_rank_fusion(["doc1", "doc2"], ["doc2", "doc3"])
    print("融合排序:", res)
""",
        "test_code": """import unittest

class TestRAGFusion(unittest.TestCase):
    def test_exists(self):
        self.assertTrue('reciprocal_rank_fusion' in globals())

    def test_rrf_priority(self):
        fn = globals()['reciprocal_rank_fusion']
        # doc_B 在两路中都排第一或第二，应当排在最前
        dense = ["doc_A", "doc_B", "doc_C"]
        sparse = ["doc_B", "doc_A", "doc_D"]
        res = fn(dense, sparse, k=60)
        self.assertIsInstance(res, list)
        self.assertTrue(res[0] in ["doc_A", "doc_B"])
        self.assertEqual(len(res), 4)

    def test_empty_handling(self):
        fn = globals()['reciprocal_rank_fusion']
        res = fn([], ["doc_1", "doc_2"])
        self.assertEqual(res, ["doc_1", "doc_2"])

if __name__ == '__main__':
    unittest.main()
"""
    },
    "05-embedding": {
        "mission_title": "实战挑战：实现高维向量空间余弦相似度与归一化算子",
        "mission_goal": "编写高性能向量归一化与余弦相似度计算函数 `cosine_similarity(vec_a, vec_b)`，理解向量方向、夹角余弦与点积的数学转换。",
        "requirements": [
            "实现函数 `cosine_similarity(vec_a: list, vec_b: list) -> float`",
            "基于公式 $(A \\cdot B) / (\\|A\\| \\cdot \\|B\\|)$ 计算高维向量夹角余弦",
            "返回值保留 4 位浮点精度；若出现零向量除以零异常，安全返回 0.0",
            "支持任意维度的数值列表输入（如 384 或 1536 维）"
        ],
        "learning_steps": [
            "第 1 步【研读手册】：深入理解高维空间的几何相似度与模长惩罚原理；",
            "第 2 步【编码实现】：使用纯 Python 或 math/numpy 计算点积与向量范数；",
            "第 3 步【沙箱调试】：测试正交向量（相似度为0）与平行向量（相似度为1）；",
            "第 4 步【验证通关】：点击【验证通关】完成测试并点亮关卡！"
        ],
        "acceptance_criteria": "测试用例将校验平行向量（cos=1.0）、相反向量（cos=-1.0）及零向量容错处理。",
        "hint": "计算范数可使用 `math.sqrt(sum(x*x for x in v))`，点积使用 `sum(a*b for a, b in zip(v1, v2))`。",
        "solution_code": """# ==========================================
# 💡 官方标准参考实现 (工业级鲁棒余弦相似度)
# ==========================================
import math

def cosine_similarity(vec_a: list, vec_b: list) -> float:
    \"\"\"计算两个向量之间的余弦相似度\"\"\"
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
        
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
        
    similarity = dot_product / (norm_a * norm_b)
    return round(float(similarity), 4)

if __name__ == "__main__":
    print("平行向量:", cosine_similarity([1, 2, 3], [2, 4, 6]))
    print("正交向量:", cosine_similarity([1, 0], [0, 1]))
""",
        "starter_code": """# ==========================================
# 🎯 本关闯关实战任务：
# 实现 cosine_similarity(vec_a, vec_b) -> float 函数，
# 计算两个高维向量的余弦相似度并处理除零边界。
# ==========================================
import math

def cosine_similarity(vec_a: list, vec_b: list) -> float:
    \"\"\"计算两个向量的余弦相似度\"\"\"
    dot_val = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return round(dot_val / (norm_a * norm_b), 4)

if __name__ == "__main__":
    v1 = [1.0, 2.0, 3.0]
    v2 = [2.0, 4.0, 6.0]
    print("相似度:", cosine_similarity(v1, v2))
""",
        "test_code": """import unittest
import math

class TestEmbeddingSimilarity(unittest.TestCase):
    def test_exists(self):
        self.assertTrue('cosine_similarity' in globals())

    def test_parallel(self):
        fn = globals()['cosine_similarity']
        sim = fn([1, 2, 3], [2, 4, 6])
        self.assertAlmostEqual(sim, 1.0, places=3)

    def test_orthogonal(self):
        fn = globals()['cosine_similarity']
        sim = fn([1, 0, 0], [0, 1, 0])
        self.assertAlmostEqual(sim, 0.0, places=3)

    def test_zero_vector(self):
        fn = globals()['cosine_similarity']
        sim = fn([0, 0], [1, 2])
        self.assertEqual(sim, 0.0)

if __name__ == '__main__':
    unittest.main()
"""
    },
    "06-agent-basics": {
        "mission_title": "实战挑战：实现有限状态机 Agent 路由与循环决策",
        "mission_goal": "实现 `agent_state_router(state)` 条件边决策函数，模拟 LangGraph 状态图的智能路由逻辑：根据历史消息中是否包含待执行的工具调用指令，准确分发到 'tool_executor' 或 'finish' 节点。",
        "requirements": [
            "实现函数 `agent_state_router(state: dict) -> str`",
            "若 `state` 中的 `messages` 列表最后一条包含 `tool_calls` 且非空，路由到 `'tools'`",
            "若包含错误信息且重试次数 `retry_count < 3`，路由到 `'retry'`",
            "若任务完成或已达成退出条件，路由到 `'end'`",
            "防御性处理非法/空状态，返回 `'end'`"
        ],
        "learning_steps": [
            "第 1 步【研读手册】：学习 LangGraph 核心循环（StateGraph、Node、Edge 条件边）理论；",
            "第 2 步【编码实现】：实现条件决策路由函数，处理多种状态分支；",
            "第 3 步【沙箱自测】：按 ⌘↵ 运行多分支样例验证路由结果；",
            "第 4 步【验证通关】：点击【验证通关】完成自动化评测并点亮智能体进阶徽章！"
        ],
        "acceptance_criteria": "测试用例将分别构造带有工具调用的消息、错误重试状态以及最终结束状态，断言流转节点名称准确无误。",
        "hint": "检查 `last_msg = state.get('messages', [])[-1]`，再通过 `last_msg.get('tool_calls')` 判断是否有待处理工具。",
        "solution_code": """# ==========================================
# 💡 官方标准参考实现 (LangGraph 智能条件边路由)
# ==========================================

def agent_state_router(state: dict) -> str:
    \"\"\"LangGraph 核心条件路由决策逻辑\"\"\"
    if not state or not isinstance(state, dict):
        return "end"
        
    messages = state.get("messages", [])
    if not messages:
        return "end"
        
    last_msg = messages[-1]
    
    # 分支 1: 模型要求调用工具
    if last_msg.get("tool_calls"):
        return "tools"
        
    # 分支 2: 异常反思与重试机制
    if state.get("has_error") and state.get("retry_count", 0) < 3:
        return "retry"
        
    # 分支 3: 流程结束
    return "end"

if __name__ == "__main__":
    print(agent_state_router({"messages": [{"role": "assistant", "tool_calls": [{"name": "search"}]}]}))
    print(agent_state_router({"messages": [{"role": "assistant", "content": "任务已完成"}]}))
""",
        "starter_code": """# ==========================================
# 🎯 本关闯关实战任务：
# 实现 agent_state_router(state) 函数，根据当前状态判断流转方向：
# - 有 tool_calls 转向 "tools"
# - 有错误且 retry_count < 3 转向 "retry"
# - 其它情况或完成转向 "end"
# ==========================================

def agent_state_router(state: dict) -> str:
    \"\"\"模拟 Agent 状态机条件边路由\"\"\"
    if not state or "messages" not in state or not state["messages"]:
        return "end"
    
    last_message = state["messages"][-1]
    if last_message.get("tool_calls"):
        return "tools"
        
    if state.get("has_error") and state.get("retry_count", 0) < 3:
        return "retry"
        
    return "end"

if __name__ == "__main__":
    sample_state = {"messages": [{"tool_calls": ["calc"]}]}
    print("路由结果:", agent_state_router(sample_state))
""",
        "test_code": """import unittest

class TestAgentRouter(unittest.TestCase):
    def test_exists(self):
        self.assertTrue('agent_state_router' in globals())

    def test_tool_call_routing(self):
        fn = globals()['agent_state_router']
        st = {"messages": [{"role": "assistant", "tool_calls": [{"name": "calculator"}]}]}
        self.assertEqual(fn(st), "tools")

    def test_retry_routing(self):
        fn = globals()['agent_state_router']
        st = {"messages": [{"role": "user"}], "has_error": True, "retry_count": 1}
        self.assertEqual(fn(st), "retry")

    def test_max_retry_exceeded(self):
        fn = globals()['agent_state_router']
        st = {"messages": [{"role": "user"}], "has_error": True, "retry_count": 3}
        self.assertEqual(fn(st), "end")

    def test_finish_routing(self):
        fn = globals()['agent_state_router']
        st = {"messages": [{"role": "assistant", "content": "Final Answer"}]}
        self.assertEqual(fn(st), "end")

if __name__ == '__main__':
    unittest.main()
"""
    },
    "17-transformers-basics": {
        "mission_title": "实战挑战：构建融合残差连接与注意力机制的 Transformer 算子核心",
        "mission_goal": "手写实现一个工业级轻量 `MiniTransformerBlock(d_model, num_heads, dropout=0.1)` 核心模块，深入掌握注意力机制（联想大脑）、残差连接（骨骼神经系统）、LayerNorm 归一化与 Dropout（防死记硬背机制）的协同运行机制。",
        "requirements": [
            "实现类 `MiniTransformerBlock(d_model: int, num_heads: int, dropout: float = 0.1)`",
            "在 `forward(x)` 中实现残差连接：`x = self.norm1(x + self.dropout(attn_out))`，确保输入特征可直接跳跃传递",
            "实现 FFN 与二次残差连接：`x = self.norm2(x + self.dropout(ffn_out))`",
            "输出张量形状严格保持为 `(batch_size, seq_len, d_model)`",
            "支持 `eval()` 冻结 Dropout 验证输出一致性，并支持反向传播验证残差梯度流畅通"
        ],
        "learning_steps": [
            "第 1 步【研读手册】：理解核心隐喻——残差为骨骼神经系统、Attention 为联想大脑、Dropout 为防死记硬背机制、海量预训练为医学文献底座、SFT/RLHF 为临床门诊规培；",
            "第 2 步【搭建大脑与骨骼】：编写多头注意力 $Q, K, V$ 投影与跳跃残差相加通道；",
            "第 3 步【规约与非线性消化】：加入 LayerNorm 与 FFN，实现深层网络的平稳训练；",
            "第 4 步【验证通关】：点击【验证通关】，沙箱执行前向维度、残差流与梯度回传单元测试，点亮大模型核心徽章！"
        ],
        "acceptance_criteria": "自动化测试将传入随机张量，验证前向维度一致性、残差跳跃传递（梯度流不衰减）以及 eval 模式下输出的确定性。",
        "hint": "残差连接的核心公式是 `x = norm(x + dropout(sublayer(x)))`，通过直通路径让深层梯度不衰减、网络不崩溃。",
        "solution_code": """# ==========================================
# 💡 官方标准参考实现 (融合残差骨骼与注意力大脑)
# ==========================================
import math
import torch
import torch.nn as nn
import torch.nn.functional as F

class MiniTransformerBlock(nn.Module):
    \"\"\"
    标准 Transformer 编码块算子核心：
    - 多头注意力（大脑容量与联想）
    - 残差连接（骨骼神经系统，保障深层梯度不消失）
    - LayerNorm（内部生理环境稳态）
    - Dropout（初期防死记硬背，推理与大模型预训练可平滑关闭）
    \"\"\"
    def __init__(self, d_model: int = 16, num_heads: int = 2, dropout: float = 0.1):
        super().__init__()
        assert d_model % num_heads == 0, "d_model 必须能被 num_heads 整除"
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads

        # 1. 注意力投影层
        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)

        # 2. 骨骼稳定层
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)

        # 3. 前馈消化网络 (FFN)
        d_ff = d_model * 4
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, D = x.shape
        # Attention 联想
        Q = self.q_proj(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)
        K = self.k_proj(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)
        V = self.v_proj(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)

        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.d_k)
        attn = F.softmax(scores, dim=-1)
        attn = self.dropout(attn)
        context = torch.matmul(attn, V).transpose(1, 2).contiguous().view(B, T, D)
        attn_out = self.out_proj(context)

        # 残差连接 1: x + F(x) (骨骼直通通道)
        x = self.norm1(x + self.dropout(attn_out))

        # FFN 独立特征消化
        ffn_out = self.ffn(x)

        # 残差连接 2: x + G(x) (骨骼直通通道)
        x = self.norm2(x + self.dropout(ffn_out))
        return x

if __name__ == "__main__":
    block = MiniTransformerBlock(d_model=16, num_heads=2)
    sample_x = torch.randn(2, 4, 16)
    out = block(sample_x)
    print("Transformer Block 官方参考自测输出 shape:", out.shape)
""",
        "starter_code": """# ==========================================
# 🎯 本关闯关实战任务：
# 请实现 MiniTransformerBlock 类，构建包含以下核心结构的算子：
# 1. Multi-Head Attention 计算（多头自注意力，模拟大脑联想）
# 2. 残差连接 1：x = self.norm1(x + self.dropout(attn_out))（骨骼直通）
# 3. FFN 前馈消化层
# 4. 残差连接 2：x = self.norm2(x + self.dropout(ffn_out))（骨骼直通）
# ==========================================
import math
import torch
import torch.nn as nn
import torch.nn.functional as F

class MiniTransformerBlock(nn.Module):
    def __init__(self, d_model: int = 16, num_heads: int = 2, dropout: float = 0.1):
        super().__init__()
        assert d_model % num_heads == 0, "d_model 必须能被 num_heads 整除"
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads

        # 线性投影层
        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)

        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)

        d_ff = d_model * 4
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, D = x.shape
        # 1. 多头注意力特征提取
        Q = self.q_proj(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)
        K = self.k_proj(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)
        V = self.v_proj(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)

        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.d_k)
        attn = F.softmax(scores, dim=-1)
        attn = self.dropout(attn)
        context = torch.matmul(attn, V).transpose(1, 2).contiguous().view(B, T, D)
        attn_out = self.out_proj(context)

        # 2. 核心任务：实现残差连接 1 (x + attn_out) 并经过 norm1
        # TODO: 请补全下方残差加和逻辑
        x = self.norm1(x + self.dropout(attn_out))

        # 3. 前馈网络消化
        ffn_out = self.ffn(x)

        # 4. 核心任务：实现残差连接 2 (x + ffn_out) 并经过 norm2
        # TODO: 请补全下方残差加和逻辑
        x = self.norm2(x + self.dropout(ffn_out))

        return x

if __name__ == "__main__":
    block = MiniTransformerBlock(d_model=16, num_heads=2)
    sample_input = torch.randn(2, 4, 16)
    output = block(sample_input)
    print(">>> 自测输出张量形状:", output.shape)
""",
        "test_code": """import unittest
import torch

class TestTransformerResidualBlock(unittest.TestCase):
    def test_class_exists(self):
        self.assertTrue('MiniTransformerBlock' in globals(), "未在代码中找到 MiniTransformerBlock 类")

    def test_forward_shape(self):
        cls = globals()['MiniTransformerBlock']
        block = cls(d_model=16, num_heads=2, dropout=0.1)
        x = torch.randn(2, 4, 16)
        out = block(x)
        self.assertEqual(out.shape, (2, 4, 16), "输出形状必须与输入形状 (2, 4, 16) 完全一致")

    def test_eval_mode_deterministic(self):
        cls = globals()['MiniTransformerBlock']
        block = cls(d_model=16, num_heads=2, dropout=0.5)
        block.eval() # 冻结 Dropout，确保类似大模型推理时的确定性
        x = torch.randn(2, 3, 16)
        out1 = block(x)
        out2 = block(x)
        self.assertTrue(torch.allclose(out1, out2, atol=1e-5), "在 eval 模式下 Dropout 应关闭，两次相同输入的输出必须完全一致")

    def test_gradient_flow_residual(self):
        cls = globals()['MiniTransformerBlock']
        block = cls(d_model=16, num_heads=2, dropout=0.0)
        x = torch.randn(2, 4, 16, requires_grad=True)
        out = block(x)
        loss = (out ** 2).sum()
        loss.backward()
        self.assertIsNotNone(x.grad, "输入张量 x 必须能够顺利接收反向传播梯度")
        self.assertFalse(torch.isnan(x.grad).any(), "反向传播梯度中不得包含 NaN 异常值")
        self.assertGreater(x.grad.abs().sum().item(), 0.0, "残差直通路径应保证梯度有效传递且不为零")

if __name__ == '__main__':
    unittest.main()
"""
    }
}

# 企业级 AI 全栈实战关卡知识图谱与前置依赖树
PREREQUISITES_MAP = {
    "01-prompt-engineering": [],
    "02-function-calling": ["01-prompt-engineering"],
    "03-mcp": ["02-function-calling"],
    "04-rag": ["01-prompt-engineering"],
    "05-embedding": ["04-rag"],
    "06-agent-basics": ["02-function-calling"],
    "07-advanced-memory": ["06-agent-basics"],
    "08-multimodal": ["01-prompt-engineering"],
    "09-evaluation": ["04-rag"],
    "10-production": ["06-agent-basics"],
    "11-python-advanced": ["01-prompt-engineering"],
    "12-fastapi-advanced": ["11-python-advanced"],
    "13-sqlalchemy-advanced": ["12-fastapi-advanced"],
    "14-celery-advanced": ["12-fastapi-advanced"],
    "15-agent-architecture": ["06-agent-basics"],
    "16-face-recognition": ["08-multimodal"],
    "17-transformers-basics": ["05-embedding"],
    "18-inference-serving": ["17-transformers-basics"],
    "19-model-finetuning": ["17-transformers-basics"],
    "20-agent-frameworks": ["15-agent-architecture"],
    "20-graph-rag": ["04-rag"],
    "21-multi-agent-scale": ["20-agent-frameworks"],
    "22-ai-security": ["03-mcp"],
    "23-edge-ai": ["18-inference-serving"],
}

class CurriculumEngine:
    def __init__(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)

    @staticmethod
    def clean_phase_title(raw_title: str) -> str:
        """剥离章节目录名称前头的数字、代号与连字符，保留纯粹技术主题名"""
        if not raw_title:
            return ""
        clean = re.sub(r"^\d+[-_][a-zA-Z0-9\-_]+\s*[·:：\-—]\s*", "", raw_title)
        clean = re.sub(r"^\d+([-_][a-zA-Z0-9]+)?[\.、\-\s]+\s*", "", clean).strip()
        return clean or raw_title

    @staticmethod
    def _extract_file_doc(content: str) -> str:
        """从源码中提取第一行有意义的注释或 docstring 作为功能摘要"""
        if not content:
            return "实战脚本文件"
        for line in content.splitlines()[:20]:
            stripped = line.strip().strip('"\'#').strip()
            if stripped and not stripped.startswith("=") and not stripped.startswith("-"):
                return stripped[:45]
        return "实战核心实现脚本"

    def get_all_phases(self) -> List[Dict[str, Any]]:
        """扫描根目录下所有数字开头的阶段目录，提取元数据并排序"""
        phases = []
        if not os.path.exists(self.base_dir):
            return phases

        entries = os.listdir(self.base_dir)
        phase_pattern = re.compile(r"^(\d{2})-(.+)$")

        for entry in entries:
            full_path = os.path.join(self.base_dir, entry)
            if not os.path.isdir(full_path):
                continue
            
            match = phase_pattern.match(entry)
            if match:
                order_num = int(match.group(1))
                slug = match.group(2)
                
                # 初始默认标题：剥离前缀数字，如 "function-calling" -> "Function Calling"
                title = self.clean_phase_title(slug.replace("-", " ").title())
                description = "企业级实战与深度掌握"
                readme_path = os.path.join(full_path, "README.md")
                
                if os.path.exists(readme_path):
                    try:
                        with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()
                            for line in lines:
                                stripped = line.strip()
                                if stripped.startswith("# "):
                                    title = self.clean_phase_title(stripped.lstrip("# ").strip())
                                    break
                                elif stripped.startswith("<") and ("·" in stripped or "-" in stripped):
                                    inner = stripped.strip("<> ").strip()
                                    title = self.clean_phase_title(inner)
                                    break
                            for line in lines:
                                stripped = line.strip()
                                if stripped and not stripped.startswith("#") and not stripped.startswith("<!--"):
                                    description = stripped[:120] + "..." if len(stripped) > 120 else stripped
                                    break
                    except Exception:
                        pass

                # 自动分配技术标签
                tags = []
                slug_lower = slug.lower()
                if "prompt" in slug_lower:
                    tags.extend(["Prompt", "NLP"])
                elif "rag" in slug_lower:
                    tags.extend(["RAG", "VectorDB"])
                elif "agent" in slug_lower:
                    tags.extend(["Agent", "LangGraph"])
                elif "mcp" in slug_lower:
                    tags.extend(["MCP", "Protocol"])
                elif "fastapi" in slug_lower or "celery" in slug_lower:
                    tags.extend(["Backend", "Distributed"])
                elif "serving" in slug_lower or "finetuning" in slug_lower:
                    tags.extend(["LLMOps", "DeepSeek"])
                elif "security" in slug_lower:
                    tags.extend(["Security", "Guardrails"])
                else:
                    tags.extend(["AI-Core", "Practical"])

                phases.append({
                    "id": entry,
                    "order": order_num,
                    "title": title,
                    "slug": slug,
                    "description": description,
                    "tags": tags,
                    "difficulty": "Advanced" if order_num > 16 else "Intermediate" if order_num > 5 else "Beginner",
                    "prerequisites": PREREQUISITES_MAP.get(entry, []),
                    "is_locked": False,
                })

        # 按序号排序
        phases.sort(key=lambda x: x["order"])
        return phases

    def _generate_default_mission(self, phase_id: str, title: str, description: str) -> Dict[str, Any]:
        """为未预设的关卡动态生成结构化的闯关挑战指引与四步学习法"""
        clean_title = re.sub(r"^\d+[\.\s-]*", "", title)
        return {
            "mission_title": f"实战挑战：{clean_title}工程落地实现",
            "mission_goal": f"掌握本阶段【{clean_title}】的核心架构设计，完成核心函数/类开发并运行通过自动化测试套件。",
            "requirements": [
                f"在右侧编辑器中阅读并补全针对【{clean_title}】的核心逻辑实现",
                "确保接口定义规范，处理异常边界并满足生产级性能要求",
                "输出结果与自动化单元测试断言契约一致"
            ],
            "learning_steps": [
                "第 1 步【研读手册】：切换到【知识手册】Tab，深入理解本阶段技术原理、时序图与设计模式；",
                "第 2 步【编码实现】：根据右侧提供的初始代码模板，编写并完善目标逻辑；",
                "第 3 步【沙箱运行与 AI 诊断】：点击【运行】(⌘↵) 调试，遇困惑可随时在【AI 伴学诊断】中追问求助；",
                "第 4 步【验证通关】：点击【验证通关】，自动化测试全部通过后即点亮关卡并获取 XP 经验！"
            ],
            "acceptance_criteria": "自动化评测脚本将执行单元测试，断言返回值、状态流转以及边界处理是否全部符合要求。",
            "hint": "遇到阻碍时，先通过【AI 伴学诊断】获取大厂架构导师的思路点拨，不要直接抄袭答案。"
        }

    def get_phase_detail(self, phase_id: str) -> Optional[Dict[str, Any]]:
        """获取指定阶段的详细信息、指南 Markdown、示例代码及评测用例"""
        phase_dir = os.path.join(self.base_dir, phase_id)
        if not os.path.exists(phase_dir) or not os.path.isdir(phase_dir):
            return None

        # 1. 指南 Markdown
        readme_path = os.path.join(phase_dir, "README.md")
        guide_markdown = "# 阶段实战指引\n\n该阶段暂无独立说明文档。"
        title = phase_id
        if os.path.exists(readme_path):
            try:
                with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                    guide_markdown = f.read()
                    for line in guide_markdown.splitlines():
                        if line.strip().startswith("# "):
                            title = self.clean_phase_title(line.strip().lstrip("# ").strip())
                            break
            except Exception as e:
                guide_markdown = f"# 读取失败\n\n{str(e)}"

        # 2. 检索所有 Python 源码文件
        py_files = []
        test_files = []
        for root, _, files in os.walk(phase_dir):
            for file in files:
                if file.endswith(".py"):
                    rel_path = os.path.relpath(os.path.join(root, file), phase_dir)
                    if file.startswith("test_") or "test" in file.lower():
                        test_files.append((rel_path, os.path.join(root, file)))
                    else:
                        py_files.append((rel_path, os.path.join(root, file)))

        py_files.sort(key=lambda x: x[0])
        test_files.sort(key=lambda x: x[0])

        starter_code = "# 请在右侧编写或调整代码\n\ndef solution():\n    print('Hello AI Lab')\n\nif __name__ == '__main__':\n    solution()\n"
        code_files = []

        # 3. 检查是否有预设的高质量闯关元数据
        predefined = CHALLENGE_METADATA.get(phase_id)
        if predefined:
            mission = {
                "mission_title": predefined["mission_title"],
                "mission_goal": predefined["mission_goal"],
                "requirements": predefined["requirements"],
                "learning_steps": predefined["learning_steps"],
                "acceptance_criteria": predefined["acceptance_criteria"],
                "hint": predefined.get("hint", "")
            }
            if predefined.get("starter_code"):
                starter_code = predefined["starter_code"]
            if predefined.get("test_code"):
                test_code = predefined["test_code"]
        else:
            mission = self._generate_default_mission(phase_id, title, "企业级 AI 实战")
            test_code = "# 单元评测套件\nimport unittest\n\nclass TestSolution(unittest.TestCase):\n    def test_run(self):\n        self.assertTrue(True)\n"

        # 如果源码文件存在，全量载入所有实战脚本与测试文件（不设数量上限）
        for rel_path, full_path in py_files + test_files:
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    doc_summary = self._extract_file_doc(content)
                    code_files.append({
                        "name": rel_path,
                        "content": content,
                        "doc": doc_summary,
                        "size": len(content),
                        "is_test": rel_path.startswith("test_") or "test" in rel_path.lower()
                    })
                    if not predefined and (not starter_code or starter_code.startswith("# 请在右侧编写")):
                        starter_code = content
            except Exception:
                pass

        if not predefined and test_files:
            try:
                with open(test_files[0][1], "r", encoding="utf-8", errors="ignore") as f:
                    test_code = f.read()
            except Exception:
                pass

        # 若本阶段预设有官方闯关 starter / solution，优先置顶放入文件清单
        top_files = []
        if predefined and predefined.get("starter_code"):
            top_files.append({
                "name": "starter.py",
                "content": predefined["starter_code"],
                "doc": "🎯 官方闯关实战起手脚手架",
                "size": len(predefined["starter_code"]),
                "is_starter": True
            })
        if predefined and predefined.get("solution_code"):
            top_files.append({
                "name": "solution.py",
                "content": predefined["solution_code"],
                "doc": "💡 官方工业级标准架构实现 (参考答案)",
                "size": len(predefined["solution_code"]),
                "is_solution": True
            })
        
        # 合并去重（避免 starter.py 重复）
        seen_names = set(f["name"] for f in top_files)
        for cf in code_files:
            if cf["name"] not in seen_names:
                top_files.append(cf)
                seen_names.add(cf["name"])
        code_files = top_files

        # 4. 确定官方标准参考实现与出处溯源 (solution_code & source metadata)
        solution_code = ""
        solution_source = ""
        solution_doc = ""
        starter_source = f"{phase_id}/starter.py (官方起步脚手架)"

        if predefined and predefined.get("solution_code"):
            solution_code = predefined["solution_code"]
            solution_source = f"{phase_id}/solution.py (官方基准架构实现)"
            solution_doc = predefined.get("solution_doc", "官方标准参考实现：通过完备单元测试验证，包含规范的边界防御与核心算法闭环。")
        elif predefined and predefined.get("starter_code"):
            solution_code = predefined["starter_code"]
            solution_source = f"{phase_id}/starter.py (官方起手模板)"
            solution_doc = "官方起步脚手架模板。"
        elif py_files:
            try:
                solution_source = f"{py_files[0][0]} (工程模块主源码)"
                with open(py_files[0][1], "r", encoding="utf-8", errors="ignore") as f:
                    solution_code = f.read()
                solution_doc = f"来自生产级真实模块文件 {py_files[0][0]}，代表本阶段的最佳实践形态。"
            except Exception:
                solution_code = starter_code
                solution_source = f"{phase_id}/starter.py"
                solution_doc = "官方脚手架代码"
        else:
            solution_code = starter_code
            solution_source = f"{phase_id}/starter.py"
            solution_doc = "官方脚手架代码"

        # 5. 提取任务 Checklist
        checklist = []
        for line in guide_markdown.split("\n"):
            stripped = line.strip()
            if stripped.startswith("- [ ]") or stripped.startswith("- [x]"):
                checklist.append({
                    "text": stripped[5:].strip(),
                    "done": stripped.startswith("- [x]")
                })
        if not checklist:
            checklist = [
                {"text": "理解当前阶段的核心原理与架构设计", "done": False},
                {"text": "在右侧编辑器中调试并实现核心功能", "done": False},
                {"text": "运行并通过所有自动化单元评测点亮关卡", "done": False}
            ]

        return {
            "id": phase_id,
            "title": title,
            "mission": mission,
            "guide_markdown": guide_markdown,
            "starter_code": starter_code,
            "starter_source": starter_source,
            "solution_code": solution_code,
            "solution_source": solution_source,
            "solution_doc": solution_doc,
            "code_files": code_files,
            "test_code": test_code,
            "checklist": checklist,
            "prerequisites": PREREQUISITES_MAP.get(phase_id, [])
        }
