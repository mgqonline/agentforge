"""
标准生产级 Agent 骨架模板 (LangGraph)
特性：DeepSeek 适配、状态机循环、自我反思节点
"""
import os
import operator
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# 自动加载根目录的环境变量
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '.env')
load_dotenv(dotenv_path)

# 1. 定义状态字典
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    draft_answer: str
    is_correct: bool
    iterations: int

# 2. 获取标准化适配的大模型
def get_llm(temperature=0):
    return ChatOpenAI(
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1",
        temperature=temperature
    )

# 3. 核心节点：初稿生成器
def generate_node(state: AgentState):
    """初稿生成节点，后续可在此处嵌入 RAG 或外部工具 API"""
    llm = get_llm(temperature=0.7) # 生成时允许一定创造性
    messages = state["messages"]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个专业的高级智能助理。请详细回答用户的问题。"),
        ("human", "{question}")
    ])
    
    response = (prompt | llm).invoke({"question": messages[-1].content})
    return {"draft_answer": response.content, "iterations": state.get("iterations", 0) + 1}

# 4. 核心节点：反思评估器
def evaluate_node(state: AgentState):
    """反思与质检节点，确保回答的准确率"""
    llm = get_llm(temperature=0) # 评估时必须严谨死板
    eval_prompt = ChatPromptTemplate.from_messages([
        ("system", "作为严格的审核员，请判断以下答案是否完全准确、没有幻觉，并且真正解答了用户的问题。只回答 'YES' 或 'NO'。"),
        ("human", "原始问题: {question}\n草稿答案: {draft}")
    ])
    
    result = (eval_prompt | llm).invoke({
        "question": state["messages"][-1].content, 
        "draft": state["draft_answer"]
    })
    
    # 简单的判定逻辑
    is_correct = "YES" in result.content.upper()
    return {"is_correct": is_correct}

# 5. 核心路由：决定流转方向
def router_edge(state: AgentState):
    # 如果审核通过，或者已经重试超过 3 次（防止死循环）
    if state["is_correct"] or state["iterations"] >= 3:
        return "end"
    return "rewrite"

# 6. 核心节点：输出组装
def finalize_node(state: AgentState):
    return {"messages": [AIMessage(content=state["draft_answer"])]}

# 构建标准工作流
def build_standard_agent():
    workflow = StateGraph(AgentState)
    
    # 注册节点
    workflow.add_node("generate", generate_node)
    workflow.add_node("evaluate", evaluate_node)
    workflow.add_node("finalize", finalize_node)
    
    # 注册边
    workflow.set_entry_point("generate")
    workflow.add_edge("generate", "evaluate")
    workflow.add_conditional_edges(
        "evaluate", 
        router_edge, 
        {"end": "finalize", "rewrite": "generate"}
    )
    workflow.add_edge("finalize", END)
    
    return workflow.compile()

if __name__ == "__main__":
    print("🚀 正在初始化标准高准度 Agent (LangGraph + DeepSeek)...")
    app = build_standard_agent()
    
    test_question = "如何用 Python 翻转一个字符串？"
    print(f"👨‍💻 用户提问: {test_question}\n")
    
    result = app.invoke({
        "messages": [HumanMessage(content=test_question)], 
        "iterations": 0
    })
    
    print("🤖 Agent 最终回答:\n", result["messages"][-1].content)
    print(f"\n[追踪] 经过了 {result['iterations']} 次内部生成与反思循环。")
