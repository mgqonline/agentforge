"""
RepoSense v4.1 (生产级持久化与沙箱隔离版)
==============================================
升级亮点：
  1. 状态流持久化治理：采用 SqliteSaver (同步) 结合 app.stream() 替代 MemorySaver，支持断点重启与持久化。
  2. 隔离沙箱集成：高风险代码运行自动重定向至 SecureSandboxRunner 沙箱。
"""

import os
import operator
import sqlite3
from typing import Annotated, TypedDict, List, Optional, Literal
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver

from sandbox_runner import SecureSandboxRunner

load_dotenv()

# 初始化沙箱执行器
sandbox_runner = SecureSandboxRunner(timeout_seconds=10)
DB_PATH = "projects/repo_sense/checkpoints.sqlite"

# 1. 定义工具集（带沙箱隔离）
@tool
def read_code_file(file_path: str) -> str:
    """读取指定路径文件的代码内容。"""
    print(f"📖 [工具]: 读取文件内容 -> '{file_path}'")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"无法读取文件 {file_path}: {e}"

@tool
def execute_python_in_sandbox(code: str) -> str:
    """在安全隔离沙箱中运行 Python 代码。**高风险操作已通过隔离防护**"""
    print(f"🛡️ [沙箱工具]: 提交代码至隔离沙箱运行...")
    res = sandbox_runner.execute_python_code(code)
    return (
        f"沙箱模式: {res['sandbox_type']}\n"
        f"退出状态码: {res['exit_code']}\n"
        f"标准输出:\n{res['stdout']}\n"
        f"错误输出:\n{res['stderr']}"
    )

# 2. 定义状态与大脑节点
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]

def call_model(state: AgentState):
    system_prompt = (
        "你是一个生产级 AI 工程师助手 RepoSense v4.1。"
        "对于高风险的代码执行，请使用 execute_python_in_sandbox 工具。"
        "所有写文件与沙箱执行操作都会受到人机协同审批防护。"
    )
    api_base = os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("MODEL_NAME", "deepseek-chat")
    
    model = ChatOpenAI(
        model_name=model_name,
        openai_api_key=api_key,
        openai_api_base=api_base,
        temperature=0
    ).bind_tools([read_code_file, execute_python_in_sandbox])
    
    response = model.invoke([SystemMessage(content=system_prompt)] + state["messages"])
    return {"messages": [response]}

tool_node = ToolNode([read_code_file, execute_python_in_sandbox])

def should_continue(state: AgentState) -> Literal["tools", END]:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

# 3. 构造 StateGraph
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

# 4. 持久化 Sqlite Checkpointer 数据库存储绑定
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
checkpointer = SqliteSaver(conn)

# 编译图并设定 HITL 中断节点
app = workflow.compile(checkpointer=checkpointer, interrupt_before=["tools"])


def main():
    print("=" * 60)
    print("🚀 RepoSense v4.1 (SQLite 断点持久化 + 沙箱隔离版) 启动成功！")
    print(f"📁 状态恢复数据库已连接: {DB_PATH}")
    print("=" * 60)

    config = {"configurable": {"thread_id": "session-prod-001"}}
    query = "请编写一段计算斐波那契数列前10项的 Python 代码，并提交到沙箱中验证输出。"
    
    print(f"\n👤 [模拟用户提问]: {query}\n")
    for event in app.stream({"messages": [HumanMessage(content=query)]}, config=config):
        for key, value in event.items():
            if key == "agent":
                msg = value["messages"][-1]
                if msg.tool_calls:
                    print(f"🛑 [HITL 审批断点挂起]: AI 请求调用工具 -> {[t['name'] for t in msg.tool_calls]}")
                    print(f"💡 [Checkpoint 数据库持久化] 状态已被实时写入 {DB_PATH}，随时可断点恢复！")

    # 模拟自动批准 resume 恢复
    print("\n✅ [模拟用户手动同意审批]: 恢复 Agent 智能体执行...")
    for event in app.stream(None, config=config):
        for key, value in event.items():
            if key == "tools":
                print("\n⚙️ [沙箱工具返回结果]:")
                print(value["messages"][-1].content)
            elif key == "agent":
                print(f"\n🤖 [AI 最终回复]:\n{value['messages'][-1].content}")

if __name__ == "__main__":
    main()
