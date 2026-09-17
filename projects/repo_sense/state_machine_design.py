import os
import asyncio
import operator
from enum import Enum
from typing import Annotated, TypedDict, List, Optional
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# 1. 定义 Agent 的执行状态（状态机）
class ExecutionPhase(Enum):
    PLANNING = "planning"      # 规划阶段：分析需求，拆解任务
    RESEARCHING = "researching" # 研究阶段：查阅代码，定位逻辑
    ACTING = "acting"          # 执行阶段：编写代码
    VERIFYING = "verifying"    # 验证阶段：运行测试，确认结果
    FINISHED = "finished"      # 完成阶段

# 2. 增强的 State 定义
class AdvancedAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    phase: ExecutionPhase       # 当前状态机所处的阶段
    plan: Optional[str]        # 存储生成的执行计划
    errors: List[str]          # 存储执行过程中的错误

# 3. 工具集定义（沿用 v2.0）
# ... (此处省略 tool 定义以保持演示简洁，实际会引用 assistant.py 中的工具)

# 4. 节点逻辑：状态机驱动

def planner_node(state: AdvancedAgentState):
    """规划节点：根据用户需求生成计划。"""
    print(f"🎯 [状态: {ExecutionPhase.PLANNING.value}] 正在规划任务...")
    model = ChatOpenAI(model_name="deepseek-chat", temperature=0)
    prompt = f"请根据用户需求，拆解出具体的执行步骤：\n{state['messages'][-1].content}"
    response = model.invoke([SystemMessage(content="你是一个架构师，负责拆解任务。"), HumanMessage(content=prompt)])
    return {"plan": response.content, "phase": ExecutionPhase.RESEARCHING, "messages": [AIMessage(content=f"已生成计划：\n{response.content}")]}

def researcher_node(state: AdvancedAgentState):
    """研究节点：利用 RAG 定位代码。"""
    print(f"🔍 [状态: {ExecutionPhase.RESEARCHING.value}] 正在调研代码库...")
    # 这里可以添加特定的 RAG 逻辑
    return {"phase": ExecutionPhase.ACTING}

def actor_node(state: AdvancedAgentState):
    """执行节点：实际修改代码。"""
    print(f"💾 [状态: {ExecutionPhase.ACTING.value}] 正在执行修改...")
    return {"phase": ExecutionPhase.VERIFYING}

def verifier_node(state: AdvancedAgentState):
    """验证节点：运行测试。"""
    print(f"✅ [状态: {ExecutionPhase.VERIFYING.value}] 正在验证结果...")
    # 如果验证失败，可以跳回 ACTING 阶段
    return {"phase": ExecutionPhase.FINISHED}

# 5. 构建状态机图
def build_state_machine_agent():
    workflow = StateGraph(AdvancedAgentState)
    
    workflow.add_node("planner", planner_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("actor", actor_node)
    workflow.add_node("verifier", verifier_node)
    
    workflow.set_entry_point("planner")
    
    # 状态机流转逻辑
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "actor")
    workflow.add_edge("actor", "verifier")
    workflow.add_edge("verifier", END)
    
    return workflow.compile()

# 此处仅为设计演示，展示状态机如何融入 LangGraph
if __name__ == "__main__":
    print("--- Agent 状态机设计原型已加载 ---")
    print("这种设计允许 Agent 在处理复杂任务时，拥有明确的阶段感知和容错重试机制。")
