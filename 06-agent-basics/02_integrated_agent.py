import os
import sys
import asyncio
import operator
from typing import Annotated, TypedDict, Union
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# MCP 相关导入
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 1. 加载配置
load_dotenv()

# --- 工具定义 A: RAG 检索工具 ---
# 预先构建 RAG 向量库 (为了演示性能，我们在启动时构建)
print("正在初始化 RAG 向量库...")
rag_file = "04-rag/ai_learning_guide.txt"
loader = TextLoader(rag_file, encoding="utf-8")
docs = loader.load()
text_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=20)
splits = text_splitter.split_documents(docs)
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)
retriever = vectorstore.as_retriever()

@tool
def search_ai_guide(query: str) -> str:
    """在《AI 学习指南》文档中搜索相关信息。适用于回答关于 RAG, MCP, Agent 等概念的问题。"""
    print(f"--- [工具]: 执行 RAG 检索 -> '{query}' ---")
    results = retriever.invoke(query)
    context = "\n".join([doc.page_content for doc in results])
    return f"从指南中找到的相关信息:\n{context}"

# --- 工具定义 B: MCP 天气工具 ---
@tool
async def get_weather_via_mcp(city: str) -> str:
    """通过 MCP 服务器获取指定城市的实时天气。"""
    print(f"--- [工具]: 执行 MCP 调用 -> 查询 {city} 天气 ---")
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["03-mcp/01_simple_server.py"],
        env=os.environ.copy()
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_weather", arguments={"city": city})
            return result.content[0].text

# 2. 整合工具
tools = [search_ai_guide, get_weather_via_mcp]
tool_node = ToolNode(tools)

# 3. 定义 LangGraph 状态与逻辑
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]

def call_model(state: AgentState):
    # 使用非思考模式模型，避免推理内容丢失报错
    model = ChatOpenAI(model_name="deepseek-chat", temperature=0).bind_tools(tools)
    response = model.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

# 4. 构建图
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")
app = workflow.compile()

# 5. 运行综合测试
async def main():
    print("\n" + "="*50)
    print("🚀 集成 Agent 已启动！它现在可以同时处理 MCP 和 RAG 任务。")
    print("="*50 + "\n")

    user_query = "帮我查一下上海的天气，并告诉我 RAG 的核心组件有哪些？"
    print(f"用户问题: {user_query}\n")

    inputs = {"messages": [HumanMessage(content=user_query)]}
    
    async for output in app.astream(inputs):
        for key, value in output.items():
            if key == "agent":
                msg = value["messages"][-1]
                if msg.tool_calls:
                    print(f"🤖 大脑: 我决定调用工具 {[t['name'] for t in msg.tool_calls]}")
                else:
                    print(f"🤖 大脑: 我已汇总所有信息，准备回答。")
                    print(f"\n最终回复:\n{msg.content}")
            elif key == "tools":
                print(f"🛠️ 工具: 任务已执行。")

if __name__ == "__main__":
    asyncio.run(main())
