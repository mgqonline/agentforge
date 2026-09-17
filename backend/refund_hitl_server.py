import os
import sqlite3
import operator
from typing import Annotated, TypedDict
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver

load_dotenv()

# ==========================================
# 1. 定义工具 (Tools)
# ==========================================
@tool
def process_refund(order_id: str, amount: float) -> str:
    """高危操作：为指定订单执行真实退款打款。"""
    print(f"\n💸 [系统底层执行]: 正在连接银行接口... 订单 {order_id} 成功退款 {amount} 元！")
    return f"退款成功：订单 {order_id}，金额 {amount} 元"

@tool
def check_order_status(order_id: str) -> str:
    """低危操作：查询订单状态。"""
    print(f"\n🔍 [系统底层执行]: 正在查询订单 {order_id} 状态...")
    return f"订单 {order_id} 状态为：已收货，支持退款。"

tools = [process_refund, check_order_status]
tool_node = ToolNode(tools)

# ==========================================
# 2. 定义 Agent 图 (Graph)
# ==========================================
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]

def call_model(state: AgentState):
    model = ChatOpenAI(model_name="deepseek-chat", temperature=0).bind_tools(tools)
    response = model.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

# 持久化机制：支持跨请求保持图状态
conn = sqlite3.connect("hitl_backend.db", check_same_thread=False)
memory = SqliteSaver(conn)

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

# 核心：拦截 tools 节点
app_graph = workflow.compile(
    checkpointer=memory,
    interrupt_before=["tools"]
)

# ==========================================
# 3. FastAPI 后端服务
# ==========================================
app = FastAPI(title="HITL Agent Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    thread_id: str
    message: str

class ApproveRequest(BaseModel):
    thread_id: str
    approved: bool

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    thread_config = {"configurable": {"thread_id": req.thread_id}}
    inputs = {"messages": [HumanMessage(content=req.message)]}
    
    final_response = ""
    is_paused = False
    pending_tool = None
    
    # 运行图
    for event in app_graph.stream(inputs, config=thread_config):
        for key, value in event.items():
            if key == "agent":
                msg = value["messages"][-1]
                if msg.content:
                    final_response = msg.content
                if msg.tool_calls:
                    pending_tool = msg.tool_calls[0]["name"]
                    
    # 检查状态是否被挂起
    snapshot = app_graph.get_state(thread_config)
    if snapshot.next:
        is_paused = True
        return {
            "status": "pending_approval",
            "message": f"🚨 Agent 申请执行高危工具 `{pending_tool}`，流程已挂起，请主管审批。"
        }
        
    return {
        "status": "completed",
        "message": final_response
    }

@app.post("/api/approve")
async def approve_endpoint(req: ApproveRequest):
    thread_config = {"configurable": {"thread_id": req.thread_id}}
    snapshot = app_graph.get_state(thread_config)
    
    if not snapshot.next:
        return {"status": "error", "message": "当前线程没有等待审批的任务。"}
        
    if req.approved:
        # 批准：传入 None，从断点继续执行
        final_response = ""
        for event in app_graph.stream(None, config=thread_config):
             for key, value in event.items():
                if key == "agent":
                    msg = value["messages"][-1]
                    if msg.content:
                        final_response = msg.content
        return {"status": "completed", "message": final_response}
    else:
        # 驳回：清除挂起状态，在实际业务中我们会修改图的状态，这里为了演示直接报错提示结束
        return {"status": "rejected", "message": "任务已被人类主管驳回。"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("02_hitl_fastapi_backend:app", host="0.0.0.0", port=8081, reload=True)
