import os
import operator
import asyncio
from typing import Annotated, TypedDict
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver # 简单的内存持久化，实际生产可用 SqliteSaver

# 1. 加载配置
load_dotenv()

# 2. 定义状态
class AgentState(TypedDict):
    # 使用 operator.add 确保消息是累加的
    messages: Annotated[list[BaseMessage], operator.add]

# 3. 定义节点逻辑
def call_model(state: AgentState):
    model = ChatOpenAI(model_name="deepseek-chat", temperature=0)
    response = model.invoke(state["messages"])
    return {"messages": [response]}

# 4. 构建图
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.set_entry_point("agent")
workflow.add_edge("agent", END)

# --- 关键点：配置持久化器 (Checkpointer) ---
# MemorySaver 会在内存中存储图的状态，通过 thread_id 进行隔离
memory = MemorySaver()

# 编译图时传入 checkpointer
app = workflow.compile(checkpointer=memory)

# 5. 模拟多轮对话测试记忆
async def run_persistence_test():
    # 定义两个不同的线程（模拟两个不同的用户或会话）
    config_1 = {"configurable": {"thread_id": "user_A"}}
    config_2 = {"configurable": {"thread_id": "user_B"}}

    print("=== 第一轮：告诉 Agent 我的名字 ===")
    input_1 = {"messages": [HumanMessage(content="你好，我叫小明。")]}
    async for event in app.astream(input_1, config=config_1):
        for value in event.values():
            print(f"Agent (线程 A): {value['messages'][-1].content}")

    print("\n=== 第二轮：切换到另一个线程 B ===")
    input_2 = {"messages": [HumanMessage(content="你好，你知道我是谁吗？")]}
    async for event in app.astream(input_2, config=config_2):
        for value in event.values():
            print(f"Agent (线程 B): {value['messages'][-1].content}")

    print("\n=== 第三轮：回到线程 A，测试它是否还记得我 ===")
    input_3 = {"messages": [HumanMessage(content="嘿，还记得我叫什么吗？")]}
    async for event in app.astream(input_3, config=config_1):
        for value in event.values():
            print(f"Agent (线程 A): {value['messages'][-1].content}")

if __name__ == "__main__":
    asyncio.run(run_persistence_test())
