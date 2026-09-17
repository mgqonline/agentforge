import os
import operator
import asyncio
from typing import Annotated, TypedDict, Literal
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_community.embeddings import DeterministicFakeEmbedding
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, RemoveMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

# ==========================================
# 1. 环境与持久化配置
# ==========================================
load_dotenv()
PROFILE_DB_DIR = "07-advanced-memory/comprehensive_profile_db"

# 长期记忆数据库初始化 (使用 FakeEmbedding 规避网络下载报错)
embeddings = DeterministicFakeEmbedding(size=384)
vectorstore = Chroma(persist_directory=PROFILE_DB_DIR, embedding_function=embeddings)

# ==========================================
# 2. 定义长效记忆工具 (Long-Term Memory)
# ==========================================
@tool
def save_user_fact(fact: str):
    """
    当发现关于用户的长期事实（如姓名、偏好、习惯、职业、家庭等）时，务必调用此工具。
    例如: "用户叫李雷", "用户喜欢在早晨喝咖啡", "用户是一名设计师"。
    """
    print(f"\n🧠 [记忆同步]: 提取并存入长期偏好 -> {fact}")
    vectorstore.add_texts(texts=[fact], metadatas=[{"category": "user_fact"}])
    return "事实已永久记录。"

tools = [save_user_fact]
tool_node = ToolNode(tools)

# ==========================================
# 3. 定义图状态 (Graph State)
# ==========================================
class AgentState(TypedDict):
    # 当前对话窗口消息
    messages: Annotated[list[BaseMessage], add_messages]
    # 对话内容的滚动摘要 (短期记忆压缩)
    summary: str
    # 从数据库中检索出的用户长期画像 (长期记忆)
    user_context: str

# ==========================================
# 4. 定义图节点 (Graph Nodes)
# ==========================================
def initialize_context(state: AgentState):
    """初始化节点：在每轮对话开始前，先从数据库查询用户的长期画像。"""
    print("\n🔍 [系统]: 正在唤醒该用户的长期记忆...")
    # 搜索与用户相关的最新记忆片段
    docs = vectorstore.similarity_search("用户 偏好 习惯 身份", k=5)
    context = "\n".join([f"- {d.page_content}" for d in docs]) if docs else "这是一个新用户，尚无长期记忆。"
    return {"user_context": context}

def call_model(state: AgentState):
    """大脑节点：整合长期画像、短期摘要和当前对话进行决策。"""
    model = ChatOpenAI(model_name="deepseek-chat", temperature=0).bind_tools(tools)
    
    # 拼装双重记忆层
    user_context = state.get("user_context", "")
    summary = state.get("summary", "")
    
    system_prompt = (
        "你是一个拥有「短期上下文压缩」和「长期偏好记忆」的专属私人助理。\n\n"
        f"【长期画像】\n以下是你之前提取并记录的该用户长期习惯与偏好：\n{user_context}\n\n"
    )
    if summary:
        system_prompt += f"【短期摘要】\n这是你们最近一段对话的要点摘要：\n{summary}\n\n"
        
    system_prompt += (
        "如果用户在当前对话中暴露了新的长期偏好或习惯，务必调用 `save_user_fact` 记录下来。"
    )
    
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}

def summarize_conversation(state: AgentState):
    """摘要节点：如果对话窗口太长，则生成摘要并折叠消息。"""
    # 当对话轮次超过设定阈值时触发（此处为了演示，阈值设为 4 条）
    if len(state["messages"]) > 4:
        print("\n📝 [系统]: 当前对话流过长，正在触发记忆摘要压缩机制...")
        model = ChatOpenAI(model_name="deepseek-chat", temperature=0)
        
        summary = state.get("summary", "")
        if summary:
            summary_message = f"这是之前的对话摘要：{summary}\n\n请将以下新产生的对话无缝整合到摘要中，保留核心事实：\n"
        else:
            summary_message = "请总结以下对话的核心内容，保留关键意图和事实：\n"
            
        # 让模型生成新的摘要
        summary_response = model.invoke([HumanMessage(content=summary_message + str(state["messages"]))])
        
        # 截断策略：生成摘要后，移除全部已消费的历史消息以释放 Token，避免拆散 tool_calls 导致 OpenAI 报错
        delete_messages = [RemoveMessage(id=m.id) for m in state["messages"] if m.id]
        
        return {"summary": summary_response.content, "messages": delete_messages}
    
    return {"summary": state.get("summary", ""), "messages": []}

