import os
import operator
from typing import Annotated, TypedDict, Literal
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage, RemoveMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

# 1. 配置
load_dotenv()

# 2. 定义状态
class SummaryState(TypedDict):
    # 使用 add_messages 替代 operator.add
    # add_messages 会根据消息 ID 自动处理追加、更新和删除 (RemoveMessage)
    messages: Annotated[list[BaseMessage], add_messages]
    # 当前对话的摘要
    summary: str

# 3. 节点逻辑

def call_model(state: SummaryState):
    """大脑节点：根据摘要和新消息进行回复。"""
    model = ChatOpenAI(model_name="deepseek-chat", temperature=0)
    
    # 获取之前的摘要
    summary = state.get("summary", "")
    
    # 如果有摘要，将其作为系统提示词的一部分
    if summary:
        system_message = f"这是之前对话的摘要：{summary}。请基于此背景回答用户。"
        messages = [SystemMessage(content=system_message)] + state["messages"]
    else:
        messages = state["messages"]
        
    response = model.invoke(messages)
    return {"messages": [response]}

def summarize_conversation(state: SummaryState):
    """摘要节点：如果对话太长，则生成摘要并清理消息列表。"""
    # 设定一个阈值：当消息超过 6 条时开始摘要
    if len(state["messages"]) > 6:
        print("📝 [系统]: 对话过长，正在生成摘要以节省 Token...")
        model = ChatOpenAI(model_name="deepseek-chat", temperature=0)
        
        # 将现有摘要和所有消息发给模型生成新摘要
        summary = state.get("summary", "")
        if summary:
            summary_message = f"这是之前的摘要：{summary}\n\n请将以下新消息整合到摘要中：\n"
        else:
            summary_message = "请总结以下对话的核心内容：\n"
            
        summary_response = model.invoke([HumanMessage(content=summary_message + str(state["messages"]))])
        
        # 核心改进：通过返回一个包含特殊逻辑的更新来清空消息
        # 在 LangGraph 中，如果我们想彻底替换列表而不是追加，
        # 我们需要在 State 定义中使用特定的 Reducer，或者在这里采用一种权衡方案。
        # 为了演示简洁，我们这里采取“保留最后两条，并更新摘要”的策略。
        return {"summary": summary_response.content, "messages": [RemoveMessage(id=m.id) for m in state["messages"][:-2] if m.id]}
    
    return {"summary": state.get("summary", ""), "messages": []}

# 4. 构建图
workflow = StateGraph(SummaryState)

workflow.add_node("agent", call_model)
workflow.add_node("summarizer", summarize_conversation)

workflow.set_entry_point("agent")
workflow.add_edge("agent", "summarizer")
workflow.add_edge("summarizer", END)

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# 5. 测试脚本
async def test_summary_memory():
    config = {"configurable": {"thread_id": "summary-test-1"}}
    
    # 模拟一串长对话
    conversation = [
        "你好，我是一名 Python 开发者。",
        "我最近在学习 LangGraph。",
        "我也对 Rust 感兴趣。",
        "我喜欢在深夜写代码。",
        "我通常使用 VS Code 配合 Vim 插件。",
        "我也很关注 AI 的伦理问题。",
        "好了，现在请告诉我，你对我了解多少？"
    ]
    
    for i, text in enumerate(conversation):
        print(f"\n👤 用户: {text}")
        input_data = {"messages": [HumanMessage(content=text)]}
        async for event in app.astream(input_data, config=config):
            for key, value in event.items():
                if key == "agent":
                    print(f"🤖 助手: {value['messages'][-1].content}")
                elif key == "summarizer" and "summary" in value:
                    print(f"✨ [摘要更新]: {value['summary'][:50]}...")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_summary_memory())
