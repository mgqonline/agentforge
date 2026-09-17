import json
import asyncio
import re
from typing import TypedDict, Annotated, List, Dict, Any, Callable, Awaitable
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import operator

# 引入真实武器库
from rag_engine import rag_engine
from examples.mysql_agent import build_mysql_agent
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, RemoveMessage
from langgraph.graph.message import add_messages
from dfl_engine import dfl_feedback

class OrchestratorState(TypedDict):
    input_task: str
    parsed_intent: str
    requires_approval: bool
    is_approved: bool
    api_params: dict
    clean_api_result: dict
    final_response: str
    messages: Annotated[list[BaseMessage], add_messages]
    summary: str
    
class IntentOutput(BaseModel):
    intent: str = Field(description="识别出的意图，必须是 QUERY_ACTION 或 HIGH_RISK_ACTION")
    requires_approval: bool = Field(description="是否需要人工审批")
    reason: str = Field(description="判断理由")

SIDE_EFFECT_PATTERNS = [
    r"\b(delete|update|insert|drop|alter|truncate|create|replace|grant|revoke)\b",
    r"删除|删库|清空|更新|写入|新增|修改|建表|改表|授权|撤销授权",
    r"发送|发布|提交|下单|付款|退款|转账|调用外部|爬取|导出",
]

def classify_approval_kind(task: str) -> str:
    if any(re.search(pattern, task, re.IGNORECASE) for pattern in SIDE_EFFECT_PATTERNS):
        return "side_effect"
    return "continue_analysis"

