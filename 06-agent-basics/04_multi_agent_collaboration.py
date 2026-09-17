import os
import operator
from typing import Annotated, TypedDict, List
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END

# 1. 加载配置
load_dotenv()

# --- 共享工具：RAG 检索 ---
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = Chroma(embedding_function=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

@tool
def research_codebase(query: str) -> str:
    """搜索代码库以获取技术细节。"""
    docs = retriever.invoke(query)
    return "\n\n".join([d.page_content for d in docs])

# 2. 定义状态
class MultiAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    research_notes: str  # 存储研究员的发现
    final_report: str    # 存储作家的最终稿

# 3. 定义节点逻辑

def researcher_node(state: MultiAgentState):
    """研究员节点：负责查资料。"""
    print("🕵️ [研究员]: 正在深入调查代码库...")
    
    # 构造研究员的指令
    system_msg = SystemMessage(content=(
        "你是一名资深技术研究员。你的任务是使用工具查找代码库的细节。"
        "请列出你的核心发现，不要进行过多的文学润色，只给事实。"
    ))
    
    model = ChatOpenAI(model_name="deepseek-chat", temperature=0).bind_tools([research_codebase])
    
    # 这里为了演示简单，我们假设研究员只执行一次检索
    # 在复杂的系统中，研究员也可以是一个带循环的子图
    last_user_msg = state["messages"][-1].content
    response = model.invoke([system_msg, HumanMessage(content=f"请研究以下课题: {last_user_msg}")])
    
    # 如果模型决定调用工具
    if response.tool_calls:
        tool_call = response.tool_calls[0]
        result = research_codebase.invoke(tool_call["args"])
        return {"research_notes": result, "messages": [response]}
    
    return {"research_notes": response.content, "messages": [response]}

def writer_node(state: MultiAgentState):
    """作家节点：负责整理成文。"""
    print("✍️ [作家]: 正在将研究笔记转化为正式报告...")
    
    system_msg = SystemMessage(content=(
        "你是一名专业的技术作家。你的任务是将研究员提供的原始笔记转化为一份结构清晰、语言优美的中文技术简报。"
        "你的回复应该直接是报告内容。"
    ))
    
    model = ChatOpenAI(model_name="deepseek-chat", temperature=0.7)
    
    prompt = f"研究员的原始笔记如下：\n{state['research_notes']}\n\n请以此编写报告。"
    response = model.invoke([system_msg, HumanMessage(content=prompt)])
    
    return {"final_report": response.content, "messages": [response]}

# 4. 构建图
workflow = StateGraph(MultiAgentState)

# 添加节点
workflow.add_node("researcher", researcher_node)
workflow.add_node("writer", writer_node)

# 设置流程：用户 -> 研究员 -> 作家 -> 结束
workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", END)

app = workflow.compile()

# 5. 运行测试
async def main():
    print("=== 多 Agent 协作：技术报告生成中 ===\n")
    
    query = "请总结一下这个项目中关于 MCP 的实现方式和核心代码位置。"
    inputs = {"messages": [HumanMessage(content=query)]}
    
    async for output in app.astream(inputs):
        for key, value in output.items():
            print(f"--- 节点 '{key}' 任务完成 ---")
            if key == "writer":
                print(f"\n✨ 最终技术报告 ✨\n")
                print(value["final_report"])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