def should_continue(state: AgentState):
    """条件路由：判断是否需要执行工具或进行摘要"""
    last_message = state["messages"][-1]
    
    # 如果模型决定调用工具（比如写入长期偏好），则跳转到工具节点
    if last_message.tool_calls:
        return "tools"
    # 否则正常结束当前推理流，进入摘要判断节点
    return "summarizer"

# ==========================================
# 5. 编排工作流流图 (StateGraph)
# ==========================================
workflow = StateGraph(AgentState)

workflow.add_node("initialize", initialize_context)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_node("summarizer", summarize_conversation)

workflow.set_entry_point("initialize")
workflow.add_edge("initialize", "agent")

workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "summarizer": "summarizer"})
workflow.add_edge("tools", "agent")
workflow.add_edge("summarizer", END)

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# ==========================================
# 6. 端到端模拟测试 (End-to-End Test)
# ==========================================
async def test_comprehensive_memory():
    config = {"configurable": {"thread_id": "vip_user_888"}}
    
    print("\n" + "="*50)
    print(" 🚀 测试阶段 1: 建立长期用户画像 (Long-Term Profile)")
    print("="*50)
    
    conversation_1 = [
        "你好，我是张三，以后你就是我的私人助理了。",
        "你要记住，我是一个纯粹的极客，平时只用 Linux，对 Windows 过敏。",
        "另外，我每天早上 9 点必须要喝一杯冰美式才能开始写代码。"
    ]
    
    for text in conversation_1:
        print(f"\n👤 张三: {text}")
        async for event in app.astream({"messages": [HumanMessage(content=text)]}, config=config):
            if "agent" in event and event["agent"]["messages"][-1].content:
                print(f"🤖 助理: {event['agent']['messages'][-1].content}")

    print("\n" + "="*50)
    print(" ⏳ 测试阶段 2: 触发短程对话摘要压缩 (Summary Memory)")
    print("="*50)
    
    conversation_2 = [
        "我现在打算开始今天的工作了。",
        "帮我看一下服务器状态，啊等等，你自己不能看，我一会用 SSH 连上去看。",
        "你觉得我第一步应该先检查日志还是先看监控看板？"
    ]
    
    for text in conversation_2:
        print(f"\n👤 张三: {text}")
        async for event in app.astream({"messages": [HumanMessage(content=text)]}, config=config):
            if "agent" in event and event["agent"]["messages"][-1].content:
                print(f"🤖 助理: {event['agent']['messages'][-1].content}")
            if "summarizer" in event and "summary" in event["summarizer"] and event["summarizer"]["summary"]:
                print(f"✨ [摘要折叠完成]: {event['summarizer']['summary'][:60]}...")

    print("\n" + "="*50)
    print(" 🌙 测试阶段 3: 断开重连后的长期记忆唤醒")
    print("="*50)
    print("（模拟会话关闭，新的一天重新开启应用...）\n")
    
    # 新的一天，开启一个全新的会话 ID (Thread)
    new_config = {"configurable": {"thread_id": "vip_user_888_day_2"}}
    
    async for event in app.astream({"messages": [HumanMessage(content="早啊！我又来搬砖了，我现在该干点啥来提神？")]}, config=new_config):
        if "agent" in event and event["agent"]["messages"][-1].content:
            print(f"🤖 助理: {event['agent']['messages'][-1].content}")

if __name__ == "__main__":
    asyncio.run(test_comprehensive_memory())
