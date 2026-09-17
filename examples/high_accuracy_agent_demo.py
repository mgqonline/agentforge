import os
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# 1. 定义 Agent 的状态 (State)
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    draft_answer: str
    is_correct: bool
    iterations: int

# 2. 节点：草稿生成器 (Generator)
def generate_draft(state: AgentState):
    """根据问题和已有信息生成初稿"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1) # 低温度保证稳定性
    messages = state["messages"]
    
    # 模拟 RAG 检索结果或工具调用结果（此处为了示例简化）
    context = "已知事实：天空是蓝色的，因为瑞利散射。"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个极其严谨的 AI 助手。请基于以下上下文回答问题：\n{context}"),
        ("human", "{question}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"context": context, "question": messages[-1].content})
    
    return {"draft_answer": response.content, "iterations": state.get("iterations", 0) + 1}

# 3. 节点：自我校验器 (Reflector / Evaluator)
def evaluate_draft(state: AgentState):
    """评估草稿的准确性，这是达到 95% 准确率的核心环节"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    eval_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个严格的审核员。请判断以下答案是否完全正确、没有幻觉，并且直接回答了用户的问题。只回答 'YES' 或 'NO'。"),
        ("human", "问题: {question}\n答案: {draft}")
    ])
    
    chain = eval_prompt | llm
    result = chain.invoke({"question": state["messages"][-1].content, "draft": state["draft_answer"]})
    
    is_correct = "YES" in result.content.upper()
    return {"is_correct": is_correct}

# 4. 路由：决定是输出还是重写 (Conditional Edge)
def should_continue(state: AgentState):
    if state["is_correct"] or state["iterations"] >= 3:
        # 如果正确，或者重试次数达到上限，则结束
        return "end"
    else:
        # 否则重新生成
        return "rewrite"

# 5. 节点：组装最终结果
def finalize_response(state: AgentState):
    return {"messages": [AIMessage(content=state["draft_answer"])]}

# 构建 LangGraph 状态机
def build_high_accuracy_agent():
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("generate", generate_draft)
    workflow.add_node("evaluate", evaluate_draft)
    workflow.add_node("finalize", finalize_response)
    
    # 定义边与控制流
    workflow.set_entry_point("generate")
    workflow.add_edge("generate", "evaluate")
    workflow.add_conditional_edges(
        "evaluate",
        should_continue,
        {
            "end": "finalize",
            "rewrite": "generate"
        }
    )
    workflow.add_edge("finalize", END)
    
    return workflow.compile()

if __name__ == "__main__":
    # 实验运行（需配置 OPENAI_API_KEY）
    # os.environ["OPENAI_API_KEY"] = "your-api-key"
    print("Agent 初始化完成。核心机制：生成草稿 -> 内部评估 -> 修正重写")
    
    # app = build_high_accuracy_agent()
    # result = app.invoke({"messages": [HumanMessage(content="天空为什么是蓝色的？")], "iterations": 0})
    # print("最终高准确率回答:", result["messages"][-1].content)
