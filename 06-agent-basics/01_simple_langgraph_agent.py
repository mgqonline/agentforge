import os
import operator
from typing import Annotated, TypedDict, Union
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# 1. 加载环境变量
load_dotenv()

# 2. 定义工具 (Tools)
@tool
def add(a: int, b: int) -> int:
    """计算两个数字的和。"""
    print(f"--- [工具调用]: 计算 {a} + {b} ---")
    return a + b

# 将工具放入列表
tools = [add]
# 定义 ToolNode（这是 LangGraph 提供的一个预置节点，专门用于执行工具）
tool_node = ToolNode(tools)

# 3. 定义状态 (State)
# State 是在图的各个节点之间传递的数据结构
class AgentState(TypedDict):
    # messages 列表存储所有的对话历史
    # Annotated[..., operator.add] 告诉 LangGraph：新的消息应该追加到列表中，而不是覆盖它
    messages: Annotated[list[BaseMessage], operator.add]

# 4. 定义节点逻辑 (Nodes)
def call_model(state: AgentState):
    """大模型节点：负责决策。"""
    print("--- [节点]: 大模型决策中... ---")
    # 使用 deepseek-chat (通常是非思考模式) 避免推理内容传递问题
    model = ChatOpenAI(model_name="deepseek-chat", temperature=0).bind_tools(tools)
    response = model.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: AgentState):
    """条件边逻辑：判断是继续调用工具还是结束。"""
    last_message = state["messages"][-1]
    # 如果模型返回了 tool_calls，说明它想用工具
    if last_message.tool_calls:
        print("--- [边]: 发现工具调用请求，转向工具节点 ---")
        return "tools"
    # 否则，结束任务
    print("--- [边]: 任务完成，准备输出 ---")
    return END

# 5. 构建图 (Build the Graph)
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# 设置入口
workflow.set_entry_point("agent")

# 添加条件边 (Conditional Edges)
# 从 agent 节点出发，根据 should_continue 的结果决定去 tools 还是 END
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        END: END
    }
)

# 添加普通边
# 工具执行完后，必须回到 agent 节点让模型看看结果
workflow.add_edge("tools", "agent")

# 编译图
app = workflow.compile()

# 6. 运行测试
def run_agent_test():
    print("=== 开始运行 LangGraph Agent 测试 ===\n")
    inputs = {"messages": [HumanMessage(content="请计算 123 加 456 等于多少？")]}

    final_response = ""
    # 使用 stream 模式查看中间过程
    for output in app.stream(inputs):
        for key, value in output.items():
            print(f"节点 '{key}' 已完成。")
            if key == "agent":
                final_response = value["messages"][-1].content

    # 打印最终结果
    print("\n" + "="*30)
    print(f"Agent 的最终回答:\n{final_response}")

if __name__ == "__main__":
    run_agent_test()

