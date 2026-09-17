import os
import asyncio
import operator
import subprocess
from enum import Enum
from typing import Annotated, TypedDict, List, Optional, Union
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# 1. 配置与环境
load_dotenv()
DB_DIR = "projects/repo_sense/chroma_db"

# 初始化 RAG 检索器
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# 2. 定义工具集
@tool
def code_search(query: str) -> str:
    """在代码库中进行语义搜索，寻找相关的代码片段或实现。"""
    print(f"🔍 [工具]: 搜索代码库 -> '{query}'")
    docs = retriever.invoke(query)
    results = [f"--- 来自文件: {doc.metadata.get('source', '未知')} ---\n{doc.page_content}" for doc in docs]
    return "\n\n".join(results)

@tool
def read_code_file(file_path: str) -> str:
    """读取指定路径文件的完整代码内容。"""
    print(f"📖 [工具]: 读取文件内容 -> '{file_path}'")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"无法读取文件 {file_path}: {e}"

@tool
def write_code_file(file_path: str, content: str) -> str:
    """写入/修改代码文件。"""
    print(f"💾 [工具]: 写入文件 -> '{file_path}'")
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"文件 {file_path} 已成功更新。"
    except Exception as e:
        return f"写入文件失败: {e}"

@tool
def run_terminal_command(command: str) -> str:
    """执行终端命令，如运行测试。"""
    print(f"💻 [工具]: 执行命令 -> '{command}'")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return f"输出:\n{result.stdout}\n错误:\n{result.stderr}"
    except Exception as e:
        return f"执行出错: {e}"

# 定义分阶段的工具节点
tools = [code_search, read_code_file, write_code_file, run_terminal_command]
tool_node = ToolNode(tools)

# 3. 状态机状态定义
class ExecutionPhase(Enum):
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    phase: ExecutionPhase
    plan: str
    retry_count: int

# 4. 节点逻辑

def planner_node(state: AgentState):
    """规划阶段：拆解任务，确定需要修改的文件和步骤。"""
    print(f"\n🎯 [PHASE: {ExecutionPhase.PLANNING.value}] 正在制定执行计划...")
    model = ChatOpenAI(model_name="deepseek-chat", temperature=0)
    system_msg = "你是一个架构师。请分析用户需求，给出详细的步骤。如果是简单查询，直接回答；如果是修改任务，请说明修改逻辑。"
    response = model.invoke([SystemMessage(content=system_msg)] + state["messages"])
    return {"plan": response.content, "phase": ExecutionPhase.EXECUTING, "messages": [AIMessage(content=f"我的执行计划如下：\n{response.content}")]}

def executor_node(state: AgentState):
    """执行阶段：实际调用工具（搜索、读取、写入）。"""
    print(f"🛠️ [PHASE: {ExecutionPhase.EXECUTING.value}] 正在执行任务...")
    model = ChatOpenAI(model_name="deepseek-chat", temperature=0).bind_tools(tools)
    # 给 Executor 的提示词要包含之前的计划
    system_msg = f"你是一个执行工程师。请根据以下计划执行任务：\n{state['plan']}\n在修改代码前必须先读原文件。"
    response = model.invoke([SystemMessage(content=system_msg)] + state["messages"])
    return {"messages": [response]}

def verifier_node(state: AgentState):
    """验证阶段：检查结果，如果失败则决定是否重试。"""
    print(f"✅ [PHASE: {ExecutionPhase.VERIFYING.value}] 正在验证执行结果...")
    model = ChatOpenAI(model_name="deepseek-chat", temperature=0).bind_tools([run_terminal_command])
    system_msg = "你是一个 QA 工程师。请检查之前的修改是否符合预期。如果有测试脚本，请运行它。如果发现问题，请指出并要求修复。"
    response = model.invoke([SystemMessage(content=system_msg)] + state["messages"])
    return {"messages": [response], "phase": ExecutionPhase.VERIFYING}

def route_after_executor(state: AgentState):
    """Executor 后的路由逻辑。"""
    last_msg = state["messages"][-1]
    if last_msg.tool_calls:
        return "tools"
    # 如果没有工具调用了，说明执行暂时告一段落，去验证
    return "verifier"

def route_after_verifier(state: AgentState):
    """Verifier 后的路由逻辑：决定是结束还是回溯修复。"""
    last_msg = state["messages"][-1]
    if last_msg.tool_calls:
        return "tools"
    
    # 简单的启发式：如果最近的消息里提到了“失败”、“错误”且重试次数没超，就回溯
    content = last_msg.content.lower()
    if ("错误" in content or "失败" in content or "fail" in content) and state.get("retry_count", 0) < 2:
        print("⚠️ 验证发现问题，准备回溯修复...")
        return "executor"
    
    return END

# 5. 构建图
workflow = StateGraph(AgentState)

workflow.add_node("planner", planner_node)
workflow.add_node("executor", executor_node)
workflow.add_node("verifier", verifier_node)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("planner")

# 规划完直接去执行
workflow.add_edge("planner", "executor")

# 执行完的路由
workflow.add_conditional_edges(
    "executor",
    route_after_executor,
    {"tools": "tools", "verifier": "verifier"}
)

# 工具节点干完活，总是回到当前阶段的节点
def route_back_from_tools(state: AgentState):
    if state["phase"] == ExecutionPhase.EXECUTING:
        return "executor"
    return "verifier"

workflow.add_conditional_edges("tools", route_back_from_tools, {"executor": "executor", "verifier": "verifier"})

# 验证完的路由
workflow.add_conditional_edges(
    "verifier",
    route_after_verifier,
    {"tools": "tools", "executor": "executor", END: END}
)

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# 6. 交互式对话
async def chat():
    print("\n" + "="*50)
    print("🤖 RepoSense v3.0 (状态机版) 已启动！")
    print("当前流程：[规划] -> [执行] -> [验证] (自动纠错)")
    print("="*50)
    
    config = {"configurable": {"thread_id": "sm-session-1"}}
    
    while True:
        try:
            user_input = input("\n👤 你: ")
            if user_input.lower() in ["exit", "quit", "退出"]:
                break
                
            inputs = {"messages": [HumanMessage(content=user_input)], "phase": ExecutionPhase.PLANNING, "retry_count": 0}
            
            async for event in app.astream(inputs, config=config):
                for key, value in event.items():
                    if key in ["planner", "executor", "verifier"]:
                        msg = value["messages"][-1]
                        if msg.content:
                            # 过滤掉中间的工具调用请求，只打印自然语言输出
                            if not isinstance(msg, AIMessage) or not msg.tool_calls:
                                print(f"\n[{key.upper()}]: {msg.content}")
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    asyncio.run(chat())
