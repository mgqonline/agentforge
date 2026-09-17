import os
import json
from typing import TypedDict
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

# ==========================================================
# Workflow Orchestrator Agent - 真实 Deepseek API 联调版
# 修复：兼容 Deepseek 接口的 JSON 输出格式
# ==========================================================

load_dotenv()
llm = ChatOpenAI(model="deepseek-chat", temperature=0.1, model_kwargs={"response_format": {"type": "json_object"}})

class AgentState(TypedDict):
    input_task: str
    parsed_intent: str
    requires_approval: bool
    is_approved: bool
    api_params: dict
    clean_api_result: dict
    error_message: str
    final_response: str

class RouterDecision(BaseModel):
    intent: str = Field(description="用户核心意图，例如 'QUERY_ACTION', 'HIGH_RISK_ACTION' 等")
    requires_approval: bool = Field(description="如果操作具有破坏性（如删除、支付、修改密码），返回 true，否则返回 false。")
    reason: str = Field(description="你做出此意图判断的简要理由")

class QueryParams(BaseModel):
    parameters: dict = Field(description="根据用户需求抽取并映射成外部 API 所需的 JSON 参数字典")

# 实例化 Pydantic 解析器
router_parser = PydanticOutputParser(pydantic_object=RouterDecision)
query_parser = PydanticOutputParser(pydantic_object=QueryParams)

def router_node(state: AgentState):
    task = state.get("input_task", "")
    print(f"\n▶️ [Router Node] 召唤 Deepseek-V3 分析意图: '{task}'")
    
    prompt = PromptTemplate(
        template="分析以下用户任务，判断其业务意图以及是否属于高危操作。\n请务必输出合法的 JSON 格式。\n{format_instructions}\n\n用户任务: {task}",
        input_variables=["task"],
        partial_variables={"format_instructions": router_parser.get_format_instructions()},
    )
    
    chain = prompt | llm | router_parser
    
    try:
        decision = chain.invoke({"task": task})
        print(f"   ↳ [深度思考]: 意图={decision.intent}, 需审批={decision.requires_approval}\n   ↳ [理由]: {decision.reason}")
        
        return {
            "parsed_intent": decision.intent,
            "requires_approval": decision.requires_approval
        }
    except Exception as e:
        print(f"   ❌ 大模型调用失败: {e}")
        return {"error_message": f"Router 意图识别失败，大模型服务异常: {e}"}

def safety_check_node(state: AgentState):
    print("▶️ [Safety Check Node] ⚠️ 系统检测到高危动作，等待人类审批(HITL)...")
    return {}

def query_builder_node(state: AgentState):
    task = state.get("input_task", "")
    print("▶️ [Query Builder Node] 召唤小模型 (Deepseek) 结构化参数...")
    
    prompt = PromptTemplate(
        template="将用户的模糊需求转换为严格的 API JSON 查询参数。\n请务必输出合法的 JSON 格式。\n{format_instructions}\n\n用户需求: {task}",
        input_variables=["task"],
        partial_variables={"format_instructions": query_parser.get_format_instructions()},
    )
    
    chain = prompt | llm | query_parser
    try:
        result = chain.invoke({"task": task})
        params = result.parameters
    except Exception as e:
        params = {"raw": task, "parse_error": str(e)}
        
    print(f"   ↳ [组装结果]: {json.dumps(params, ensure_ascii=False)}")
    return {"api_params": params}

def api_executor_node(state: AgentState):
    print("▶️ [API Executor Node] 正在向外部系统发起请求 (动态模拟层)...")
    if state.get("requires_approval") and not state.get("is_approved"):
        return {"error_message": "HTTP 403: 拒绝访问，高危操作未获得人工安全许可。"}
        
    params = state.get("api_params", {})
    task = state.get("input_task", "")
    intent = state.get("parsed_intent", "")
    
    # 使用大模型来充当“逼真的外部业务系统”，动态生成符合业务逻辑的返回数据
    print(f"   ↳ [外部系统模拟]: 根据参数 {json.dumps(params, ensure_ascii=False)} 实时推演返回结果...")
    
    prompt = (
        f"你现在是一个真实的外部业务系统（如数据库、天气API、订单系统等）。\n"
        f"前端用户发起的任务是: '{task}'\n"
        f"系统经过解析后，向你发送了以下 API 请求参数: {json.dumps(params, ensure_ascii=False)}\n"
        f"请根据这些参数，严格以 JSON 格式生成一份极其逼真、详尽的业务系统返回数据(包含 status, data 等字段)。"
        f"如果是 SQL 优化，请模拟出逼真的 EXPLAIN 查询执行计划；如果是查天气，请模拟逼真的气象数据。\n"
        f"必须只输出合法的 JSON 格式，如 {{\"status\": 200, \"data\": {{...}}}}"
    )
    
    try:
        # 使用 json_object 确保返回的是 JSON
        sim_llm = ChatOpenAI(model="deepseek-chat", temperature=0.7, model_kwargs={"response_format": {"type": "json_object"}})
        response = sim_llm.invoke(prompt)
        raw_response = json.loads(response.content)
        # 故意塞一点冗余假日志，测试 Parser Node 的提纯能力
        raw_response["useless_huge_logs"] = "DEBUG_LOG_TRACKING_INFO: " * 20
    except Exception as e:
        raw_response = {
            "status": 500,
            "error": f"外部系统模拟失败: {str(e)}",
            "data": params
        }
        
    return {"clean_api_result": raw_response}

