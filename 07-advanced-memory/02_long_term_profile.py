import os
import operator
import asyncio
from typing import Annotated, TypedDict, List
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

# 1. 配置
load_dotenv()
PROFILE_DB_DIR = "07-advanced-memory/profile_db"

# 初始化向量库用于存储用户画像
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = Chroma(persist_directory=PROFILE_DB_DIR, embedding_function=embeddings)

# 2. 定义长效记忆工具
@tool
def save_user_fact(fact: str):
    """
    当发现关于用户的长期事实（如姓名、偏好、习惯、职业等）时，调用此工具。
    例如: "用户叫小明", "用户习惯深夜工作", "用户是一名 Rust 开发者"。
    """
    print(f"🧠 [记忆同步]: 正在将事实存入长期内存 -> {fact}")
    vectorstore.add_texts(texts=[fact], metadatas=[{"category": "user_fact"}])
    return "事实已记录。"

@tool
def query_user_profile(query: str) -> str:
    """查询关于该用户的长期记忆。"""
    docs = vectorstore.similarity_search(query, k=5)
    if not docs:
        return "没有找到相关的长期记忆。"
    facts = "\n".join([f"- {d.page_content}" for d in docs])
    return f"关于该用户的长期记忆片段:\n{facts}"

tools = [save_user_fact, query_user_profile]
tool_node = ToolNode(tools)

# 3. 定义状态
class ProfileState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    # 存储从数据库检索出的背景信息，供模型参考
    user_context: str

# 4. 节点逻辑

def call_model(state: ProfileState):
    """大脑节点：整合长期背景和当前对话。"""
    model = ChatOpenAI(model_name="deepseek-chat", temperature=0).bind_tools(tools)
    
    # 构建包含长期背景的系统提示词
    context = state.get("user_context", "尚不了解该用户。")
    system_prompt = (
        f"你是一个拥有长效记忆的助手。以下是你对该用户的长期了解：\n{context}\n"
        "如果对话中出现了关于用户的新事实，请务必调用 save_user_fact 进行更新。"
        "回答时请表现得像一个认识用户很久的朋友。"
    )
    
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}

def initialize_context(state: ProfileState):
    """初始化节点：在对话开始前，先去向量库搜一下用户是谁。"""
    print("🔍 [系统]: 正在唤醒长期记忆...")
    # 简单起见，我们用“该用户”作为关键词搜索
    docs = vectorstore.similarity_search("用户信息 偏好 习惯", k=10)
    context = "\n".join([d.page_content for d in docs]) if docs else "这是一个新用户。"
    return {"user_context": context}

def should_continue(state: ProfileState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

# 5. 构建图
workflow = StateGraph(ProfileState)

workflow.add_node("initialize", initialize_context)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("initialize")
workflow.add_edge("initialize", "agent")

workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# 6. 模拟两场会话，展示跨 session 记忆
async def run_long_term_demo():
    config = {"configurable": {"thread_id": "permanent-user-1"}}

    print("\n--- 场景 1: 第一次见面 ---")
    input_1 = {"messages": [HumanMessage(content="嘿，你好！我叫阿强，我是一名 Rust 迷，我发誓我这辈子只用 Vim 写代码。")]}
    async for event in app.astream(input_1, config=config):
        for key, value in event.items():
            if key == "agent" and value["messages"][-1].content:
                print(f"🤖 Agent: {value['messages'][-1].content}")

    print("\n" + "="*50)
    print("模拟：程序关闭... 数据库已持久化。")
    print("="*50)

    print("\n--- 场景 2: 第二天再次见面 ---")
    # 注意：这里我们甚至可以换一个全新的 thread_id，只要逻辑上关联到同一个人（实际开发中可用 user_id）
    # 为了演示简单，我们仍用同一 thread，但关键在于 initialize 节点是从磁盘读取的
    input_2 = {"messages": [HumanMessage(content="又是忙碌的一天，你还记得我喜欢用什么编辑器吗？")]}
    async for event in app.astream(input_2, config=config):
        for key, value in event.items():
            if key == "agent" and value["messages"][-1].content:
                print(f"🤖 Agent: {value['messages'][-1].content}")

if __name__ == "__main__":
    asyncio.run(run_long_term_demo())