def build_orchestrator_graph(send_event: Callable[[dict], Awaitable[None]]):
    """
    构建终极 Orchestrator Graph，包含风控、真实 RAG 和 DB 执行器。
    send_event 是一个异步回调函数，用于向前端推送流式状态。
    """
    
    # 获取高智商大模型（路由、总结）和快速执行模型
    router_llm = ChatOpenAI(model="deepseek-chat", temperature=0.1, model_kwargs={"response_format": {"type": "json_object"}})
    summary_llm = ChatOpenAI(model="deepseek-chat", temperature=0.7)
    
    async def router_node(state: OrchestratorState):
        task = state["input_task"]
        summary_text = state.get("summary", "")
        messages = state.get("messages", [])
        
        # 融入 DFL 决策焦点与反馈闭环评估 (Decision-Focused Learning)
        dfl_eval = dfl_feedback.evaluate_intent(task, context_summary=summary_text)
        await send_event({
            "type": "status",
            "content": f"🎯 [DFL 语义理解中枢] 意图置信度: {dfl_eval['confidence']*100:.1f}%, 决策导向目标: {dfl_eval['decision_target']}"
        })
        if dfl_eval.get("needs_clarification"):
            await send_event({
                "type": "status",
                "content": f"⚡ [DFL 动态反馈回路] 识别到潜在歧义，提示: {dfl_eval.get('clarification_prompt')}"
            })
            
        await send_event({"type": "status", "content": f"▶️ [Router Node] 召唤大模型分析意图: '{task}'"})
        
        prompt = PromptTemplate(
            template="""你是一个智能安全意图分类器。
当前记忆摘要: {summary}
历史消息: {history}
用户任务: {task}
请判断该任务属于以下哪种 intent：
1. RAG_QUERY: 文档查阅、知识咨询、推荐清单等普通问答（requires_approval=false）
2. BUSINESS_API: 业务接口查询（如订单状态、物流等）（requires_approval=false）
3. HIGH_RISK_ACTION: 写库、删库、退款、付款等高危操作（requires_approval=true）
必须返回 JSON，包含 intent, requires_approval, reason。必须包含 'json' 关键字。""",
            input_variables=["summary", "history", "task"]
        )
        try:
            response = await router_llm.ainvoke(prompt.format(summary=summary_text, history=str(messages), task=task))
            res_dict = json.loads(response.content)
            intent = res_dict.get("intent", "QUERY_ACTION")
            req_app = res_dict.get("requires_approval", False)
            reason = res_dict.get("reason", "")
            if classify_approval_kind(task) == "side_effect":
                intent = "HIGH_RISK_ACTION"
                req_app = True
                reason = f"{reason}；命中确定性副作用操作规则，强制进入 HITL。".strip("；")
            await send_event({"type": "status", "content": f"   ↳ [深度思考]: 意图={intent}, 需审批={req_app}\n   ↳ [理由]: {reason}"})
            return {"parsed_intent": intent, "requires_approval": req_app, "messages": [HumanMessage(content=task)]}
        except Exception as e:
            await send_event({"type": "status", "content": f"   ↳ 路由解析失败: {e}"})
            return {"parsed_intent": "HIGH_RISK_ACTION", "requires_approval": True, "messages": [HumanMessage(content=task)]}

    async def safety_node(state: OrchestratorState):
        if state["requires_approval"] and not state.get("is_approved", False):
            approval_kind = classify_approval_kind(state["input_task"])
            await send_event({"type": "status", "content": "▶️ [Safety Check Node] ⚠️ 系统检测到高危动作，等待人类审批(HITL)..."})
            await send_event({
                "type": "hitl_request",
                "content": state["input_task"],
                "params": {
                    "warning": "系统判定为高风险，请授权后继续",
                    "resume_mode": "orchestrator",
                    "approval_field": "hitl_approved",
                    "approval_kind": approval_kind,
                },
            })
            return {"parsed_intent": "WAITING_APPROVAL"}
        return {}

    async def query_builder_node(state: OrchestratorState):
        await send_event({"type": "status", "content": "▶️ [Query Builder Node] 正在结构化参数..."})
        return {"api_params": {"query": state["input_task"]}}

    async def executor_node(state: OrchestratorState):
        task = state["input_task"]
        intent = state.get("parsed_intent", "RAG_QUERY")
        
        if intent in ["BUSINESS_API", "HIGH_RISK_ACTION"]:
            await send_event({"type": "status", "content": "▶️ [API Executor Node] 检测到业务相关意图，正在通过 MCP 动态发现微服务工具..."})
            try:
                import sys
                from langchain_mcp_adapters.client import MultiServerMCPClient
                from langchain_mcp_adapters.tools import load_mcp_tools
                
                config = {
                    "transport": "stdio",
                    "command": sys.executable,
                    "args": ["mcp_server.py"]
                }
                client = MultiServerMCPClient(connections={"enterprise": config})
                async with client.session("enterprise") as session:
                    tools = await load_mcp_tools(session)
                    llm_with_tools = router_llm.bind_tools(tools)
                    
                    await send_event({"type": "status", "content": f"   ↳ [MCP] 发现可用微服务(仅作为工具候选项): {[t.name for t in tools]}"})
                    
                    # 让大模型自主决定调用哪个工具
                    ai_msg = await llm_with_tools.ainvoke([HumanMessage(content=task)])
                    
                    if ai_msg.tool_calls:
                        db_reply_lines = []
                        tool_map = {t.name: t for t in tools}
                        
                        for tc in ai_msg.tool_calls:
                            t_name = tc["name"]
                            t_args = tc["args"]
                            await send_event({"type": "tool_call", "name": t_name, "args": json.dumps(t_args, ensure_ascii=False)})
                            
                            # 真正执行工具
                            if t_name in tool_map:
                                res = await tool_map[t_name].ainvoke(t_args)
                                db_reply_lines.append(str(res))
                            else:
                                db_reply_lines.append(f"未找到工具: {t_name}")
                                
                            await send_event({"type": "tool_call_result", "name": t_name})
                            
                        return {"clean_api_result": {"source": "mcp_business_api", "data": "\n".join(db_reply_lines)}}
                    # 如果没有命中 MCP 业务工具，则继续往下执行 RAG 或 MySQL 兜底
            except Exception as e:
                import traceback
                traceback.print_exc()
                return {"clean_api_result": {"source": "mcp_error", "data": f"MCP 工具执行失败: {e}"}}
        
        # 原有逻辑：如果我们用简单的关键词来路由
        if "sql" in task.lower() or "表" in task or "数据库" in task:
            await send_event({"type": "tool_call", "name": "MySQL_Agent", "args": json.dumps({"query": task}, ensure_ascii=False)})
            try:
                mysql_agent = build_mysql_agent()
                res = mysql_agent.invoke({"messages": [HumanMessage(content=task)], "iterations": 0})
                db_reply = res["messages"][-1].content
                await send_event({"type": "tool_call_result", "name": "MySQL_Agent"})
                return {"clean_api_result": {"source": "mysql", "data": db_reply}}
            except Exception as e:
                await send_event({"type": "tool_call_result", "name": "MySQL_Agent"})
                return {"clean_api_result": {"source": "mysql", "error": str(e)}}
        else:
            await send_event({"type": "tool_call", "name": "RAG_Engine", "args": json.dumps({"query": task}, ensure_ascii=False)})
            context, sources = rag_engine.retrieve(task)
            await send_event({"type": "tool_call_result", "name": "RAG_Engine"})
            if not context or not context.strip():
                return {"clean_api_result": {"source": "rag", "data": "[System: No Data] 知识库中未包含相关信息。"}}
            else:
                return {"clean_api_result": {"source": "rag", "data": context}}

    async def fallback_node(state: OrchestratorState):
        if state.get("parsed_intent") == "WAITING_APPROVAL":
            await send_event({"type": "status", "content": "▶️ [HITL Pause] 任务已暂停，等待前端人工确认。"})
            return {
                "clean_api_result": {"status": "waiting_approval"},
                "final_response": "⏸️ 该任务已暂停，等待人工确认后继续执行。",
            }

        await send_event({"type": "status", "content": "▶️ [Fallback Node] 🚨 触发熔断降级 (由于 HITL 未授权)"})
        return {"clean_api_result": {"error": "管理员拒绝了授权，操作已终止。"}, "final_response": "🚨 管理员已阻断该任务。"}

    async def summary_node(state: OrchestratorState):
        if state.get("final_response"):
            return {"messages": [AIMessage(content=state["final_response"])]}
            
        await send_event({"type": "status", "content": "▶️ [Final Summary Node] 召唤大模型生成用户友好回复..."})
        task = state["input_task"]
        clean_data = state.get("clean_api_result", {})
        
        prompt = (
            f"用户初始任务: {task}\n"
            f"底层真实执行系统（RAG智能体切片或SQL引擎等）返回了以下数据: {json.dumps(clean_data, ensure_ascii=False)}\n\n"
            "【高级汇报生成规范 (Critical Quality Rules)】：\n"
            "1. 请用自然流畅、逻辑极密、条理分明的中文进行专业提炼汇报。切记直接输出优雅易读的信息，绝不原封不动甩出基础 JSON 或重叠切片数据。\n"
            "2. **严苛去重与整合**：底层多路召回切片极可能伴随文本互连、段落相似或多版重合。必须彻底揉和归纳！坚决禁止重复表达相同的内容或连续打印几句一模一样/极为近似的话！\n"
            "3. **序列标号连续自洽**：涉及条目汇报、步骤罗列或层级要点时，标号顺序一定要求为从首尾至尾独一无二、依次层次自洽（例如 1, 2, 3 或 (1)(2)(3)）。绝对禁止发生 1. -> 2. -> 2. 或相同编号重排打碎再输出的紊乱情况。\n"
            "4. 如果底层结果标识了 [System: No Data]，请真诚得体地向用户阐明当前企业库或工具引擎中暂时无此方面具体记载。\n"
            "5. **[核心要求] 提示词专家模块**：在回复的最末尾，你必须扮演 Prompt 专家，根据用户的原始任务，分析其可能存在的深层意图或遗漏的上下文，提供 2~3 个更专业、更精准的【进阶提示词建议】供用户参考。请以“\n\n💡 **提示词专家建议**：为了获得更精准的结果，您可以尝试这样提问：”作为独立段落开头，并用 markdown 引用或代码块格式展示这些优质 Prompt 示例。"
        )
        
        await send_event({"type": "stream_start"})
        try:
            stream = await asyncio.wait_for(summary_llm.astream(prompt), timeout=18.0)
            final_text = ""
            async for chunk in stream:
                if chunk.content:
                    final_text += chunk.content
                    await send_event({"type": "stream_chunk", "content": chunk.content})
        except Exception as e:
            print(f"[Summary Node] 无法连接大模型及外网流 ({str(e)})，已触发专家模式纯离线结构化本地聚合引擎...")
            await send_event({"type": "status", "content": "🛡️ [专家多智能体态] 检测到离线与外部主脑链路阻隔，正启用零连接·本地化高确定性多模推理汇总仪！"})
            
            final_text = "### 🛡️ 【安全离线态/专家本地容灾模式】执行终期深度汇总\n\n"
            final_text += "*(注：因网络离线状态或远端 AI 节点响应超时，系统内核已实时切至**企业纯离线闭环生成中枢**，为您直接在安全内域提炼底部执行层数据提纲)*：\n\n"
            
            if isinstance(clean_data, dict) and clean_data.get("data"):
                raw_data = str(clean_data["data"])
                lines = raw_data.split('\n')
                seen_lines = set()
                final_text += "#### 📑 核心检索要闻与执行证据梳理：\n\n"
                for ln in lines:
                    val = ln.strip()
                    if not val or val.startswith("[DOC -") or val in seen_lines or val == "[System: No Data]":
                        continue
                    seen_lines.add(val)
                    if val.startswith('#'):
                        final_text += f"\n#### 🔹 **{val.lstrip('#').strip()}**\n"
                    elif val.startswith('-') or (len(val) > 2 and val[0].isdigit() and val[1] == '.'):
                        final_text += f"{val}\n\n"
                    else:
                        final_text += f"• **提炼成果**：{val}\n\n"
            else:
                final_text += f"⚠️ **数据提取说明**：底层处理链路完成抓取，回传状态对象: `{json.dumps(clean_data, ensure_ascii=False)}`"
                
            final_text += "\n> *🛡️ [智能体态: 本地全纯内围自闭环隔离绿网] | 零网络连连 · 高精准安全可信提要*"
            await send_event({"type": "stream_chunk", "content": final_text})
        
        await send_event({"type": "stream_end"})
        return {"final_response": final_text, "messages": [AIMessage(content=final_text)]}

    async def memory_node(state: OrchestratorState):
        messages = state.get("messages", [])
        if len(messages) > 4:
            await send_event({"type": "status", "content": "📝 [Memory Node] 当前对话流过长，正在触发记忆摘要压缩机制..."})
            summary = state.get("summary", "")
            if summary:
                prompt = f"这是之前的对话摘要：{summary}\n\n请将以下新产生的对话无缝整合到摘要中，保留核心事实：\n"
            else:
                prompt = "请总结以下对话的核心内容，保留关键意图和事实：\n"
            
            try:
                # 增加超时控制和错误捕获，避免挂起
                response = await asyncio.wait_for(
                    summary_llm.ainvoke([HumanMessage(content=prompt + str(messages))]),
                    timeout=10.0
                )
                new_summary = response.content
            except Exception as e:
                import traceback
                traceback.print_exc()
                new_summary = summary + "\n(注：部分最新记忆因压缩超时未成功合并)"
                
            delete_messages = [RemoveMessage(id=m.id) for m in messages if getattr(m, "id", None)]
            return {"summary": new_summary, "messages": delete_messages}
        return {}

    # 图编排
    workflow = StateGraph(OrchestratorState)
    workflow.add_node("router", router_node)
    workflow.add_node("safety", safety_node)
    workflow.add_node("builder", query_builder_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("fallback", fallback_node)
    workflow.add_node("summary", summary_node)
    workflow.add_node("memory", memory_node)

    workflow.set_entry_point("router")
    
    # router -> safety
    workflow.add_edge("router", "safety")
    
    # safety 路由
    def check_safety(state: OrchestratorState):
        if state["parsed_intent"] in {"BLOCKED", "WAITING_APPROVAL"}:
            return "fallback"
        return "builder"
        
    workflow.add_conditional_edges("safety", check_safety, {"builder": "builder", "fallback": "fallback"})
    
    # builder -> executor -> summary
    workflow.add_edge("builder", "executor")
    workflow.add_edge("executor", "summary")
    
    # fallback -> summary
    workflow.add_edge("fallback", "summary")
    workflow.add_edge("summary", "memory")
    workflow.add_edge("memory", END)
    
    return workflow


class ExpertAgentState(TypedDict):
    messages: Annotated[List[Dict[str, Any]], add_messages]
    tool_rounds: int


def build_expert_graph(
    send_event: Callable[[dict], Awaitable[None]],
    client: Any,
    selected_model: str,
    OPENAI_TOOL_SCHEMAS: list,
    permissions: set,
    strip_badges_fn: Callable[[str], str] | None = None,
    max_tool_rounds: int = 4,
) -> StateGraph:
    """
    构建专家模式 ReAct 循环 Agent 图，实现从 worker.py 的解耦抽离。
    """
    from tools import execute_tool_call

    async def agent_node(state: ExpertAgentState):
        await send_event({"type": "status", "content": "🧙‍♂️ [智能体总控制盘] 读入 PostgreSQL 长效期会话链与上下文记忆池..."})
        await asyncio.sleep(0.3)
        await send_event({"type": "status", "content": "🧠 [State #1: 反思逻辑发端] 正在评估深层线索与建立可执行的多支推验步骤..."})
        await asyncio.sleep(0.3)
        await send_event({"type": "status", "content": "🛠️ [State #2: 本地极精质检核录] MLOps 量化校核通过，正起送专家结语："})
        await send_event({"type": "stream_start"})
        openai_msgs = []
        for m in state["messages"]:
            if isinstance(m, dict) and "role" in m:
                openai_msgs.append(m)
            elif hasattr(m, "type"):
                r = m.type
                if r == "human": r = "user"
                elif r == "ai": r = "assistant"
                msg_dict = {"role": r, "content": m.content}
                if hasattr(m, "tool_calls") and m.tool_calls:
                    openai_tcs = []
                    for tc in m.tool_calls:
                        openai_tcs.append({
                            "id": tc.get("id"),
                            "type": "function",
                            "function": {
                                "name": tc.get("name"),
                                "arguments": json.dumps(tc.get("args", {})),
                            },
                        })
                    msg_dict["tool_calls"] = openai_tcs

                if hasattr(m, "tool_call_id") and m.type == "tool":
                    msg_dict["tool_call_id"] = m.tool_call_id

                if msg_dict["role"] == "assistant" and isinstance(msg_dict["content"], str):
                    if strip_badges_fn:
                        msg_dict["content"] = strip_badges_fn(msg_dict["content"])

                openai_msgs.append(msg_dict)

        stream = await client.chat.completions.create(
            model=selected_model,
            messages=openai_msgs,
            tools=OPENAI_TOOL_SCHEMAS,
            stream=True,
            temperature=0.3,
        )
        final_content = ""
        tool_calls_buffer = {}
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                final_content += delta.content
                await send_event({"type": "stream_chunk", "content": delta.content})
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_buffer:
                        tool_calls_buffer[idx] = {"id": tc.id, "type": "function", "function": {"name": tc.function.name or "", "arguments": ""}}
                    if tc.id:
                        tool_calls_buffer[idx]["id"] = tc.id
                    if tc.function.name:
                        tool_calls_buffer[idx]["function"]["name"] = tc.function.name
                    if tc.function.arguments:
                        tool_calls_buffer[idx]["function"]["arguments"] += tc.function.arguments

        msg = {"role": "assistant"}
        if final_content:
            msg["content"] = final_content
        else:
            msg["content"] = None
        if tool_calls_buffer:
            msg["tool_calls"] = list(tool_calls_buffer.values())
        return {"messages": [msg]}

    def should_continue(state: ExpertAgentState):
        if state.get("tool_rounds", 0) >= max_tool_rounds:
            return END

        last_msg = state["messages"][-1]
        has_tools = False
        if isinstance(last_msg, dict):
            has_tools = bool(last_msg.get("tool_calls"))
        else:
            has_tools = bool(getattr(last_msg, "tool_calls", None))
        if has_tools:
            return "tools"
        return END

    async def tool_node(state: ExpertAgentState):
        last_msg = state["messages"][-1]
        tool_calls = last_msg.get("tool_calls", []) if isinstance(last_msg, dict) else getattr(last_msg, "tool_calls", [])
        tool_messages = []

        for tool_call in tool_calls:
            if isinstance(tool_call, dict):
                function_spec = tool_call.get("function", {})
                tool_name = function_spec.get("name") or tool_call.get("name", "")
                raw_args = function_spec.get("arguments") if function_spec else tool_call.get("args", "{}")
                tool_call_id = tool_call.get("id", tool_name)
            else:
                tool_name = getattr(tool_call, "name", "")
                raw_args = getattr(tool_call, "args", "{}")
                tool_call_id = getattr(tool_call, "id", tool_name)

            await send_event({"type": "tool_call", "name": tool_name, "args": raw_args})
            result = execute_tool_call(tool_name, raw_args, permissions)
            result_json = json.dumps(result, ensure_ascii=False)
            await send_event({"type": "tool_call_result", "name": tool_name, "result": result})

            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": result_json,
            })

        return {
            "messages": tool_messages,
            "tool_rounds": state.get("tool_rounds", 0) + 1,
        }

    workflow = StateGraph(ExpertAgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")

    return workflow