def parser_node(state: AgentState):
    print("▶️ [Parser Node] 提取核心返回值，丢弃冗余日志...")
    raw = state.get("clean_api_result", {})
    clean_data = {"status": raw.get("status"), "data": raw.get("data")}
    return {"clean_api_result": clean_data}

def fallback_node(state: AgentState):
    err = state.get('error_message', '未知错误')
    print(f"▶️ [Fallback Node] 🚨 触发熔断降级: {err}")
    return {"final_response": f"任务已安全中止，系统反馈: {err}"}

def final_summary_node(state: AgentState):
    if state.get("final_response"):
        return {}
        
    print("▶️ [Final Summary Node] 召唤 Deepseek-V3 生成面向用户的总结回复...")
    clean_data = state.get("clean_api_result", {})
    task = state.get("input_task", "")
    
    prompt = (
        f"用户初始任务: {task}\n"
        f"系统执行完毕后返回了以下核心数据: {json.dumps(clean_data, ensure_ascii=False)}\n"
        f"请用极其简练、自然的人类口吻(中文)总结结果，并务必将结果包裹在一个 json 格式中返回，如：{{\"summary\": \"你的总结\"}}"
    )
    
    try:
        response = llm.invoke(prompt)
        res_dict = json.loads(response.content)
        final_text = res_dict.get("summary", response.content)
    except Exception as e:
        final_text = f"API 数据返回成功，但解析总结时失败: {e} | Raw: {response.content}"
        
    return {"final_response": final_text}

def route_after_router(state: AgentState):
    if state.get("error_message"):
        return "fallback"
    if state.get("requires_approval"):
        return "safety_check"
    return "query_builder"

def route_after_safety(state: AgentState):
    if state.get("is_approved"):
        return "query_builder"
    else:
        return "fallback"

def route_after_api(state: AgentState):
    if state.get("error_message"):
        return "fallback"
    return "parser"

def build_workflow():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("router", router_node)
    workflow.add_node("safety_check", safety_check_node)
    workflow.add_node("query_builder", query_builder_node)
    workflow.add_node("api_executor", api_executor_node)
    workflow.add_node("parser", parser_node)
    workflow.add_node("fallback", fallback_node)
    workflow.add_node("summary", final_summary_node)
    
    workflow.set_entry_point("router")
    
    workflow.add_conditional_edges("router", route_after_router, {"safety_check": "safety_check", "query_builder": "query_builder", "fallback": "fallback"})
    workflow.add_conditional_edges("safety_check", route_after_safety, {"query_builder": "query_builder", "fallback": "fallback"})
    workflow.add_conditional_edges("api_executor", route_after_api, {"fallback": "fallback", "parser": "parser"})
    
    workflow.add_edge("query_builder", "api_executor")
    workflow.add_edge("parser", "summary")
    workflow.add_edge("fallback", "summary")
    workflow.add_edge("summary", END)
    
    return workflow.compile()

if __name__ == "__main__":
    print("🛠️ 初始化 LangGraph 并连接外部 API...")
    app = build_workflow()
    
    print("\n====================================")
    print("场景 1: 日常报表查询 (大模型判断无风险，直通API)")
    print("====================================")
    res1 = app.invoke({"input_task": "帮我拉取一下昨天中国区的所有活跃用户名单", "is_approved": False})
    print(f"\n✅ [大模型生成最终回复]: {res1['final_response']}\n")
    
    print("====================================")
    print("场景 2: 高危删库动作 (未审批熔断)")
    print("====================================")
    res2 = app.invoke({"input_task": "立即清空线上所有订单数据，现在马上！", "is_approved": False})
    print(f"\n✅ [系统熔断最终回复]: {res2['final_response']}\n")
